"""Show or hide entity groups according to Options.

Unticked special functions and equipment hide their entities: they stay in
the entity registry, disabled by the integration, and come back (with their
history) when ticked again. Entities disabled by the user, and entities that
are disabled by default for other reasons, are never enabled here.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .binary_sensor import BINARY_SENSORS
from .const import EQUIPMENT_ENTITIES, FUNCTION_ENTITIES
from .coordinator import AirPackConfigEntry
from .number import NUMBERS
from .select import SELECTS
from .sensor import SENSORS
from .switch import SWITCHES
from .time import TIMES

_LOGGER = logging.getLogger(__name__)

GROUPED_KEYS: frozenset[str] = frozenset(
    key
    for groups in (FUNCTION_ENTITIES, EQUIPMENT_ENTITIES)
    for keys in groups.values()
    for key in keys
)

# Grouped entities that are disabled by default anyway (diagnostic inputs etc.):
# ticking their group must not enable them.
DISABLED_BY_DEFAULT: frozenset[str] = frozenset(
    d.key
    for descriptions in (BINARY_SENSORS, NUMBERS, SELECTS, SENSORS, SWITCHES, TIMES)
    for d in descriptions
    if d.key in GROUPED_KEYS and d.entity_registry_enabled_default is False
)


def async_sync_entity_visibility(hass: HomeAssistant, entry: AirPackConfigEntry) -> None:
    """Apply Options to the entity registry (call before platforms are set up)."""
    coordinator = entry.runtime_data
    hidden = coordinator.hidden_keys
    prefix = f"{coordinator.unique_prefix}_"
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        key = reg_entry.unique_id.removeprefix(prefix)
        if key not in GROUPED_KEYS:
            continue
        if key in hidden:
            if reg_entry.disabled_by is None:
                _LOGGER.debug("Hiding %s (unticked in Options)", reg_entry.entity_id)
                registry.async_update_entity(
                    reg_entry.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
                )
        elif (
            reg_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
            and key not in DISABLED_BY_DEFAULT
        ):
            _LOGGER.debug("Showing %s (ticked in Options)", reg_entry.entity_id)
            registry.async_update_entity(reg_entry.entity_id, disabled_by=None)
