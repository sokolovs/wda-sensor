import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, UnitOfTemperature
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .helpers import calc_target, get_config_value, update
from .const import *  # noqa F403

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Set up WDASensor from a config entry. """
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data["coordinator"]

    async_add_entities([
            WDASensor(hass, config_entry),
            WDAPeriodicSensor(hass, config_entry, coordinator),
            WDACurveSensor(hass, config_entry)
        ], update_before_add=True)


class WDASensor(SensorEntity):
    """ Weather Dependent Automation Sensor for boiler automation. """

    def __init__(self, hass, config_entry):
        """ Initialize the sensor. """
        self._hass = hass
        self._config = config_entry

        self._attr_has_entity_name = True
        self._attr_translation_key = "wda_sensor"
        self._attr_unique_id = f"wda_sensor_{config_entry.entry_id}"
        self._attr_available = False
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:home-thermometer"

    async def async_added_to_hass(self):
        """ Subscribe to sensors and configuration update. """
        await super().async_added_to_hass()

        # Subscribe to update configuration via OptionsFlow
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass,
                SENSOR_UPDATE_SIGNAL,
                self.handle_options_update
            )
        )

        # Subscribe to update sensors
        sensor_entities = [
            get_config_value(self._config, "wda_outside_temp"),
            get_config_value(self._config, "wda_inside_temp"),
            get_config_value(self._config, "wda_wind_speed"),
            get_config_value(self._config, "wda_outside_humidity"),
        ]

        for entity_id in sensor_entities:
            if entity_id:
                self.async_on_remove(
                    async_track_state_change_event(
                        self._hass, entity_id, self.handle_sensor_update
                    )
                )

    async def handle_sensor_update(self, event):
        """ Handle sensors update. """
        _LOGGER.info(
            f"Sensor state change detected: {event.data.get('entity_id')}, "
            f"updating sensor: {self.name}")
        await self.async_update()
        self.async_write_ha_state()

    async def handle_options_update(self):
        """ Handle options update. """
        _LOGGER.info(f"Configuration updated, updating sensor: {self.name}")
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self):
        """ Fetch new state data for the sensor. """
        try:
            result = await update(self._hass, self._config)
            if result is None:
                self._attr_available = False
                self._attr_native_value = None
                _LOGGER.warning(
                    f"Failed to update {self.name}: "
                    f"outside temperature sensor is not configured now")
                return

            self._attr_available = True
            self._attr_native_value = result
        except Exception as e:
            self._attr_available = False
            self._attr_native_value = None
            _LOGGER.error(f"Failed to update {self.name}: {e}")


class WDAPeriodicSensor(CoordinatorEntity, SensorEntity):
    """ Periodically updated sensor """

    def __init__(self, hass, config_entry, coordinator):
        self._hass = hass
        self._config = config_entry
        super().__init__(coordinator)

        self._attr_has_entity_name = True
        self._attr_translation_key = "wda_periodic_sensor"
        self._attr_unique_id = f"wda_periodic_sensor_{config_entry.entry_id}"
        self._attr_available = False
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:clock"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Subscribe to update configuration via OptionsFlow
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass,
                SENSOR_UPDATE_SIGNAL,
                self.handle_options_update
            )
        )

        # Subscribe to HA started
        self.async_on_remove(
            self._hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED,
                self.handle_ha_started
            )
        )

    async def handle_options_update(self):
        """ Handle options update. """
        _LOGGER.info(f"Configuration updated, updating sensor: {self.name}")

        # We have new update interval for coordinator
        update_interval = timedelta(seconds=get_config_value(
            self._config, "wda_update_interval", DEFAULT_UPDATE_INTERVAL))
        if self.coordinator.update_interval != update_interval:
            self.coordinator.update_interval = update_interval

        # Refresh data
        await self.coordinator.async_refresh()

    async def handle_ha_started(self, event):
         _LOGGER.info(f"HA started, updating sensor: {self.name}")
         await self.coordinator.async_refresh()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if isinstance(self.coordinator.data, int):
            return self.coordinator.data


class WDACurveSensor(SensorEntity):
    """ Sensor for calculating heating curve graph data. """

    def __init__(self, hass, config_entry):
        """Initialize the sensor."""
        self._hass = hass
        self._config = config_entry

        self._attr_has_entity_name = True
        self._attr_translation_key = "wda_sensor_graph_data"
        self._attr_unique_id = f"wda_sensor_curve_{config_entry.entry_id}"
        self._attr_available = True
        self._attr_icon = "mdi:chart-bell-curve-cumulative"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return int(
            get_config_value(self._config, "wda_heating_curve", DEFAULT_HEATING_CURVE))

    @property
    def extra_state_attributes(self):
        """ Return the state attributes. """
        heating_curve = int(
            get_config_value(self._config, "wda_heating_curve", DEFAULT_HEATING_CURVE))
        exp_min = float(get_config_value(self._config, "wda_exp_min", DEFAULT_EXP_MIN))
        exp_max = float(get_config_value(self._config, "wda_exp_max", DEFAULT_EXP_MAX))
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
