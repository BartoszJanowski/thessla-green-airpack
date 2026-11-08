"""Integration behaviour: resilience, state mirroring, writes."""

from __future__ import annotations

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.thessla_green_airpack.const import CONF_READ_ONLY, DOMAIN
from custom_components.thessla_green_airpack.registers import Table

from .conftest import entity_id, setup_entry


async def _refresh(hass: HomeAssistant, entry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


def _state(hass: HomeAssistant, platform: str, key: str):
    eid = entity_id(hass, platform, key)
    assert eid, f"{platform}.{key} not created"
    return hass.states.get(eid)


async def test_setup_and_values(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED

    assert _state(hass, "sensor", "outside_temperature").state == "0.0"
    assert _state(hass, "sensor", "supply_temperature").state == "17.3"
    assert _state(hass, "sensor", "exhaust_temperature").state == "21.4"
    assert _state(hass, "sensor", "supply_air_flow").state == "120"
    assert _state(hass, "sensor", "supply_filter_wear").state == "8"
    assert _state(hass, "sensor", "heat_recovery_efficiency").state == "80.8"
    assert _state(hass, "sensor", "supply_filter_date").state == "2022-11-02"
    assert _state(hass, "sensor", "active_alarms").state == "0"
    assert _state(hass, "select", "season_mode").state == "winter"
    assert _state(hass, "switch", "power").state == "on"
    assert _state(hass, "time", "manual_airing_time_to_start").state == "13:30:00"

    fan = _state(hass, "fan", "ventilation")
    assert fan.state == "on"
    assert fan.attributes["percentage"] == 30
    assert fan.attributes["preset_mode"] == "auto"

    device = entry.runtime_data.device_info
    assert device["sw_version"] == "4.85.2"


async def test_unsupported_registers_never_break_setup(hass: HomeAssistant, fake) -> None:
    """ERV registers 4704/4711 missing (upstream issue #29) -> entities just absent."""
    await setup_entry(hass)
    assert entity_id(hass, "select", "post_heater_mode") is None
    assert entity_id(hass, "binary_sensor", "post_heater_on") is None
    # Sensors not fitted are hidden too: 0x8000 (TZ2) or raw 0 for optional
    # sensors (TN2 / TZ3, as reported by firmware 4.87).
    assert entity_id(hass, "sensor", "gwc_temperature") is None
    assert entity_id(hass, "sensor", "duct_supply_temperature") is None
    assert entity_id(hass, "sensor", "fpx_temperature") is None
    assert "gwc" not in {str(f) for f in hass.config_entries.async_entries(DOMAIN)[0].runtime_data.capabilities.features}
    # Everything else still works.
    assert _state(hass, "sensor", "ambient_temperature").state == "17.4"


async def test_absent_feature_entities_disabled(hass: HomeAssistant, fake) -> None:
    """GWC not detected -> GWC settings exist but are disabled (hidden)."""
    await setup_entry(hass)
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id(hass, "switch", "gwc_enabled"))
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_sensor_lost_at_runtime_shows_unknown(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    fake.bank[Table.INPUT][0x11] = 0x8000
    await _refresh(hass, entry)
    assert _state(hass, "sensor", "supply_temperature").state == STATE_UNKNOWN
    assert _state(hass, "sensor", "heat_recovery_efficiency").state == STATE_UNKNOWN
    assert _state(hass, "sensor", "outside_temperature").state == "0.0"


async def test_offline_then_recovers(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    fake.online = False
    await _refresh(hass, entry)
    assert _state(hass, "sensor", "outside_temperature").state == STATE_UNAVAILABLE
    fake.online = True
    await _refresh(hass, entry)
    assert _state(hass, "sensor", "outside_temperature").state == "0.0"


async def test_restart_while_offline_uses_cached_capabilities(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    fake.online = False
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    fake.online = True
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_panel_change_is_mirrored(hass: HomeAssistant, fake) -> None:
    """Changes made on the Air++ panel appear after the next poll."""
    entry = await setup_entry(hass)
    fake.bank[Table.HOLDING][0x1070] = 1  # manual
    fake.bank[Table.HOLDING][0x1071] = 0  # summer
    fake.bank[Table.HOLDING][0x1080] = 2  # fireplace
    fake.bank[Table.INPUT][0x110] = 55
    await _refresh(hass, entry)
    fan = _state(hass, "fan", "ventilation")
    assert fan.attributes["preset_mode"] == "manual"
    assert fan.attributes["percentage"] == 55
    assert _state(hass, "select", "season_mode").state == "summer"
    assert _state(hass, "select", "special_mode").state == "fireplace"
    assert _state(hass, "sensor", "active_function").state == "fireplace"


async def test_input_triggered_function_not_selectable(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    fake.bank[Table.HOLDING][0x1080] = 5  # hygrostat airing (input-triggered)
    await _refresh(hass, entry)
    assert _state(hass, "select", "special_mode").state == STATE_UNKNOWN
    assert _state(hass, "sensor", "active_function").state == "airing_hygrostat"


async def test_set_percentage_in_auto_uses_temporary_mode(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass)
    eid = entity_id(hass, "fan", "ventilation")
    await hass.services.async_call(
        "fan", "set_percentage", {"entity_id": eid, "percentage": 55}, blocking=True
    )
    assert fake.writes == [(0x1130, [2, 55, 1])]
    state = hass.states.get(eid)
    assert state.attributes["preset_mode"] == "temporary"
    assert state.attributes["percentage"] == 55


async def test_set_percentage_in_manual_writes_manual_airflow(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    fake.bank[Table.HOLDING][0x1070] = 1
    await _refresh(hass, entry)
    eid = entity_id(hass, "fan", "ventilation")
    await hass.services.async_call(
        "fan", "set_percentage", {"entity_id": eid, "percentage": 70}, blocking=True
    )
    assert fake.writes == [(0x1072, [70])]


async def test_set_percentage_zero_rejected(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass)
    eid = entity_id(hass, "fan", "ventilation")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "fan", "set_percentage", {"entity_id": eid, "percentage": 0}, blocking=True
        )
    assert fake.writes == []


async def test_preset_modes(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass)
    eid = entity_id(hass, "fan", "ventilation")
    await hass.services.async_call(
        "fan", "set_preset_mode", {"entity_id": eid, "preset_mode": "manual"}, blocking=True
    )
    assert fake.writes[-1] == (0x1130, [1])
    assert hass.states.get(eid).attributes["preset_mode"] == "manual"
    await hass.services.async_call(
        "fan", "set_preset_mode", {"entity_id": eid, "preset_mode": "auto"}, blocking=True
    )
    assert fake.writes[-1] == (0x1130, [0])


async def test_select_switch_number_time_writes(hass: HomeAssistant, fake) -> None:
    fake.bank[Table.INPUT][0x14] = 215  # duct exchangers (TN2): supply temperature settings shown
    await setup_entry(hass)
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": entity_id(hass, "select", "special_mode"), "option": "open_windows"},
        blocking=True,
    )
    assert fake.writes[-1] == (0x1080, [10])
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id(hass, "switch", "power")}, blocking=True
    )
    assert fake.writes[-1] == (0x1123, [0])
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id(hass, "switch", "bypass_enabled")}, blocking=True
    )
    assert fake.writes[-1] == (0x10E0, [1])  # inverted register
    await hass.services.async_call(
        "number", "set_value",
        {"entity_id": entity_id(hass, "number", "supply_air_temperature_manual"), "value": 21.5},
        blocking=True,
    )
    assert fake.writes[-1] == (0x1074, [43])
    await hass.services.async_call(
        "time", "set_value",
        {"entity_id": entity_id(hass, "time", "manual_airing_time_to_start"), "time": "06:30:00"},
        blocking=True,
    )
    assert fake.writes[-1] == (0x107B, [0x0630])


