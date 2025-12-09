import logging

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from .const import *  # noqa F403

_LOGGER = logging.getLogger(__name__)


def get_config_value(config_entry, key, default=None):
    if config_entry:
        # Value priority: options > data > default
        if key in config_entry.options:
            return config_entry.options.get(key)
        if key in config_entry.data:
            return config_entry.data.get(key)
    return default


def calc_target(
        outside_temp: float,
        heating_curve: int,
        exp_min: float = DEFAULT_EXP_MIN,
        exp_max: float = DEFAULT_EXP_MAX,
        outside_temp_min: int = DEFAULT_MIN_OUTSIDE_TEMP,
        outside_temp_max: int = DEFAULT_MAX_OUTSIDE_TEMP) -> float:
    """
    Calculation of the target temperature of the coolant based on the outside
    temperature and the heating curve number
    """

    # Curve normolization from 1 to 200
    # We bring it into the range from 0 to 1
    normalized_hc = (heating_curve - 1) / 199

    # The degree of the exponent depends on the curve number.
    # Range from exp_min to exp_max
    exponent = exp_min + normalized_hc * (exp_max - exp_min)

    # The maximum temperature of the coolant — from 20 to 150°C
    a = 20 + (150 - 20) * normalized_hc

    # Temperature factor
    denominator = outside_temp_max - outside_temp_min
    temp_factor = (outside_temp_max - outside_temp) / denominator
    temp_factor = 1 if temp_factor > 1 else temp_factor

    # Target temperature of the coolant
    target = a * (1 - (1 - temp_factor) ** exponent)
    return target


async def get_sensor_value(hass, entity_id, default=None):
    """ Get current sensor value by `entity_id` """
    if not entity_id:
        return default

    state = hass.states.get(entity_id)
    if state is None or state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
        return default

    try:
        return float(state.state)
    except ValueError:
        _LOGGER.warning(f"Cannot convert state of {entity_id} to float: {state.state}")

    return default


async def update(hass, config):
    """
    Return calculated sensor value for update.
    Return None if `wda_outside_temp` sensor is not configured
    """

    # Get data from settings
    min_coolant_temp = int(
        get_config_value(config, "wda_min_coolant_temp", DEFAULT_MIN_COOLANT_TEMP))
    max_coolant_temp = int(
        get_config_value(config, "wda_max_coolant_temp", DEFAULT_MAX_COOLANT_TEMP))
    target_room_temp = float(
        get_config_value(config, "wda_target_room_temp", DEFAULT_TARGET_ROOM_TEMP))
    heating_curve = int(
        get_config_value(config, "wda_heating_curve", DEFAULT_HEATING_CURVE))

    # Correction settings
    room_temp_correction = float(get_config_value(config, "wda_room_temp_correction", 0))
    wind_correction = float(get_config_value(config, "wda_wind_correction", 0))
    humidity_correction = float(get_config_value(config, "wda_humidity_correction", 0))

    # Exponent range
    exp_min = float(get_config_value(config, "wda_exp_min", DEFAULT_EXP_MIN))
    exp_max = float(get_config_value(config, "wda_exp_max", DEFAULT_EXP_MAX))

    # Get data from sensors
    outside_temp = await get_sensor_value(hass, get_config_value(config, "wda_outside_temp"))
    if outside_temp is None:
        return

    outside_temp = float(outside_temp)
    wind_speed = await get_sensor_value(
        hass, get_config_value(config, "wda_wind_speed"))
    outside_humidity = await get_sensor_value(
        hass, get_config_value(config, "wda_outside_humidity"))
    inside_temp = await get_sensor_value(
        hass, get_config_value(config, "wda_inside_temp"))

    # Base value
    target_heat_temp = calc_target(outside_temp, heating_curve, exp_min, exp_max)

    # Room Temperature Correction
    if room_temp_correction and inside_temp is not None:
        correction_value = (target_room_temp - float(inside_temp)) * room_temp_correction
        target_heat_temp = target_heat_temp + correction_value

    # Wind Speed Correction
    if wind_correction and wind_speed is not None:
        correction_value = float(wind_speed) * wind_correction
        target_heat_temp = target_heat_temp + correction_value

    # Humidity Correction
    if humidity_correction and outside_humidity is not None:
        correction_value = (
            max(0, (float(outside_humidity) - DEFAULT_HUMIDITY_THRESHOLD) *
                humidity_correction)
        )
        target_heat_temp = target_heat_temp + correction_value

    # Going beyond the limits of values
    if target_heat_temp < min_coolant_temp:
        target_heat_temp = min_coolant_temp
    if target_heat_temp > max_coolant_temp:
        target_heat_temp = max_coolant_temp

    return int(round(target_heat_temp))
