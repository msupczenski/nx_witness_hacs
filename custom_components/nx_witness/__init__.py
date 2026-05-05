"""NX Witness integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import NXWitnessDataUpdateCoordinator
from .stream_view import NXWitnessStreamView

_VIEW_REGISTERED_KEY = "_stream_view_registered"

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CAMERA, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NX Witness from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.data[DOMAIN].get(_VIEW_REGISTERED_KEY):
        hass.http.register_view(NXWitnessStreamView(hass))
        hass.data[DOMAIN][_VIEW_REGISTERED_KEY] = True

    coordinator = NXWitnessDataUpdateCoordinator(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    # Setup SSL and login
    await coordinator._async_setup()
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.host)},
        manufacturer="Network Optix",
        model="NX Witness Server",
        name="NX Witness",
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok
