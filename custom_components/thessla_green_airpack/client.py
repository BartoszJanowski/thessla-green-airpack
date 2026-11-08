"""Async Modbus TCP client wrapper for AirPack devices.

* one persistent connection, every request serialised with a lock
* typed errors so the coordinator can tell "register not supported"
  apart from "device unreachable"
* optional read-only mode that blocks every write before it reaches the socket
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .errors import (
    AirPackError,
    CommunicationError,
    ConnectError,
    DeviceError,
    InvalidValue,
    ReadOnlyError,
    UnsupportedRegister,
)
from .registers import Table

__all__ = [
    "AirPackClient",
    "AirPackError",
    "CommunicationError",
    "ConnectError",
    "DeviceError",
    "InvalidValue",
    "ReadOnlyError",
    "UnsupportedRegister",
]

_LOGGER = logging.getLogger(__name__)

# Modbus exception codes
ILLEGAL_FUNCTION = 0x01
ILLEGAL_DATA_ADDRESS = 0x02
ILLEGAL_DATA_VALUE = 0x03
GATEWAY_PATH_UNAVAILABLE = 0x0A
GATEWAY_TARGET_NO_RESPONSE = 0x0B


class AirPackClient:
    """Thin, serialised wrapper around pymodbus' AsyncModbusTcpClient."""

    def __init__(
        self,
        host: str,
        port: int,
        unit_id: int,
        *,
        timeout: float = 3.0,
        request_delay: float = 0.0,
        read_only: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.request_delay = request_delay
        self.read_only = read_only
        self._lock = asyncio.Lock()
        self._client: AsyncModbusTcpClient | None = None

    # -- connection ------------------------------------------------------------

    async def _ensure_connected(self) -> AsyncModbusTcpClient:
        if self._client is not None and self._client.connected:
            return self._client
        if self._client is not None:
            self._client.close()
        # reconnect_delay=0: we reconnect ourselves on the next request instead of
        # letting pymodbus retry in the background.
        self._client = AsyncModbusTcpClient(
            self.host,
            port=self.port,
            timeout=self.timeout,
            retries=1,
            reconnect_delay=0,
        )
        try:
            connected = await self._client.connect()
        except (OSError, ModbusException) as err:
            raise ConnectError(f"Cannot connect to {self.host}:{self.port}: {err}") from err
        if not connected:
            raise ConnectError(f"Cannot connect to {self.host}:{self.port}")
        return self._client

    async def close(self) -> None:
        """Close the connection."""
        async with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def _drop_connection(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # -- requests --------------------------------------------------------------

    async def _call(self, what: str, func_name: str, *args, **kwargs):
        async with self._lock:
            client = await self._ensure_connected()
            try:
                response = await getattr(client, func_name)(
                    *args, device_id=self.unit_id, **kwargs
                )
            except (TimeoutError, asyncio.TimeoutError, OSError, ModbusException) as err:
                self._drop_connection()
                raise CommunicationError(f"{what}: {err}") from err
            finally:
                if self.request_delay:
                    await asyncio.sleep(self.request_delay)

        if response is None:
            self._drop_connection()
            raise CommunicationError(f"{what}: no response")
        if response.isError():
            code = getattr(response, "exception_code", None)
            if code in (ILLEGAL_FUNCTION, ILLEGAL_DATA_ADDRESS):
                raise UnsupportedRegister(f"{what}: illegal address", code)
            if code == ILLEGAL_DATA_VALUE:
                raise InvalidValue(f"{what}: illegal data value", code)
            if code in (GATEWAY_PATH_UNAVAILABLE, GATEWAY_TARGET_NO_RESPONSE):
                raise CommunicationError(f"{what}: gateway reports no response from device")
            raise DeviceError(f"{what}: exception code {code}", code)
        return response

    async def read(self, table: Table, address: int, count: int) -> list[int]:
        """Read ``count`` values from a table; bits are returned as 0/1."""
        what = f"read {table} {address:#06x}+{count}"
        match table:
            case Table.COIL:
                resp = await self._call(what, "read_coils", address, count=count)
                return [int(b) for b in resp.bits[:count]]
            case Table.DISCRETE:
                resp = await self._call(what, "read_discrete_inputs", address, count=count)
                return [int(b) for b in resp.bits[:count]]
            case Table.INPUT:
                resp = await self._call(what, "read_input_registers", address, count=count)
            case Table.HOLDING:
                resp = await self._call(what, "read_holding_registers", address, count=count)
        registers = list(resp.registers)
        if len(registers) < count:
            raise CommunicationError(f"{what}: short response ({len(registers)} values)")
        return registers[:count]

    async def write_register(self, address: int, value: int) -> None:
        """Write one holding register (FC06)."""
        self._check_writable()
        _LOGGER.debug("Writing %#06x = %s", address, value)
        await self._call(f"write {address:#06x}", "write_register", address, value)

    async def write_registers(self, address: int, values: Sequence[int]) -> None:
        """Write several consecutive holding registers atomically (FC16)."""
        self._check_writable()
        _LOGGER.debug("Writing %#06x = %s", address, list(values))
        await self._call(f"write {address:#06x}+{len(values)}", "write_registers", address, list(values))

    def _check_writable(self) -> None:
        if self.read_only:
            raise ReadOnlyError("Integration is in read-only mode")
