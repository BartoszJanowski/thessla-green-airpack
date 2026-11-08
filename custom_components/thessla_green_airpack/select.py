"""Selects for Thessla Green AirPack."""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AirPackConfigEntry
from .entity import AirPackEntity, AirPackEntityDescription, supported_descriptions


@dataclass(frozen=True, kw_only=True)
class AirPackSelectDescription(AirPackEntityDescription, SelectEntityDescription):
    """Select description: raw value <-> option."""

    mapping: dict[int, str] = field(default_factory=dict)


CONFIG = EntityCategory.CONFIG

SELECTS: tuple[AirPackSelectDescription, ...] = (
    AirPackSelectDescription(key="season_mode", mapping={0: "summer", 1: "winter"}),
    # Only functions that can be activated manually; input-triggered ones are
    # shown by the "Active function" sensor.
    AirPackSelectDescription(
        key="special_mode",
        mapping={0: "none", 1: "hood", 2: "fireplace", 7: "airing", 10: "open_windows", 11: "empty_house"},
    ),
    AirPackSelectDescription(key="comfort_mode_panel", mapping={0: "eco", 1: "comfort"}),
    AirPackSelectDescription(
        key="bypass_user_mode", entity_category=CONFIG,
        mapping={1: "damper_only", 2: "damper_unbalance", 3: "damper_exhaust_off"},
    ),
    AirPackSelectDescription(
        key="gwc_regen", entity_category=CONFIG,
        mapping={0: "none", 1: "daily", 2: "temperature"},
    ),
    AirPackSelectDescription(
        key="post_heater_mode", entity_category=CONFIG,
        mapping={0: "inactive", 1: "mode_1", 2: "mode_2"},
    ),
    AirPackSelectDescription(
        key="pres_check_day", entity_category=CONFIG, entity_registry_enabled_default=False,
        mapping={0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    coordinator = entry.runtime_data
    async_add_entities(
        AirPackSelect(coordinator, d) for d in supported_descriptions(coordinator, SELECTS)
    )


class AirPackSelect(AirPackEntity, SelectEntity):
    """Register-backed select."""

    entity_description: AirPackSelectDescription

    @property
    def options(self) -> list[str]:
        """Available options."""
        return list(self.entity_description.mapping.values())

    @property
    def current_option(self) -> str | None:
        """Current option (None if the device reports a value not selectable here)."""
        return self.entity_description.mapping.get(self.value)

    async def async_select_option(self, option: str) -> None:
        """Write the selected option."""
        raw = next(k for k, v in self.entity_description.mapping.items() if v == option)
        await self.coordinator.async_write(self.entity_description.reg_key, raw)
