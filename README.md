<div align="center">

<img src="https://raw.githubusercontent.com/Nigel1992/NLZiet-Kodi-Addon/master/icon.png" width="300" alt="NLZiet Kodi Addon Logo"/>

# <span style="color:#E60000;">NLZiet Kodi Addon</span>

[![GitHub stars](https://img.shields.io/github/stars/Nigel1992/NLZiet-Kodi-Addon?style=social)](https://github.com/Nigel1992/NLZiet-Kodi-Addon)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Latest release:** v0.0.8 — 2026-04-02. See the [Changelog](CHANGELOG.md) or [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).

<sub><sup>Unofficial NLZiet Kodi Addon &mdash; Watch live TV, series, movies, and more from NLZiet directly in Kodi. Supports profiles, DRM, and a modern UI.</sup></sub>

</div>

---

> ⚠️ **Warning:** This add-on is under constant development. Some features may be broken or incomplete. Please see the To-Do section below for known issues and planned improvements. Use at your own risk and check back for frequent updates!

---

## ✨ Features

- <span style="color:#E60000;">**Live TV**</span>: Stream all supported NLZiet channels with EPG info.
- <span style="color:#007ACC;">**Series**</span>: Browse, search, and play series with full season/episode navigation.
- <span style="color:#F39C12;">**Movies**</span>: Discover and watch movies from the NLZiet catalog.
- <span style="color:#27AE60;">**Profile Management**</span>: Switch between user profiles from the Kodi UI.
- <span style="color:#8E44AD;">**DRM Support**</span>: Widevine-protected streams via `inputstream.adaptive`.
- <span style="color:#2980B9;">**Placement Rows**</span>: Home screen rows mirror the official NLZiet app (e.g., "Recommended", "Popular Series").
- <span style="color:#C0392B;">**Episode Numbering**</span>: Accurate SxxExx and Dutch soap (Afl. N) parsing, with season mapping.
- <span style="color:#16A085;">**Search**</span>: Find series, movies, and episodes by title.
- <span style="color:#34495E;">**Robust Handshake**</span>: Automatic manifest/license extraction and fallback logic.
- <span style="color:#E67E22;">**Debug Logging**</span>: Easy log collection for troubleshooting.

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

----

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
4. (Optional) Install `inputstream.adaptive` for DRM playback.

---

## 🛣️ Roadmap / Coming Soon

- **My List**: Add/remove favorites and resume playback.
- **Kids Profile Support**: Full kids mode and parental controls.
- **Improved Search**: Filter by genre, year, and more.
- **Offline Viewing**: Download for offline playback (if supported).
- **Multi-language Subtitles**: Enhanced subtitle selection and download.
- **UI Polish**: More artwork, skin integration, and info dialogs.
- **Automated Testing**: CI for code quality and releases.

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

Pull requests, bug reports, and feature suggestions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📄 License

MIT. See [LICENSE](LICENSE).

---

## ⚠️ Disclaimer

This project is not affiliated with or endorsed by NLZiet. Use at your own risk. For personal, non-commercial use only.
