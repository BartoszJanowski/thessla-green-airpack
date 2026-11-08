"""Diagnostics: raw register dump and detected capabilities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import AirPackConfigEntry

TO_REDACT = {CONF_HOST, "serial", "serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AirPackConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = {
        k: (v.isoformat() if hasattr(v, "isoformat") else v)
        for k, v in (coordinator.data or {}).items()
    }
    return {
        "entry": async_redact_data({"data": dict(entry.data), "options": dict(entry.options)}, TO_REDACT),
        "family": coordinator.family.key,
        "capabilities": async_redact_data(coordinator.capabilities.as_dict(), TO_REDACT),
        "failed_keys": sorted(coordinator.failed_keys),
        "data": data,
        "raw": dict(sorted(coordinator.raw.items())),
    }
