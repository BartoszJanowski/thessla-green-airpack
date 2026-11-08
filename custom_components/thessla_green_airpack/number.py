"""Number (setting) entities for Thessla Green AirPack."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirPackConfigEntry
from .entity import AirPackEntity, AirPackEntityDescription, supported_descriptions


@dataclass(frozen=True, kw_only=True)
class AirPackNumberDescription(AirPackEntityDescription, NumberEntityDescription):
    """Number description; min/max default to the register range."""


CONFIG = EntityCategory.CONFIG


def _pct(key: str, **kw) -> AirPackNumberDescription:
    return AirPackNumberDescription(
        key=key, native_unit_of_measurement=PERCENTAGE, native_step=1,
        mode=NumberMode.BOX, entity_category=CONFIG, **kw,
    )


def _temp(key: str, enabled: bool = True) -> AirPackNumberDescription:
    return AirPackNumberDescription(
        key=key, device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_step=0.5,
        mode=NumberMode.BOX, entity_category=CONFIG,
        entity_registry_enabled_default=enabled,
    )


def _minutes(key: str) -> AirPackNumberDescription:
    return AirPackNumberDescription(
        key=key, device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES, native_step=1,
        mode=NumberMode.BOX, entity_category=CONFIG,
    )


NUMBERS: tuple[AirPackNumberDescription, ...] = (
    # Everyday airflow control is the Ventilation fan entity; these are the
    # stored per-mode settings, so they live under Configuration.
    _pct("air_flow_rate_manual"),
    _pct("air_flow_rate_temporary", entity_registry_enabled_default=False),
    _temp("supply_air_temperature_manual"),
    _temp("supply_air_temperature_temporary", enabled=False),
    _pct("fan_speed_1_coef"),
    _pct("fan_speed_2_coef"),
    _pct("fan_speed_3_coef"),
    _pct("hood_supply_coef"),
    _pct("hood_exhaust_coef"),
    _pct("fireplace_supply_coef"),
    _pct("airing_bathroom_coef"),
    _pct("airing_coef"),
    _pct("contamination_coef"),
    _pct("empty_house_coef"),
    _pct("airing_switch_coef"),
    _pct("open_window_coef"),
    _minutes("airing_panel_mode_time"),
    _minutes("airing_switch_mode_time"),
    _minutes("airing_switch_mode_on_delay"),
    _minutes("airing_switch_mode_off_delay"),
    _minutes("fireplace_mode_time"),
    _temp("min_bypass_temperature"),
    _temp("air_temperature_summer_free_heating"),
    _temp("air_temperature_summer_free_cooling"),
    _pct("bypass_coef_1"),
    _pct("bypass_coef_2"),
    _temp("min_gwc_air_temperature"),
    _temp("max_gwc_air_temperature"),
    _temp("delta_t_gwc"),
    AirPackNumberDescription(
        key="gwc_regen_period", device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS, native_step=1,
        mode=NumberMode.BOX, entity_category=CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up numbers."""
    coordinator = entry.runtime_data
    async_add_entities(
        AirPackNumber(coordinator, d) for d in supported_descriptions(coordinator, NUMBERS)
    )


class AirPackNumber(AirPackEntity, NumberEntity):
    """Register-backed number."""

    entity_description: AirPackNumberDescription

    def __init__(self, coordinator, description: AirPackNumberDescription) -> None:
        super().__init__(coordinator, description)
        reg = coordinator.reg(description.reg_key)
        self._attr_native_min_value = float(reg.min if reg.min is not None else 0)
        self._attr_native_max_value = float(reg.max if reg.max is not None else 65535)

    @property
    def native_value(self) -> float | None:
        """Current value."""
        return self.value

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value."""
        step = self.entity_description.native_step or 1
        if step >= 1:
            value = int(round(value))
        await self.coordinator.async_write(self.entity_description.reg_key, value)
