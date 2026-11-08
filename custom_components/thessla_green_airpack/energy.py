"""Recovered heat energy: integration of the heat recovery power over time.

Pure Python (no Home Assistant imports). Times are timezone-aware datetimes
in the local time zone of the Home Assistant instance, so "today" and
"this month" follow the user's calendar.

Energy is kept in hourly, daily and monthly buckets, which gives:

* today / this month / this year (calendar periods),
* last 24 h  = current hour + 23 previous hours,
* last 30 days = today + 29 previous days,
* last 12 months = current month + 11 previous months,

plus a lifetime total that only ever increases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

# Energy keys (coordinator data keys / sensor keys)
TOTAL = "heat_recovery_energy_total"
TODAY = "heat_recovery_energy_today"
LAST_24H = "heat_recovery_energy_last_24h"
LAST_30_DAYS = "heat_recovery_energy_last_30_days"
THIS_MONTH = "heat_recovery_energy_this_month"
LAST_12_MONTHS = "heat_recovery_energy_last_12_months"
THIS_YEAR = "heat_recovery_energy_this_year"
# Data key holding the time the energy values were computed for.
VALUES_TIME = "heat_recovery_energy_time"
ENERGY_KEYS = (TOTAL, TODAY, LAST_24H, LAST_30_DAYS, THIS_MONTH, LAST_12_MONTHS, THIS_YEAR)

# Air: density 1.2 kg/m³ × specific heat 1005 J/(kg·K) / 3600 s/h ≈ 0.335 W per (m³/h · K)
AIR_HEAT_CAPACITY = 1.2 * 1005 / 3600


def heat_recovery_power(
    flow: float | None,
    outside: float | None,
    supply: float | None,
    bypass_open: bool | None,
    running: bool | None = True,
) -> float | None:
    """Heat passed to the fresh air by the exchanger, W (None = unknown).

    Only heating is counted: an open bypass, a stopped unit or supply air not
    warmer than the outside air give 0 W.
    """
    if running is False or bypass_open:
        return 0.0
    if flow is None or outside is None or supply is None:
        return None
    delta = supply - outside
    if delta <= 0 or flow <= 0:
        return 0.0
    return round(flow * AIR_HEAT_CAPACITY * delta, 1)


def _hour_key(now: datetime) -> int:
    # Absolute hour number: no ambiguity on DST changes.
    return int(now.timestamp() // 3600)


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _months_back(day: date, months: int) -> str:
    index = day.year * 12 + day.month - 1 - months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass
class RecoveredEnergy:
    """Accumulates recovered heat (kWh) from periodic power samples."""

    max_gap: timedelta = timedelta(minutes=10)
    total: float = 0.0
    hours: dict[int, float] = field(default_factory=dict)
    days: dict[str, float] = field(default_factory=dict)
    months: dict[str, float] = field(default_factory=dict)
    _last_time: datetime | None = None
    _last_power: float | None = None

    def add_sample(self, now: datetime, power: float | None) -> None:
        """Add a power sample (W). Unknown power or long gaps are not integrated."""
        last_time, last_power = self._last_time, self._last_power
        self._last_time, self._last_power = now, power
        if power is None or last_power is None or last_time is None:
            return
        elapsed = now - last_time
        if elapsed <= timedelta(0) or elapsed > self.max_gap:
            return
        kwh = (last_power + power) / 2 * elapsed.total_seconds() / 3600 / 1000
        if kwh <= 0:
            return
        self.total += kwh
        # Bucket by the middle of the interval, so an interval spanning
        # midnight lands on the day it mostly belongs to.
        middle = last_time + elapsed / 2
        hour, day = _hour_key(middle), middle.date()
        self.hours[hour] = self.hours.get(hour, 0.0) + kwh
        self.days[day.isoformat()] = self.days.get(day.isoformat(), 0.0) + kwh
        self.months[_month_key(day)] = self.months.get(_month_key(day), 0.0) + kwh
        self._prune(now)

    def _prune(self, now: datetime) -> None:
        hour = _hour_key(now)
        self.hours = {h: v for h, v in self.hours.items() if h > hour - 24}
        oldest_day = (now.date() - timedelta(days=30)).isoformat()
        self.days = {d: v for d, v in self.days.items() if d > oldest_day}
        oldest_month = _months_back(now.date(), 12)
        self.months = {m: v for m, v in self.months.items() if m > oldest_month}

    def values(self, now: datetime) -> dict[str, float]:
        """All statistics at ``now``, kWh."""
        hour, today = _hour_key(now), now.date()
        oldest_day = (today - timedelta(days=30)).isoformat()
        oldest_month = _months_back(today, 12)
        year_prefix = f"{today.year:04d}-"
        return {
            k: round(v, 3)
            for k, v in {
                TOTAL: self.total,
                TODAY: self.days.get(today.isoformat(), 0.0),
                LAST_24H: sum(v for h, v in self.hours.items() if h > hour - 24),
                LAST_30_DAYS: sum(v for d, v in self.days.items() if oldest_day < d <= today.isoformat()),
                THIS_MONTH: self.months.get(_month_key(today), 0.0),
                LAST_12_MONTHS: sum(
                    v for m, v in self.months.items() if oldest_month < m <= _month_key(today)
                ),
                THIS_YEAR: sum(
                    v for m, v in self.months.items() if m.startswith(year_prefix) and m <= _month_key(today)
                ),
            }.items()
        }

    def as_dict(self) -> dict[str, Any]:
        """Serialise for storage (the last sample is not kept: restarts are gaps)."""
        return {
            "total": self.total,
            "hours": {str(h): v for h, v in self.hours.items()},
            "days": dict(self.days),
            "months": dict(self.months),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], max_gap: timedelta | None = None) -> RecoveredEnergy:
        """Deserialise from storage."""
        energy = cls(
            total=float(data.get("total", 0.0)),
            hours={int(h): float(v) for h, v in data.get("hours", {}).items()},
            days={str(d): float(v) for d, v in data.get("days", {}).items()},
            months={str(m): float(v) for m, v in data.get("months", {}).items()},
        )
        if max_gap is not None:
            energy.max_gap = max_gap
        return energy
