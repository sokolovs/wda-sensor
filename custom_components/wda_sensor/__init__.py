""" Weather Dependent Automation Sensor integration. """
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import WDAUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """ Set up sensor from a config entry. """
    hass.data.setdefault(DOMAIN, {})
    coordinator = WDAUpdateCoordinator(hass, config_entry)
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": coordinator
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
