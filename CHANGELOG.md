# Changelog

All notable changes to the NX Witness Home Assistant integration are documented here.

## [0.4.7] - 2026-05-13

### Fixed
- HACS now shows proper version numbers instead of git commit hashes
- Added changelog so release notes appear in the HACS update dialog

## [0.4.6] - 2025-04-25

### Added
- Best shot image entity for NX Witness analytics events

### Fixed
- Expanded `deviceType` filter to include multi-lens and third-party cameras

## [0.4.4] - 2025-04-01

### Added
- Auto-discover NX Witness servers in the config flow

### Fixed
- Expanded `deviceType` filter to include additional camera models

## [0.4.3] - 2025-03-15

### Changed
- Token is now refreshed more frequently to avoid authentication failures

### Fixed
- Camera streams are now proxied through Home Assistant to mint per-request NX tickets

## [0.4.2] - 2025-03-01

### Added
- HACS integration support (`hacs.json`, `manifest.json` compliance)

### Changed
- Efficiency improvements across the integration

## [0.4.1] - 2025-02-15

### Fixed
- Handle multiple simultaneous NX Witness events firing for the same camera

## [0.4.0] - 2025-02-01

### Added
- Analytics object attributes on binary sensor entities
- Documentation: NX Witness rules setup and Home Assistant alert how-to guides

## [0.3.2] - 2025-01-20

### Fixed
- Caption parsing: split caption into separate `classification` and `area` attributes
- Cleaned up Cvedia event types

## [0.3.1] - 2025-01-10

### Changed
- Refactored intrusion event attributes into separate `event_type`, `classification`, and `area` fields

## [0.3.0] - 2025-01-01

### Changed
- Enriched event sensor attributes with clean types, object class, and description

## [0.2.2] - 2024-12-15

### Fixed
- Restored camera event sensors after simplification pass

## [0.2.1] - 2024-12-01

### Fixed
- Event log parsing and sensor keying for nested `eventData`
- Analytics track matching for Home Assistant binary sensors

## [0.2.0] - 2024-11-15

### Added
- Object detection sensors: person, vehicle, face
- Parent NX Witness device with `via_device` references for all child entities

## [0.1.3] - 2024-11-01

### Fixed
- Version display in HACS
- Integration icon

## [0.1.2] - 2024-10-25

### Added
- Integration icon

## [0.1.1] - 2024-10-15

### Changed
- Improved documentation and UI strings

## [0.1.0] - 2024-10-01

### Added
- Initial release: camera entity support for NX Witness VMS
