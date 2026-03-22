# Changelog

All notable changes to this project are recorded in this file.

## [0.0.5] - 2026-03-22

### Added
- Landscape thumbnail picker: introduced `_pick_landscape_thumb` to select the best landscape-oriented artwork.

### Changed
- Updated `browse_series`, `show_series_season`, and `do_search` to utilize the new thumbnail picker.
- Enhanced `get_series_list` and `get_series_episodes` in `NLZietAPI` for improved data retrieval and increased limits.

### Notes
- See commit 41af5e0 for implementation details and code-level changes.

----

## [0.0.4] - 2026-03-19

### Added
- Grouped search folders: search now presents per-group folders (e.g. "Series: X", "Movies: X") when results span multiple groups.
- `search_group` route to view results filtered to a single group.
- Landscape thumbnail selection helper (`_pick_landscape_thumb`) to prefer wide/landscape artwork.

### Changed
- Episode labeling prefers `S{n}:A{m}` subtitle codes and uses the subtitle remainder as the episode title when present; falls back to subtitle-only or the API formatted label.
- Menu icons now prefer bundled PNGs first; inactive profiles use the bundled inactive icon.
- Active profile stays highlighted (green) until another is selected; profile changes use `Container.Update(...,replace)` to avoid history cycling.
- HTTP debug logging is now gated behind the `debug_http` setting.

### Fixed
- Search presentation and routing refinements; clearer grouping and improved fallback behavior.

----

## [0.0.2] - 2026-03-19

### Added
- Implemented Search for Series and Movies — results now route to series folders or playable Movie/Episode items.
- Search requests send repeated `contentType` params (`contentType=Movie&contentType=Series`).
- Search sends `Authorization: Bearer <token>` when available and will attempt PKCE authorize+exchange using the saved cookie session.
- `X-Profile-Id` header is included when a profile is selected.

### Fixed
- Search routing fixed: Series open series detail, Movies/Episodes play correctly.
- Fallback search added using series/movies/channels endpoints when primary search returns no results.

### Changed
- Addon version bumped to `0.0.2`.

----

See the GitHub Releases page for binary releases and tags: https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases
