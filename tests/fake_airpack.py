"""In-memory AirPack that replaces pymodbus' AsyncModbusTcpClient in tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymodbus.exceptions import ModbusIOException

from custom_components.thessla_green_airpack.registers import AIRPACK4_REGISTERS, Group, Table

UNIT = 10
SERIAL = "1a2b3c4d5e6f"


@dataclass
class Response:
    registers: list[int] = field(default_factory=list)
    bits: list[bool] = field(default_factory=list)
    exception_code: int | None = None

    def isError(self) -> bool:  # noqa: N802 (pymodbus API)
        return self.exception_code is not None


def default_bank() -> dict[Table, dict[int, int]]:
    """Every documented register present; values like the Air++ screenshot."""
    bank: dict[Table, dict[int, int]] = {t: {} for t in Table}
    for reg in AIRPACK4_REGISTERS:
        if reg.group != Group.WRITE_ONLY:
            bank[reg.table][reg.address] = 0
    bank[Table.HOLDING][0x1FFF] = 4  # filter type (read side of the command register)
    bank[Table.INPUT].update(
        {
            0x00: 4, 0x01: 85, 0x04: 2,  # firmware 4.85.2
            0x10: 0, 0x11: 173, 0x12: 214,  # TZ1 0.0, TN1 17.3, TP 21.4
            0x13: 0x8000,  # no TZ2 (0x8000 = no sensor)
            0x14: 0, 0x15: 0,  # no TN2 / TZ3: firmware 4.87 reports exactly 0
            0x16: 174,  # TO 17.4
            0x18: 0x1A, 0x19: 0x2B, 0x1A: 0x3C, 0x1B: 0x4D, 0x1C: 0x5E, 0x1D: 0x6F,
            0x10F: 1, 0x110: 30, 0x111: 30, 0x112: 120, 0x113: 120, 0x114: 10, 0x115: 120,
        }
    )
    bank[Table.HOLDING].update(
        {
            0x0100: 120, 0x0101: 120,
            0x1070: 0, 0x1071: 1, 0x1072: 30, 0x1073: 40, 0x1074: 44, 0x1075: 44,
            0x1078: 30, 0x1079: 60, 0x107A: 100, 0x107B: 0x1330,
            0x1082: 100, 0x1083: 100, 0x1084: 20, 0x1085: 100, 0x1086: 100, 0x1087: 100,
            0x1088: 20, 0x1089: 5, 0x108A: 5, 0x108D: 1, 0x108E: 100, 0x108F: 100,
            0x10A1: 11, 0x10A2: 43, 0x10A8: 4, 0x10AB: 0x0500, 0x10AC: 0x1700,
            0x10AD: 0x1900, 0x10AE: 0x0700, 0x10E1: 23, 0x10E2: 43, 0x10E3: 43,
            0x10EB: 1, 0x10EC: 50, 0x10ED: 50,
            0x1123: 1, 0x1150: 0, 0x1151: 0x1215,
            0x1182: 8, 0x1183: 6, 0x1234: 0x2D62, 0x1236: 0x2D62, 0x1FFE: 44,
            0x1FD0: 0x4169, 0x1FD1: 0x7250, 0x1FD2: 0x6163, 0x1FD3: 0x6B00,
        }
    )
    # Like the AirPack 400V in upstream issue #29: no ERV registers.
    del bank[Table.HOLDING][0x1260]
    del bank[Table.HOLDING][0x1267]
    # The command group lives at 0x1130-0x1135 (write side).
    for address in range(0x1130, 0x1136):
        bank[Table.HOLDING][address] = 0
    return bank


class FakeAirPack:
    """Device state + behaviour shared by all fake client instances."""

    def __init__(self) -> None:
        self.bank = default_bank()
        self.online = True
        self.unit = UNIT
        self.writes: list[tuple[int, list[int]]] = []
        self.reads = 0

    # -- device behaviour ---------------------------------------------------------
    def _apply_write(self, address: int, values: list[int]) -> int | None:
        holding = self.bank[Table.HOLDING]
        if any(a not in holding for a in range(address, address + len(values))):
            return 2
        for offset, value in enumerate(values):
            holding[address + offset] = value
        # Emulate the controller acting on the command groups.
        if address == 0x1130:
            holding[0x1070] = values[0]
            if len(values) == 3 and values[2] == 1:
                holding[0x1073] = values[1]
                self.bank[Table.INPUT][0x110] = values[1]
        if address == 0x1072 and holding[0x1070] == 1:
            self.bank[Table.INPUT][0x110] = values[0]
        return None

    def client_factory(self, host, **kwargs):
        return FakeModbusClient(self)


class FakeModbusClient:
    """Mimics the subset of AsyncModbusTcpClient used by the integration."""

    def __init__(self, device: FakeAirPack) -> None:
        self.device = device
        self.connected = False

    async def connect(self) -> bool:
        self.connected = self.device.online
        return self.connected

    def close(self) -> None:
        self.connected = False

    def _check(self, device_id: int) -> None:
        if not self.device.online or device_id != self.device.unit:
            raise ModbusIOException("No response received")

    def _read(self, table: Table, address: int, count: int, device_id: int) -> Response:
        self._check(device_id)
        self.device.reads += 1
        data = self.device.bank[table]
        if count > 16 or any(a not in data for a in range(address, address + count)):
            return Response(exception_code=2)
        values = [data[a] for a in range(address, address + count)]
        if table in (Table.COIL, Table.DISCRETE):
            return Response(bits=[bool(v) for v in values] + [False] * (-count % 8))
        return Response(registers=values)

    async def read_coils(self, address, *, count=1, device_id=1):
        return self._read(Table.COIL, address, count, device_id)

    async def read_discrete_inputs(self, address, *, count=1, device_id=1):
        return self._read(Table.DISCRETE, address, count, device_id)

    async def read_input_registers(self, address, *, count=1, device_id=1):
        return self._read(Table.INPUT, address, count, device_id)

    async def read_holding_registers(self, address, *, count=1, device_id=1):
        return self._read(Table.HOLDING, address, count, device_id)

    async def write_register(self, address, value, *, device_id=1):
        self._check(device_id)
        self.device.writes.append((address, [value]))
        code = self.device._apply_write(address, [value])
        return Response(registers=[value], exception_code=code)

    async def write_registers(self, address, values, *, device_id=1):
        self._check(device_id)
        self.device.writes.append((address, list(values)))
        code = self.device._apply_write(address, list(values))
        return Response(exception_code=code)
