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
| `event_type` | `intrusion` | Human-readable event type (e.g. `motion`, `intrusion`, `object_detected`) |
| `classification` | `Person` | Detected object type for analytics events (if available) |
| `area` | `Front Yard Intrusion` | Rule/zone name from NX Witness (if available) |
| `event_state` | `detected` | `detected` or `stopped` |
| `event_description` | `Person detected on zone A` | Description from the event (if available) |
| `last_detection` | `2026-03-02T10:00:00` | ISO timestamp of the last event |
| `active_events` | `[{...}, {...}]` | List of all concurrent active events (only present when 2+ events fire at the same time for a camera) |

### Example Automation

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
          message: "Person detected!"
```

## Setting Up Rules in NX Witness

For this integration to receive events, NX Witness must be configured to log them. The integration polls `/rest/v4/events/log` every 5 seconds, so **every rule must write to the log** — otherwise Home Assistant will never see the event.

> **Important:** In every Event Rule, set the action to **Write to Log** with timing **When event starts**. Also enable the **Interval of Action** (e.g. once per 1 minute) to avoid flooding Home Assistant with duplicate events.

### Opening Event Rules

In the NX Witness Desktop Client: **System Administration → Event Rules → Add Rule**

---

### Rule Type 1: Analytics Object Detected (Person / Vehicle / Animal)

Use this rule type to detect specific objects identified by your analytics engine.

| Setting | Value |
|---|---|
| WHEN EVENT | `Analytics Object Detected` |
| Occurs At | Select your cameras |
| Of Type | `Person`, `Vehicle`, or `Animal` |
| AND OBJECT | `Has attributes` (leave Attributes blank to match all) |
| DO ACTION | `Write to Log` → `When event starts` |
| Interval of Action | Once in 1 Min |

Create one rule per object type (e.g. "Person Object Detection", "Vehicle Object Detection").

**Result in Home Assistant:**
- `event_type`: `object_detected`
- `classification`: `Person`, `Vehicle`, or `Animal`

---

### Rule Type 2: Analytics Event — Intrusion Detection

Use this rule type for zone-based intrusion events from analytics plugins (e.g. CVEDIA RT).

| Setting | Value |
|---|---|
| WHEN EVENT | `Analytics Event` |
| Occurs At | Select your cameras |
| Of Type | `Intrusion detection` |
| AND CAPTION | Optional keyword filter (leave blank to catch all) |
| DO ACTION | `Write to Log` → `When event starts` |
| Interval of Action | Once in 1 Min |

**Result in Home Assistant:**
- `event_type`: `intrusion`
- `classification` and `area`: populated from the event caption

---

### Motion Detection (no Event Rule needed)

Motion detection is configured at the camera level and does not require an Event Rule.

1. Right-click the camera → **Camera Settings** → **Motion Detection** tab
2. Enable motion detection and adjust sensitivity and detection regions

Motion events are written to the log automatically.

**Result in Home Assistant:**
- `event_type`: `motion`

---

## Creating Alerts in Home Assistant

Once NX Witness rules are logging events, you can trigger alerts in Home Assistant using the `binary_sensor.camera_name_event` sensors created by this integration. The sensor turns `on` for 30 seconds when an event is detected, then returns to `off`.

> Replace `camera_name` in the examples below with your actual camera entity name (e.g. `binary_sensor.garage_event`), and `YOUR_PHONE` with your mobile app notify target (find it under **Settings → Devices & Services → Companion App**).

---

### Method 1: Single-Camera Automation

Trigger a notification when a specific camera detects a Person:

```yaml
automation:
  - alias: "NX Witness: Person detected"
    trigger:
      - platform: state
        entity_id: binary_sensor.camera_name_event
        to: "on"
    condition:
      - condition: template
        value_template: "{{ state_attr('binary_sensor.camera_name_event', 'classification') == 'Person' }}"
    action:
      - service: notify.mobile_app_YOUR_PHONE
        data:
          title: "Security Alert"
          message: >
            Person detected
            (Area: {{ state_attr('binary_sensor.camera_name_event', 'area') }})
```

Change the `classification` value to `Vehicle` or `Animal` to filter for those object types instead.

---

### Method 2: Multi-Camera Automation

Watch several cameras at once and include the triggering camera in the message:

```yaml
automation:
  - alias: "NX Witness: Person on any camera"
    trigger:
      - platform: state
        entity_id:
          - binary_sensor.camera_one_event
          - binary_sensor.camera_two_event
        to: "on"
    condition:
      - condition: template
        value_template: "{{ state_attr(trigger.entity_id, 'classification') == 'Person' }}"
    action:
      - service: notify.mobile_app_YOUR_PHONE
        data:
          title: "Security Alert"
          message: >
            Person detected
            (Camera: {{ trigger.entity_id }},
             Area: {{ state_attr(trigger.entity_id, 'area') }})
```

---

### Method 3: Persistent Alert (HA Alert Integration)

For a repeating alert that stays visible in the Home Assistant UI until acknowledged, add the following to `configuration.yaml`:

```yaml
alert:
  camera_person_alert:
    name: "Person detected - Camera Name"
    done_message: "All clear - Camera Name"
    entity_id: binary_sensor.camera_name_event
    state: "on"
    repeat: 5
    can_acknowledge: true
    notifiers:
      - mobile_app_YOUR_PHONE
```

Restart Home Assistant after saving. The alert will repeat every 5 minutes until the sensor turns `off` or it is acknowledged in the UI.

---

## Changelog

### 0.4.2
- Internal refactor: shared SSL context and event helpers extracted into `utils.py` — eliminates duplicated SSL setup code across config flow and coordinator
- API client consolidated into a single `_request()` helper with automatic token refresh on 401, replacing four near-identical retry blocks
- Event lookup optimised: the coordinator now pre-indexes events by camera ID so each binary sensor does an O(1) dict lookup instead of scanning the full event list on every 5-second poll tick
- Session cleanup: coordinator now closes the aiohttp session on integration unload

### 0.4.1
- **Bug fix:** When NX fires multiple rules simultaneously for the same camera (e.g. an `analyticsObject` person-tracking event and a separate `analytics` intrusion-rule event at the same time), the sensor now processes **all** of them instead of stopping at the first match
- The most-recent event continues to drive the primary attributes (`event_type`, `classification`, `area`, etc.)
- New `active_events` attribute: a list of all concurrent active events — useful in automations/templates when you need to check every alert type that fired at once (e.g. to confirm both a person was detected *and* an intrusion zone was triggered)

### 0.4.0
- `analytics_attributes` attribute added to event sensors — exposes raw analytics data (e.g. `species`, `track_duration`) from `analyticsObject` events as a snake_case dict for use in HA templates
- Fixed `_extract_object_class()` to correctly parse the `{name, value}` list format returned by the NX Witness API for analytics object attributes

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

Current version: 0.4.2

## License

MIT License
