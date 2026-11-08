"""Exception types (no Home Assistant / pymodbus imports)."""

from __future__ import annotations


class AirPackError(Exception):
    """Base error."""


class CommunicationError(AirPackError):
    """Device or gateway unreachable / no response."""


class ConnectError(CommunicationError):
    """TCP connection to the gateway could not be established."""


class DeviceError(AirPackError):
    """Device answered with a Modbus exception."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class UnsupportedRegister(DeviceError):
    """Register (range) does not exist on this device (exception 01/02)."""


class InvalidValue(DeviceError):
    """Device rejected the written value (exception 03)."""


class ReadOnlyError(AirPackError):
    """Write attempted while the client is in read-only mode."""