async def test_number_out_of_range_rejected(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": entity_id(hass, "number", "air_flow_rate_manual"), "value": 5},
            blocking=True,
        )
    assert fake.writes == []


async def test_filter_buttons(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass)
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id(hass, "button", "exhaust_filter_replaced")},
        blocking=True,
    )
    assert fake.writes[-1] == (0x1FFF, [0x21])


async def test_read_only_mode_blocks_writes(hass: HomeAssistant, fake) -> None:
    await setup_entry(hass, options={CONF_READ_ONLY: True})
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": entity_id(hass, "switch", "power")}, blocking=True
        )
    assert fake.writes == []


async def test_active_alarms(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    fake.bank[Table.HOLDING][0x2001] = 1  # error summary
    fake.bank[Table.HOLDING][0x200D] = 1  # S13
    await _refresh(hass, entry)
    state = _state(hass, "sensor", "active_alarms")
    assert state.state == "1"
    assert state.attributes["codes"] == ["S13"]
    assert _state(hass, "binary_sensor", "error").state == "on"


async def test_redetect_picks_up_new_hardware(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    assert entity_id(hass, "sensor", "gwc_temperature") is None
    fake.bank[Table.INPUT][0x15] = 95  # GWC sensor now fitted: 9.5 °C
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id(hass, "button", "redetect")}, blocking=True
    )
    await hass.async_block_till_done()
    assert _state(hass, "sensor", "gwc_temperature").state == "9.5"
    assert entry.state is ConfigEntryState.LOADED


