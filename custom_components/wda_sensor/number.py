import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity


from .helpers import get_config_value
from .const import *  # noqa F403

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Set up number entities  """
    async_add_entities([
        WDANumber(hass, config_entry, OPT_WDA_HEATING_CURVE, {
            "min": MIN_HEATING_CURVE,
            "max": MAX_HEATING_CURVE,
            "step": HEATING_CURVE_STEP,
            "category": EntityCategory.CONFIG,
            "icon": "mdi:chart-ppf",
            "coerce": int
        }),
        WDANumber(hass, config_entry, OPT_WDA_TARGET_ROOM_TEMP, {
            "min": MIN_TARGET_ROOT_TEMP,
            "max": MAX_TARGET_ROOT_TEMP,
            "step": TARGET_ROOT_TEMP_STEP,
            "unit": UnitOfTemperature.CELSIUS,
            "category": EntityCategory.CONFIG,
            "device_class": NumberDeviceClass.TEMPERATURE,
            "icon": "mdi:temperature-celsius",
            "coerce": float
        })
    ])


class WDANumber(NumberEntity, RestoreEntity):
    """ Number entity associated with a configuration parameter """

    def __init__(self, hass, config, name, entity_config):
        self._hass = hass
        self._config = config
        self._name = name
        self._entity_config = entity_config

        self._attr_mode = NumberMode.BOX
        self._attr_has_entity_name = True
        self._attr_translation_key = name
        self._attr_unique_id = f"{self._attr_translation_key}_{config.entry_id}"

        self._coerce = entity_config.get("coerce")
        self._icon = entity_config.get("icon")
        self._attr_native_min_value = entity_config.get("min")
        self._attr_native_max_value = entity_config.get("max")
        self._attr_native_step = entity_config.get("step")
        self._attr_native_unit_of_measurement = entity_config.get("unit")
        self._attr_device_class = entity_config.get("device_class")
        self._attr_entity_category = entity_config.get("category")
        self._attr_native_value = get_config_value(config, name)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()

        # Restore last state
        if last_state is not None:
            value = float(last_state.state)
            if callable(self._coerce):
                self._attr_native_value = self._coerce(value)
            else:
                self._attr_native_value = value

    async def async_set_native_value(self, value: float) -> None:
        """ Set value """
        if callable(self._coerce):
            self._attr_native_value = self._coerce(value)
        else:
            self._attr_native_value = value

        self.async_write_ha_state()
        _LOGGER.info(f"Successfully set '{self._attr_translation_key}' to '{value}'")

    @property
    def assumed_state(self) -> bool:
        return True

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def icon(self):
        return self._icon
