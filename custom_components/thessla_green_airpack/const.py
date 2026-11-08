"""Constants for the Thessla Green AirPack integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "thessla_green_airpack"
MANUFACTURER: Final = "Thessla Green"

CONF_UNIT_ID: Final = "unit_id"
CONF_MODEL: Final = "model"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TIMEOUT: Final = "timeout"
CONF_REQUEST_DELAY: Final = "request_delay"
CONF_READ_ONLY: Final = "read_only"

DEFAULT_NAME: Final = "AirPack"
DEFAULT_PORT: Final = 502
DEFAULT_UNIT_ID: Final = 10
DEFAULT_SCAN_INTERVAL: Final = 30  # s
DEFAULT_TIMEOUT: Final = 3  # s
DEFAULT_REQUEST_DELAY: Final = 0  # ms
DEFAULT_READ_ONLY: Final = False

MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

MAX_REGISTERS_PER_READ: Final = 16  # documented device limit
MAX_MERGE_GAP: Final = 8  # undocumented addresses we optimistically read through
ALARM_FULL_READ_EVERY: Final = 10  # polls

STORAGE_VERSION: Final = 1
