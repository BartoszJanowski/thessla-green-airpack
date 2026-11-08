"""Bypass modes: only mode 1 is recommended for AirPack4."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from custom_components.thessla_green_airpack.const import CONF_READ_ONLY, DOMAIN
from custom_components.thessla_green_airpack.issues import bypass_issue_id
from custom_components.thessla_green_airpack.registers import Table
from custom_components.thessla_green_airpack.repairs import async_create_fix_flow

from .conftest import SERIAL, entity_id, make_entry, setup_entry

INTEGRATION = er.RegistryEntryDisabler.INTEGRATION


def _issue(hass: HomeAssistant, entry):
    return ir.async_get(hass).async_get_issue(DOMAIN, bypass_issue_id(entry))


async def _refresh(hass: HomeAssistant, entry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def _fix(hass: HomeAssistant, entry):
    issue = _issue(hass, entry)
    flow = await async_create_fix_flow(hass, issue.issue_id, issue.data)
    flow.hass = hass
    flow.handler = DOMAIN
    flow.flow_id = "test"
    result = await flow.async_step_init()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    return await flow.async_step_confirm({})


async def test_bypass_coefficients_hidden_by_default(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass)
    registry = er.async_get(hass)
    for key in ("bypass_coef_1", "bypass_coef_2"):
        assert registry.async_get(entity_id(hass, "number", key)).disabled_by is INTEGRATION
    # Mode selector and temperatures stay visible.
    assert registry.async_get(entity_id(hass, "select", "bypass_user_mode")).disabled_by is None
    assert registry.async_get(entity_id(hass, "number", "min_bypass_temperature")).disabled_by is None


async def test_existing_install_hides_bypass_coefficients_once(hass: HomeAssistant, fake) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=2)
    registry = er.async_get(hass)
    coef1 = registry.async_get_or_create("number", DOMAIN, f"{SERIAL}_bypass_coef_1", config_entry=entry)
    assert coef1.disabled_by is None
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(coef1.entity_id).disabled_by is INTEGRATION
    assert entry.minor_version == 3

    # Enabled again by the user -> stays enabled (migration runs only once).
    registry.async_update_entity(coef1.entity_id, disabled_by=None)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(coef1.entity_id).disabled_by is None


async def test_bypass_mode_labels_warn() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).parent.parent / "custom_components" / DOMAIN / "translations"
    en = json.loads((root / "en.json").read_text())["entity"]["select"]["bypass_user_mode"]["state"]
    pl = json.loads((root / "pl.json").read_text())["entity"]["select"]["bypass_user_mode"]["state"]
    assert "recommended" in en["damper_only"] and "not recommended" in en["damper_unbalance"]
    assert "zalecany" in pl["damper_only"] and "niezalecany" in pl["damper_exhaust_off"]


async def test_issue_follows_bypass_mode(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    assert _issue(hass, entry) is None
    fake.bank[Table.HOLDING][0x10EB] = 2  # changed on the Air++ panel
    await _refresh(hass, entry)
    issue = _issue(hass, entry)
    assert issue is not None and issue.is_fixable
    assert issue.translation_placeholders["mode"] == "2"
    fake.bank[Table.HOLDING][0x10EB] = 1
    await _refresh(hass, entry)
    assert _issue(hass, entry) is None


async def test_fix_flow_sets_mode_1(hass: HomeAssistant, fake) -> None:
    fake.bank[Table.HOLDING][0x10EB] = 3
    entry = await setup_entry(hass)
    result = await _fix(hass, entry)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert fake.writes[-1] == (0x10EB, [1])
    await hass.async_block_till_done()
    assert _issue(hass, entry) is None


async def test_fix_flow_read_only_shows_error(hass: HomeAssistant, fake) -> None:
    fake.bank[Table.HOLDING][0x10EB] = 2
    entry = await setup_entry(hass, {CONF_READ_ONLY: True})
    result = await _fix(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "write_failed"}
    assert fake.writes == []


async def test_issue_removed_on_unload(hass: HomeAssistant, fake) -> None:
    fake.bank[Table.HOLDING][0x10EB] = 2
    entry = await setup_entry(hass)
    assert _issue(hass, entry) is not None
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert _issue(hass, entry) is None
