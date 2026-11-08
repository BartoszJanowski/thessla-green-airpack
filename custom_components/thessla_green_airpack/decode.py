"""Pure decode/encode helpers for AirPack register values (no Home Assistant imports)."""

from __future__ import annotations

from datetime import date, time
from typing import Any

from .registers import (
    FLOW_NOT_AVAILABLE,
    TEMP_NO_SENSOR,
    TIME_DISABLED,
    DType,
    Reg,
)


class EncodeError(ValueError):
    """Value cannot be written to a register."""


def to_signed(raw: int) -> int:
    """Interpret a 16-bit value as two's complement."""
    return raw - 0x10000 if raw & 0x8000 else raw


def _bcd_byte(byte: int) -> int | None:
    hi, lo = byte >> 4, byte & 0x0F
    if hi > 9 or lo > 9:
        return None
    return hi * 10 + lo


def _to_bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


def decode(reg: Reg, raw: int) -> Any:
    """Decode a raw register value. Returns None for "no value" sentinels."""
    match reg.dtype:
        case DType.BOOL:
            return bool(raw)
        case DType.U16:
            return raw
        case DType.S16:
            return to_signed(raw)
        case DType.TEMP10:
            if raw == TEMP_NO_SENSOR:
                return None
            return round(to_signed(raw) * 0.1, 1)
        case DType.HALF:
            return raw * 0.5
        case DType.FLOW:
            return None if raw == FLOW_NOT_AVAILABLE else raw
        case DType.VOLT:
            return round(raw * 10.0 / 4095, 2)
        case DType.BCD_TIME:
            if raw in TIME_DISABLED:
                return None
            hour, minute = _bcd_byte(raw >> 8), _bcd_byte(raw & 0xFF)
            if hour is None or minute is None or hour > 23 or minute > 59:
                return None
            return time(hour, minute)
        case DType.PACKED_DATE:
            day = raw & 0x1F
            month = (raw >> 5) & 0x0F
            year = 2000 + (raw >> 9)
            try:
                return date(year, month, day)
            except ValueError:
                return None
    raise ValueError(f"Unknown dtype {reg.dtype}")


def encode(reg: Reg, value: Any) -> int:
    """Encode an engineering value to a raw register value, validating range."""
    if not reg.writable:
        raise EncodeError(f"{reg.key} is read-only")

    if reg.dtype == DType.BCD_TIME:
        if value is None:
            return TIME_DISABLED[0]
        if not isinstance(value, time):
            raise EncodeError(f"{reg.key} expects a time")
        return (_to_bcd(value.hour) << 8) | _to_bcd(value.minute)

    if isinstance(value, bool):
        value = int(value)
    if not isinstance(value, (int, float)):
        raise EncodeError(f"{reg.key} expects a number, got {value!r}")
    if reg.min is not None and value < reg.min:
        raise EncodeError(f"{reg.key}: {value} is below minimum {reg.min}")
    if reg.max is not None and value > reg.max:
        raise EncodeError(f"{reg.key}: {value} is above maximum {reg.max}")

    match reg.dtype:
        case DType.HALF:
            return int(round(value * 2))
        case DType.BOOL | DType.U16:
            if value != int(value):
                raise EncodeError(f"{reg.key} expects an integer")
            return int(value)
    raise EncodeError(f"{reg.key}: dtype {reg.dtype} is not writable")


def firmware_string(major: int | None, minor: int | None, patch: int | None) -> str | None:
    """Spec: registers 0x0004, 0x0054, 0x0002 -> "4.84.2"."""
    if major is None or minor is None:
        return None
    version = f"{major}.{minor}"
    if patch is not None:
        version += f".{patch}"
    return version


def firmware_tuple(firmware: str | None) -> tuple[int, ...]:
    """'4.85.2' -> (4, 85, 2)."""
    if not firmware:
        return ()
    try:
        return tuple(int(part) for part in firmware.split("."))
    except ValueError:
        return ()


def module_version(raw: int | None) -> str | None:
    """Spec: 0x010d -> "1.13" ([0xMMmm])."""
    if raw is None or raw in (0, 0xFFFF):
        return None
    return f"{raw >> 8}.{raw & 0xFF:02d}"


def serial_string(parts: list[int | None]) -> str | None:
    """Spec: 0x001a,0x002b,... -> "1a2b 3c4d 5e6f"."""
    if not parts or any(p is None for p in parts):
        return None
    hexes = "".join(f"{p & 0xFF:02x}" for p in parts)  # type: ignore[operator]
    if set(hexes) == {"0"}:
        return None
    return " ".join(hexes[i : i + 4] for i in range(0, len(hexes), 4))


def ascii_string(words: list[int | None]) -> str | None:
    """Two ASCII chars per register, high byte first."""
    chars: list[str] = []
    for word in words:
        if word is None:
            return None
        for byte in (word >> 8, word & 0xFF):
            if byte == 0:
                return "".join(chars).strip() or None
            if 32 <= byte < 127:
                chars.append(chr(byte))
    return "".join(chars).strip() or None


def heat_recovery_efficiency(
    outside: float | None,
    supply: float | None,
    extract: float | None,
    bypass_open: bool | None,
) -> float | None:
    """Supply-side temperature efficiency, % (None when not meaningful)."""
    if outside is None or supply is None or extract is None or bypass_open:
        return None
    delta = extract - outside
    if abs(delta) < 2.0:
        return None
    efficiency = (supply - outside) / delta * 100.0
    return round(max(0.0, min(100.0, efficiency)), 1)
