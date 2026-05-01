"""Active LAN discovery for NX Witness mediaservers.

NX Mediaserver does not advertise itself via mDNS/SSDP, so we actively probe
each host on the local IPv4 subnets for /api/moduleInformation and match the
NX-specific response shape.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
from dataclasses import dataclass

import aiohttp

from homeassistant.components import network
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PORT
from .utils import create_client_session, create_ssl_context

_LOGGER = logging.getLogger(__name__)

PROBE_TIMEOUT = 1.5
MAX_CONCURRENCY = 64
MAX_HOSTS = 1024  # safety cap so a /16 doesn't hang HA


@dataclass(frozen=True)
class DiscoveredServer:
    """A mediaserver found on the LAN."""

    host: str
    port: int
    name: str
    version: str
    customization: str
    system_id: str

    @property
    def url(self) -> str:
        return f"https://{self.host}:{self.port}"

    @property
    def label(self) -> str:
        return f"{self.name} ({self.host}) — v{self.version}"


async def _probe(
    session: aiohttp.ClientSession, ip: str, port: int
) -> DiscoveredServer | None:
    for scheme in ("https", "http"):
        url = f"{scheme}://{ip}:{port}/api/moduleInformation"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=PROBE_TIMEOUT)
            ) as response:
                if response.status != 200:
                    continue
                data = await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            continue

        reply = data.get("reply") if isinstance(data, dict) else None
        if not isinstance(reply, dict):
            continue
        if reply.get("type") != "Media Server" or reply.get("realm") != "VMS":
            continue
        return DiscoveredServer(
            host=ip,
            port=port,
            name=reply.get("name") or f"NX server {ip}",
            version=reply.get("version") or "?",
            customization=reply.get("customization") or "",
            system_id=reply.get("localSystemId") or reply.get("id") or "",
        )
    return None


async def _candidate_hosts(hass: HomeAssistant) -> list[str]:
    adapters = await network.async_get_adapters(hass)
    hosts: list[str] = []
    seen: set[str] = set()
    for adapter in adapters:
        if not adapter.get("enabled"):
            continue
        for ipv4 in adapter.get("ipv4", []):
            address = ipv4.get("address")
            prefix = ipv4.get("network_prefix")
            if not address or prefix is None:
                continue
            try:
                net = ipaddress.IPv4Network(f"{address}/{prefix}", strict=False)
            except ValueError:
                continue
            # Skip overly large or non-LAN networks
            if net.prefixlen < 22 or not net.is_private:
                continue
            for host in net.hosts():
                ip = str(host)
                if ip in seen:
                    continue
                seen.add(ip)
                hosts.append(ip)
                if len(hosts) >= MAX_HOSTS:
                    return hosts
    return hosts


async def discover_servers(
    hass: HomeAssistant, port: int = DEFAULT_PORT
) -> list[DiscoveredServer]:
    """Scan local IPv4 subnets for NX mediaservers on the given port."""
    hosts = await _candidate_hosts(hass)
    if not hosts:
        return []

    ssl_context = await hass.async_add_executor_job(create_ssl_context)
    session = create_client_session(ssl_context)
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def bounded(ip: str) -> DiscoveredServer | None:
        async with semaphore:
            return await _probe(session, ip, port)

    try:
        results = await asyncio.gather(*(bounded(ip) for ip in hosts))
    finally:
        await session.close()

    found = [r for r in results if r is not None]
    # De-duplicate by system id (a multi-server system advertises the same id)
    by_id: dict[str, DiscoveredServer] = {}
    for server in found:
        key = server.system_id or f"{server.host}:{server.port}"
        by_id.setdefault(key, server)
    discovered = list(by_id.values())
    _LOGGER.debug("Discovered %d NX server(s) across %d hosts", len(discovered), len(hosts))
    return discovered
