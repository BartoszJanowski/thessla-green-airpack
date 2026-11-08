"""Binary sensors for Thessla Green AirPack4."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirPackConfigEntry
from .entity import AirPackEntity, AirPackEntityDescription, supported_descriptions


@dataclass(frozen=True, kw_only=True)
class AirPackBinarySensorDescription(AirPackEntityDescription, BinarySensorEntityDescription):
    """Binary sensor description."""


def _diag(key: str, enabled: bool = False, device_class=None) -> AirPackBinarySensorDescription:
    return AirPackBinarySensorDescription(
        key=key,
        device_class=device_class,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enabled,
    )


RUNNING = BinarySensorDeviceClass.RUNNING
PROBLEM = BinarySensorDeviceClass.PROBLEM

BINARY_SENSORS: tuple[AirPackBinarySensorDescription, ...] = (
    AirPackBinarySensorDescription(key="alarm", device_class=PROBLEM),
    AirPackBinarySensorDescription(key="error", device_class=PROBLEM),
    AirPackBinarySensorDescription(key="bypass_actuator", device_class=BinarySensorDeviceClass.OPENING),
    AirPackBinarySensorDescription(key="antifreeze_mode", device_class=RUNNING),
    AirPackBinarySensorDescription(key="gwc_regen_flag", device_class=RUNNING),
    AirPackBinarySensorDescription(key="constant_flow_active", device_class=RUNNING),
    AirPackBinarySensorDescription(key="post_heater_on", device_class=RUNNING),
    # outputs (coils)
    _diag("power_supply_fans", enabled=True, device_class=RUNNING),
    _diag("gwc_relay", device_class=RUNNING),
    _diag("heating_cable", device_class=RUNNING),
    _diag("duct_water_heater_pump", device_class=RUNNING),
    _diag("work_permit"),
    _diag("info_output"),
    _diag("hood_output"),
    # Raw input states. Several inputs are normally-closed (1 = OK), so no
    # problem/safety device classes here; real faults come via the S/E alarms.
    _diag("expansion", device_class=BinarySensorDeviceClass.CONNECTIVITY),
    *(
        _diag(key)
        for key in (
            "fire_alarm_input",
            "duct_heater_protection",
            "ahu_filter_protection",
            "dp_ahu_filter_overflow",
            "dp_duct_filter_overflow",
            "hood_input",
            "contamination_sensor",
            "airing_sensor",
            "airing_switch",
            "airing_mini",
            "fan_speed_1_input",
            "fan_speed_2_input",
            "fan_speed_3_input",
            "fireplace_input",
            "empty_house_input",
        )
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        AirPackBinarySensor(coordinator, d)
        for d in supported_descriptions(coordinator, BINARY_SENSORS)
    )


class AirPackBinarySensor(AirPackEntity, BinarySensorEntity):
    """Register-backed binary sensor."""

    @property
    def is_on(self) -> bool | None:
        """State."""
        value = self.reg_value
        return None if value is None else bool(value)
