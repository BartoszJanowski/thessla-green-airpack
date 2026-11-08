"""Fix flows for repair issues."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .issues import RECOMMENDED_BYPASS_MODE


class BypassModeFixFlow(RepairsFlow):
    """Confirm, then set the bypass back to mode 1."""

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Start."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Warning + confirmation."""
        errors: dict[str, str] = {}
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry is None or getattr(entry, "runtime_data", None) is None:
                return self.async_abort(reason="not_loaded")
            try:
                await entry.runtime_data.async_write("bypass_user_mode", RECOMMENDED_BYPASS_MODE)
            except HomeAssistantError:
                errors["base"] = "write_failed"
            else:
                return self.async_create_entry(data={})
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}), errors=errors)


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Fix flow for an issue."""
    return BypassModeFixFlow((data or {})["entry_id"])
