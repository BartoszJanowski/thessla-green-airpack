"""Config / options / reconfigure flow tests."""

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.thessla_green_airpack.const import (
    CONF_MODEL,
    CONF_READ_ONLY,
    CONF_REQUEST_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_UNIT_ID,
    DOMAIN,
)

from .conftest import setup_entry
from .fake_airpack import SERIAL

USER_INPUT = {
    CONF_NAME: "Rekuperator",
    CONF_HOST: "192.0.2.10",
    CONF_PORT: 502,
    CONF_UNIT_ID: 10,
    CONF_MODEL: "airpack4_400v_energypp",
}


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_success(hass: HomeAssistant, fake) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], dict(USER_INPUT))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Rekuperator"
    assert result["result"].unique_id == SERIAL
    assert result["data"][CONF_UNIT_ID] == 10
    assert CONF_NAME not in result["data"]


async def test_user_flow_cannot_connect(hass: HomeAssistant, fake) -> None:
    fake.online = False
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], dict(USER_INPUT))
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_wrong_unit_id(hass: HomeAssistant, fake) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_UNIT_ID: 31}
    )
    assert result["errors"] == {"base": "no_response"}


async def test_user_flow_already_configured(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], dict(USER_INPUT))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL: 10, CONF_TIMEOUT: 5, CONF_REQUEST_DELAY: 50, CONF_READ_ONLY: True},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_READ_ONLY] is True
    assert entry.runtime_data.client.read_only is True


async def test_reconfigure(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.99", CONF_PORT: 8899, CONF_UNIT_ID: 10}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "192.0.2.99"
    assert entry.data[CONF_PORT] == 8899
