import logging

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass  # noqa: F401
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.selector import (
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType
)

import voluptuous as vol

from .const import *  # noqa F403

_LOGGER = logging.getLogger(__name__)


async def create_schema(hass, config_entry=None, user_input=None, config_flow=True):
    """ Common schema for ConfigFlow and OptionsFlow."""
    return vol.Schema({
        vol.Required(OPT_NAME): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),

        # Settings
        vol.Required(OPT_WDA_MIN_COOLANT_TEMP, default=DEFAULT_MIN_COOLANT_TEMP):
            NumberSelector(NumberSelectorConfig(
                min=10, max=50, mode=NumberSelectorMode.BOX,
                unit_of_measurement=UnitOfTemperature.CELSIUS)),

        vol.Required(OPT_WDA_MAX_COOLANT_TEMP, default=DEFAULT_MAX_COOLANT_TEMP):
            NumberSelector(NumberSelectorConfig(
                min=20, max=150, mode=NumberSelectorMode.BOX,
                unit_of_measurement=UnitOfTemperature.CELSIUS)),

        # Update interval (periodic sensor only)
        vol.Required(OPT_WDA_UPDATE_INTERVAL, default=str(DEFAULT_UPDATE_INTERVAL)):
            SelectSelector(SelectSelectorConfig(
                options=UPDATE_INTERVAL_CHOICES,
                mode=SelectSelectorMode.DROPDOWN)),

        # Sensors
        vol.Required(OPT_WDA_OUTSIDE_TEMP):
            EntitySelector(EntitySelectorConfig(EntityFilterSelectorConfig(
                domain=Platform.SENSOR,
                # device_class=SensorDeviceClass.TEMPERATURE
            ))),
        vol.Optional(OPT_WDA_INSIDE_TEMP):
            EntitySelector(EntitySelectorConfig(EntityFilterSelectorConfig(
                domain=Platform.SENSOR,
                # device_class=SensorDeviceClass.TEMPERATURE
            ))),
        vol.Optional(OPT_WDA_WIND_SPEED):
            EntitySelector(EntitySelectorConfig(EntityFilterSelectorConfig(
                domain=Platform.SENSOR,
                # device_class=[SensorDeviceClass.SPEED, SensorDeviceClass.WIND_SPEED]
            ))),
        vol.Optional(OPT_WDA_OUTSIDE_HUMIDITY):
            EntitySelector(EntitySelectorConfig(EntityFilterSelectorConfig(
                domain=Platform.SENSOR,
                # device_class=SensorDeviceClass.HUMIDITY
            ))),

        vol.Required(SECTION_ADVANCED_SETTINGS): section(vol.Schema({
            # Corrections
            vol.Optional(OPT_WDA_ROOM_TEMP_CORRECTION, default=DEFAULT_ROOM_TEMP_CORRECTION):
                NumberSelector(NumberSelectorConfig(
                    min=0.0, max=10.0, mode=NumberSelectorMode.BOX)),
            vol.Optional(OPT_WDA_WIND_CORRECTION, default=DEFAULT_WIND_CORRECTION):
                NumberSelector(NumberSelectorConfig(
                    min=0.0, max=2.0, step=0.1, mode=NumberSelectorMode.BOX)),
            vol.Optional(OPT_WDA_HUMIDITY_CORRECTION, default=DEFAULT_HUMIDITY_CORRECTION):
                NumberSelector(NumberSelectorConfig(
                    min=0.0, max=1.0, step=0.01, mode=NumberSelectorMode.BOX)),

            # Exponent
            vol.Optional(OPT_WDA_EXP_MIN, default=DEFAULT_EXP_MIN):
                NumberSelector(NumberSelectorConfig(
                    min=0.0, max=20.0, step=0.1, mode=NumberSelectorMode.BOX)),
            vol.Optional(OPT_WDA_EXP_MAX, default=DEFAULT_EXP_MAX):
                NumberSelector(NumberSelectorConfig(
                    min=0.0, max=20.0, step=0.1, mode=NumberSelectorMode.BOX)),
        }), {"collapsed": True})
    })


def check_user_input(user_input):
    errors = {}
    if user_input is not None:
        min_coolant_temp = user_input[OPT_WDA_MIN_COOLANT_TEMP]
        max_coolant_temp = user_input[OPT_WDA_MAX_COOLANT_TEMP]
        exp_min = user_input[OPT_WDA_EXP_MIN]
        exp_max = user_input[OPT_WDA_EXP_MAX]

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
                    title=user_input[OPT_NAME],
                    data=user_input)

        schema = await create_schema(
            hass=self.hass,
            user_input=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
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
                # Update configuration
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=user_input[OPT_NAME],
                    options=user_input)

                # Send signal to subscribers
                async_dispatcher_send(self.hass, f"{SENSOR_UPDATE_SIGNAL}_{self.config_entry.entry_id}")

                # Close flow
                return self.async_create_entry(title="", data=user_input)

        schema = await create_schema(
            hass=self.hass,
            config_entry=self.config_entry,
            user_input=user_input,
            config_flow=False
        )

        options = user_input or self.config_entry.options or self.config_entry.data or {}
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, options),
            errors=errors
        )
