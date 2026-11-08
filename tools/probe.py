#!/usr/bin/env python3
"""Read-only probe for Thessla Green AirPack4 devices over Modbus TCP.

Dumps every register from the integration's register map (decoded), the
readable block layout and the list of unsupported addresses. Useful for
support ("which registers does my unit have?") and as a test fixture.

This tool CANNOT write to the device:
  * it does not import the integration's client (the only module with writes)
  * the pymodbus client is wrapped in a proxy that only exposes read methods
  * every outgoing PDU is checked: only function codes 1-4 may be sent

Usage:
  python -I tools/probe.py --host 192.168.1.50 [--port 502] [--unit 10] [--json probe-out.json]
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
from pathlib import Path
import sys
import types

from pymodbus.client import AsyncModbusTcpClient

PKG_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "thessla_green_airpack"
READ_FUNCTION_CODES = frozenset({1, 2, 3, 4})
READ_METHODS = frozenset(
    {
        "connect",
        "close",
        "connected",
        "read_coils",
        "read_discrete_inputs",
        "read_input_registers",
        "read_holding_registers",
    }
)


def _load_pkg_modules():
    """Import HA-free modules of the integration without running its __init__."""
    pkg = types.ModuleType("tga")
    pkg.__path__ = [str(PKG_DIR)]
    sys.modules["tga"] = pkg
    return (
        importlib.import_module("tga.registers"),
        importlib.import_module("tga.decode"),
        importlib.import_module("tga.planner"),
        importlib.import_module("tga.errors"),
    )


registers, decode, planner, errors = _load_pkg_modules()


def _guard_pdu(sending: bool, pdu):
    """pymodbus trace hook: refuse to send anything that is not a read."""
    if sending and pdu.function_code not in READ_FUNCTION_CODES:
        raise PermissionError(f"probe is read-only: refusing function code {pdu.function_code}")
    return pdu


class ReadOnlyModbus:
    """Proxy exposing only connection + read methods of a pymodbus client."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        kwargs = {"port": port, "timeout": timeout, "retries": 1, "reconnect_delay": 0}
        try:
            client = AsyncModbusTcpClient(host, trace_pdu=_guard_pdu, **kwargs)
        except TypeError:  # very old pymodbus without trace hooks
            client = AsyncModbusTcpClient(host, **kwargs)
        object.__setattr__(self, "_client", client)

    def __getattr__(self, name: str):
        if name not in READ_METHODS:
            raise PermissionError(f"probe is read-only: '{name}' is not allowed")
        return getattr(object.__getattribute__(self, "_client"), name)

    def __setattr__(self, name: str, value) -> None:
        raise PermissionError("probe is read-only")


class Reader:
    """Read function compatible with planner.detect_blocks."""

    def __init__(self, modbus: ReadOnlyModbus, unit: int, delay: float) -> None:
        self.modbus = modbus
        self.unit = unit
        self.delay = delay
        self.requests = 0

    async def __call__(self, table, address: int, count: int) -> list[int]:
        method = {
            "coil": "read_coils",
            "discrete": "read_discrete_inputs",
            "input": "read_input_registers",
            "holding": "read_holding_registers",
        }[str(table)]
        self.requests += 1
        try:
            resp = await getattr(self.modbus, method)(address, count=count, device_id=self.unit)
        except PermissionError:
            raise
        except Exception as err:  # noqa: BLE001
            raise errors.CommunicationError(f"{method} {address:#06x}+{count}: {err}") from err
        finally:
            if self.delay:
                await asyncio.sleep(self.delay)
        if resp.isError():
            code = getattr(resp, "exception_code", None)
            if code in (1, 2):
                raise errors.UnsupportedRegister(f"{method} {address:#06x}+{count}", code)
            raise errors.CommunicationError(f"{method} {address:#06x}+{count}: exception {code}")
        values = resp.bits if str(table) in ("coil", "discrete") else resp.registers
        return [int(v) for v in values[:count]]


async def probe(args) -> dict:
    modbus = ReadOnlyModbus(args.host, args.port, args.timeout)
    if not await modbus.connect():
        raise SystemExit(f"Cannot connect to {args.host}:{args.port}")
    reader = Reader(modbus, args.unit, args.delay / 1000)
    regs = [r for r in registers.AIRPACK4_REGISTERS if r.group != registers.Group.WRITE_ONLY]

    out: dict = {
        "host": args.host,
        "port": args.port,
        "unit": args.unit,
        "blocks": [],
        "unsupported": {},
        "raw": {},
        "values": {},
    }
    try:
        for table in registers.Table:
            for group in registers.Group:
                addrs = [r.address for r in regs if r.table == table and r.group == group]
                if not addrs:
                    continue
                res = await planner.detect_blocks(
                    reader, table, addrs, max_count=16, max_gap=args.max_gap
                )
                out["blocks"] += [b.as_dict() | {"group": str(group)} for b in res.blocks]
                out["unsupported"].setdefault(str(table), []).extend(res.unsupported)
                for address, raw in res.values.items():
                    out["raw"][f"{table}:{address}"] = raw
    finally:
        modbus.close()

    for reg in regs:
        raw = out["raw"].get(f"{reg.table}:{reg.address}")
        if raw is None:
            continue
        value = decode.decode(reg, raw)
        out["values"][reg.key] = value.isoformat() if hasattr(value, "isoformat") else value

    raw = out["raw"]
    out["firmware"] = decode.firmware_string(raw.get("input:0"), raw.get("input:1"), raw.get("input:4"))
    out["serial"] = decode.serial_string([raw.get(f"input:{a}") for a in range(0x18, 0x1E)])
    out["device_name"] = decode.ascii_string([raw.get(f"holding:{a}") for a in range(0x1FD0, 0x1FD8)])
    out["requests"] = reader.requests
    return out


def _print_report(out: dict) -> None:
    print(f"Firmware: {out['firmware']}   Serial: {out['serial']}   Name: {out['device_name']}")
    print(f"Requests: {out['requests']}   Readable blocks: {len(out['blocks'])}")
    for table, addrs in out["unsupported"].items():
        if addrs:
            print(f"Unsupported {table}: {', '.join(f'{a:#06x}' for a in addrs)}")
    print()
    by_key = {r.key: r for r in registers.AIRPACK4_REGISTERS}
    for key, value in out["values"].items():
        reg = by_key[key]
        raw = out["raw"][f"{reg.table}:{reg.address}"]
        if reg.group == registers.Group.ALARM and not value:
            continue  # only show active alarms
        print(f"  {reg.table:8} {reg.address:#06x}  raw={raw:#06x} ({raw:5d})  {key} = {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--delay", type=float, default=0, help="delay between requests, ms")
    parser.add_argument("--max-gap", type=int, default=8)
    parser.add_argument("--json", type=Path, help="write full result as JSON")
    args = parser.parse_args()

    out = asyncio.run(probe(args))
    _print_report(out)
    if args.json:
        args.json.write_text(json.dumps(out, indent=2, default=str))
        print(f"\nSaved {args.json}")


if __name__ == "__main__":
    main()
