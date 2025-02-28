import logging

from homeassistant import config_entries
from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

import voluptuous as vol

from . import get_config_value
from .const import DOMAIN, SENSOR_UPDATE_SIGNAL

_LOGGER = logging.getLogger(__name__)


async def create_schema(config_entry=None, hass=None):
    """ Common schema for ConfigFlow and OptionsFlow."""

    sensors = {
        s.entity_id: s.name
        for s in hass.states.async_all()
        if s.domain == Platform.SENSOR
    }

    def get_config(key, default=None):
        return get_config_value(config_entry, key, default)

    return vol.Schema({
        vol.Required("name", default=get_config("name", "")): str,

        # Settings
        vol.Required(
            "wda_min_coolant_temp",
            default=get_config("wda_min_coolant_temp", 40)): vol.All(
                vol.Coerce(int), vol.Range(min=10, max=40)),

        vol.Required(
            "wda_max_coolant_temp",
            default=get_config("wda_max_coolant_temp", 80)): vol.All(
                vol.Coerce(int), vol.Range(min=40, max=120)),

        vol.Required(
            "wda_target_room_temp",
            default=get_config("wda_target_room_temp", 21.5)): vol.All(
                vol.Coerce(float), vol.Range(min=7, max=32)),

        vol.Required(
            "wda_heating_curve",
            default=get_config("wda_heating_curve", 25)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=100)),

        # Sensors
        vol.Required(
            "wda_outside_temp",
            default=get_config("wda_outside_temp")): vol.In(sensors),
        vol.Optional(
            "wda_inside_temp",
            default=get_config("wda_inside_temp")): vol.Maybe(vol.In(sensors)),
        vol.Optional(
            "wda_wind_speed",
            default=get_config("wda_wind_speed")): vol.Maybe(vol.In(sensors)),
        vol.Optional(
            "wda_outside_humidity",
            default=get_config("wda_outside_humidity")): vol.Maybe(vol.In(sensors)),

        # Corrections
        vol.Optional(
            "wda_room_temp_correction",
            default=get_config("wda_room_temp_correction", 2.0)): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=10)),
        vol.Optional(
            "wda_wind_correction",
            default=get_config("wda_wind_correction", 0.2)): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=1)),
        vol.Optional(
            "wda_humidity_correction",
            default=get_config("wda_humidity_correction", 0.05)): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=0.2))
    })


class WDASensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ Handle a config flow for Weather Dependent Automation Sensor. """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """ Handle the initial step. """
        _LOGGER.info("Request to create config: %s", user_input)

        errors = {}

        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        schema = await create_schema(hass=self.hass)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WDASensorOptionsFlow(config_entry)


class WDASensorOptionsFlow(config_entries.OptionsFlow):
    """ Handle options flow. """

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """ Manage the options. """
        _LOGGER.warning("Request to update options: %s", user_input)

        errors = {}

        if user_input is not None:
            for key in ["wda_inside_temp", "wda_wind_speed", "wda_outside_humidity"]:
                if not user_input.get(key):
                    user_input[key] = None

            # Update configuration
            self.hass.config_entries.async_update_entry(self.config_entry, options=user_input)

            # Send signal to subscribers
            async_dispatcher_send(self.hass, SENSOR_UPDATE_SIGNAL)

            return self.async_create_entry(title="", data=user_input)

        schema = await create_schema(
            config_entry=self.config_entry,
            hass=self.hass
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )
