# NX Witness HACS Integration — Claude Code Guidelines

## Release hygiene (required on every feature or fix)

When making any user-visible change, always update **both** of the following in the same commit or a follow-up commit before pushing:

1. **`custom_components/nx_witness/manifest.json`** — bump `"version"` (semver patch for fixes, minor for new features)
2. **`README.md`** — add a new `### X.Y.Z` section at the top of the `## Changelog` block and update the `Current version:` line at the bottom

No exceptions — this applies even to small bug fixes.

## Repository layout

```
custom_components/nx_witness/
  __init__.py        # platform registration (PLATFORMS list)
  manifest.json      # version lives here
  coordinator.py     # DataUpdateCoordinator, 5-second event polling
  nx_client.py       # REST API v4 wrapper
  binary_sensor.py   # per-camera event sensor
  camera.py          # live stream + snapshot
  image.py           # best shot image entity
  stream_view.py     # HTTP proxy for single-use stream tickets
  config_flow.py     # setup UI + LAN discovery
  discovery.py       # LAN scanner
  utils.py           # shared SSL/session/payload helpers
  const.py           # intervals, timeouts, domain
```

## Key constants

| Constant | Value | Notes |
|---|---|---|
| `EVENT_LOG_INTERVAL` | 5 s | How often events are polled |
| `UPDATE_INTERVAL` | 30 s | How often camera list refreshes |
| `EVENT_SENSOR_TIMEOUT` | 30 s | How long binary sensor stays `on` |
| `DEFAULT_PORT` | 7001 | NX Witness REST API port |

## NX Witness API endpoints in use

- `POST /rest/v4/login/sessions` — auth
- `POST /rest/v4/login/tickets` — single-use media tickets
- `GET  /rest/v4/devices` — camera list
- `GET  /rest/v4/events/log?startTimeMs=` — event polling
- `GET  /rest/v4/devices/{id}/image` — snapshot
- `GET  /rest/v4/devices/{id}/media` — live stream
- `GET  /rest/v4/analytics/objectTracks/{trackId}/bestShot` — best shot image
