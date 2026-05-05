"""HTTP view that proxies camera stream requests to NX Witness.

NX Witness `_ticket` authorization is single-use. ffmpeg/Stream opens the
source URL multiple times (probe, read, reconnects), so we cannot embed a
ticket directly in `stream_source`. Instead, `stream_source` returns a URL
served by this view, which mints a fresh ticket per request and 302-redirects
to the real NX media URL.
"""
from __future__ import annotations

import logging
import secrets

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STREAM_PATH = "/api/nx_witness/stream/{entry_id}/{secret}/{camera_id}"


class NXWitnessStreamView(HomeAssistantView):
    """Mints a fresh NX ticket and redirects to the camera media URL."""

    url = STREAM_PATH
    name = "api:nx_witness:stream"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(
        self,
        request: web.Request,
        entry_id: str,
        secret: str,
        camera_id: str,
    ) -> web.Response:
        coordinator = self.hass.data.get(DOMAIN, {}).get(entry_id)
        if coordinator is None or not secrets.compare_digest(
            secret, getattr(coordinator, "stream_secret", "")
        ):
            return web.Response(status=404)

        ticket = await coordinator.client.get_ticket()
        if not ticket:
            _LOGGER.error("Failed to mint ticket for camera %s", camera_id)
            return web.Response(status=502)

        location = (
            f"{coordinator.host}/rest/v4/devices/{camera_id}/media?_ticket={ticket}"
        )
        return web.Response(status=302, headers={"Location": location})


def stream_path_for(entry_id: str, secret: str, camera_id: str) -> str:
    return f"/api/nx_witness/stream/{entry_id}/{secret}/{camera_id}"
