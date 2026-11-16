# NLZiet Kodi Addon — Technical Documentation

Developer/contributor reference. For end-user docs, see [USER_GUIDE.md](USER_GUIDE.md).

## Architecture

- **Entry point**: `default.py` — Kodi plugin entry, routing, UI, context menus, playback.
- **Background service**: `service.py` — library updates, watched sync, reminders, daily checks, resume sync, logo lookup.
- **Shared modules**: `resources/lib/` — `library.py`, `library_art.py`, `library_resume.py`, `metadata.py`, `playback_extras.py`, `watch_sync.py`, `watch_history.py`, `resume_store.py`, `corner.py`, `router.py`, `errors.py`, `diagnostics.py`, `parental.py`, `trakt_status.py`, `subtitles.py`, `logo_cache.py`, `tvmaze.py`, `nlziet_api.py`, `iptvmgr.py`, `kodi/ui.py`, `app_context.py`, `search_filters.py`, `reminders.py`.

Shared modules are kept in sync with the Videoland addon via `scripts/sync-shared.py` and `SHARED.lock`.

## Library system

- `library.Library` manages series/movies in `addon_data/plugin.video.nlziet/library.json`.
- Exports `.strm` + `.nfo` per episode/movie into `TV Shows/` and `Movies/` folders.
- `LocalFS` handles local (`os`) and remote (`xbmcvfs` for smb/nfs) paths.
- `LibraryStore` persists tracked items; `_load` only accepts known keys.
- `update_all()` adds new episodes, removes expired ones, never deletes on empty API answer.
- `remove()` validates folder safety (`_is_safe_folder`, `_path_inside_root`) to prevent path traversal.
- `migrate_legacy_folder()` moves 1.6.x `KodiNLZietLibrary` into the addon folder (symlink-safe).
- `library_from_lists()` syncs "My Series" and "Watch Later" to the library.
- `register_library_sources()` / `ensure_sources_xml()` / `_fix_library_sources_db()` register folders as Kodi video sources with content type + `metadata.local` scraper, and trigger scans.

## Playback

- `playback_extras`: chapters/markers, skip watcher (intro/recap), next-episode prompt (corner pill), `apply_language`, `start_background` (non-daemon threads).
- `watch_sync`: watched-status logic, `PlaybackWatch`, `Repeats`, `plugin_params`, `strm_target`.
- `watch_history`: local watch history list.
- `resume_store`: VOD resume positions (position/total, pruning).
- `corner`: corner pill overlay for skip/next-episode.
- Service `PlaybackFollower`: samples player, sends watched status, handles Up Next, binge, stop-after, subtitle search.

## API

- `nlziet_api`: NLZiet REST API client (auth, content, watched, continue watching, chapters).
- `metadata`: TMDb/TVmaze fill-in for missing fields; disk cache (7 days), offline back-off, `_safe_id` validation.
- `tvmaze`: show/episode lookup with cache.

## Routing

- `router.Router.dispatch()` maps `mode` to handlers. Handler names must match `EXPECTED_HANDLER_NAMES` in `tests/test_router.py`.

## Settings

- `resources/settings.xml` defines all settings. Defaults are set there; code uses `_setting`/`_setting_on`/`_int_setting` with fallbacks.

## Diagnostics

- `diagnostics.run_checks()` returns sign-in, InputStream/Widevine, connections, TMDb key, library sources, Kodi-vs-library counts.
- Daily background check in service.

## Parental control

- `parental.ParentalControl`: PIN hashing, profile lock, temporary unlock (finite timestamp check).

## Trakt

- `trakt_status`: watched status cache, scrobble logic, watchlist import.

## Testing

- `pytest -q` from addon root. Kodi is stubbed in `tests/conftest.py`.
- 299 tests. Shared module hashes verified by `test_shared_modules.py` + `SHARED.lock`.

## Build & release

- `scripts/build-release.py`: creates `build/plugin.video.nlziet-<version>.zip` from git-tracked files.
- `scripts/build-menu-icons.py`: rebuilds menu icons (requires cairosvg).
- `scripts/sync-shared.py`: syncs shared modules with Videoland addon; `--check` is read-only.
- CI: `.github/workflows/tests.yml` (pytest + zip), `release.yml` (on `v*` tags).

## Versioning

Current: **2.0.0** (addon.xml). License: CC-BY-NC 4.0 (code) / MIT (addon packaging).

## Credits

- **djdirty (Wilfried)** — author of PR #48.
- Nigel1992 — maintainer.