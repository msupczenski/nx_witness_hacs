"""Config flow for NX Witness integration."""
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_PORT, DOMAIN
from .discovery import DiscoveredServer, discover_servers
from .nx_client import NXWitnessClient
from .utils import create_client_session, create_ssl_context

_LOGGER = logging.getLogger(__name__)

MANUAL_ENTRY = "__manual__"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def _normalize_host(host: str) -> str:
    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    if ":" not in host.split("//", 1)[1]:
        host = f"{host}:{DEFAULT_PORT}"
    return host


class NXWitnessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NX Witness."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: list[DiscoveredServer] = []
        self._selected_host: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initial step — scan the LAN and present a picklist."""
        if user_input is None:
            try:
                self._discovered = await discover_servers(self.hass)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("LAN discovery failed; falling back to manual entry")
                self._discovered = []

            if not self._discovered:
                return await self.async_step_manual()

            options = {
                f"{server.host}:{server.port}": server.label
                for server in self._discovered
            }
            options[MANUAL_ENTRY] = "Enter server details manually"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required("server"): vol.In(options)}
                ),
            )

        choice = user_input["server"]
        if choice == MANUAL_ENTRY:
            return await self.async_step_manual()

        match = next(
            (
                s
                for s in self._discovered
                if f"{s.host}:{s.port}" == choice
            ),
            None,
        )
        if match is None:
            return await self.async_step_manual()
        self._selected_host = match.url
        return await self.async_step_credentials()

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect credentials for a discovered server."""
        assert self._selected_host is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            result = await self._try_create_entry(
                self._selected_host,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            if isinstance(result, dict):
                return result
            errors["base"] = result

        return self.async_show_form(
            step_id="credentials",
            data_schema=STEP_CREDENTIALS_SCHEMA,
            errors=errors,
            description_placeholders={"host": self._selected_host},
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manual host/credentials entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = _normalize_host(user_input[CONF_HOST])
            result = await self._try_create_entry(
                host,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            if isinstance(result, dict):
                return result
            errors["base"] = result

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _try_create_entry(
        self, host: str, username: str, password: str
    ) -> FlowResult | str:
        """Validate credentials and create the entry, or return an error key."""
        ssl_context = await self.hass.async_add_executor_job(create_ssl_context)
        session = create_client_session(ssl_context)
        client = NXWitnessClient(host, username, password, session)
        try:
            if await client.login():
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"NX Witness ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )
            return "cannot_connect"
        except aiohttp.ClientError:
            return "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during login")
            return "unknown"
        finally:
            if not session.closed:
                await session.close()
