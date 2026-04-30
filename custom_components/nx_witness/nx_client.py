"""NX Witness REST API v4 Client."""
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class NXWitnessClient:
    """Client for NX Witness REST API v4."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the client."""
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.session = session
        self.token: str | None = None

    async def login(self) -> bool:
        """Login and obtain session token."""
        url = f"{self.host}/rest/v4/login/sessions"
        try:
            async with self.session.post(
                url,
                json={"username": self.username, "password": self.password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (200, 201):
                    result = await response.json()
                    self.token = result.get("token")
                    _LOGGER.info("Login successful, token obtained")
                    return True
                text = await response.text()
                _LOGGER.error("Login failed with status %s: %s", response.status, text)
                return False
        except aiohttp.ClientError as ex:
            _LOGGER.error("Login failed: %s", ex)
            return False

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> tuple[int, Any]:
        """Make an authenticated request, refreshing the token once on 401."""
        for attempt in range(2):
            if not self.token and not await self.login():
                return 0, None
            headers = {"Authorization": f"Bearer {self.token}"}
            try:
                async with self.session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                    **kwargs,
                ) as response:
                    if response.status == 401 and attempt == 0:
                        _LOGGER.debug("Token expired, re-logging in")
                        self.token = None
                        continue
                    if response.status in (200, 201):
                        return response.status, await response.json()
                    _LOGGER.error(
                        "%s %s returned %s", method.upper(), url, response.status
                    )
                    return response.status, None
            except aiohttp.ClientError as ex:
                _LOGGER.error("Request error %s %s: %s", method.upper(), url, ex)
                return 0, None
        return 0, None

    async def get_ticket(self, force_new_token: bool = False) -> str | None:
        """Get a one-time ticket for media streaming."""
        if force_new_token:
            self.token = None
        url = f"{self.host}/rest/v4/login/tickets"
        _, result = await self._request("post", url)
        if isinstance(result, dict):
            ticket = result.get("token")
            _LOGGER.debug("Ticket obtained")
            return ticket
        return None

    async def get_cameras(self) -> list[dict[str, Any]]:
        """Get list of cameras from NX Witness."""
        url = f"{self.host}/rest/v4/devices"
        _, data = await self._request("get", url)
        if not isinstance(data, list):
            return []
        cameras = [
            {
                "id": device.get("id"),
                "name": device.get("name"),
                "model": device.get("model"),
                "status": device.get("status"),
            }
            for device in data
            if device.get("deviceType") == "Camera"
        ]
        _LOGGER.debug("Found %d cameras", len(cameras))
        return cameras

    def get_camera_stream_url(self, camera_id: str, ticket: str) -> str:
        """Get stream URL for a camera with ticket."""
        return f"{self.host}/rest/v4/devices/{camera_id}/media?_ticket={ticket}"

    async def get_event_log(
        self,
        start_time_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get events from NX Witness event log."""
        url = f"{self.host}/rest/v4/events/log"
        params: dict[str, int] = {}
        if start_time_ms is not None:
            params["startTimeMs"] = start_time_ms
        _, data = await self._request("get", url, params=params)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "events", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []
