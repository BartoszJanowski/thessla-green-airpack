"""Switches for Thessla Green AirPack4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirPackConfigEntry
from .entity import AirPackEntity, AirPackEntityDescription, supported_descriptions


@dataclass(frozen=True, kw_only=True)
class AirPackSwitchDescription(AirPackEntityDescription, SwitchEntityDescription):
    """Switch description; ``inverted`` registers store 0 = enabled.

    ``on_value`` / ``off_value``: on is that exact register value, turning off
    writes ``off_value`` (for registers with a special "auto" value).
    """

    inverted: bool = False
    on_value: int | None = None
    off_value: int | None = None


SWITCHES: tuple[AirPackSwitchDescription, ...] = (
    AirPackSwitchDescription(key="power", register="on_off_panel_mode"),
    # Enabling/disabling a function is a setting, not an everyday control.
    AirPackSwitchDescription(
        key="bypass_enabled", register="bypass_off", inverted=True,
        entity_category=EntityCategory.CONFIG,
    ),
    AirPackSwitchDescription(
        key="gwc_enabled", register="gwc_off", inverted=True,
        entity_category=EntityCategory.CONFIG,
    ),
    # Open windows exhaust intensity "AUTO" (101 = from the active mode); off -> 100 %,
    # the first value below AUTO on the Air++ panel.
    AirPackSwitchDescription(
        key="open_window_coef_auto", register="open_window_coef", on_value=101, off_value=100,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        AirPackSwitch(coordinator, d) for d in supported_descriptions(coordinator, SWITCHES)
    )


class AirPackSwitch(AirPackEntity, SwitchEntity):
    """Register-backed switch."""

    entity_description: AirPackSwitchDescription

    @property
    def is_on(self) -> bool | None:
        """State."""
        value = self.reg_value
        if value is None:
            return None
        if self.entity_description.on_value is not None:
            return value == self.entity_description.on_value
        return bool(value) != self.entity_description.inverted

    async def _set(self, on: bool) -> None:
        description = self.entity_description
        if description.on_value is not None:
            raw = description.on_value if on else description.off_value
            if not on and self.reg_value != description.on_value:
                return  # already a custom intensity: keep it
        else:
            raw = int(on != description.inverted)
        await self.coordinator.async_write(description.reg_key, raw)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self._set(False)