async def test_diagnostics(hass: HomeAssistant, fake) -> None:
    from custom_components.thessla_green_airpack.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry = await setup_entry(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"]["host"] == "**REDACTED**"
    assert "post_heater_mode" not in diag["capabilities"]["supported"]
    assert diag["raw"]["input:16"] == 0
    # No serial number anywhere (README promises this).
    assert all(diag["raw"][f"input:{a}"] == "**REDACTED**" for a in range(0x18, 0x1E))
    assert "1a2b" not in str(diag) and "3c4d" not in str(diag)


async def test_unload(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert DOMAIN not in {e.domain for e in hass.config_entries.async_loaded_entries(DOMAIN)}


async def test_entity_categories(hass: HomeAssistant, fake) -> None:
    """Controls = what the Air++ home screen has; settings live under Configuration."""
    await setup_entry(hass)
    registry = er.async_get(hass)
    for platform, key in (
        ("number", "air_flow_rate_manual"),
        ("number", "supply_air_temperature_manual"),
        ("switch", "bypass_enabled"),
    ):
        assert registry.async_get(entity_id(hass, platform, key)).entity_category == "config"
    for key in ("air_flow_rate_temporary", "supply_air_temperature_temporary"):
        reg = registry.async_get(entity_id(hass, "number", key))
        assert reg.entity_category == "config"
        assert reg.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    for platform, key in (("fan", "ventilation"), ("switch", "power"), ("select", "season_mode")):
        assert registry.async_get(entity_id(hass, platform, key)).entity_category is None


async def test_migration_hides_temporary_settings(hass: HomeAssistant, fake) -> None:
    """Existing installs (minor version 1) get the Temporary settings hidden once."""
    from .conftest import SERIAL, make_entry

    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, minor_version=1)
    registry = er.async_get(hass)
    existing = registry.async_get_or_create(
        "number", DOMAIN, f"{SERIAL}_supply_air_temperature_temporary", config_entry=entry
    )
    assert existing.disabled_by is None
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(existing.entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert entry.minor_version == 2


async def test_special_functions_option(hass: HomeAssistant, fake) -> None:
    """Functions not configured by the installer (e.g. hood) can be hidden in Options."""
    from custom_components.thessla_green_airpack.const import CONF_SPECIAL_FUNCTIONS

    entry = await setup_entry(hass)
    eid = entity_id(hass, "select", "special_mode")
    assert "hood" in hass.states.get(eid).attributes["options"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "scan_interval": 30, "timeout": 3, "request_delay": 0, "read_only": False,
            CONF_SPECIAL_FUNCTIONS: ["fireplace", "airing", "open_windows", "empty_house"],
        },
    )
    await hass.async_block_till_done()
    options = hass.states.get(eid).attributes["options"]
    assert options == ["none", "fireplace", "airing", "open_windows", "empty_house"]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "select", "select_option", {"entity_id": eid, "option": "hood"}, blocking=True
        )
    assert fake.writes == []
    # A hood activated by the OK input still shows in the Active function sensor.
    fake.bank[Table.HOLDING][0x1080] = 1
    await _refresh(hass, entry)
    assert hass.states.get(eid).state == STATE_UNKNOWN
    assert _state(hass, "sensor", "active_function").state == "hood"


