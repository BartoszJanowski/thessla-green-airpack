"""Constants for the Thessla Green AirPack4 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "thessla_green_airpack"
MANUFACTURER: Final = "Thessla Green"

# Sidebar panel with the live flow diagram (also opened from the device page).
PANEL_URL_PATH: Final = "airpack4"
PANEL_TITLE: Final = "AirPack4"
PANEL_ICON: Final = "mdi:hvac"
PANEL_WEBCOMPONENT: Final = "thessla-airpack-panel"

CONF_UNIT_ID: Final = "unit_id"
CONF_MODEL: Final = "model"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TIMEOUT: Final = "timeout"
CONF_REQUEST_DELAY: Final = "request_delay"
CONF_READ_ONLY: Final = "read_only"
CONF_SPECIAL_FUNCTIONS: Final = "special_functions"

DEFAULT_NAME: Final = "AirPack"
DEFAULT_PORT: Final = 502
DEFAULT_UNIT_ID: Final = 10
DEFAULT_SCAN_INTERVAL: Final = 30  # s
DEFAULT_TIMEOUT: Final = 3  # s
DEFAULT_REQUEST_DELAY: Final = 0  # ms
DEFAULT_READ_ONLY: Final = False

# Special functions that can be activated manually (select option -> register 0x1080 value).
# Which ones the unit offers depends on installer settings that are not exposed
# over Modbus (e.g. hood type), so the user picks them in Options.
SPECIAL_FUNCTIONS: Final = {
    "hood": 1,
    "fireplace": 2,
    "airing": 7,
    "open_windows": 10,
    "empty_house": 11,
}

# Entities belonging to each special function: hidden together with the
# function when it is unticked in Options (keys = entity unique-id suffixes).
FUNCTION_ENTITIES: Final[dict[str, tuple[str, ...]]] = {
    "hood": ("hood_supply_coef", "hood_exhaust_coef"),
    "fireplace": ("fireplace_supply_coef", "fireplace_mode_time"),
    "airing": ("airing_coef", "airing_panel_mode_time", "manual_airing_time_to_start"),
    "open_windows": ("open_window_coef", "open_window_coef_auto"),
    "empty_house": ("empty_house_coef",),
}

# Optional equipment and accessories (Options -> Installed equipment).
# GWC and duct exchangers are detected by their temperature sensors (TZ3 / TN2)
# and ticked by default when found. ERV registers answer even without the
# system, and accessories cannot be detected over Modbus: unticked by default.
CONF_EQUIPMENT: Final = "equipment"
EQUIPMENT_ENTITIES: Final[dict[str, tuple[str, ...]]] = {
    "gwc": (
        "gwc_enabled", "gwc_regen", "gwc_regen_flag", "gwc_state", "gwc_temperature", "gwc_relay",
        "min_gwc_air_temperature", "max_gwc_air_temperature", "delta_t_gwc", "gwc_regen_period",
        "start_gwc_regen_winter_time", "stop_gwc_regen_winter_time",
        "start_gwc_regen_summer_time", "stop_gwc_regen_summer_time",
    ),
    # Supply temperature setpoints are only kept in COMFORT, i.e. by duct exchangers.
    "duct": (
        "comfort_mode_panel", "comfort_state", "required_temperature", "duct_supply_temperature",
        "supply_air_temperature_manual", "supply_air_temperature_temporary",
    ),
    "erv": ("post_heater_mode", "post_heater_on"),
    "airs": (
        "fan_speed_1_coef", "fan_speed_2_coef", "fan_speed_3_coef",
        "fan_speed_1_input", "fan_speed_2_input", "fan_speed_3_input", "airing_mini",
    ),
    "hygrostat": ("airing_bathroom_coef", "airing_sensor"),
    "air_quality": ("contamination_coef", "contamination_sensor"),
    "airing_switch": (
        "airing_switch_coef", "airing_switch_mode_time",
        "airing_switch_mode_on_delay", "airing_switch_mode_off_delay", "airing_switch",
    ),
}
EQUIPMENT: Final = tuple(EQUIPMENT_ENTITIES)

MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

MAX_REGISTERS_PER_READ: Final = 16  # documented device limit
MAX_MERGE_GAP: Final = 8  # undocumented addresses we optimistically read through
ALARM_FULL_READ_EVERY: Final = 10  # polls

STORAGE_VERSION: Final = 1
