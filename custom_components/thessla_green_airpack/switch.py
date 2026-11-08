"""Switches for Thessla Green AirPack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirPackConfigEntry
from .entity import AirPackEntity, AirPackEntityDescription, supported_descriptions


@dataclass(frozen=True, kw_only=True)
class AirPackSwitchDescription(AirPackEntityDescription, SwitchEntityDescription):
    """Switch description; ``inverted`` registers store 0 = enabled."""

    inverted: bool = False


SWITCHES: tuple[AirPackSwitchDescription, ...] = (
    AirPackSwitchDescription(key="power", register="on_off_panel_mode"),
    AirPackSwitchDescription(key="bypass_enabled", register="bypass_off", inverted=True),
    AirPackSwitchDescription(key="gwc_enabled", register="gwc_off", inverted=True),
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
        value = self.value
        if value is None:
            return None
        return bool(value) != self.entity_description.inverted

    async def _set(self, on: bool) -> None:
        await self.coordinator.async_write(
            self.entity_description.reg_key, int(on != self.entity_description.inverted)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self._set(False)
