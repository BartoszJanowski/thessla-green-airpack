"""Sensors for Thessla Green AirPack4."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KEY_ACTIVE_ALARMS, KEY_EFFICIENCY, AirPackConfigEntry
from .entity import AirPackEntity, AirPackEntityDescription, supported_descriptions
from .registers import ALARM_DESCRIPTIONS

SPECIAL_MODES = {
    0: "none",
    1: "hood",
    2: "fireplace",
    3: "airing_bell_switch",
    4: "airing_switch",
    5: "airing_hygrostat",
    6: "airing_air_quality",
    7: "airing_manual",
    8: "airing_auto_schedule",
    9: "airing_manual_schedule",
    10: "open_windows",
    11: "empty_house",
}
OPERATING_MODES = {0: "auto", 1: "manual", 2: "temporary"}
BYPASS_STATES = {0: "inactive", 1: "free_heating", 2: "free_cooling"}
GWC_STATES = {0: "inactive", 1: "winter", 2: "summer"}
COMFORT_STATES = {0: "inactive", 1: "heating", 2: "cooling"}
FPX_STATES = {0: "off", 1: "fpx1", 2: "fpx2"}
WEEKDAYS = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"}


@dataclass(frozen=True, kw_only=True)
class AirPackSensorDescription(AirPackEntityDescription, SensorEntityDescription):
    """Sensor description."""

    value_fn: Callable[[Any], Any] | None = None
    attrs_fn: Callable[[Any], dict[str, Any]] | None = None


def _temp(key: str, **kw) -> AirPackSensorDescription:
    return AirPackSensorDescription(
        key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        **kw,
    )


def _enum(key: str, register: str, mapping: dict[int, str], **kw) -> AirPackSensorDescription:
    return AirPackSensorDescription(
        key=key,
        register=register,
        device_class=SensorDeviceClass.ENUM,
        options=list(dict.fromkeys(mapping.values())),
        value_fn=lambda v, m=mapping: m.get(v),
        **kw,
    )


def _flow(key: str, **kw) -> AirPackSensorDescription:
    return AirPackSensorDescription(
        key=key,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        **kw,
    )


def _percent(key: str, **kw) -> AirPackSensorDescription:
    return AirPackSensorDescription(
        key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        **kw,
    )


def _volt(key: str) -> AirPackSensorDescription:
    return AirPackSensorDescription(
        key=key,
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
    )


SENSORS: tuple[AirPackSensorDescription, ...] = (
    _temp("outside_temperature"),
    _temp("supply_temperature"),
    _temp("exhaust_temperature"),
    _temp("fpx_temperature"),
    _temp("duct_supply_temperature"),
    _temp("gwc_temperature"),
    _temp("ambient_temperature"),
    _temp("required_temperature"),
    _flow("supply_air_flow"),
    _flow("exhaust_air_flow"),
    _flow("supply_flowrate", entity_registry_enabled_default=False),
    _flow("exhaust_flowrate", entity_registry_enabled_default=False),
    _percent("supply_percentage"),
    _percent("exhaust_percentage"),
    _percent("min_percentage", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    _percent("max_percentage", entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
    _percent("supply_filter_wear"),
    _percent("exhaust_filter_wear"),
    _percent(KEY_EFFICIENCY, suggested_display_precision=0),
    AirPackSensorDescription(key="supply_filter_date", device_class=SensorDeviceClass.DATE),
    AirPackSensorDescription(key="exhaust_filter_date", device_class=SensorDeviceClass.DATE),
    _enum("operating_mode", "mode", OPERATING_MODES),
    _enum("active_function", "special_mode", SPECIAL_MODES),
    _enum("bypass_state", "bypass_mode", BYPASS_STATES),
    _enum("gwc_state", "gwc_mode", GWC_STATES),
    _enum("comfort_state", "comfort_mode", COMFORT_STATES),
    _enum("fpx_state", "antifreeze_stage", FPX_STATES),
    _enum(
        "schedule_day", "day_of_week", WEEKDAYS,
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
    ),
    AirPackSensorDescription(
        key="schedule_period",
        register="period",
        value_fn=lambda v: v + 1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    AirPackSensorDescription(
        key=KEY_ACTIVE_ALARMS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=len,
        attrs_fn=lambda codes: {
            "codes": list(codes or []),
            "alarms": [{"code": c, "description": ALARM_DESCRIPTIONS[c]} for c in codes or []],
        },
    ),
    AirPackSensorDescription(key="stop_ahu_code", entity_category=EntityCategory.DIAGNOSTIC),
    _volt("dac_supply"),
    _volt("dac_exhaust"),
    _volt("dac_heater"),
    _volt("dac_cooler"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        AirPackSensor(coordinator, d) for d in supported_descriptions(coordinator, SENSORS)
    ]
    entities.append(AirPackFirmwareSensor(coordinator))
    async_add_entities(entities)


class AirPackSensor(AirPackEntity, SensorEntity):
    """Register-backed sensor."""

    entity_description: AirPackSensorDescription

    @property
    def native_value(self) -> Any:
        """Current value."""
        value = self.value
        if value is None:
            return None
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(value)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Extra attributes."""
        if self.entity_description.attrs_fn:
            return self.entity_description.attrs_fn(self.value)
        return None


class AirPackFirmwareSensor(AirPackEntity, SensorEntity):
    """Firmware / module versions (diagnostic)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, AirPackSensorDescription(key="firmware", register="firmware"))

    @property
    def available(self) -> bool:
        """Identity is cached, so always available when the coordinator is."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> str | None:
        """Controller firmware."""
        return self.coordinator.capabilities.identity.get("firmware")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Other identity information."""
        identity = self.coordinator.capabilities.identity
        return {k: v for k, v in identity.items() if k != "firmware"}
