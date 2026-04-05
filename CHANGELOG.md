# Changelog

All notable changes to this project are recorded in this file.

## [Unreleased]

### Added
- **Kodi fanart support**: Added addon fanart metadata and menu-level fanart assignment so skins can render `resources/media/background.jpg` when opening/browsing the addon.
- **Logout icon asset**: Added dedicated `menu_logout.png` and wired main menu logout item to prefer this asset.
- **Converted localization catalogs**: Added `resource.language.en_gb/strings.po` and `resource.language.nl_nl/strings.po` for converted settings string resolution.

### Changed
- Settings now run in Dutch-only mode for addon settings UI: removed language switch controls from settings and removed language-dependent branching in settings label paths.
- Localization layout migrated from legacy `resources/language/English|Dutch/strings.xml` to Kodi resource language folders used by converted settings.
- Service wrapper simplified to a minimal monitor loop; removed language-change monitor/state persistence logic.
- Addon metadata now keeps Dutch summary/description only.

### Fixed
- Fixed missing/blank settings labels by keeping converted `version="1"` settings structure and providing matching string IDs in resource language catalogs.
- Fixed inconsistent language rendering in settings by using Dutch labels in both fallback catalogs.

### Notes
- `resources/settings.xml` remains in converted format (`<settings version="1">` + section/category/group/setting/control hierarchy) per Kodi conversion guidance.

----

## [0.0.9] - 2026-04-04

### Added
- **Token-Based OAuth2 Authentication**: Secure PKCE-based login flow with automatic token refresh. Sessions persist across Kodi restarts via cookie storage.
- **Dialog-Based Login**: Modern Kodi dialog login interface — credentials are never exposed in addon settings menu for better security UX.
- **Optional Credential Storage**: Users choose between "Save tokens only" (recommended, requires login only when tokens expire) or "Save email+password" (auto-refresh convenience).
- **Auto-Token Refresh**: Sessions automatically refresh when tokens expire. Fallback to form login if refresh fails, with user re-login prompt.
- **Dynamic Login/Sign Out Button**: Main menu displays "Login" when not authenticated and "Sign Out" when user has active session.
- **Protected Content Menu**: Series, Movies, TV Shows, Search, and My List menu items hidden for unauthenticated users to prevent API errors.
- **Logout Confirmation Flow**: Two-step logout with optional "Keep My List" to preserve favorites after sign out.
- **Smart Artwork by Aspect Ratio**: Automatically separates and assigns images based on aspect ratio — landscape (16:9) for fanart/poster, portrait (2:3) for covers, preventing face-cutting.
- **High-Resolution Fanart Images**: Image URLs now request 3840px width from the NLZiet image service, rendering crisp 4K-quality artwork instead of small pixelated thumbnails.
- **Global API Instance Caching**: 5-minute TTL cache reduces initialization overhead and disk I/O on every menu interaction.
- **Instant Context Menu Response**: Menu operations (Add/Remove My List, etc.) now near-instantaneous by reusing cached API instances instead of creating new ones per item.
- **Channel Optimization**: Skips unnecessary `/v9/content/detail` requests for channel items (endpoint not supported), eliminating 404 errors.

### Changed
- Authentication workflow completely redesigned: moved from settings-based credentials to secure dialog-based OAuth2 flow.
- API instance creation now centralized via `get_api_instance()` function with caching logic for 15+ menu functions.
- Image optimization function now requests 3840px width instead of stripping parameters, ensuring high-quality fanart display.
- Context menu items now use cached API instances instead of creating new NLZietAPI objects per item interaction.

### Fixed
- Channel menus no longer generate 404 errors from unsupported `/v9/content/detail` endpoint.
- Image aspect ratio correctly preserved in Kodi artwork keys — landscape images no longer assigned to portrait keys and vice versa.
- Small pixelated fanart images now request higher resolution from API, eliminating zoom/crop appearance on large screens.
- Menu response time reduced from 2-3 seconds to near-instant for context operations (Add/Remove My List).

### Notes
- OAuth2 PKCE flow ensures secure token exchange without exposing client secrets.
- Cookie-based session persistence uses HTTP LWP format for cross-session recognition.
- Token expiry buffer set to 30 seconds for proactive refresh before actual expiration.
- Image resolution optimization applies to both portrait and landscape image picking functions.
- API cache timeout set to 300 seconds (5 minutes) — balance between freshness and performance.

----

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

