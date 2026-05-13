"""Image platform for NX Witness - best shot images from analytics events."""
import logging
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .binary_sensor import _extract_event_timestamp_ms, _extract_event_type_raw
from .const import DOMAIN
from .coordinator import NXWitnessDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Event types that should trigger a best shot image fetch
_BEST_SHOT_TRIGGERS = {"nx.analytics.BestShot", "nx.analytics.ObjectDetected"}


def _extract_track_id(event: dict[str, Any]) -> str | None:
    """Extract analytics object track ID from event data."""
    event_data = event.get("eventData")
    if not isinstance(event_data, dict):
        return None
    for field in ("objectTrackId", "trackId", "objectId", "analyticsTrackId"):
        value = event_data.get(field)
        if isinstance(value, str) and value:
            return value
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NX Witness best shot image entities."""
    coordinator: NXWitnessDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_camera_ids: set[str] = set()

    def _create_image_entities() -> list[NXWitnessBestShotImageEntity]:
        new_entities: list[NXWitnessBestShotImageEntity] = []
        for camera in coordinator.data.get("cameras", []):
            camera_id = camera.get("id")
            if not camera_id or camera_id in known_camera_ids:
                continue
            known_camera_ids.add(camera_id)
            camera_name = camera.get("name", f"Camera {camera_id}")
            new_entities.append(
                NXWitnessBestShotImageEntity(coordinator, camera_id, camera_name)
            )
        return new_entities

    initial_entities = _create_image_entities()
    if initial_entities:
        async_add_entities(initial_entities)

    def _handle_coordinator_update() -> None:
        new_entities = _create_image_entities()
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))


class NXWitnessBestShotImageEntity(CoordinatorEntity, ImageEntity):
    """Best shot image entity updated when analytics events arrive for a camera."""

    _attr_has_entity_name = True
    _attr_content_type = "image/jpeg"

    def __init__(
        self,
        coordinator: NXWitnessDataUpdateCoordinator,
        camera_id: str,
        camera_name: str,
    ) -> None:
        """Initialize the best shot image entity."""
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self)

        self._camera_id = camera_id
        self._attr_name = "Best Shot"
        self._attr_unique_id = f"{DOMAIN}_{camera_id}_best_shot"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, camera_id)},
            name=camera_name,
            manufacturer="Network Optix",
            via_device=(DOMAIN, coordinator.host),
        )
        self._cached_image: bytes | None = None
        self._last_event_ts: int = 0

    async def async_image(self) -> bytes | None:
        """Return the cached best shot image bytes."""
        return self._cached_image

    def _handle_coordinator_update(self) -> None:
        """Check for new analytics events and schedule an image fetch when one arrives."""
        events = (
            self.coordinator.data.get("events_by_camera", {}).get(self._camera_id, [])
        )

        best_ts = 0
        best_event: dict[str, Any] | None = None
        for event in events:
            raw_type = _extract_event_type_raw(event)
            if raw_type not in _BEST_SHOT_TRIGGERS:
                continue
            ts = _extract_event_timestamp_ms(event)
            # Prefer BestShot events over ObjectDetected when timestamps are equal
            if ts > best_ts or (
                ts == best_ts
                and raw_type == "nx.analytics.BestShot"
                and best_event is not None
                and _extract_event_type_raw(best_event) != "nx.analytics.BestShot"
            ):
                best_ts = ts
                best_event = event

        if best_event is not None and best_ts > self._last_event_ts:
            self._last_event_ts = best_ts
            track_id = _extract_track_id(best_event)
            self.hass.async_create_task(self._async_fetch_image(track_id))

        super()._handle_coordinator_update()

    async def _async_fetch_image(self, track_id: str | None) -> None:
        """Fetch best shot from NX Witness and update entity state."""
        image = await self.coordinator.client.get_best_shot_image(
            self._camera_id, track_id
        )
        if image:
            self._cached_image = image
            self._attr_image_last_updated = dt_util.utcnow()
            self.async_write_ha_state()
            _LOGGER.debug("Best shot updated for camera %s (track=%s)", self._camera_id, track_id)
        else:
            _LOGGER.warning(
                "Failed to fetch best shot for camera %s (track=%s)", self._camera_id, track_id
            )
