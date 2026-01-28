import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .helpers import calc_target, get_config_value, get_entity_id, get_sensor_value_by_uniq, update
from .const import *  # noqa F403

_LOGGER = logging.getLogger(__name__)
_SUBSCRIBE_ATTEMPTS_DELAY = 5


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Set up WDASensor from a config entry. """
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data["coordinator"]

    async_add_entities([
            WDASensor(hass, config_entry),
            WDAPeriodicSensor(hass, config_entry, coordinator),
            WDACurveSensor(hass, config_entry)
        ], update_before_add=True)


class WDASensorMixin:
    """ Sensor mixin  """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def subscribe_with_retry(
            self,
            unique_id,
            platform=Platform.NUMBER,
            attempt=1,
            max_attempts=10):
        """ Subscribe to sensor updates with retry """
        if not (getattr(self, "handle_sensor_update", False) and callable(self.handle_sensor_update)):
            return

        entity_id = await get_entity_id(
            hass=self._hass,
            platform=platform,
            unique_id=unique_id
        )

        if entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self._hass, entity_id, self.handle_sensor_update))
            _LOGGER.debug(f"Subscribe to '{entity_id}' for '{self._attr_translation_key}': SUCCESS")
        else:
            if attempt < max_attempts:
                _LOGGER.debug(
                    f"Subscription attempt '{attempt}' to '{unique_id}' "
                    f"failed, try again in 5 seconds...")

                async def _delayed_subscribe(_):
                    await self.subscribe_with_retry(
                        unique_id,
                        platform,
                        attempt + 1,
                        max_attempts)

                async_call_later(
                    hass=self._hass,
                    delay=_SUBSCRIBE_ATTEMPTS_DELAY,
                    action=_delayed_subscribe
                )
            else:
                _LOGGER.error(
                    f"Unable to find entity '{unique_id}' "
                    f"to subscribe to after '{max_attempts}' attempts")


class WDASensor(WDASensorMixin, SensorEntity):
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

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)}
        )

    async def async_added_to_hass(self):
        """ Subscribe to sensors and configuration update. """
        await super().async_added_to_hass()

        # Subscribe to update configuration via OptionsFlow
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass,
                f"{SENSOR_UPDATE_SIGNAL}_{self._config.entry_id}",
                self.handle_options_update
            )
        )

        # Subscribe to update weather sensors
        subscribe_to_entities = [
            get_config_value(self._config, OPT_WDA_OUTSIDE_TEMP),
            get_config_value(self._config, OPT_WDA_INSIDE_TEMP),
            get_config_value(self._config, OPT_WDA_WIND_SPEED),
            get_config_value(self._config, OPT_WDA_OUTSIDE_HUMIDITY),
        ]

        for entity_id in subscribe_to_entities:
            if entity_id:
                self.async_on_remove(
                    async_track_state_change_event(
                        self._hass, entity_id, self.handle_sensor_update
                    )
                )

        # Subscribe to number inputs
        await self.subscribe_with_retry(
            unique_id=f"{OPT_WDA_TARGET_ROOM_TEMP}_{self._config.entry_id}"
        )
        await self.subscribe_with_retry(
            unique_id=f"{OPT_WDA_HEATING_CURVE}_{self._config.entry_id}"
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
                _LOGGER.debug(
                    f"Failed to update {self.name}: "
                    f"some sensors is not available now")
                return

            self._attr_available = True
            self._attr_native_value = result
        except Exception as e:
            self._attr_available = False
            self._attr_native_value = None
            _LOGGER.error(f"Failed to update {self.name}: {e}")


class WDAPeriodicSensor(WDASensorMixin, CoordinatorEntity, SensorEntity):
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

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)}
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Subscribe to update configuration via OptionsFlow
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass,
                f"{SENSOR_UPDATE_SIGNAL}_{self._config.entry_id}",
                self.handle_options_update
            )
        )

        # Subscribe to HA started
        self._hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            self.handle_ha_started
        )

        # Subscribe to number inputs
        await self.subscribe_with_retry(
            unique_id=f"{OPT_WDA_TARGET_ROOM_TEMP}_{self._config.entry_id}"
        )
        await self.subscribe_with_retry(
            unique_id=f"{OPT_WDA_HEATING_CURVE}_{self._config.entry_id}"
        )

    async def handle_sensor_update(self, event):
        """ Handle sensors update. """
        _LOGGER.info(
            f"Sensor state change detected: {event.data.get('entity_id')}, "
            f"updating sensor: {self.name}")

        # Refresh data
        await self.coordinator.async_refresh()

    async def handle_options_update(self):
        """ Handle options update. """
        _LOGGER.info(f"Configuration updated, updating sensor: {self.name}")

        # We have new update interval for coordinator
        update_interval = timedelta(seconds=int(get_config_value(
            self._config, OPT_WDA_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)))
        if self.coordinator.update_interval != update_interval:
            self.coordinator.update_interval = update_interval

        # Refresh data
        await self.coordinator.async_refresh()

    async def handle_ha_started(self, event):
        _LOGGER.info(f"HA started, updating sensor: {self.name}")

        # Refresh data
        await self.coordinator.async_refresh()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if isinstance(self.coordinator.data, int):
            return self.coordinator.data


class WDACurveSensor(WDASensorMixin, SensorEntity):
    """ Sensor for calculating heating curve graph data. """

    def __init__(self, hass, config_entry):
        """Initialize the sensor."""
        self._hass = hass
        self._config = config_entry

        self._attr_has_entity_name = True
        self._attr_translation_key = "wda_sensor_graph_data"
        self._attr_unique_id = f"wda_sensor_curve_{config_entry.entry_id}"
        self._attr_available = False
        self._attr_native_value = None
        self._attr_icon = "mdi:chart-bell-curve-cumulative"

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)}
        )

    async def async_added_to_hass(self):
        """ Subscribe to sensors and configuration update. """
        await super().async_added_to_hass()

        # Subscribe to update configuration via OptionsFlow
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass,
                f"{SENSOR_UPDATE_SIGNAL}_{self._config.entry_id}",
                self.handle_options_update
            )
        )

        # Subscribe to number input (heating curve number)
        await self.subscribe_with_retry(
            unique_id=f"{OPT_WDA_HEATING_CURVE}_{self._config.entry_id}")

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
        """ Update sensor value """
        try:
            result = await get_sensor_value_by_uniq(
                hass=self._hass,
                platform=Platform.NUMBER,
                unique_id=f"{OPT_WDA_HEATING_CURVE}_{self._config.entry_id}",
                coerce=int
            )

            if result is None:
                self._attr_available = False
                self._attr_native_value = None
                _LOGGER.debug(
                    f"Failed to update {self.name}: "
                    f"heating curve number is not available now")
                return

            self._attr_available = True
            self._attr_native_value = result
        except Exception as e:
            self._attr_available = False
            self._attr_native_value = None
            _LOGGER.error(f"Failed to update {self.name}: {e}")

    @property
    def extra_state_attributes(self):
        """ Return the state attributes. """
        extra_attrs = {
            "graph_data_map": {},
            "graph_data_items": []
        }

        heating_curve = self.native_value
        if heating_curve is None:
            return extra_attrs

        # Get advanced settings
        adv_config = get_config_value(self._config, SECTION_ADVANCED_SETTINGS, {})

        exp_min = float(adv_config.get(OPT_WDA_EXP_MIN, DEFAULT_EXP_MIN))
        exp_max = float(adv_config.get(OPT_WDA_EXP_MAX, DEFAULT_EXP_MAX))
        graph_data = self.generate_graph_data(heating_curve, exp_min, exp_max)
        return {
            "graph_data_map": graph_data,
            "graph_data_items": list(graph_data.items())
        }

    def generate_graph_data(self, heating_curve, exp_min, exp_max):
        # Graph config
        graph_config = get_config_value(self._config, SECTION_CURVE_GRAPH_SETTINGS, {})
        min_outside_temp = int(graph_config.get(OPT_GRAPH_MIN_OUTSIDE_TEMP, GRAPH_MIN_OUTSIDE_TEMP))
        max_outside_temp = int(graph_config.get(OPT_GRAPH_MAX_OUTSIDE_TEMP, GRAPH_MAX_OUTSIDE_TEMP))

        # Range of outside temperature
        outside_temps = list(range(min_outside_temp, max_outside_temp + 1))
        return {
            temp: round(calc_target(temp, heating_curve, exp_min, exp_max), 1)
            for temp in outside_temps
        }
