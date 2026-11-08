"""Buttons for Thessla Green AirPack4."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client import AirPackError
from .const import CONF_EQUIPMENT, DOMAIN, EQUIPMENT
from .coordinator import AirPackConfigEntry, AirPackCoordinator
from .entity import AirPackEntity, AirPackEntityDescription
from .registers import FILTER_CHANGE_EXHAUST, FILTER_CHANGE_SUPPLY


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirPackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = [AirPackRedetectButton(coordinator)]
    # Filter replacement applies to units without AFC (spec 0x1FFF).
    if coordinator.is_supported("supply_filter_wear"):
        entities.append(AirPackFilterButton(coordinator, "supply_filter_replaced", FILTER_CHANGE_SUPPLY))
    if coordinator.is_supported("exhaust_filter_wear"):
        entities.append(AirPackFilterButton(coordinator, "exhaust_filter_replaced", FILTER_CHANGE_EXHAUST))
    async_add_entities(entities)


class AirPackFilterButton(AirPackEntity, ButtonEntity):
    """Confirm a filter replacement (resets wear and alarms)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AirPackCoordinator, key: str, command: int) -> None:
        super().__init__(coordinator, AirPackEntityDescription(key=key, register="filter_change"))
        self._command = command

    @property
    def available(self) -> bool:
        """Available when the device is reachable."""
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Send the filter-change command."""
        await self.coordinator.async_filter_replaced(self._command)


class AirPackRedetectButton(AirPackEntity, ButtonEntity):
    """Re-run hardware / register detection, then reload."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AirPackCoordinator) -> None:
        super().__init__(coordinator, AirPackEntityDescription(key="redetect", register="redetect"))

    @property
    def available(self) -> bool:
        """Always pressable."""
        return True

    async def async_press(self) -> None:
        """Detect and reload so new / removed entities appear."""
        coordinator = self.coordinator
        entry = coordinator.config_entry
        before = set(coordinator.detected_equipment())
        try:
            await coordinator.async_detect()
        except AirPackError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="detect_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        # Newly detected equipment (GWC, duct exchangers) gets ticked in Options.
        added = set(coordinator.detected_equipment()) - before
        if added and CONF_EQUIPMENT in entry.options:
            ticked = set(entry.options[CONF_EQUIPMENT]) | added
            self.hass.config_entries.async_update_entry(
                entry,
                options={**entry.options, CONF_EQUIPMENT: [e for e in EQUIPMENT if e in ticked]},
            )  # the options listener reloads the entry
            return
        await self.hass.config_entries.async_reload(entry.entry_id)
