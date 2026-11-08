"""Shared fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.thessla_green_airpack.const import CONF_MODEL, CONF_UNIT_ID, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .fake_airpack import SERIAL, UNIT, FakeAirPack


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations."""
    return


@pytest.fixture
def fake() -> FakeAirPack:
    """Fake device patched in place of pymodbus' TCP client."""
    device = FakeAirPack()
    with patch(
        "custom_components.thessla_green_airpack.client.AsyncModbusTcpClient",
        side_effect=device.client_factory,
    ):
        yield device


def make_entry(options: dict | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="AirPack",
        unique_id=SERIAL,
        data={
            CONF_HOST: "192.0.2.10",
            CONF_PORT: 502,
            CONF_UNIT_ID: UNIT,
            CONF_MODEL: "airpack4_400v_energypp",
        },
        options=options or {},
    )


async def setup_entry(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = make_entry(options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def entity_id(hass: HomeAssistant, platform: str, key: str) -> str | None:
    """Entity ID by unique-id key."""
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{SERIAL}_{key}")
