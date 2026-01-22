from awesomeversion import AwesomeVersion

from homeassistant.const import __version__ as HAVERSION  # noqa: N812

HA_VERSION = AwesomeVersion(HAVERSION)

# WDA domain
DOMAIN = "wda_sensor"
SENSOR_UPDATE_SIGNAL = "WDA_SENSOR_OPTIONS_UPDATED"

# Config options
OPT_NAME = "name"
OPT_WDA_MIN_COOLANT_TEMP = "wda_min_coolant_temp"
OPT_WDA_MAX_COOLANT_TEMP = "wda_max_coolant_temp"
OPT_WDA_TARGET_ROOM_TEMP = "wda_target_room_temp"
OPT_WDA_HEATING_CURVE = "wda_heating_curve"
OPT_WDA_UPDATE_INTERVAL = "wda_update_interval"
OPT_WDA_OUTSIDE_TEMP = "wda_outside_temp"
OPT_WDA_INSIDE_TEMP = "wda_inside_temp"
OPT_WDA_WIND_SPEED = "wda_wind_speed"
OPT_WDA_OUTSIDE_HUMIDITY = "wda_outside_humidity"
OPT_WDA_ROOM_TEMP_CORRECTION = "wda_room_temp_correction"
OPT_WDA_WIND_CORRECTION = "wda_wind_correction"
OPT_WDA_HUMIDITY_CORRECTION = "wda_humidity_correction"
OPT_WDA_EXP_MIN = "wda_exp_min"
OPT_WDA_EXP_MAX = "wda_exp_max"

# Min/max heating curve number
MIN_HEATING_CURVE = 1
MAX_HEATING_CURVE = 200
HEATING_CURVE_STEP = 1

# Min/max target root temperatur
MIN_TARGET_ROOT_TEMP = 5.0
MAX_TARGET_ROOT_TEMP = 30.0
TARGET_ROOT_TEMP_STEP = 0.1

# Defaults
DEFAULT_MIN_COOLANT_TEMP = 40
DEFAULT_MAX_COOLANT_TEMP = 80
DEFAULT_TARGET_ROOM_TEMP = 21.5
DEFAULT_HEATING_CURVE = 80
DEFAULT_HUMIDITY_THRESHOLD = 50
DEFAULT_ROOM_TEMP_CORRECTION = 2.0
DEFAULT_WIND_CORRECTION = 0.2
DEFAULT_HUMIDITY_CORRECTION = 0.05

# Outside temperature range
DEFAULT_MIN_OUTSIDE_TEMP = -50
DEFAULT_MAX_OUTSIDE_TEMP = 20

# Default exponent range
DEFAULT_EXP_MIN = 2.2
DEFAULT_EXP_MAX = 3.8

# Graph sensor X range
GRAPH_MIN_OUTSIDE_TEMP = -25
GRAPH_MAX_OUTSIDE_TEMP = 20

# Update interval (seconds)
DEFAULT_UPDATE_INTERVAL = 3600
UPDATE_INTERVAL_CHOICES = [
    {"value": "300", "label": "5m"},
    {"value": "600", "label": "10m"},
    {"value": "900", "label": "15m"},
    {"value": "1200", "label": "20m"},
    {"value": "1800", "label": "30m"},
    {"value": "3600", "label": "1h"},
    {"value": "7200", "label": "2h"}
]
