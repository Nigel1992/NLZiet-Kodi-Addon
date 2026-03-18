# Changelog

This file documents notable changes to the NLZiet Kodi Addon. For packaged releases see the [GitHub Releases page](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).

## [0.0.2] - 2026-03-19

### Added
- Implemented Search for Series and Movies — searching now returns proper Series folders and playable Movie/Episode items.
- Search requests now include repeated `contentType` parameters (e.g. `contentType=Movie&contentType=Series`) to match the upstream API.
- Search includes `Authorization: Bearer <token>` and attempts a PKCE authorize+exchange when a cookie session is present so authenticated searches work reliably.
- `X-Profile-Id` is sent when an active profile is selected.

### Fixed
- Corrected search result routing so Series open the series detail view and Movies/Episodes trigger playback.
- Added fallback search logic (querying series/movies/channels) when the primary search endpoint returns no results.

### Changed
- Bumped add-on version to `0.0.2`.
- Created release archive and published GitHub release `v0.0.2`.

---

Previous releases and a full history are available on the GitHub Releases page.
