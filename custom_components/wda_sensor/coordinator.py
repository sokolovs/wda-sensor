import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN, OPT_WDA_UPDATE_INTERVAL
from .helpers import get_config_value, update

_LOGGER = logging.getLogger(__name__)


class WDAUpdateCoordinator(DataUpdateCoordinator):
    """ Periodic sensor data updater """

    def __init__(self, hass, config_entry):
        self.hass = hass
        self.config_entry = config_entry

        update_interval = get_config_value(
            config_entry, OPT_WDA_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=int(update_interval)))

    async def _async_update_data(self):
        result = None
        try:
            result = await update(self.hass, self.config_entry)
            _LOGGER.debug(f"Data received for sensor update: {result}")

            if result is None:
                _LOGGER.warning(
                    f"Failed to update {self.__class__.__name__}: "
                    f"outside temperature sensor is not configured now")
        except Exception as e:
            raise UpdateFailed(f"Exception while sensor update: {e}")

        return result
