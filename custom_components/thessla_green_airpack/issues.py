"""Repair issues (Settings -> System -> Repairs)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

BYPASS_MODE_ISSUE = "bypass_mode_not_recommended"
RECOMMENDED_BYPASS_MODE = 1


def bypass_issue_id(entry: ConfigEntry) -> str:
    """Issue ID for one AirPack."""
    return f"{BYPASS_MODE_ISSUE}_{entry.entry_id}"


@callback
def async_update_issues(hass: HomeAssistant, entry: ConfigEntry, data: dict[str, Any]) -> None:
    """Bypass modes 2 / 3: the manual says AirPack4 should use mode 1 only."""
    mode = data.get("bypass_user_mode")
    if mode is None:
        return  # unknown right now: keep the current state
    if mode == RECOMMENDED_BYPASS_MODE:
        ir.async_delete_issue(hass, DOMAIN, bypass_issue_id(entry))
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        bypass_issue_id(entry),
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=BYPASS_MODE_ISSUE,
        translation_placeholders={"name": entry.title, "mode": str(mode)},
        data={"entry_id": entry.entry_id},
    )


@callback
def async_clear_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the issues of an unloaded entry."""
    ir.async_delete_issue(hass, DOMAIN, bypass_issue_id(entry))
