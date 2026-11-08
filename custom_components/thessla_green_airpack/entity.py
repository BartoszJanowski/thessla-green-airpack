"""Base entity for AirPack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import AirPackCoordinator
from .registers import Feature


@dataclass(frozen=True, kw_only=True)
class AirPackEntityDescription(EntityDescription):
    """Common description fields.

    ``register`` defaults to ``key``. ``requires`` lists extra keys that must be
    supported. ``feature`` marks optional hardware: if it was not detected the
    entity is created disabled (hidden) instead of cluttering the UI.
    """

    register: str | None = None
    requires: tuple[str, ...] = ()
    feature: Feature | None = None

    @property
    def reg_key(self) -> str:
        """Coordinator data key."""
        return self.register or self.key


def supported_descriptions(coordinator: AirPackCoordinator, descriptions) -> list:
    """Descriptions whose registers exist on this device."""
    return [
        d
        for d in descriptions
        if coordinator.is_supported(d.reg_key)
        and all(coordinator.is_supported(k) for k in d.requires)
    ]


class AirPackEntity(CoordinatorEntity[AirPackCoordinator]):
    """Entity bound to one register (or computed value)."""

    _attr_has_entity_name = True
    entity_description: AirPackEntityDescription

    def __init__(
        self, coordinator: AirPackCoordinator, description: AirPackEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_prefix}_{description.key}"
        self._attr_device_info = coordinator.device_info
        if description.translation_key is None:
            self._attr_translation_key = description.key
        feature = description.feature
        if feature is None:
            reg = coordinator.family.index.get(description.reg_key)
            feature = reg.feature if reg else None
        if not coordinator.feature_present(feature):
            self._attr_entity_registry_enabled_default = False

    @property
    def available(self) -> bool:
        """Unavailable when the last read of this register failed."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.reg_key not in self.coordinator.failed_keys
        )

    @property
    def value(self) -> Any:
        """Decoded value (None = unknown)."""
        return (self.coordinator.data or {}).get(self.entity_description.reg_key)
