<div align="center">

<img src="https://raw.githubusercontent.com/Nigel1992/NLZiet-Kodi-Addon/master/icon.png" width="300" alt="NLZiet Kodi Addon Logo"/>

# NLZiet Kodi Addon

[![GitHub stars](https://img.shields.io/github/stars/Nigel1992/NLZiet-Kodi-Addon?style=social)](https://github.com/Nigel1992/NLZiet-Kodi-Addon)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Latest release:** v1.0.0 — 2026-04-06. See the [Changelog](CHANGELOG.md) or [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).

<sub>Unofficial NLZiet Kodi Addon - Watch live TV, series, movies, and more from NLZiet directly in Kodi. Supports profiles, DRM, and a modern UI.</sub>

</div>

---

> ⚠️ **Warning:** This add-on is under constant development. Some features may be broken or incomplete. Please see the To-Do section below for known issues and planned improvements. Use at your own risk and check back for frequent updates!

---

## ✨ Features

- **Live TV**: Stream all supported NLZiet channels with EPG info.
- **Series**: Browse, search, and play series with full season/episode navigation.
- **Movies**: Discover and watch movies from the NLZiet catalog.
- **Profile Management**: Switch between user profiles from the Kodi UI.
- **DRM Support**: Widevine-protected streams via `inputstream.adaptive` with automatic `inputstreamhelper` verification.
- **Placement Rows**: Home screen rows mirror the official NLZiet app (e.g., "Recommended", "Popular Series").
- **Episode Numbering**: Accurate SxxExx and Dutch soap (Afl. N) parsing, with season mapping.
- **Search**: Find series, movies, and episodes by title.
- **Robust Handshake**: Automatic manifest/license extraction and fallback logic.
- **Debug Logging**: Easy log collection for troubleshooting.

---
### New in v1.0.0

**Authentication & Security:**
- **Token-Based OAuth2 Authentication**: Secure PKCE-based login flow with automatic token refresh. Sessions persist across Kodi restarts via cookie storage.
- **Dialog-Based Login**: Modern login interface — credentials never appear in addon settings menu for better security.
- **Optional Credential Storage**: Choose between "Save tokens only" (recommended) or "Save tokens+credentials" (convenience).
- **Auto-Token Refresh**: Sessions automatically refresh when tokens expire, with 60-second proactive buffer. Falls back to re-login if needed.
- **Cookie-Based Session Fallback**: When refresh_token unavailable, uses preserved session cookie for silent PKCE re-authorization.
- **Sign Out Button**: Dynamic main menu button shows "Login" or "Sign Out" based on authentication status.

**Live TV & EPG:**
- **Live TV EPG Display**: Current program ("Nu live") and next program ("Straks") display with broadcast times (HH:MM-HH:MM).
- **EPG Parser Improvements**: Fixed nested API response structure; correctly extracts program titles, times, descriptions from nested content objects.
- **Smart Program Selection**: Prioritizes currently-playing programs over future/past programs for accurate EPG display.
- **EPG Performance Cache**: 45-second fast cache reduces menu load time while keeping data fresh.

**Performance & Optimization:**
- **Global API Instance Caching**: 5-minute TTL cache eliminates repeated API initialization and disk I/O overhead.
- **Context Menu Instant Response**: Operations (Add/Remove My List, etc.) now near-instantaneous using cached API instances.
- **Live TV Performance**: Removed unnecessary 1-second sleep and per-channel fallback logic; reduced cancel delay significantly.
- **Channel Optimization**: Skips unsupported `/v9/content/detail` requests for channels, eliminating 404 errors.

**UI/UX & Media:**
- **Smart Artwork by Aspect Ratio**: Automatically separates landscape (16:9) for fanart and portrait (2:3) for covers, preventing face-cutting.
- **High-Resolution Fanart**: Image URLs request 3840px from NLZiet service, rendering crisp 4K artwork instead of pixelated images.
- **Fanart Support**: Added addon fanart metadata for skin integration; renders `resources/media/background.jpg` seamlessly.
- **Live TV Context Menu Fix**: Prevented "Resume from" and "Play from beginning" options on live channels; streams play directly via properties.

**DRM & Dependencies:**
- **InputStream Helper Integration**: Uses `script.module.inputstreamhelper` v0.6.0 for automatic DRM dependency verification.
- **Widevine Support**: Ensures `inputstream.adaptive` v2.6.18+ and Widevine CDM are installed before DRM playback.

**Bug Fixes:**
- Fixed undefined variable references in series detail fallback logic (#8).
- Fixed missing settings labels with converted settings structure (v1 format).
- Fixed inconsistent language rendering in settings UI.
- Fixed image aspect ratio assignment preventing landscape/portrait confusion.
- Fixed pixelated fanart by requesting optimal resolution.

### New in v0.0.8

- **Full Localization**: Complete Dutch and English UI with 47 translation entries. Users can toggle language in settings (Dutch by default).
- **Language Change Detection**: Addon notifies users when language setting changes, with instructions to restart addon to apply.
- **TV Show Broadcast Dates**: Episodes now display broadcast/aired dates in both Dutch ("Uitgezonden") and English ("Aired").
- **Enhanced TV Shows Browsing**: Reorganized TV shows with 18 genre categories (Sports, News, Drama, Comedy, Documentary, etc.).
- **TV Shows Endpoint Optimization**: Switched from `recommendVideos` to `allPopularPrograms` for full content access (overcomes ~40 item limit).
- **Subtitle Control**: Default subtitle setting now properly enforced for DRM and non-DRM streams with robust boolean parsing.
- **Movie Playability Fix**: Movies in genre browsing now correctly marked as playable items.
- **Episode Details**: Episodes without descriptions now properly display available metadata (broadcast date, expiry info).
- **Settings Documentation**: Bilingual help text added explaining language change requirements.
- **Advanced Debug Logging**: Enhanced logging for live TV detection, subtitle handling, and language change detection.

### New in v0.0.7

- Persist cookie-based login across Kodi restarts so the add-on recognizes logged-in sessions.
- Bumped addon version to `0.0.7` and added release package.

### New in v0.0.6

- **TV Shows**: Added a dedicated "TV Shows" main-menu entry using the recommend API (recommend/withContext) to surface episodic video content.
- **Documentary**: New "Documentary" main-menu entry using the filtered recommend endpoint (category=Programs, genre=Documentary).
- **Account integration**: Settings > Account shows **Subscription**, **Subscription expires**, and **Max devices** (read-only) populated from the customer summary API when authenticated.
- **Logout & reset**: Settings > Account includes a `Logout` action that clears cookies, tokens, profile selection and the local My List (confirmation required).
- **Silent account refresh**: Account info is refreshed silently on addon launch and after login/profile changes.
- **Protected menu items**: Manage profiles, Search, My List, Series, Movies and Channels are shown only when authenticated to avoid errors for anonymous users.
- **Profiles UI**: Profiles were moved to a dedicated Settings > Profiles section and are non-editable from Settings (use Manage profiles in the addon's main menu).
- **PKCE token fallback**: Improved token/cookie handling with a PKCE authorize+exchange fallback to obtain tokens from an existing cookie session.

---


---

## 🖼️ Screenshots

Coming soon...
<p align="center">
  <img src="docs/screenshot_main.png" width="400" alt="Main Menu"/>
  <img src="docs/screenshot_series.png" width="400" alt="Series View"/>
</p>

---

## 🚀 Installation

1. Download the latest release from [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).
2. In Kodi, go to **Add-ons > Install from zip file** and select the downloaded zip.
3. Configure your NLZiet credentials in the add-on settings.
4. (Optional) Install `inputstream.adaptive` for DRM playback. The addon will verify installation automatically via `inputstreamhelper`.

### Local Addon Check (Filtered Source)

To run addon-check locally without scanning local environment/cache folders, use:

```bash
scripts/run-addon-check-local.sh
```

Run a specific branch only:

```bash
scripts/run-addon-check-local.sh --branch omega
```

---

## 🛣️ Roadmap / Coming Soon

- **Kids Profile Support**: Full kids mode and parental controls.
- **Improved Search**: Filter by genre, year, release date, and more.
- **Playback History**: Track watched episodes and movies.
- **Advanced Sorting**: Sort series by newest, oldest, alphabetical, popularity.
- **UI Polish**: Enhanced skins integration, custom info dialogs, and animations.
- **Automated Testing**: CI/CD pipeline for code quality and automated releases.

---

## 📝 To-Do

- [X] **Fix issue where only 50 movies/series are shown** (pagination/limit handling)
- [X] **Episodes use episode title instead of count** (show SxxExx or Afl. N when possible)
- [X] **Fix subfolders in series option** (better season/episode navigation)
- [ ] **Improve error messages and user feedback**
- [ ] **Add Dutch/English language toggle**
- [ ] **Better artwork and fanart for all content**
- [X] **Settings: allow custom API endpoint for advanced users**
- [ ] **Add more debug and diagnostic tools**
- [ ] **Accessibility improvements for screen readers**
- [ ] **Add more unit/integration tests**

---

## 🤝 Contributing

Pull requests, bug reports, and feature suggestions are welcome. Open an issue or pull request in this repository.

---

## 📄 License

MIT. See [LICENSE](LICENSE).

---

## ⚠️ Disclaimer

This project is not affiliated with or endorsed by NLZiet. Use at your own risk. For personal, non-commercial use only.
