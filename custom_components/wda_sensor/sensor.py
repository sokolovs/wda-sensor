import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

from . import get_config_value
from .calc import calc_target
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Set up WDASensor from a config entry. """
    async_add_entities([WDASensor(hass, config_entry)], update_before_add=True)
    async_add_entities([WDACurveSensor(hass, config_entry)], update_before_add=True)


class WDASensor(SensorEntity):
    """ Weather Dependent Automation Sensor for boiler automation. """

    # Defaults
    min_coolant_temp = DEFAULT_MIN_COOLANT_TEMP
    max_coolant_temp = DEFAULT_MAX_COOLANT_TEMP
    target_room_temp = DEFAULT_TARGET_ROOM_TEMP
    heating_curve = DEFAULT_HEATING_CURVE
    humidity_threshold = DEFAULT_HUMIDITY_THRESHOLD

    def __init__(self, hass, config_entry):
        """ Initialize the sensor. """
        self._hass = hass
        self._config = config_entry

        self._attr_name = self._config.data.get("name", "Target Coolant Temperature")
        self._attr_unique_id = f"wda_sensor_{config_entry.entry_id}"
        self._attr_available = False
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:home-thermometer"

    async def async_added_to_hass(self):
        """ Subscribe to sensors and configuration update. """
        # Subscribe to update configuration vie OptionsFlow
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass,
                SENSOR_UPDATE_SIGNAL,
                self.handle_options_update
            )
        )

        # Subscribe to update sensors
        sensor_entities = [
            self.get_config("wda_outside_temp"),
            self.get_config("wda_inside_temp"),
            self.get_config("wda_wind_speed"),
            self.get_config("wda_outside_humidity"),
        ]

        for entity_id in sensor_entities:
            if entity_id:
                self.async_on_remove(
                    async_track_state_change_event(
                        self._hass, entity_id, self.handle_sensor_update
                    )
                )

    async def handle_sensor_update(self, event):
        """ Handle options update. """
        _LOGGER.warning(
            "Sensor state change detected: %s, updating sensor: %s",
            (event.data.get("entity_id"), self.name))
        await self.async_update()
        self.async_write_ha_state()

    async def handle_options_update(self):
        """ Handle sensors update. """
        _LOGGER.warning("Configuration updated, updating sensor: %s", self.name)
        await self.async_update()
        self.async_write_ha_state()

    async def async_get_sensor_value(self, entity_id, default=None):
        if not entity_id:
            return default

        state = self._hass.states.get(entity_id)
        if state is None or state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            return default

        try:
            return float(state.state)
        except ValueError:
            _LOGGER.warning("Cannot convert state of %s to float: %s", entity_id, state.state)
            return default

    def get_config(self, key, default=None):
        return get_config_value(self._config, key, default)

    async def async_update(self):
        """ Fetch new state data for the sensor. """
        try:
            # Get data from settings
            min_coolant_temp = int(
                self.get_config("wda_min_coolant_temp", self.min_coolant_temp))
            max_coolant_temp = int(
                self.get_config("wda_max_coolant_temp", self.max_coolant_temp))
            target_room_temp = float(
                self.get_config("wda_target_room_temp", self.target_room_temp))
            heating_curve = int(
                self.get_config("wda_heating_curve", self.heating_curve))

            # Correction settings
            room_temp_correction = float(self.get_config("wda_room_temp_correction", 0))
            wind_correction = float(self.get_config("wda_wind_correction", 0))
            humidity_correction = float(self.get_config("wda_humidity_correction", 0))

            # Exponent range
            exp_min = float(self.get_config("wda_exp_min", DEFAULT_EXP_MIN))
            exp_max = float(self.get_config("wda_exp_max", DEFAULT_EXP_MAX))

            # Get data from sensors
            outside_temp = await self.async_get_sensor_value(self.get_config("wda_outside_temp"))
            if outside_temp is None:
                self._attr_available = False
                self._attr_native_value = None
                _LOGGER.warning(
                    "Failed to update WDASensor: outside temperature sensor is not configured")
                return

            outside_temp = float(outside_temp)
            wind_speed = await self.async_get_sensor_value(
                self.get_config("wda_wind_speed"))
            outside_humidity = await self.async_get_sensor_value(
                self.get_config("wda_outside_humidity"))
            inside_temp = await self.async_get_sensor_value(
                self.get_config("wda_inside_temp"))

            # Base value
            target_heat_temp = calc_target(outside_temp, heating_curve, exp_min, exp_max)

            # Room Temperature Correction
            if room_temp_correction and inside_temp is not None:
                correction_value = (target_room_temp - float(inside_temp)) * room_temp_correction
                target_heat_temp = target_heat_temp + correction_value

            # Wind Speed Correction
            if wind_correction and wind_speed is not None:
                correction_value = float(wind_speed) * wind_correction
                target_heat_temp = target_heat_temp + correction_value

            # Humidity Correction
            if humidity_correction and outside_humidity is not None:
                correction_value = (
                    max(0, (float(outside_humidity) - self.humidity_threshold) *
                        humidity_correction)
                )
                target_heat_temp = target_heat_temp + correction_value

            # Going beyond the limits of values
            if target_heat_temp < min_coolant_temp:
                target_heat_temp = min_coolant_temp
            if target_heat_temp > max_coolant_temp:
                target_heat_temp = max_coolant_temp

            self._attr_available = True
            self._attr_native_value = int(round(target_heat_temp))
        except Exception as e:
            self._attr_available = False
            self._attr_native_value = None
            _LOGGER.error("Failed to update WDASensor: %s", e)


class WDACurveSensor(Entity):
    """ Sensor for calculating heating curve graph data. """

    def __init__(self, hass, config_entry):
        """Initialize the sensor."""
        self._hass = hass
        self._config = config_entry

        self._attr_name = self._config.data.get("name", "Heating Curve Graph Data")
        self._attr_unique_id = f"wda_sensor_curve_{config_entry.entry_id}"
        self._attr_available = True
        self._attr_icon = "mdi:chart-bell-curve-cumulative"

    def get_config(self, key, default=None):
        return get_config_value(self._config, key, default)

    @property
    def extra_state_attributes(self):
        """ Return the state attributes. """
        heating_curve = int(
            self.get_config("wda_heating_curve", DEFAULT_HEATING_CURVE))
        exp_min = float(self.get_config("wda_exp_min", DEFAULT_EXP_MIN))
        exp_max = float(self.get_config("wda_exp_max", DEFAULT_EXP_MAX))
        graph_data = self.generate_graph_data(heating_curve, exp_min, exp_max)
        return {
            "heating_curve": heating_curve,
            "graph_data_map": graph_data,
            "graph_data_items": list(graph_data.items())
        }

    def generate_graph_data(self, heating_curve, exp_min, exp_max):
        # Range of outside temperature
        outside_temps = list(range(GRAPH_MIN_OUTSIDE_TEMP, GRAPH_MAX_OUTSIDE_TEMP + 1))
        return {
            temp: round(calc_target(temp, heating_curve, exp_min, exp_max), 1)
            for temp in outside_temps
        }
