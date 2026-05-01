"""DataUpdateCoordinator for NX Witness."""
import logging
import secrets
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, EVENT_LOG_INTERVAL, UPDATE_INTERVAL
from .nx_client import NXWitnessClient
from .utils import create_client_session, create_ssl_context, extract_camera_id

_LOGGER = logging.getLogger(__name__)


class NXWitnessDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching NX Witness data."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        username: str,
        password: str,
    ) -> None:
        """Initialize."""
        self.hass = hass
        self.host = host
        self.username = username
        self.password = password
        self.client = None
        self.cameras = []
        self.events = []
        self.last_camera_check = datetime.min
        self._session = None
        self.stream_secret = secrets.token_urlsafe(16)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=EVENT_LOG_INTERVAL),
        )

    async def _async_setup(self):
        """Set up the coordinator with SSL context."""
        ssl_context = await self.hass.async_add_executor_job(create_ssl_context)
        self._session = create_client_session(ssl_context)
        self.client = NXWitnessClient(
            self.host,
            self.username,
            self.password,
            self._session,
        )
        if not await self.client.login():
            raise UpdateFailed("Failed to login to NX Witness")

    async def _async_update_data(self):
        """Update data via library."""
        try:
            now = datetime.now()

            if (now - self.last_camera_check).total_seconds() >= UPDATE_INTERVAL:
                cameras = await self.client.get_cameras()
                if cameras:
                    self.cameras = cameras
                self.last_camera_check = now

            start_time_ms = int((now - timedelta(minutes=1)).timestamp() * 1000)
            self.events = await self.client.get_event_log(start_time_ms)

            # Pre-index events by camera_id for O(1) sensor lookup
            events_by_camera: dict[str, list] = {}
            for ev in self.events:
                cam_id = extract_camera_id(ev)
                if cam_id:
                    events_by_camera.setdefault(cam_id, []).append(ev)

            return {
                "cameras": self.cameras,
                "events": self.events,
                "events_by_camera": events_by_camera,
            }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with NX Witness: {err}") from err

    async def async_shutdown(self) -> None:
        """Clean up resources."""
        await super().async_shutdown()
        if self._session and not self._session.closed:
            await self._session.close()
