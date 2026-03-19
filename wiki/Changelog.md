# Changelog

This file documents notable changes to the NLZiet Kodi Addon. For packaged releases see the [GitHub Releases page](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).

## [0.0.3] - 2026-03-19

### Added
- Persistent profile UI: active profile displays green and remains highlighted until changed.
- Prefer bundled PNG menu icons (`menu_*.png`) for main menu items (login, profiles, search, series, movies, channels); `menu_tv.png` used as a Channels fallback.
- `CREDITS.md` with Lucide icon attribution.

### Changed
- Non-active profiles now use `emoji_google_inactive.png` as their thumb; active profiles use `emoji_google_active.png` and show `Active` in supported skins.
- `select_profile` now updates the container with `Container.Update(...,replace)` to avoid adding navigation history so Back returns to the main menu instead of cycling profiles.
- Added a PNG-first icon picker (`_pick_png()`) in `main_menu()`.

### Fixed
- Back navigation no longer toggles between previously selected profiles.

---

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
