"""Data update coordinator: capability detection, resilient polling and writes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import (
    AirPackClient,
    AirPackError,
    CommunicationError,
    InvalidValue,
    ReadOnlyError,
    UnsupportedRegister,
)
from .const import (
    ALARM_FULL_READ_EVERY,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MANUFACTURER,
    MAX_MERGE_GAP,
    MAX_REGISTERS_PER_READ,
    PANEL_URL_PATH,
    STORAGE_VERSION,
)
from .decode import (
    EncodeError,
    ascii_string,
    decode,
    encode,
    firmware_string,
    heat_recovery_efficiency,
    module_version,
    serial_string,
)
from .energy import ENERGY_KEYS, VALUES_TIME, RecoveredEnergy, heat_recovery_power
from .models import Family, family_for_model, model_name
from .planner import Block, detect_blocks
from .registers import (
    ALARM_DESCRIPTIONS,
    CFG_MODE1_ADDRESS,
    FILTER_CHANGE_ADDRESS,
    Feature,
    Group,
    Reg,
    Table,
)

_LOGGER = logging.getLogger(__name__)

type AirPackConfigEntry = ConfigEntry[AirPackCoordinator]

MODE_AUTO, MODE_MANUAL, MODE_TEMPORARY = 0, 1, 2

# Computed (virtual) keys
KEY_EFFICIENCY = "heat_recovery_efficiency"
KEY_ACTIVE_ALARMS = "active_alarms"
KEY_RECOVERY_POWER = "heat_recovery_power"
# A nested tuple means "any of these".
COMPUTED_DEPENDENCIES: dict[str, tuple[str | tuple[str, ...], ...]] = {
    KEY_EFFICIENCY: ("outside_temperature", "supply_temperature", "exhaust_temperature"),
    KEY_ACTIVE_ALARMS: ("alarm", "error"),
    KEY_RECOVERY_POWER: (
        "outside_temperature",
        "supply_temperature",
        ("supply_air_flow", "supply_flowrate"),
    ),
    **{key: (KEY_RECOVERY_POWER,) for key in ENERGY_KEYS},
}
ENERGY_SAVE_DELAY = 120  # s; also flushed when Home Assistant stops


@dataclass
class Capabilities:
    """What the connected device supports. Persisted between restarts."""

    blocks: list[Block] = field(default_factory=list)
    block_groups: list[Group] = field(default_factory=list)
    supported: set[str] = field(default_factory=set)
    absent: set[str] = field(default_factory=set)  # supported but "no value" at detection
    features: set[Feature] = field(default_factory=set)
    identity: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Serialise for storage."""
        return {
            "blocks": [b.as_dict() | {"group": str(g)} for b, g in zip(self.blocks, self.block_groups)],
            "supported": sorted(self.supported),
            "absent": sorted(self.absent),
            "features": sorted(str(f) for f in self.features),
            "identity": self.identity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Capabilities:
        """Deserialise from storage."""
        return cls(
            blocks=[Block.from_dict(b) for b in data["blocks"]],
            block_groups=[Group(b["group"]) for b in data["blocks"]],
            supported=set(data["supported"]),
            absent=set(data.get("absent", [])),
            features={Feature(f) for f in data.get("features", [])},
            identity=dict(data.get("identity", {})),
        )


class AirPackCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the AirPack and exposes decoded values keyed by register key."""

    config_entry: AirPackConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: AirPackConfigEntry, client: AirPackClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self.family: Family = family_for_model(entry.data.get(CONF_MODEL, ""))
        self.capabilities = Capabilities()
        self.failed_keys: set[str] = set()
        self.raw: dict[str, int] = {}
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._poll_count = 0
        self._failed_blocks: set[Block] = set()
        self.energy = RecoveredEnergy(max_gap=self._energy_max_gap())
        self._energy_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.energy"
        )

    def _energy_max_gap(self) -> timedelta:
        """Longest pause between polls that is still integrated."""
        return max(timedelta(minutes=10), 3 * (self.update_interval or timedelta(0)))

    # -- identity --------------------------------------------------------------

    @property
    def unique_prefix(self) -> str:
        """Prefix for entity unique IDs."""
        return self.config_entry.unique_id or self.config_entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Device registry info."""
        identity = self.capabilities.identity
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_prefix)},
            manufacturer=MANUFACTURER,
            model=model_name(self.config_entry.data.get(CONF_MODEL, "")),
            name=self.config_entry.title,
            sw_version=identity.get("firmware"),
            serial_number=identity.get("serial"),
            # "Open configuration page" on the device page opens the flow diagram panel.
            configuration_url=f"homeassistant://{PANEL_URL_PATH}",
        )

    def reg(self, key: str) -> Reg:
        """Register definition by key."""
        return self.family.index[key]

    def is_supported(self, key: str) -> bool:
        """True if the device has this register (or all inputs of a computed value)."""
        if key in COMPUTED_DEPENDENCIES:
            return all(
                any(self.is_supported(d) for d in dep) if isinstance(dep, tuple) else self.is_supported(dep)
                for dep in COMPUTED_DEPENDENCIES[key]
            )
        return key in self.capabilities.supported and key not in self.capabilities.absent

    def feature_present(self, feature: Feature | None) -> bool:
        """True if optional hardware was detected (or no feature required)."""
        return feature is None or feature in self.capabilities.features

    # -- setup / detection -----------------------------------------------------

    async def _async_setup(self) -> None:
        """Load cached capabilities, or detect them (first run)."""
        stored_energy = await self._energy_store.async_load()
        if stored_energy:
            try:
                self.energy = RecoveredEnergy.from_dict(stored_energy, self._energy_max_gap())
            except (TypeError, ValueError) as err:
                _LOGGER.warning("Ignoring invalid stored energy statistics: %s", err)
        stored = await self._store.async_load()
        if stored:
            try:
                self.capabilities = Capabilities.from_dict(stored)
            except (KeyError, ValueError) as err:
                _LOGGER.warning("Ignoring invalid stored capabilities: %s", err)
        if not self.capabilities.blocks:
            try:
                await self.async_detect()
            except CommunicationError as err:
                raise UpdateFailed(f"Cannot detect device capabilities: {err}") from err
            return
        # Refresh identity (firmware may have been updated); never fatal.
        try:
            await self._read_identity()
        except AirPackError as err:
            _LOGGER.debug("Could not refresh identity: %s", err)

    async def async_detect(self) -> None:
        """Probe which registers exist and which optional hardware is fitted."""
        _LOGGER.info("Detecting %s capabilities", self.config_entry.title)
        caps = Capabilities()
        values: dict[str, Any] = {}
        for table in Table:
            for group in (Group.STATE, Group.ALARM, Group.IDENTITY):
                regs = [r for r in self.family.registers if r.table == table and r.group == group]
                if not regs:
                    continue
                result = await detect_blocks(
                    self.client.read,
                    table,
                    [r.address for r in regs],
                    max_count=MAX_REGISTERS_PER_READ,
                    max_gap=MAX_MERGE_GAP,
                )
                if group != Group.IDENTITY:
                    caps.blocks += result.blocks
                    caps.block_groups += [group] * len(result.blocks)
                for reg in regs:
                    if reg.address in result.values:
                        caps.supported.add(reg.key)
                        self.raw[f"{reg.table}:{reg.address}"] = result.values[reg.address]
                        values[reg.key] = decode(reg, result.values[reg.address])
                if result.unsupported:
                    _LOGGER.info(
                        "%s %s registers not supported: %s",
                        table,
                        group,
                        ", ".join(f"{a:#06x}" for a in result.unsupported),
                    )

        for key in caps.supported:
            reg = self.family.index[key]
            raw = self.raw.get(f"{reg.table}:{reg.address}")
            if (reg.absent_if_none and values.get(key) is None) or (
                reg.absent_if_zero and raw == 0
            ):
                caps.absent.add(key)

        caps.features = self._detect_features(
            {k: v for k, v in values.items() if k not in caps.absent}, caps
        )
        caps.identity = self._identity_from_raw()
        self.capabilities = caps
        await self._store.async_save(caps.as_dict())
        _LOGGER.info(
            "Detected %d supported registers, %d readable blocks, features: %s",
            len(caps.supported),
            len(caps.blocks),
            ", ".join(sorted(caps.features)) or "none",
        )

    @staticmethod
    def _detect_features(values: dict[str, Any], caps: Capabilities) -> set[Feature]:
        features: set[Feature] = set()
        if values.get("gwc_temperature") is not None:
            features.add(Feature.GWC)
        if values.get("duct_supply_temperature") is not None:
            features.add(Feature.DUCT)
        if values.get("supply_air_flow") is not None or values.get("constant_flow_active"):
            features.add(Feature.CF)
        if values.get("expansion"):
            features.add(Feature.EXPANSION)
        if "post_heater_mode" in caps.supported:
            features.add(Feature.ERV)
        return features

    def _identity_from_raw(self) -> dict[str, Any]:
        raw = self.raw.get
        identity = {
            "firmware": firmware_string(raw("input:0"), raw("input:1"), raw("input:4")),
            "serial": serial_string([raw(f"input:{a}") for a in range(0x18, 0x1E)]),
            "device_name": ascii_string([raw(f"holding:{a}") for a in range(0x1FD0, 0x1FD8)]),
            "cf_version": module_version(raw("holding:240")),
            "expansion_version": module_version(raw("holding:241")),
        }
        return {k: v for k, v in identity.items() if v is not None}

    async def _read_identity(self) -> None:
        for reg in self.family.registers:
            if reg.group != Group.IDENTITY or reg.key not in self.capabilities.supported:
                continue
            try:
                (value,) = await self.client.read(reg.table, reg.address, 1)
            except UnsupportedRegister:
                continue
            self.raw[f"{reg.table}:{reg.address}"] = value
        self.capabilities.identity.update(self._identity_from_raw())

    # -- polling ---------------------------------------------------------------

    def _regs_in_block(self, block: Block) -> list[Reg]:
        return [
            r
            for r in self.family.registers
            if r.table == block.table
            and block.start <= r.address <= block.end
            and r.key in self.capabilities.supported
            and r.group in (Group.STATE, Group.ALARM)
        ]

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.data or {})
        failed: set[str] = set()
        caps = self.capabilities
        self._poll_count += 1
        periodic_alarm_read = self._poll_count % ALARM_FULL_READ_EVERY == 1
        read_alarms = False
        attempted = succeeded = 0
        comm_error: Exception | None = None

        # State blocks first: the fresh alarm/error summary flags decide whether
        # the detailed alarm flags need reading in this poll.
        ordered = sorted(
            zip(caps.blocks, caps.block_groups), key=lambda bg: bg[1] == Group.ALARM
        )
        for block, group in ordered:
            if group == Group.ALARM:
                read_alarms = (
                    periodic_alarm_read or bool(data.get("alarm")) or bool(data.get("error"))
                )
                if not read_alarms:
                    continue
            regs = self._regs_in_block(block)
            if not regs:
                continue
            attempted += 1
            try:
                raw = await self.client.read(block.table, block.start, block.count)
            except UnsupportedRegister:
                # Firmware changed under us? Isolate the block, keep going.
                _LOGGER.warning(
                    "Block %s %#06x+%d became unsupported; re-run hardware detection",
                    block.table, block.start, block.count,
                )
                failed.update(r.key for r in regs)
                continue
            except AirPackError as err:
                if block not in self._failed_blocks:
                    _LOGGER.info("Reading %s %#06x+%d failed: %s", block.table, block.start, block.count, err)
                self._failed_blocks.add(block)
                failed.update(r.key for r in regs)
                if isinstance(err, CommunicationError):
                    comm_error = err
                    if succeeded == 0 and attempted >= 2:
                        break  # device clearly unreachable; don't wait for every timeout
                continue
            if block in self._failed_blocks:
                _LOGGER.info("Reading %s %#06x+%d recovered", block.table, block.start, block.count)
                self._failed_blocks.discard(block)
            succeeded += 1
            for reg in regs:
                value = raw[reg.address - block.start]
                self.raw[f"{reg.table}:{reg.address}"] = value
                data[reg.key] = decode(reg, value)

        if attempted and not succeeded:
            raise UpdateFailed(f"Device not responding: {comm_error}")

        if not read_alarms:
            # Summary flags clear -> no detailed alarm can be active.
            for reg in self.family.registers:
                if reg.group == Group.ALARM and reg.key in caps.supported:
                    data[reg.key] = False

        self._compute(data)
        self.failed_keys = failed
        return data

    def _compute(self, data: dict[str, Any]) -> None:
        bypass_open = data.get("bypass_actuator")
        if bypass_open is None and data.get("bypass_mode") is not None:
            bypass_open = data["bypass_mode"] != 0
        data[KEY_EFFICIENCY] = heat_recovery_efficiency(
            data.get("outside_temperature"),
            data.get("supply_temperature"),
            data.get("exhaust_temperature"),
            bypass_open,
        )
        data[KEY_ACTIVE_ALARMS] = [
            code
            for code in ALARM_DESCRIPTIONS
            if data.get(f"alarm_{code.lower()}")
        ]
        if self.is_supported(KEY_RECOVERY_POWER):
            flow = data.get("supply_air_flow")
            if flow is None:
                flow = data.get("supply_flowrate")
            power = heat_recovery_power(
                flow,
                data.get("outside_temperature"),
                data.get("supply_temperature"),
                bypass_open,
                data.get("on_off_panel_mode"),
            )
            data[KEY_RECOVERY_POWER] = power
            now = dt_util.now()
            self.energy.add_sample(now, power)
            data.update(self.energy.values(now))
            data[VALUES_TIME] = now
            self._energy_store.async_delay_save(self.energy.as_dict, ENERGY_SAVE_DELAY)

    # -- writes ----------------------------------------------------------------

    async def _guarded_write(self, coro) -> None:
        try:
            await coro
        except ReadOnlyError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="read_only"
            ) from err
        except InvalidValue as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_value"
            ) from err
        except AirPackError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_write(self, key: str, value: Any) -> None:
        """Write one register (engineering value), then refresh."""
        reg = self.reg(key)
        try:
            raw = encode(reg, value)
        except EncodeError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="out_of_range",
                translation_placeholders={"error": str(err)},
            ) from err
        await self._guarded_write(self.client.write_register(reg.address, raw))
        await self._optimistic({key: decode(reg, raw)})

    async def async_set_mode(self, mode: int, airflow: int | None = None) -> None:
        """Switch AUTO/MANUAL/TEMPORARY via the dedicated 0x1130 group."""
        if mode == MODE_TEMPORARY:
            if airflow is None:
                airflow = self.current_airflow() or 50
            await self.async_set_temporary_airflow(airflow)
            return
        await self._guarded_write(self.client.write_register(CFG_MODE1_ADDRESS, mode))
        await self._optimistic({"mode": mode})

    async def async_set_temporary_airflow(self, airflow: int) -> None:
        """Atomic FC16 write [2, airflow, 1] to 0x1130 (what the Air++ panel does)."""
        airflow = self._validate_airflow(airflow)
        await self._guarded_write(
            self.client.write_registers(CFG_MODE1_ADDRESS, [MODE_TEMPORARY, airflow, 1])
        )
        await self._optimistic({"mode": MODE_TEMPORARY, "air_flow_rate_temporary": airflow})

    async def async_set_airflow(self, airflow: int) -> None:
        """Set airflow like the panel: MANUAL edits manual airflow, else TEMPORARY override."""
        if self.data and self.data.get("mode") == MODE_MANUAL:
            airflow = self._validate_airflow(airflow)
            await self.async_write("air_flow_rate_manual", airflow)
            return
        await self.async_set_temporary_airflow(airflow)

    async def async_filter_replaced(self, command: int) -> None:
        """Register a filter change (0x11 supply / 0x21 exhaust)."""
        await self._guarded_write(self.client.write_register(FILTER_CHANGE_ADDRESS, command))
        await self.async_request_refresh()

    def _validate_airflow(self, airflow: int) -> int:
        reg = self.reg("air_flow_rate_manual")
        low, high = int(reg.min or 10), int(reg.max or 100)
        if self.data:
            low = max(low, int(self.data.get("min_percentage") or low))
        if not low <= airflow <= high:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="out_of_range",
                translation_placeholders={"error": f"airflow {airflow}% not in {low}-{high}%"},
            )
        return int(airflow)

    def current_airflow(self) -> int | None:
        """Currently requested supply airflow, %."""
        data = self.data or {}
        if data.get("supply_percentage") is not None and self.is_supported("supply_percentage"):
            return int(data["supply_percentage"])
        mode = data.get("mode")
        if mode == MODE_MANUAL:
            return data.get("air_flow_rate_manual")
        if mode == MODE_TEMPORARY:
            return data.get("air_flow_rate_temporary")
        return None

    async def _optimistic(self, values: dict[str, Any]) -> None:
        """Show the written value immediately, then read back the real state."""
        if self.data is not None:
            self.async_set_updated_data({**self.data, **values})
        await self.async_request_refresh()

    async def async_remove_store(self) -> None:
        """Delete persisted capabilities."""
        await self._store.async_remove()

    async def async_save_energy(self) -> None:
        """Persist energy statistics now (unload/reload)."""
        await self._energy_store.async_save(self.energy.as_dict())

    @property
    def connection_label(self) -> str:
        """host:port/unit for diagnostics."""
        data = self.config_entry.data
        return f"{data[CONF_HOST]}:{data[CONF_PORT]}"
