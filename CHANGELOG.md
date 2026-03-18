# Changelog

All notable changes to this project are recorded in this file.

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
