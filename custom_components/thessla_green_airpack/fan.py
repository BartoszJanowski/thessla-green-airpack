"""Ventilation fan entity: airflow % and AUTO / MANUAL / TEMPORARY presets.

Power is deliberately not part of this entity (there is a separate switch),
so the fan has no turn_on / turn_off feature.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import (
    MODE_AUTO,
    MODE_MANUAL,
    MODE_TEMPORARY,
    AirPackConfigEntry,
    AirPackCoordinator,
)
from .entity import AirPackEntity, AirPackEntityDescription

PRESETS = {MODE_AUTO: "auto", MODE_MANUAL: "manual", MODE_TEMPORARY: "temporary"}
PRESET_TO_MODE = {name: mode for mode, name in PRESETS.items()}

DESCRIPTION = AirPackEntityDescription(
    key="ventilation", register="mode", requires=("air_flow_rate_manual",)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the fan."""
    coordinator = entry.runtime_data
    if coordinator.is_supported("mode") and coordinator.is_supported("air_flow_rate_manual"):
        async_add_entities([AirPackFan(coordinator)])


class AirPackFan(AirPackEntity, FanEntity):
    """AirPack ventilation."""

    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    _attr_preset_modes = list(PRESETS.values())
    _attr_speed_count = 100

    def __init__(self, coordinator: AirPackCoordinator) -> None:
        super().__init__(coordinator, DESCRIPTION)
        self._attr_translation_key = "ventilation"

    @property
    def is_on(self) -> bool | None:
        """On unless the unit is switched off (power switch)."""
        power = (self.coordinator.data or {}).get("on_off_panel_mode")
        return True if power is None else bool(power)

    @property
    def percentage(self) -> int | None:
        """Requested supply airflow, % (special functions can exceed 100)."""
        airflow = self.coordinator.current_airflow()
        return None if airflow is None else min(100, int(airflow))

    @property
    def preset_mode(self) -> str | None:
        """AUTO / MANUAL / TEMPORARY."""
        return PRESETS.get(self.reg_value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Raw airflow (may be >100% during special functions)."""
        return {"airflow": self.coordinator.current_airflow()}

    async def async_set_percentage(self, percentage: int) -> None:
        """Set airflow like the Air++ panel does."""
        if percentage == 0:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="use_power_switch"
            )
        await self.coordinator.async_set_airflow(max(10, percentage))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Switch operating mode."""
        await self.coordinator.async_set_mode(PRESET_TO_MODE[preset_mode])
