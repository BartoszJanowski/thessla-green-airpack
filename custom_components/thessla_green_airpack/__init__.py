"""Thessla Green AirPack4 integration (Modbus TCP)."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .client import AirPackClient
from .const import (
    CONF_READ_ONLY,
    CONF_REQUEST_DELAY,
    CONF_TIMEOUT,
    CONF_UNIT_ID,
    DEFAULT_READ_ONLY,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .coordinator import AirPackConfigEntry, AirPackCoordinator
from .frontend import async_register_card

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the dashboard card once."""
    await async_register_card(hass)
    return True


# Entities that became "disabled by default" after first release (minor version 2).
HIDDEN_IN_V1_2 = ("air_flow_rate_temporary", "supply_air_temperature_temporary")


async def async_migrate_entry(hass: HomeAssistant, entry: AirPackConfigEntry) -> bool:
    """Migrate older config entries."""
    if entry.version > 1:
        return False
    if entry.minor_version < 2:
        registry = er.async_get(hass)
        prefix = entry.unique_id or entry.entry_id
        for key in HIDDEN_IN_V1_2:
            entity_id = registry.async_get_entity_id("number", DOMAIN, f"{prefix}_{key}")
            if entity_id and (reg_entry := registry.async_get(entity_id)) and reg_entry.disabled_by is None:
                registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
        hass.config_entries.async_update_entry(entry, minor_version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AirPackConfigEntry) -> bool:
    """Set up an AirPack from a config entry."""
    client = AirPackClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_UNIT_ID],
        timeout=entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        request_delay=entry.options.get(CONF_REQUEST_DELAY, DEFAULT_REQUEST_DELAY) / 1000,
        read_only=entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY),
    )
    coordinator = AirPackCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.close()
        raise
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: AirPackConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AirPackConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.close()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: AirPackConfigEntry) -> None:
    """Delete cached capabilities when the entry is removed."""
    from homeassistant.helpers.storage import Store

    from .const import STORAGE_VERSION

    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
