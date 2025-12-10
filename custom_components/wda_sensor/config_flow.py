import logging

from homeassistant import config_entries
from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.translation import async_get_translations

import voluptuous as vol

from .const import *  # noqa F403
from .helpers import get_config_value

_LOGGER = logging.getLogger(__name__)


async def get_user_language(hass):
    user_language = hass.data.get("language")
    return user_language if user_language else hass.config.language


async def get_translation(hass, key, default="Not found..."):
    language = await get_user_language(hass)
    translations = await async_get_translations(hass, language, "common", [])
    return translations.get(key, default)


async def create_schema(hass, config_entry=None, user_input=None):
    """ Common schema for ConfigFlow and OptionsFlow."""

    sensors = {}
    sensors[NOT_SELECTED_VALUE] = await get_translation(hass, NOT_SELECTED_VALUE, "Not selected...")

    # Add sensors
    sorted_sensors = sorted(
        [s for s in hass.states.async_all() if s.domain == Platform.SENSOR],
        key=lambda s: s.name.lower()
    )
    sensors.update({s.entity_id: s.name for s in sorted_sensors})

    def get_config(key, default=None):
        if user_input is not None:
            return user_input.get(key, default)
        return get_config_value(config_entry, key, default)

    return vol.Schema({
        vol.Required("name", default=get_config("name", "")): str,

        # Settings
        vol.Required(
            "wda_min_coolant_temp",
            default=get_config("wda_min_coolant_temp", DEFAULT_MIN_COOLANT_TEMP)):
                vol.All(vol.Coerce(int), vol.Range(min=10, max=50)),

        vol.Required(
            "wda_max_coolant_temp",
            default=get_config("wda_max_coolant_temp", DEFAULT_MAX_COOLANT_TEMP)):
                vol.All(vol.Coerce(int), vol.Range(min=20, max=150)),

        vol.Required(
            "wda_target_room_temp",
            default=get_config("wda_target_room_temp", DEFAULT_TARGET_ROOM_TEMP)):
                vol.All(vol.Coerce(float), vol.Range(min=5, max=30)),

        vol.Required(
            "wda_heating_curve",
            default=get_config("wda_heating_curve", DEFAULT_HEATING_CURVE)):
                vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),

        # Update interval (periodic sensor only)
        vol.Required(
            "wda_update_interval",
            default=get_config("wda_update_interval", DEFAULT_UPDATE_INTERVAL)):
                vol.All(vol.Coerce(int), vol.In(UPDATE_INTERVAL_CHOICES)),

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
            default=get_config("wda_room_temp_correction", DEFAULT_ROOM_TEMP_CORRECTION)):
                vol.All(vol.Coerce(float), vol.Range(min=0, max=10)),
        vol.Optional(
            "wda_wind_correction",
            default=get_config("wda_wind_correction", DEFAULT_WIND_CORRECTION)):
                vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
        vol.Optional(
            "wda_humidity_correction",
            default=get_config("wda_humidity_correction", DEFAULT_HUMIDITY_CORRECTION)):
                vol.All(vol.Coerce(float), vol.Range(min=0, max=0.4)),

        # Exponent
        vol.Optional(
            "wda_exp_min",
            default=get_config("wda_exp_min", DEFAULT_EXP_MIN)):
                vol.All(vol.Coerce(float), vol.Range(min=0, max=20.0)),
        vol.Optional(
            "wda_exp_max",
            default=get_config("wda_exp_max", DEFAULT_EXP_MAX)):
                vol.All(vol.Coerce(float), vol.Range(min=0, max=20.0)),

    })


def check_user_input(user_input):
    errors = {}
    if user_input is not None:
        min_coolant_temp = user_input["wda_min_coolant_temp"]
        max_coolant_temp = user_input["wda_max_coolant_temp"]
        exp_min = user_input["wda_exp_min"]
        exp_max = user_input["wda_exp_max"]

        if exp_min > exp_max:
            errors["base"] = "exp_min_must_be_less"
            errors["wda_exp_min"] = "exp_min_must_be_less"

        if min_coolant_temp > max_coolant_temp:
            errors["base"] = "min_coolant_temp_must_be_less"
            errors["wda_min_coolant_temp"] = "min_coolant_temp_must_be_less"
    return errors


class WDASensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ Handle a config flow for Weather Dependent Automation Sensor. """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """ Handle the initial step. """
        _LOGGER.debug(f"Request to create config: {user_input}")

        errors = {}
        if user_input is not None:
            errors = check_user_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input["name"],
                    data=user_input)

        schema = await create_schema(
            hass=self.hass,
            user_input=user_input)
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
        if HA_VERSION < '2024.12':
            self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """ Manage the options. """
        _LOGGER.debug(f"Request to update options: {user_input}")

        errors = {}
        if user_input is not None:
            errors = check_user_input(user_input)

            if not errors:
                for key in [
                        "wda_inside_temp",
                        "wda_wind_speed",
                        "wda_outside_humidity"]:
                    input_value = user_input.get(key)
                    if input_value == NOT_SELECTED_VALUE:
                        user_input[key] = None

                # Update configuration
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=user_input)

                # Send signal to subscribers
                async_dispatcher_send(self.hass, SENSOR_UPDATE_SIGNAL)

                return self.async_create_entry(title="", data=user_input)

        schema = await create_schema(
            hass=self.hass,
            config_entry=self.config_entry,
            user_input=user_input
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )
