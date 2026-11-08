"""Time entities (HH:MM settings) for Thessla Green AirPack4."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirPackConfigEntry
from .entity import AirPackEntity, AirPackEntityDescription, supported_descriptions


@dataclass(frozen=True, kw_only=True)
class AirPackTimeDescription(AirPackEntityDescription, TimeEntityDescription):
    """Time description."""


CONFIG = EntityCategory.CONFIG

TIMES: tuple[AirPackTimeDescription, ...] = (
    AirPackTimeDescription(key="manual_airing_time_to_start", entity_category=CONFIG),
    AirPackTimeDescription(key="start_gwc_regen_winter_time", entity_category=CONFIG),
    AirPackTimeDescription(key="stop_gwc_regen_winter_time", entity_category=CONFIG),
    AirPackTimeDescription(key="start_gwc_regen_summer_time", entity_category=CONFIG),
    AirPackTimeDescription(key="stop_gwc_regen_summer_time", entity_category=CONFIG),
    AirPackTimeDescription(
        key="pres_check_time", entity_category=CONFIG, entity_registry_enabled_default=False
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up time entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        AirPackTime(coordinator, d) for d in supported_descriptions(coordinator, TIMES)
    )


class AirPackTime(AirPackEntity, TimeEntity):
    """Register-backed HH:MM value (unknown = disabled on the device)."""

    @property
    def native_value(self) -> time | None:
        """Current value."""
        return self.value

    async def async_set_value(self, value: time) -> None:
        """Write a new time."""
        await self.coordinator.async_write(self.entity_description.reg_key, value)
