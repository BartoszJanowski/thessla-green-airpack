"""Config flow for Thessla Green AirPack."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .client import (
    AirPackClient,
    AirPackError,
    CommunicationError,
    ConnectError,
    DeviceError,
    UnsupportedRegister,
)

SERVER_DEVICE_FAILURE = 0x04
from .const import (
    CONF_MODEL,
    CONF_READ_ONLY,
    CONF_REQUEST_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_UNIT_ID,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_READ_ONLY,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .decode import serial_string
from .models import DEFAULT_MODEL, MODELS
from .registers import Table

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Gateway not reachable."""


class NoResponse(Exception):
    """Gateway reachable but the device does not answer (wrong unit ID / wiring)."""


class InvalidResponse(Exception):
    """Device answers but does not look like an AirPack."""


def _int_box(minimum: int, maximum: int, step: int = 1, unit: str | None = None) -> NumberSelector:
    config = NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=NumberSelectorMode.BOX)
    if unit:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def _connection_schema(defaults: dict[str, Any]) -> dict:
    return {
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): TextSelector(),
        vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): _int_box(1, 65535),
        vol.Required(
            CONF_UNIT_ID, default=defaults.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
        ): _int_box(1, 247),
    }


async def validate_connection(host: str, port: int, unit_id: int) -> str | None:
    """Connect, read firmware and serial. Returns the serial number (if any)."""
    client = AirPackClient(host, port, unit_id, timeout=5)
    try:
        try:
            firmware = await client.read(Table.INPUT, 0x0000, 2)
        except ConnectError as err:
            raise CannotConnect from err
        except CommunicationError as err:
            raise NoResponse from err
        except UnsupportedRegister as err:
            raise InvalidResponse from err
        except DeviceError as err:
            # Some gateways answer "device failure" (04) for an absent unit ID.
            if err.code == SERVER_DEVICE_FAILURE:
                raise NoResponse from err
            raise InvalidResponse from err
        except AirPackError as err:
            raise InvalidResponse from err
        if not 1 <= firmware[0] <= 99:
            raise InvalidResponse
        try:
            serial = serial_string(await client.read(Table.INPUT, 0x0018, 6))
        except AirPackError:
            serial = None
        return serial
    finally:
        await client.close()


class AirPackConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    async def _validate(self, user_input: dict[str, Any], errors: dict[str, str]) -> str | None:
        try:
            serial = await validate_connection(
                user_input[CONF_HOST], int(user_input[CONF_PORT]), int(user_input[CONF_UNIT_ID])
            )
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except NoResponse:
            errors["base"] = "no_response"
        except InvalidResponse:
            errors["base"] = "invalid_response"
        except Exception:
            _LOGGER.exception("Unexpected error while validating connection")
            errors["base"] = "unknown"
        else:
            if serial:
                return serial.replace(" ", "")
            return (
                f"{user_input[CONF_HOST]}:{int(user_input[CONF_PORT])}:{int(user_input[CONF_UNIT_ID])}"
            )
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First step: connection + model."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_PORT] = int(user_input[CONF_PORT])
            user_input[CONF_UNIT_ID] = int(user_input[CONF_UNIT_ID])
            unique_id = await self._validate(user_input, errors)
            if unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(
                    updates={k: user_input[k] for k in (CONF_HOST, CONF_PORT, CONF_UNIT_ID)}
                )
                name = user_input.pop(CONF_NAME, DEFAULT_NAME) or DEFAULT_NAME
                return self.async_create_entry(title=name, data=user_input)

        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
                **_connection_schema(defaults),
                vol.Required(CONF_MODEL, default=defaults.get(CONF_MODEL, DEFAULT_MODEL)): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=key, label=name)
                            for key, (name, _family) in MODELS.items()
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change host / port / unit ID of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_PORT] = int(user_input[CONF_PORT])
            user_input[CONF_UNIT_ID] = int(user_input[CONF_UNIT_ID])
            unique_id = await self._validate(user_input, errors)
            if unique_id:
                if entry.unique_id and ":" not in entry.unique_id and unique_id != entry.unique_id:
                    return self.async_abort(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        schema = vol.Schema(_connection_schema(user_input or dict(entry.data)))
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options flow."""
        return AirPackOptionsFlow()


class AirPackOptionsFlow(OptionsFlow):
    """Polling / connection tuning and read-only mode."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_TIMEOUT: int(user_input[CONF_TIMEOUT]),
                    CONF_REQUEST_DELAY: int(user_input[CONF_REQUEST_DELAY]),
                    CONF_READ_ONLY: bool(user_input[CONF_READ_ONLY]),
                }
            )
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _int_box(MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL, unit="s"),
                vol.Required(
                    CONF_TIMEOUT, default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                ): _int_box(1, 30, unit="s"),
                vol.Required(
                    CONF_REQUEST_DELAY,
                    default=options.get(CONF_REQUEST_DELAY, DEFAULT_REQUEST_DELAY),
                ): _int_box(0, 1000, 10, unit="ms"),
                vol.Required(
                    CONF_READ_ONLY, default=options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
