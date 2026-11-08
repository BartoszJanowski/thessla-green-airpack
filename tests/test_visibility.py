"""Options -> which special-function settings and equipment entities are shown."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.thessla_green_airpack.const import (
    CONF_EQUIPMENT,
    CONF_SPECIAL_FUNCTIONS,
    DOMAIN,
    EQUIPMENT_ENTITIES,
    FUNCTION_ENTITIES,
    SPECIAL_FUNCTIONS,
)
from custom_components.thessla_green_airpack.registers import Table

from .conftest import SERIAL, entity_id, make_entry, setup_entry

INTEGRATION = er.RegistryEntryDisabler.INTEGRATION
USER = er.RegistryEntryDisabler.USER


def _disabled_by(hass: HomeAssistant, platform: str, key: str):
    eid = entity_id(hass, platform, key)
    assert eid, f"{platform}.{key} not created"
    return er.async_get(hass).async_get(eid).disabled_by


async def _set_options(hass: HomeAssistant, entry, functions: list[str], equipment: list[str]) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "scan_interval": 30, "timeout": 3, "request_delay": 0, "read_only": False,
            CONF_SPECIAL_FUNCTIONS: functions, CONF_EQUIPMENT: equipment,
        },
    )
    await hass.async_block_till_done()


def test_groups_reference_real_entities() -> None:
    from custom_components.thessla_green_airpack.visibility import GROUPED_KEYS
    from custom_components.thessla_green_airpack import (
        binary_sensor, number, select, sensor, switch, time,
    )

    keys = {
        d.key
        for module in (binary_sensor, number, select, sensor, switch, time)
        for name in ("BINARY_SENSORS", "NUMBERS", "SELECTS", "SENSORS", "SWITCHES", "TIMES")
        for d in getattr(module, name, ())
    }
    assert GROUPED_KEYS <= keys, GROUPED_KEYS - keys
    assert set(FUNCTION_ENTITIES) == set(SPECIAL_FUNCTIONS)


async def test_defaults_without_detected_equipment(hass: HomeAssistant, fake) -> None:
    """No TN2 / TZ3, ERV registers present: only special-function settings shown."""
    fake.bank[Table.HOLDING][0x1260] = 0
    fake.bank[Table.HOLDING][0x1267] = 2  # answers like on firmware 4.87 without ERV
    entry = await setup_entry(hass)
    assert entry.runtime_data.equipment == []
    assert _disabled_by(hass, "number", "hood_supply_coef") is None
    assert _disabled_by(hass, "select", "comfort_mode_panel") is INTEGRATION
    assert _disabled_by(hass, "sensor", "comfort_state") is INTEGRATION
    assert _disabled_by(hass, "sensor", "required_temperature") is INTEGRATION
    assert _disabled_by(hass, "select", "post_heater_mode") is INTEGRATION
    assert _disabled_by(hass, "binary_sensor", "post_heater_on") is INTEGRATION
    assert _disabled_by(hass, "number", "fan_speed_1_coef") is INTEGRATION
    assert _disabled_by(hass, "number", "airing_bathroom_coef") is INTEGRATION
    assert _disabled_by(hass, "number", "contamination_coef") is INTEGRATION
    assert _disabled_by(hass, "number", "airing_switch_coef") is INTEGRATION
    assert _disabled_by(hass, "switch", "gwc_enabled") is INTEGRATION
    # Not grouped: unchanged.
    assert _disabled_by(hass, "switch", "bypass_enabled") is None


async def test_detected_duct_exchangers_shown(hass: HomeAssistant, fake) -> None:
    fake.bank[Table.INPUT][0x14] = 215  # TN2 21.5 °C
    entry = await setup_entry(hass)
    assert entry.runtime_data.equipment == ["duct"]
    assert _disabled_by(hass, "select", "comfort_mode_panel") is None
    assert _disabled_by(hass, "sensor", "duct_supply_temperature") is None


async def test_options_hide_and_show_groups(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    others = ["fireplace", "airing", "open_windows", "empty_house"]
    await _set_options(hass, entry, others, ["duct", "airs"])
    assert _disabled_by(hass, "number", "hood_supply_coef") is INTEGRATION
    assert _disabled_by(hass, "number", "hood_exhaust_coef") is INTEGRATION
    assert _disabled_by(hass, "number", "fireplace_mode_time") is None
    assert _disabled_by(hass, "select", "comfort_mode_panel") is None
    assert _disabled_by(hass, "number", "fan_speed_1_coef") is None
    # Diagnostic inputs stay disabled by default even when their group is ticked.
    assert _disabled_by(hass, "binary_sensor", "fan_speed_1_input") is INTEGRATION
    assert hass.states.get(entity_id(hass, "select", "comfort_mode_panel")).state == "eco"

    await _set_options(hass, entry, ["hood", *others], [])
    assert _disabled_by(hass, "number", "hood_supply_coef") is None
    assert _disabled_by(hass, "select", "comfort_mode_panel") is INTEGRATION
    assert _disabled_by(hass, "number", "fan_speed_1_coef") is INTEGRATION


async def test_user_disabled_entities_untouched(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    registry = er.async_get(hass)
    registry.async_update_entity(entity_id(hass, "number", "fan_speed_2_coef"), disabled_by=USER)
    await _set_options(hass, entry, list(SPECIAL_FUNCTIONS), ["airs"])
    assert _disabled_by(hass, "number", "fan_speed_1_coef") is None
    assert _disabled_by(hass, "number", "fan_speed_2_coef") is USER


async def test_existing_install_hides_unticked(hass: HomeAssistant, fake) -> None:
    """Entities created enabled by 1.1.x get hidden on the first start of 1.2."""
    entry = make_entry({CONF_SPECIAL_FUNCTIONS: ["fireplace", "airing", "open_windows", "empty_house"]})
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = {
        key: registry.async_get_or_create(platform, DOMAIN, f"{SERIAL}_{key}", config_entry=entry)
        for platform, key in (
            ("select", "comfort_mode_panel"),
            ("number", "hood_supply_coef"),
            ("number", "airing_bathroom_coef"),
            ("number", "fireplace_mode_time"),
        )
    }
    assert all(e.disabled_by is None for e in old.values())
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(old["comfort_mode_panel"].entity_id).disabled_by is INTEGRATION
    assert registry.async_get(old["hood_supply_coef"].entity_id).disabled_by is INTEGRATION
    assert registry.async_get(old["airing_bathroom_coef"].entity_id).disabled_by is INTEGRATION
    assert registry.async_get(old["fireplace_mode_time"].entity_id).disabled_by is None


async def test_redetect_ticks_new_equipment(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    await _set_options(hass, entry, list(SPECIAL_FUNCTIONS), ["airs"])
    assert _disabled_by(hass, "switch", "gwc_enabled") is INTEGRATION
    fake.bank[Table.INPUT][0x15] = 95  # GWC sensor (TZ3) fitted
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id(hass, "button", "redetect")}, blocking=True
    )
    await hass.async_block_till_done()
    assert entry.options[CONF_EQUIPMENT] == ["gwc", "airs"]
    assert _disabled_by(hass, "switch", "gwc_enabled") is None
    assert hass.states.get(entity_id(hass, "sensor", "gwc_temperature")).state == "9.5"


def test_every_equipment_has_label() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).parent.parent / "custom_components" / DOMAIN
    for lang in ("en", "pl"):
        data = json.loads((root / "translations" / f"{lang}.json").read_text())
        assert set(data["selector"]["equipment"]["options"]) == set(EQUIPMENT_ENTITIES)
