""" Weather Dependent Automation Sensor integration. """
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    DEFAULT_EXP_MAX,
    DEFAULT_EXP_MIN,
    DEFAULT_HUMIDITY_CORRECTION,
    DEFAULT_ROOM_TEMP_CORRECTION,
    DEFAULT_WIND_CORRECTION,
    DOMAIN,
    OPT_WDA_EXP_MAX,
    OPT_WDA_EXP_MIN,
    OPT_WDA_HUMIDITY_CORRECTION,
    OPT_NAME,
    OPT_WDA_ROOM_TEMP_CORRECTION,
    OPT_WDA_WIND_CORRECTION,
    SECTION_ADVANCED_SETTINGS
)
from .coordinator import WDAUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """ Set up sensor from a config entry. """
    hass.data.setdefault(DOMAIN, {})

    # Create device
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=config_entry.options.get(OPT_NAME) or config_entry.data.get(OPT_NAME),
        manufacturer="Sergey V. Sokolov",
        model="Weather Driven Heating Control"
    )

    # Create coordinator for periodic updates
    coordinator = WDAUpdateCoordinator(hass, config_entry)
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": coordinator,
        "device_id": device.id,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, [Platform.NUMBER])
    await hass.config_entries.async_forward_entry_setups(config_entry, [Platform.SENSOR])
    await coordinator.async_config_entry_first_refresh()
    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """ Update options for entry that was configured via user interface. """
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """ Unload a config entry. """
    await hass.config_entries.async_unload_platforms(config_entry, [Platform.SENSOR, Platform.NUMBER])
    return True


async def async_migrate_entry(hass, config_entry):
    """ Migrating configuration """

    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version
    )

    # From V1 to V2
    if config_entry.version == 1:
        new_data = new_options = None

        if config_entry.data:
            new_data = {**config_entry.data}
            new_data[SECTION_ADVANCED_SETTINGS] = {}

            new_data[SECTION_ADVANCED_SETTINGS][OPT_WDA_ROOM_TEMP_CORRECTION] = (
                new_data.pop(OPT_WDA_ROOM_TEMP_CORRECTION, DEFAULT_ROOM_TEMP_CORRECTION))

            new_data[SECTION_ADVANCED_SETTINGS][OPT_WDA_WIND_CORRECTION] = (
                new_data.pop(OPT_WDA_WIND_CORRECTION, DEFAULT_WIND_CORRECTION))

            new_data[SECTION_ADVANCED_SETTINGS][OPT_WDA_HUMIDITY_CORRECTION] = (
                new_data.pop(OPT_WDA_HUMIDITY_CORRECTION, DEFAULT_HUMIDITY_CORRECTION))

            new_data[SECTION_ADVANCED_SETTINGS][OPT_WDA_EXP_MIN] = (
                new_data.pop(OPT_WDA_EXP_MIN, DEFAULT_EXP_MIN))

            new_data[SECTION_ADVANCED_SETTINGS][OPT_WDA_EXP_MAX] = (
                new_data.pop(OPT_WDA_EXP_MAX, DEFAULT_EXP_MAX))

        if config_entry.options:
            new_options = {**config_entry.options}
            new_options[SECTION_ADVANCED_SETTINGS] = {}

            new_options[SECTION_ADVANCED_SETTINGS][OPT_WDA_ROOM_TEMP_CORRECTION] = (
                new_options.pop(OPT_WDA_ROOM_TEMP_CORRECTION, DEFAULT_ROOM_TEMP_CORRECTION))

            new_options[SECTION_ADVANCED_SETTINGS][OPT_WDA_WIND_CORRECTION] = (
                new_options.pop(OPT_WDA_WIND_CORRECTION, DEFAULT_WIND_CORRECTION))

            new_options[SECTION_ADVANCED_SETTINGS][OPT_WDA_HUMIDITY_CORRECTION] = (
                new_options.pop(OPT_WDA_HUMIDITY_CORRECTION, DEFAULT_HUMIDITY_CORRECTION))

            new_options[SECTION_ADVANCED_SETTINGS][OPT_WDA_EXP_MIN] = (
                new_options.pop(OPT_WDA_EXP_MIN, DEFAULT_EXP_MIN))

            new_options[SECTION_ADVANCED_SETTINGS][OPT_WDA_EXP_MAX] = (
                new_options.pop(OPT_WDA_EXP_MAX, DEFAULT_EXP_MAX))

        # Update entry config
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options=new_options,
            version=2
        )

        _LOGGER.debug(
            "Migration to configuration version %s.%s successful",
            config_entry.version, config_entry.minor_version)

        return True

    return False
