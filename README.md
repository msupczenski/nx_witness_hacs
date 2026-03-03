# NX Witness Integration for Home Assistant

Simple integration to add NX Witness cameras to Home Assistant.

## Features

- Automatic camera discovery
- Live camera snapshots
- Video streaming support
- Dynamic event sensors from `/rest/v4/events/log`
- Enriched event attributes: `event_type`, `classification` (Person, Vehicle, Face), and `area` (zone/rule name)
- Simple username/password setup — no webhooks or server-side rules needed

## Installation

### Via HACS (Custom Repository)

1. Open HACS → Integrations
2. Click the three-dot menu → Custom repositories
3. Add: `https://github.com/msupczenski/nx_witness_hacs`
4. Category: Integration
5. Click "Download"
6. Restart Home Assistant

### Manual

1. Copy `custom_components/nx_witness` to your Home Assistant `custom_components` folder
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "NX Witness"
4. Enter:
   - **Host**: Must be in format `https://IP_ADDRESS:7001` (e.g., `https://192.168.1.100:7001`)
   - **Username**: Your NX Witness username
   - **Password**: Your NX Witness password
5. Click Submit

All cameras will be automatically discovered.

## NX Witness Rule Setup

Events are only surfaced in Home Assistant if you have rules configured in NX Witness to write them to the event log. Two rule patterns are supported.

---

### Option 1 — Analytics Object Detected (recommended for object/species data)

This produces structured events that include a full `analytics_attributes` payload (e.g. `Species`, `Track Duration`).

1. In NX Witness open **Event Rules**
2. Create a new rule:
   - **Event**: `Analytics: Object Detected`
   - **At**: select the camera(s) you want to monitor
   - **Action**: `Write to Log`
3. Save and enable the rule

The sensor will populate `event_type: analytics_object`, `classification` (from `objectTypeId`, e.g. `animal`), and `analytics_attributes` (all key/value pairs the analytics plugin reports, e.g. `species: Bear`, `track_duration: 23.40`).

---

### Option 2 — Generic / Intrusion Analytics (caption-based)

This covers rules driven by analytics plugins that fire a named event and write a caption in the format **`Type - Class - Zone`** (e.g. `Person - Person - Front Yard Intrusion`).

1. In NX Witness open **Event Rules**
2. Create a new rule:
   - **Event**: the analytics event type from your plugin (e.g. `cvedia.rt.intrusion`, `Soft Trigger`, etc.)
   - **At**: select the camera(s)
   - **Action**: `Write to Log`
3. Save and enable the rule

The sensor will populate `event_type` (e.g. `intrusion`), `classification` (e.g. `Person`), and `area` (e.g. `Front Yard Intrusion`) by parsing the caption.

---

## Requirements

- NX Witness Server with REST API v4 support
- Home Assistant 2024.1.0+
- Network access from Home Assistant to NX Witness server

## Troubleshooting

**Cannot Connect Error:**
- Verify NX Witness server is running
- Check that credentials are correct
- Ensure port 7001 is accessible
- Host must be in format: `https://192.168.1.100:7001` (including https:// and :7001)

**Cameras Not Appearing:**
- Check Home Assistant logs
- Verify user has camera viewing permissions in NX Witness
- Reload the integration

## Event Sensor Attributes

Each camera gets a `binary_sensor` entity (e.g. `binary_sensor.camera_1_event`) that turns `on` when an event is detected within the last 30 seconds. The following attributes are available for use in automations and templates:

| Attribute | Example | Description |
|---|---|---|
| `camera_id` | `{uuid}` | Internal NX Witness camera ID |
| `event_type` | `intrusion` | Human-readable event type (e.g. `motion`, `intrusion`, `analytics_object`) |
| `classification` | `animal` | Detected object type for analytics events (if available) |
| `area` | `Front Yard Intrusion` | Rule/zone name from NX Witness caption (if available) |
| `event_state` | `detected` | `detected` or `stopped` |
| `event_description` | `Person detected on zone A` | Description from the event (if available) |
| `last_detection` | `2026-03-02T10:00:00` | ISO timestamp of the last event |
| `analytics_attributes` | `{species: Bear, track_duration: "23.40"}` | Raw key/value attributes from the analytics plugin (Option 1 rules only) |

> `analytics_attributes` is a dict with snake_cased keys. Any attribute your analytics plugin reports (Species, Track Duration, Confidence, etc.) will appear here automatically.

### Example Automations

**Option 2 — trigger on intrusion classification (caption-based):**
```yaml
automation:
  - alias: "Person detected on front door camera"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_event
        to: "on"
    condition:
      - condition: template
        value_template: "{{ state_attr('binary_sensor.front_door_event', 'classification') == 'Person' }}"
    action:
      - service: notify.mobile_app
        data:
          message: "Person detected at {{ state_attr('binary_sensor.front_door_event', 'area') }}!"
```

**Option 1 — trigger on analytics object species:**
```yaml
automation:
  - alias: "Bear detected on wildlife camera"
    trigger:
      - platform: state
        entity_id: binary_sensor.wildlife_camera_event
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('binary_sensor.wildlife_camera_event', 'analytics_attributes', {}).get('species') == 'Bear' }}
    action:
      - service: notify.mobile_app
        data:
          message: >
            Bear detected! Track duration: {{ state_attr('binary_sensor.wildlife_camera_event', 'analytics_attributes', {}).get('track_duration') }}s
```

## Changelog

### 0.3.3
- New `analytics_attributes` sensor attribute surfaces all key/value pairs from `eventData.attributes` (e.g. `species: Bear`, `track_duration: 23.40`) for Analytics Object Detected rules
- Added NX Witness Rule Setup section to README covering both Option 1 (Analytics Object Detected) and Option 2 (caption-based intrusion/generic) rule patterns
- Fixed `_extract_object_class()` to correctly handle `eventData.attributes` as a list of `{name, value}` dicts (matching actual NX Witness API format)

### 0.3.2
- `area` attribute now shows only the zone/rule name (e.g. `Front Yard Intrusion`) instead of the full caption string
- `classification` attribute now correctly extracted from caption format `Type - Class - Zone` (e.g. `Person`)
- `event_type` now cleaned for third-party analytics events using `cvedia.rt.*` prefix (e.g. `intrusion` instead of `cvedia.rt.intrusion`)

### 0.3.1
- Split intrusion event attributes into three distinct fields: `event_type`, `classification`, and `area`
- `event_type` now reflects the actual NX Witness event type ID (e.g. `intrusion`, `motion`) rather than the zone caption
- `classification` replaces `object_class` (e.g. `Person`, `Vehicle`)
- New `area` attribute surfaces the rule/zone caption (e.g. `Front Yard Intrusion`)
- Removed `last_event_type` backwards-compatibility attribute

### 0.3.0
- Enriched event sensor attributes: `event_type`, `event_state`, `event_description`, `object_class`
- `event_type` is now a clean, human-readable string (e.g. `motion` instead of `nx.base.MotionEvent`)
- Analytics object detection (Person, Vehicle, Face, etc.) surfaced via `object_class`

### 0.2.2
- Initial release with camera discovery, streaming, and event sensors

## Version

Current version: 0.3.3

## License

MIT License
