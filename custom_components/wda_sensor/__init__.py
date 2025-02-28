""" Weather Dependent Automation Sensor integration. """
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


def get_config_value(config_entry, key, default=None):
    if config_entry:
        # Value priority: options > data > default
        if key in config_entry.options:
            return config_entry.options.get(key)
        if key in config_entry.data:
            return config_entry.data.get(key)
    return default


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """ Set up sensor from a config entry. """
    await hass.config_entries.async_forward_entry_setups(config_entry, [Platform.SENSOR])
    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """ Update options for entry that was configured via user interface. """
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """ Unload a config entry. """
    await hass.config_entries.async_forward_entry_unload(config_entry, Platform.SENSOR)
    return True
