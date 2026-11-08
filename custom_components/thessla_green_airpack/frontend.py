"""Serve and auto-register the bundled dashboard card."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ICON, PANEL_TITLE, PANEL_URL_PATH, PANEL_WEBCOMPONENT

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "thessla-airpack-card.js"
URL_BASE = f"/{DOMAIN}"
_DATA_REGISTERED = f"{DOMAIN}_card_registered"
_DATA_PANEL = f"{DOMAIN}_panel_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the card JS and add it to every dashboard (no manual resource)."""
    if hass.data.get(_DATA_REGISTERED):
        return
    if getattr(hass, "http", None) is None:
        _LOGGER.debug("HTTP not available; dashboard card not registered")
        return
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig
    except ImportError:  # pragma: no cover
        return

    directory = Path(__file__).parent / "frontend"
    version = await hass.async_add_executor_job(_read_version)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(directory), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILENAME}?v={version}")
    hass.data[_DATA_REGISTERED] = True


async def async_register_panel(hass: HomeAssistant) -> None:
    """Add the "AirPack4" sidebar panel showing the live flow diagram."""
    if hass.data.get(_DATA_PANEL) or "frontend" not in hass.config.components:
        return
    from homeassistant.components import panel_custom

    version = await hass.async_add_executor_job(_read_version)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_WEBCOMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{URL_BASE}/{CARD_FILENAME}?v={version}",
    )
    hass.data[_DATA_PANEL] = True


def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel (when the last AirPack is unloaded)."""
    if not hass.data.pop(_DATA_PANEL, False):
        return
    from homeassistant.components import frontend

    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)


def _read_version() -> str:
    manifest = Path(__file__).parent / "manifest.json"
    return json.loads(manifest.read_text())["version"]
