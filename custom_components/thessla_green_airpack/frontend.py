"""Serve and auto-register the bundled dashboard card."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "thessla-airpack-card.js"
URL_BASE = f"/{DOMAIN}"
_DATA_REGISTERED = f"{DOMAIN}_card_registered"


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


def _read_version() -> str:
    manifest = Path(__file__).parent / "manifest.json"
    return json.loads(manifest.read_text())["version"]
