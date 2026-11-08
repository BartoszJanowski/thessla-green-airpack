"""Declarative Modbus register map for Thessla Green AirPack4 devices.

This module is the single source of truth for register addresses, data types,
ranges and grouping. It must not import Home Assistant so that the standalone
``tools/probe.py`` can reuse it.

Source: "Protokół Modbus RTU – Tabela rejestrów MODBUS_USER_AirPack_4" (2022).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Table(StrEnum):
    """Modbus data table."""

    COIL = "coil"  # FC01
    DISCRETE = "discrete"  # FC02
    INPUT = "input"  # FC04
    HOLDING = "holding"  # FC03


class DType(StrEnum):
    """How a raw 16-bit (or 1-bit) value is decoded."""

    BOOL = "bool"
    U16 = "u16"
    S16 = "s16"
    TEMP10 = "temp10"  # signed, x0.1 °C, 0x8000 = no sensor
    HALF = "half"  # unsigned, x0.5 (°C)
    FLOW = "flow"  # unsigned, 65535 = not available (CF inactive)
    VOLT = "volt"  # 0..4095 -> 0..10 V
    BCD_TIME = "bcd_time"  # 0xHHMM, BCD digits; 0x2400/0xA200 = disabled
    PACKED_DATE = "packed_date"  # b0-4 day, b5-8 month, b9-15 year-2000


class Group(StrEnum):
    """Polling group."""

    STATE = "state"  # read on every poll
    ALARM = "alarm"  # detailed alarm flags, read when summary flags are set
    IDENTITY = "identity"  # read at setup only (firmware, serial, ...)
    WRITE_ONLY = "write_only"  # never read (command registers)


class Feature(StrEnum):
    """Optional hardware. Entities for absent features are disabled by default."""

    GWC = "gwc"  # ground heat exchanger
    DUCT = "duct"  # duct heater / cooler (COMFORT mode)
    CF = "cf"  # constant flow
    EXPANSION = "expansion"
    ERV = "erv"


@dataclass(frozen=True, slots=True)
class Reg:
    """A single Modbus register / bit."""

    key: str
    table: Table
    address: int
    dtype: DType = DType.U16
    writable: bool = False
    min: float | None = None  # engineering units
    max: float | None = None  # engineering units
    group: Group = Group.STATE
    feature: Feature | None = None
    # Hide the entity when the register reads "no value" during detection
    # (e.g. temperature sensor not fitted -> 0x8000).
    absent_if_none: bool = False
    # Also treat a raw 0 at detection as "not fitted". Firmware 4.87 reports
    # optional sensors that are not installed (TN2, TZ3) as exactly 0.
    absent_if_zero: bool = False


# Special raw values.
TEMP_NO_SENSOR = 0x8000
FLOW_NOT_AVAILABLE = 0xFFFF
TIME_DISABLED = (0x2400, 0xA200)

# Atomic write groups (FC16). See spec page 14.
CFG_MODE1_ADDRESS = 0x1130  # [mode, airflow %, change flag]
CFG_MODE2_ADDRESS = 0x1133  # [mode, supply temp *2, change flag]
FILTER_CHANGE_ADDRESS = 0x1FFF
FILTER_CHANGE_SUPPLY = 0x11
FILTER_CHANGE_EXHAUST = 0x21

C, D, I, H = Table.COIL, Table.DISCRETE, Table.INPUT, Table.HOLDING


def _alarm(code: str) -> Reg:
    """Alarm flag register: address = 0x2000 + alarm number."""
    return Reg(
        f"alarm_{code.lower()}", H, 0x2000 + int(code[1:]), DType.BOOL, group=Group.ALARM
    )


# Alarm code -> English description (shown in the "active alarms" attributes).
ALARM_DESCRIPTIONS: dict[str, str] = {
    "S2": "I2C communication error",
    "S6": "FPX heater thermal protection tripped too many times",
    "S7": "Calibration impossible - outside air too cold",
    "S8": "Product key required",
    "S9": "Unit stopped from AirS panel",
    "S10": "Fire alarm input (P.POZ.) active",
    "S13": "Unit stopped from Air+/AirL+/Air++/AirMobile panel",
    "S14": "Water heater anti-freeze protection tripped too many times",
    "S15": "Water heater anti-freeze protection ineffective",
    "S16": "Electric heater thermal protection tripped with FPX active",
    "S17": "Filters not replaced (pressure switch)",
    "S19": "Filters not replaced (no pressure switch)",
    "S20": "Duct filter not replaced",
    "S22": "Heat exchanger anti-freeze protection (FPX) failed",
    "S23": "Exchanger inlet temperature sensor failure in FPX conditions",
    "S24": "Supply duct sensor after water heater failure",
    "S25": "Outside air temperature sensor failure",
    "S26": "Outside air and glycol GWC temperature sensors failure",
    "S28": "Secondary heater control failure - disconnect power",
    "S29": "Temperature before heat exchanger too high",
    "S30": "Supply fan not working",
    "S31": "Exhaust fan not working",
    "S32": "No communication with TG-02 module",
    "E99": "Product key required",
    "E100": "No reading from outside air sensor (TZ1)",
    "E101": "No reading from supply air sensor (TN1)",
    "E102": "No reading from extract air sensor (TP)",
    "E103": "No reading from exchanger inlet / FPX sensor (TZ2)",
    "E104": "No reading from ambient sensor (TO)",
    "E105": "No reading from duct supply sensor (TN2)",
    "E106": "No reading from glycol GWC sensor (TZ3)",
    "E108": "No reading from sensor after heat exchanger (TW)",
    "E138": "Supply fan CF sensor failure",
    "E139": "Exhaust fan CF sensor failure",
    "E140": "Supply filter CF sensor failure",
    "E141": "Exhaust filter CF sensor failure",
    "F142": "Supply filter missing",
    "F143": "Exhaust filter missing",
    "E144": "Supply fan cannot maintain airflow",
    "E145": "Exhaust fan cannot maintain airflow",
    "F146": "Supply filter replacement required",
    "F147": "Exhaust filter replacement required",
    "E148": "Supply filter wear above limit",
    "E149": "Exhaust filter wear above limit",
    "E150": "Supply filter replacement required",
    "E151": "Exhaust filter replacement required",
    "E152": "Extract air temperature above maximum",
    "E156": "Supply filter maximum service time exceeded",
    "E157": "Exhaust filter maximum service time exceeded",
    "E196": "Installation balancing not performed",
    "E197": "Installation balancing interrupted",
    "E198": "No communication with CF2 module",
    "E200": "Unit electric heater thermal protection tripped",
    "E201": "Duct electric heater thermal protection tripped",
    "E202": "Secondary heater control failure",
    "E203": "Secondary heater control failure",
    "E249": "No communication with Expansion module",
    "E251": "Duct filter replacement required",
}


AIRPACK4_REGISTERS: tuple[Reg, ...] = (
    # ---- 01 coils (outputs, read-only) --------------------------------------
    Reg("duct_water_heater_pump", C, 0x0005, DType.BOOL),
    Reg("bypass_actuator", C, 0x0009, DType.BOOL),
    Reg("info_output", C, 0x000A, DType.BOOL),
    Reg("power_supply_fans", C, 0x000B, DType.BOOL),
    Reg("heating_cable", C, 0x000C, DType.BOOL),
    Reg("work_permit", C, 0x000D, DType.BOOL),
    Reg("gwc_relay", C, 0x000E, DType.BOOL),
    Reg("hood_output", C, 0x000F, DType.BOOL),
    # ---- 02 discrete inputs ------------------------------------------------
    Reg("duct_heater_protection", D, 0x0000, DType.BOOL),
    Reg("expansion", D, 0x0001, DType.BOOL),
    Reg("dp_duct_filter_overflow", D, 0x0003, DType.BOOL),
    Reg("hood_input", D, 0x0004, DType.BOOL),
    Reg("contamination_sensor", D, 0x0005, DType.BOOL),
    Reg("airing_sensor", D, 0x0006, DType.BOOL),
    Reg("airing_switch", D, 0x0007, DType.BOOL),
    Reg("airing_mini", D, 0x000A, DType.BOOL),
    Reg("fan_speed_3_input", D, 0x000B, DType.BOOL),
    Reg("fan_speed_2_input", D, 0x000C, DType.BOOL),
    Reg("fan_speed_1_input", D, 0x000D, DType.BOOL),
    Reg("fireplace_input", D, 0x000E, DType.BOOL),
    Reg("fire_alarm_input", D, 0x000F, DType.BOOL),
    Reg("dp_ahu_filter_overflow", D, 0x0012, DType.BOOL),
    Reg("ahu_filter_protection", D, 0x0013, DType.BOOL),
    Reg("empty_house_input", D, 0x0015, DType.BOOL),
    # ---- 04 input registers --------------------------------------------------
    Reg("firmware_major", I, 0x0000, group=Group.IDENTITY),
    Reg("firmware_minor", I, 0x0001, group=Group.IDENTITY),
    Reg("day_of_week", I, 0x0002),
    Reg("period", I, 0x0003),
    Reg("firmware_patch", I, 0x0004, group=Group.IDENTITY),
    Reg("outside_temperature", I, 0x0010, DType.TEMP10),  # TZ1
    Reg("supply_temperature", I, 0x0011, DType.TEMP10),  # TN1
    Reg("exhaust_temperature", I, 0x0012, DType.TEMP10),  # TP (extract)
    Reg("fpx_temperature", I, 0x0013, DType.TEMP10, absent_if_none=True),  # TZ2
    Reg(
        "duct_supply_temperature", I, 0x0014, DType.TEMP10,
        feature=Feature.DUCT, absent_if_none=True, absent_if_zero=True,
    ),  # TN2
    Reg(
        "gwc_temperature", I, 0x0015, DType.TEMP10,
        feature=Feature.GWC, absent_if_none=True, absent_if_zero=True,
    ),  # TZ3
    Reg("ambient_temperature", I, 0x0016, DType.TEMP10, absent_if_none=True),  # TO
    *(
        Reg(f"serial_number_{n}", I, 0x0018 + n - 1, group=Group.IDENTITY)
        for n in range(1, 7)
    ),
    Reg("constant_flow_active", I, 0x010F, DType.BOOL),
    Reg("supply_percentage", I, 0x0110),
    Reg("exhaust_percentage", I, 0x0111),
    Reg("supply_flowrate", I, 0x0112, DType.FLOW),
    Reg("exhaust_flowrate", I, 0x0113, DType.FLOW),
    Reg("min_percentage", I, 0x0114),
    Reg("max_percentage", I, 0x0115),
    # ---- 03 holding registers: identity ---------------------------------------
    Reg("cf_version", H, 0x00F0, group=Group.IDENTITY),
    Reg("exp_version", H, 0x00F1, group=Group.IDENTITY),
    *(Reg(f"device_name_{n}", H, 0x1FD0 + n, group=Group.IDENTITY) for n in range(8)),
    # ---- 03 holding registers: state -----------------------------------------
    Reg("supply_air_flow", H, 0x0100, DType.FLOW, feature=Feature.CF, absent_if_none=True),
    Reg("exhaust_air_flow", H, 0x0101, DType.FLOW, feature=Feature.CF, absent_if_none=True),
    Reg("dac_supply", H, 0x0500, DType.VOLT),
    Reg("dac_exhaust", H, 0x0501, DType.VOLT),
    Reg("dac_heater", H, 0x0502, DType.VOLT),
    Reg("dac_cooler", H, 0x0503, DType.VOLT),
    Reg("antifreeze_mode", H, 0x1060, DType.BOOL),
    Reg("antifreeze_stage", H, 0x1066),
    Reg("mode", H, 0x1070),  # 0 auto, 1 manual, 2 temporary (write via 0x1130)
    Reg("season_mode", H, 0x1071, writable=True, min=0, max=1),
    Reg("air_flow_rate_manual", H, 0x1072, writable=True, min=10, max=100),
    Reg("air_flow_rate_temporary", H, 0x1073, writable=True, min=10, max=100),
    Reg("supply_air_temperature_manual", H, 0x1074, DType.HALF, writable=True, min=10, max=45),
    Reg("supply_air_temperature_temporary", H, 0x1075, DType.HALF, writable=True, min=10, max=45),
    Reg("fan_speed_1_coef", H, 0x1078, writable=True, min=10, max=45),
    Reg("fan_speed_2_coef", H, 0x1079, writable=True, min=46, max=75),
    Reg("fan_speed_3_coef", H, 0x107A, writable=True, min=76, max=100),
    Reg("manual_airing_time_to_start", H, 0x107B, DType.BCD_TIME, writable=True),
    Reg("special_mode", H, 0x1080, writable=True, min=0, max=11),
    Reg("hood_supply_coef", H, 0x1082, writable=True, min=100, max=150),
    Reg("hood_exhaust_coef", H, 0x1083, writable=True, min=100, max=150),
    Reg("fireplace_supply_coef", H, 0x1084, writable=True, min=5, max=50),
    Reg("airing_bathroom_coef", H, 0x1085, writable=True, min=100, max=150),
    Reg("airing_coef", H, 0x1086, writable=True, min=100, max=150),
    Reg("contamination_coef", H, 0x1087, writable=True, min=100, max=150),
    Reg("empty_house_coef", H, 0x1088, writable=True, min=10, max=50),
    Reg("airing_panel_mode_time", H, 0x1089, writable=True, min=1, max=45),
    Reg("airing_switch_mode_time", H, 0x108A, writable=True, min=1, max=45),
    Reg("airing_switch_mode_on_delay", H, 0x108B, writable=True, min=0, max=20),
    Reg("airing_switch_mode_off_delay", H, 0x108C, writable=True, min=0, max=20),
    Reg("fireplace_mode_time", H, 0x108D, writable=True, min=1, max=10),
    Reg("airing_switch_coef", H, 0x108E, writable=True, min=100, max=150),
    # 10-100 %, 101 = take the intensity from the active AUTO / MANUAL mode (fw 4.72+)
    Reg("open_window_coef", H, 0x108F, writable=True, min=10, max=101),
    Reg("gwc_off", H, 0x10A0, writable=True, min=0, max=1, feature=Feature.GWC),
    Reg("min_gwc_air_temperature", H, 0x10A1, DType.HALF, writable=True, min=0, max=10, feature=Feature.GWC),
    Reg("max_gwc_air_temperature", H, 0x10A2, DType.HALF, writable=True, min=15, max=40, feature=Feature.GWC),
    Reg("gwc_regen", H, 0x10A6, writable=True, min=0, max=2, feature=Feature.GWC),
    Reg("gwc_mode", H, 0x10A7, feature=Feature.GWC),
    Reg("gwc_regen_period", H, 0x10A8, writable=True, min=4, max=8, feature=Feature.GWC),
    Reg("delta_t_gwc", H, 0x10AA, DType.HALF, writable=True, min=0, max=5, feature=Feature.GWC),
    Reg("start_gwc_regen_winter_time", H, 0x10AB, DType.BCD_TIME, writable=True, feature=Feature.GWC),
    Reg("stop_gwc_regen_winter_time", H, 0x10AC, DType.BCD_TIME, writable=True, feature=Feature.GWC),
    Reg("start_gwc_regen_summer_time", H, 0x10AD, DType.BCD_TIME, writable=True, feature=Feature.GWC),
    Reg("stop_gwc_regen_summer_time", H, 0x10AE, DType.BCD_TIME, writable=True, feature=Feature.GWC),
    Reg("gwc_regen_flag", H, 0x10AF, DType.BOOL, feature=Feature.GWC),
    Reg("comfort_mode_panel", H, 0x10D0, writable=True, min=0, max=1),
    Reg("comfort_mode", H, 0x10D1),
    Reg("bypass_off", H, 0x10E0, writable=True, min=0, max=1),
    Reg("min_bypass_temperature", H, 0x10E1, DType.HALF, writable=True, min=5, max=20),
    Reg("air_temperature_summer_free_heating", H, 0x10E2, DType.HALF, writable=True, min=15, max=30),
    Reg("air_temperature_summer_free_cooling", H, 0x10E3, DType.HALF, writable=True, min=15, max=30),
    Reg("bypass_mode", H, 0x10EA),
    Reg("bypass_user_mode", H, 0x10EB, writable=True, min=1, max=3),
    Reg("bypass_coef_1", H, 0x10EC, writable=True, min=10, max=100),
    Reg("bypass_coef_2", H, 0x10ED, writable=True, min=10, max=151),
    Reg("stop_ahu_code", H, 0x1120),
    Reg("on_off_panel_mode", H, 0x1123, DType.BOOL, writable=True, min=0, max=1),
    Reg("pres_check_day", H, 0x1150, writable=True, min=0, max=6),
    Reg("pres_check_time", H, 0x1151, DType.BCD_TIME, writable=True),
    Reg("supply_filter_wear", H, 0x1182),
    Reg("exhaust_filter_wear", H, 0x1183),
    Reg("supply_filter_date", H, 0x1234, DType.PACKED_DATE),
    Reg("exhaust_filter_date", H, 0x1236, DType.PACKED_DATE),
    Reg("post_heater_on", H, 0x1260, DType.BOOL, feature=Feature.ERV),
    Reg("post_heater_mode", H, 0x1267, writable=True, min=0, max=2, feature=Feature.ERV),
    Reg("required_temperature", H, 0x1FFE, DType.HALF),
    Reg("filter_change", H, FILTER_CHANGE_ADDRESS, writable=True, group=Group.WRITE_ONLY),
    Reg("alarm", H, 0x2000, DType.BOOL),
    Reg("error", H, 0x2001, DType.BOOL),
    *(_alarm(code) for code in ALARM_DESCRIPTIONS),
)


def by_key(registers: tuple[Reg, ...]) -> dict[str, Reg]:
    """Index registers by key (and assert uniqueness)."""
    index: dict[str, Reg] = {}
    for reg in registers:
        if reg.key in index:
            raise ValueError(f"Duplicate register key {reg.key}")
        index[reg.key] = reg
    return index
