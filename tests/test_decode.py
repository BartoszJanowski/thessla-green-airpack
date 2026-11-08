"""Pure decoder / planner tests."""

from datetime import date, time

import pytest

from custom_components.thessla_green_airpack.decode import (
    EncodeError,
    ascii_string,
    decode,
    encode,
    firmware_string,
    heat_recovery_efficiency,
    module_version,
    serial_string,
)
from custom_components.thessla_green_airpack.errors import UnsupportedRegister
from custom_components.thessla_green_airpack.models import AIRPACK4, MODELS
from custom_components.thessla_green_airpack.planner import Block, detect_blocks, group_addresses
from custom_components.thessla_green_airpack.registers import Table

R = AIRPACK4.index


def test_temperature() -> None:
    reg = R["outside_temperature"]
    assert decode(reg, 214) == 21.4
    assert decode(reg, 0xFFF6) == -1.0
    assert decode(reg, 0x8000) is None


def test_half_degree_roundtrip() -> None:
    reg = R["supply_air_temperature_manual"]
    assert decode(reg, 44) == 22.0
    assert encode(reg, 22.5) == 45
    with pytest.raises(EncodeError):
        encode(reg, 50)


def test_flow_not_available() -> None:
    assert decode(R["supply_air_flow"], 0xFFFF) is None
    assert decode(R["supply_air_flow"], 120) == 120


def test_bcd_time() -> None:
    reg = R["manual_airing_time_to_start"]
    assert decode(reg, 0x1330) == time(13, 30)
    assert decode(reg, 0x2400) is None
    assert decode(reg, 0xA200) is None
    assert encode(reg, time(6, 30)) == 0x0630
    assert encode(reg, None) == 0x2400


def test_packed_date() -> None:
    # Spec example: 0x2d62 -> 2022-11-02
    assert decode(R["supply_filter_date"], 0x2D62) == date(2022, 11, 2)
    assert decode(R["supply_filter_date"], 0) is None


def test_identity_strings() -> None:
    assert firmware_string(4, 84, 2) == "4.84.2"
    assert serial_string([0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F]) == "1a2b 3c4d 5e6f"
    assert module_version(0x010D) == "1.13"
    assert module_version(0x001B) == "0.27"
    words = [0x4169, 0x7250, 0x6163, 0x6B20, 0x4D2D, 0x3100, 0, 0]
    assert ascii_string(words) == "AirPack M-1"


def test_encode_rejects_read_only_and_range() -> None:
    with pytest.raises(EncodeError):
        encode(R["mode"], 1)
    with pytest.raises(EncodeError):
        encode(R["air_flow_rate_manual"], 5)
    assert encode(R["air_flow_rate_manual"], 55) == 55


def test_efficiency() -> None:
    assert heat_recovery_efficiency(0.0, 17.3, 21.4, False) == 80.8
    assert heat_recovery_efficiency(0.0, 17.3, 21.4, True) is None
    assert heat_recovery_efficiency(20.0, 20.5, 21.0, False) is None
    assert heat_recovery_efficiency(None, 17.3, 21.4, False) is None


def test_models() -> None:
    assert len(MODELS) == 20
    assert MODELS["airpack4_400v_energypp"][0] == "AirPack4 400v Energy++"


def test_group_addresses() -> None:
    assert group_addresses([0, 1, 2, 20, 21], 16, 8) == [[0, 1, 2], [20, 21]]
    assert group_addresses(range(0, 40), 16, 8) == [list(range(16)), list(range(16, 32)), list(range(32, 40))]
    assert group_addresses([0, 5, 9], 16, 4) == [[0, 5, 9]]
    assert group_addresses([0, 5, 9], 16, 3) == [[0], [5, 9]]
    assert group_addresses([0, 5, 9], 16, 2) == [[0], [5], [9]]


async def test_detect_blocks_splits_unsupported() -> None:
    present = {0x10: 1, 0x11: 2, 0x13: 3, 0x15: 4}

    async def read(table, start, count):
        if any(a not in present for a in range(start, start + count)):
            raise UnsupportedRegister("x", 2)
        return [present[a] for a in range(start, start + count)]

    res = await detect_blocks(read, Table.HOLDING, [0x10, 0x11, 0x13, 0x14, 0x15], max_count=16, max_gap=8)
    assert res.unsupported == [0x14]
    assert res.values == present
    covered = {a for b in res.blocks for a in range(b.start, b.end + 1)}
    assert covered >= set(present)
    assert all(isinstance(b, Block) for b in res.blocks)
