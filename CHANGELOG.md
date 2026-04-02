# Changelog

All notable changes to this project are recorded in this file.

## [0.0.8] - 2026-04-02

### Added
- **Full Dutch/English Localization**: Complete UI translation with 47 translation entries covering all menu items, settings, and notifications. Users can toggle language in settings.
- **Language Change Notification**: Addon now detects language setting changes and notifies user to restart addon/Kodi to apply the change.
- **TV Show Broadcast Date Display**: Episodes now show broadcast/aired date in both Dutch ("Uitgezonden") and English ("Aired") formats.
- **TV Shows Category System**: Organized TV shows by 18 genres (Comedy, Drama, Sports, News, Documentary, etc.) for better browsing.
- **Subtitle Enforcement**: Subtitle default setting now properly enforced across DRM and non-DRM playback with robust boolean parsing.
- **Enhanced Debug Logging**: Added comprehensive debug logging for live TV detection, subtitle handling, and language changes.
- **Settings Information**: Added bilingual help text in settings explaining language change requirements.

### Changed
- TV shows endpoint optimized: switched from `recommendVideos` to `allPopularPrograms` to overcome ~40 item limit.
- Movie browsing improved: items in genre view now correctly marked as playable (not folders).
- Episode subtitle detection enhanced: episodes now show their actual names (e.g., "Tweede helft" for NOS Voetbal).
- Broadcast date extraction upgraded: added support for `broadcastAt` field from API responses.
- Settings UI enhanced with bilingual labels throughout all 7 categories.

### Fixed
- Movies in genre browsing now display as playable items instead of folders.
- TV show category and series genre lists now display proper counts (4 genres for Series, 18 for TV Shows, 10 for Movies).
- Subtitle setting boolean parsing now handles all Kodi return value formats (None, '', 'true', 'false', True, False, '1', '0').
- Episodes without descriptions now display broadcast date and other metadata correctly.
- Genre/category routing fixed to properly distinguish between playable content and folder navigation.

### Notes
- Language localization uses Kodi's standard language infrastructure with .po files for future native support.
- Subtitle enforcement includes special handling for both Widevine DRM and standard HLS/DASH streams.
- Live TV streams are specially flagged in debug logs for enhanced troubleshooting.

----

## [0.0.7] - 2026-03-26

### Added
- Persist cookie-based login across Kodi restarts so the add-on recognizes logged-in sessions.

### Changed
- Bumped addon version to `0.0.7` and created release zip package.

### Fixed
- Minor fixes and packaging updates.

----

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

## [0.0.6] - 2026-03-25

### Added
- Main menu: new "TV Shows" and "Documentary" entries using the recommend endpoints.
- Settings: new **Account** section showing subscription name, subscription expiry, and max devices (read-only).
- Settings: `Logout` action that clears cookies, tokens, profiles and local My List (with confirmation).

### Changed
- Profiles moved into a dedicated **Profiles** settings category and are now read-only in Settings.
- Main menu now hides protected items (Profiles, Search, My List, Series, Movies, Channels) when not authenticated.
- Account info is refreshed silently on addon launch and after login/profile changes.

### Fixed / Notes
- Improved token/cookie handling and added a PKCE fallback to exchange cookie sessions for tokens when needed.
- Various UI and parsing improvements: thumbnail selection, expiry formatting, and defensive API parsing.

----