async def test_sidebar_panel_and_device_link(hass: HomeAssistant, fake) -> None:
    """The flow diagram panel is registered and linked from the device page."""
    from unittest.mock import AsyncMock, patch

    from homeassistant.helpers import device_registry as dr

    hass.config.components.add("frontend")
    with (
        patch(
            "homeassistant.components.panel_custom.async_register_panel", new=AsyncMock()
        ) as register,
        patch("homeassistant.components.frontend.async_remove_panel") as remove,
    ):
        entry = await setup_entry(hass)
        register.assert_awaited_once()
        kwargs = register.await_args.kwargs
        assert kwargs["frontend_url_path"] == "airpack4"
        assert kwargs["webcomponent_name"] == "thessla-airpack-panel"
        assert kwargs["module_url"].startswith("/thessla_green_airpack/thessla-airpack-card.js?v=")

        device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.unique_id)})
        assert device.configuration_url == "homeassistant://airpack4"

        assert await hass.config_entries.async_unload(entry.entry_id)
        remove.assert_called_once()


async def test_open_windows_intensity_auto(hass: HomeAssistant, fake) -> None:
    """0x108F = 101 means AUTO (intensity from the active mode), not 101 %."""
    fake.bank[Table.HOLDING][0x108F] = 101
    entry = await setup_entry(hass)
    number = entity_id(hass, "number", "open_window_coef")
    switch = entity_id(hass, "switch", "open_window_coef_auto")
    assert hass.states.get(number).state == STATE_UNKNOWN
    assert hass.states.get(number).attributes["max"] == 100
    assert hass.states.get(switch).state == "on"

    # Setting an intensity leaves AUTO, like lowering it on the Air++ panel.
    await hass.services.async_call(
        "number", "set_value", {"entity_id": number, "value": 80}, blocking=True
    )
    assert fake.writes[-1] == (0x108F, [80])
    await _refresh(hass, entry)
    assert hass.states.get(number).state == "80"
    assert hass.states.get(switch).state == "off"

    # Turning off again keeps the custom value; turning on writes AUTO.
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    assert fake.writes[-1] == (0x108F, [80])
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
    assert fake.writes[-1] == (0x108F, [101])
    await _refresh(hass, entry)
    assert hass.states.get(number).state == STATE_UNKNOWN

    # Leaving AUTO with the switch starts at 100 %.
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    assert fake.writes[-1] == (0x108F, [100])


async def test_number_temperatures_follow_unit_system(hass: HomeAssistant, fake) -> None:
    """Number state goes through Home Assistant's unit conversion (°C -> °F)."""
    from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

    hass.config.units = US_CUSTOMARY_SYSTEM
    await setup_entry(hass)
    state = hass.states.get(entity_id(hass, "number", "min_bypass_temperature"))
    assert state.attributes["unit_of_measurement"] == "°F"
    assert float(state.state) == pytest.approx(52.7, abs=0.1)  # 11.5 °C
