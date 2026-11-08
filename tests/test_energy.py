"""Recovered heat: power formula, energy integration and statistics."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.thessla_green_airpack import energy as e
from custom_components.thessla_green_airpack.energy import RecoveredEnergy, heat_recovery_power
from custom_components.thessla_green_airpack.registers import Table

from .conftest import entity_id, setup_entry

TZ = ZoneInfo("Europe/Warsaw")


def at(*args: int) -> datetime:
    return datetime(*args, tzinfo=TZ)


# -- power ----------------------------------------------------------------------


def test_power_formula() -> None:
    # 140 m³/h heated from -2 °C to 17 °C: 140 × 0.335 × 19 ≈ 891 W
    assert heat_recovery_power(140, -2.0, 17.0, False) == pytest.approx(891.1, abs=0.1)


def test_power_zero_when_not_recovering_heat() -> None:
    assert heat_recovery_power(140, 0.0, 17.0, True) == 0.0  # bypass open
    assert heat_recovery_power(140, 0.0, 17.0, False, running=False) == 0.0  # unit off
    assert heat_recovery_power(140, 25.0, 22.0, False) == 0.0  # summer: no heat gained
    assert heat_recovery_power(0, 0.0, 17.0, False) == 0.0


def test_power_unknown_without_inputs() -> None:
    assert heat_recovery_power(None, 0.0, 17.0, False) is None
    assert heat_recovery_power(140, None, 17.0, False) is None
    assert heat_recovery_power(140, 0.0, None, False) is None


# -- integration ------------------------------------------------------------------


def test_integrates_trapezoid() -> None:
    rec = RecoveredEnergy(max_gap=timedelta(hours=1))
    rec.add_sample(at(2026, 11, 8, 10, 0), 1000)
    rec.add_sample(at(2026, 11, 8, 10, 30), 1000)
    rec.add_sample(at(2026, 11, 8, 11, 0), 0)  # ramp 1000 -> 0 over 30 min = 0.25 kWh
    values = rec.values(at(2026, 11, 8, 11, 0))
    assert values[e.TOTAL] == pytest.approx(0.75)
    assert values[e.TODAY] == pytest.approx(0.75)
    assert values[e.LAST_24H] == pytest.approx(0.75)


def test_gaps_and_unknown_power_are_not_integrated() -> None:
    rec = RecoveredEnergy(max_gap=timedelta(minutes=10))
    rec.add_sample(at(2026, 11, 8, 10, 0), 1000)
    rec.add_sample(at(2026, 11, 8, 11, 0), 1000)  # 1 h gap (HA down) -> skipped
    assert rec.total == 0
    rec.add_sample(at(2026, 11, 8, 11, 6), None)  # sensor lost
    rec.add_sample(at(2026, 11, 8, 11, 12), 1000)
    assert rec.total == 0
    rec.add_sample(at(2026, 11, 8, 11, 18), 1000)
    assert rec.total == pytest.approx(0.1)


def _run(rec: RecoveredEnergy, start: datetime, end: datetime, power: float) -> None:
    """Constant power, one sample every 5 minutes (wall clock, DST-safe)."""
    now = start
    while now <= end:
        rec.add_sample(now, power)
        now = (now.astimezone(ZoneInfo("UTC")) + timedelta(minutes=5)).astimezone(TZ)


def test_calendar_periods_reset() -> None:
    rec = RecoveredEnergy()
    _run(rec, at(2025, 12, 31, 22, 0), at(2026, 1, 1, 2, 0), 1000)  # 4 h at 1 kW
    values = rec.values(at(2026, 1, 1, 2, 0))
    assert values[e.TOTAL] == pytest.approx(4.0)
    assert values[e.TODAY] == pytest.approx(2.0)
    assert values[e.THIS_MONTH] == pytest.approx(2.0)
    assert values[e.THIS_YEAR] == pytest.approx(2.0)
    assert values[e.LAST_24H] == pytest.approx(4.0)
    assert values[e.LAST_30_DAYS] == pytest.approx(4.0)
    assert values[e.LAST_12_MONTHS] == pytest.approx(4.0)


def test_rolling_windows() -> None:
    rec = RecoveredEnergy()
    # 1 kWh on each of 40 days, as 1 h at 1 kW around noon.
    for day in range(40):
        noon = at(2026, 10, 1, 12, 0) + timedelta(days=day)
        _run(rec, noon, noon + timedelta(hours=1), 1000)
    now = at(2026, 11, 9, 18, 0)  # day 40 = Nov 9
    values = rec.values(now)
    assert values[e.TOTAL] == pytest.approx(40.0)
    assert values[e.TODAY] == pytest.approx(1.0)
    assert values[e.LAST_24H] == pytest.approx(1.0)  # only today's noon hour
    assert values[e.LAST_30_DAYS] == pytest.approx(30.0)  # Oct 11 .. Nov 9
    assert values[e.THIS_MONTH] == pytest.approx(9.0)
    assert values[e.LAST_12_MONTHS] == pytest.approx(40.0)
    assert values[e.THIS_YEAR] == pytest.approx(40.0)
    # 25 h later the 24 h window is empty, the lifetime total is unchanged.
    later = now + timedelta(hours=25)
    assert rec.values(later)[e.LAST_24H] == 0
    assert rec.values(later)[e.TOTAL] == pytest.approx(40.0)


def test_twelve_months_window_and_pruning() -> None:
    rec = RecoveredEnergy()
    for month in range(1, 13):
        start = at(2025, month, 15, 12, 0)
        _run(rec, start, start + timedelta(hours=1), 1000)
    for month in range(1, 4):
        start = at(2026, month, 15, 12, 0)
        _run(rec, start, start + timedelta(hours=1), 1000)
    values = rec.values(at(2026, 3, 20, 0, 0))
    assert values[e.TOTAL] == pytest.approx(15.0)
    assert values[e.THIS_YEAR] == pytest.approx(3.0)
    assert values[e.LAST_12_MONTHS] == pytest.approx(12.0)  # Apr 2025 .. Mar 2026
    assert len(rec.months) <= 12
    assert len(rec.days) <= 30
    assert len(rec.hours) <= 24


def test_storage_roundtrip() -> None:
    rec = RecoveredEnergy()
    _run(rec, at(2026, 11, 8, 10, 0), at(2026, 11, 8, 11, 0), 1200)
    restored = RecoveredEnergy.from_dict(rec.as_dict())
    now = at(2026, 11, 8, 11, 0)
    assert restored.values(now) == rec.values(now)
    # The last sample is not restored: the restart gap is not integrated.
    restored.add_sample(at(2026, 11, 8, 11, 5), 1200)
    assert restored.total == rec.total


# -- entities ---------------------------------------------------------------------


def _state(hass: HomeAssistant, key: str):
    eid = entity_id(hass, "sensor", key)
    assert eid, f"sensor.{key} not created"
    return hass.states.get(eid)


async def test_recovery_entities(hass: HomeAssistant, fake, freezer: FrozenDateTimeFactory) -> None:
    await hass.config.async_set_time_zone("Europe/Warsaw")
    freezer.move_to("2026-11-08 10:00:00+01:00")
    entry = await setup_entry(hass)

    # 120 m³/h, 0.0 °C -> 17.3 °C: 120 × 0.335 × 17.3 ≈ 695.5 W
    power = _state(hass, "heat_recovery_power")
    assert float(power.state) == pytest.approx(695.5, abs=0.1)
    assert power.attributes["unit_of_measurement"] == "W"
    assert float(_state(hass, e.TOTAL).state) == 0

    freezer.tick(timedelta(minutes=6))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    expected = 695.5 * 0.1 / 1000  # 6 min
    for key in (e.TOTAL, e.TODAY, e.LAST_24H, e.LAST_30_DAYS, e.THIS_MONTH, e.LAST_12_MONTHS, e.THIS_YEAR):
        state = _state(hass, key)
        assert float(state.state) == pytest.approx(expected, abs=0.001), key
        assert state.attributes["unit_of_measurement"] == "kWh"

    assert _state(hass, e.TOTAL).attributes["state_class"] == "total_increasing"
    today = _state(hass, e.TODAY)
    assert today.attributes["state_class"] == "total"
    assert dt_util.parse_datetime(today.attributes["last_reset"]) == dt_util.start_of_local_day(
        dt_util.now()
    )
    assert "state_class" not in _state(hass, e.LAST_24H).attributes

    # Statistics survive a restart (reload).
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert float(_state(hass, e.TOTAL).state) == pytest.approx(expected, abs=0.001)


async def test_recovery_power_unknown_when_sensor_lost(hass: HomeAssistant, fake) -> None:
    entry = await setup_entry(hass)
    fake.bank[Table.INPUT][0x11] = 0x8000
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, "heat_recovery_power").state == STATE_UNKNOWN


async def test_recovery_absent_without_flow_data(hass: HomeAssistant, fake) -> None:
    """No measured or target airflow registers -> no recovery entities."""
    for address in (0x0100, 0x0101):
        del fake.bank[Table.HOLDING][address]
    for address in range(0x010F, 0x0116):
        del fake.bank[Table.INPUT][address]
    await setup_entry(hass)
    assert entity_id(hass, "sensor", "heat_recovery_power") is None
    assert entity_id(hass, "sensor", e.TOTAL) is None
    assert entity_id(hass, "sensor", "outside_temperature") is not None
