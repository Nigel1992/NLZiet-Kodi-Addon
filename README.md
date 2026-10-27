<p align="center">
  <a href="https://discord.gg/UbPRh74PzV">
    <img alt="Join our Discord" src="https://img.shields.io/badge/Join%20our%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" />
  </a>
</p>


<div align="center">

<img src="https://raw.githubusercontent.com/Nigel1992/NLZiet-Kodi-Addon/master/icon.png" width="300" alt="NLZiet Kodi Addon Logo"/>

# NLZiet Kodi Addon

[![GitHub stars](https://img.shields.io/github/stars/Nigel1992/NLZiet-Kodi-Addon?style=social)](https://github.com/Nigel1992/NLZiet-Kodi-Addon)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Latest release:** v1.4.3 — 2026-10-28. See the [Changelog](CHANGELOG.md) or [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).

<sub>Unofficial NLZiet Kodi Addon - Watch live TV, series, movies, and more from NLZiet directly in Kodi. Supports profiles, DRM, and a modern UI.</sub>

</div>

---

> ⚠️ **Warning:** This add-on is under constant development. Some features may be broken or incomplete. Please see the To-Do section below for known issues and planned improvements. Use at your own risk and check back for frequent updates!

---

## ✨ Features

- **Live TV**: Stream all supported NLZiet channels with EPG info.
- **Series**: Browse, search, and play series with full season/episode navigation.
- **Movies**: Discover and watch movies from the NLZiet catalog.
- **Saved lists**: Add **any** content (Series, TV Shows, Documentaires, Films, Kanalen, episodes) to **My List** via the item context menu; My List groups items into a subsection per category and is stored **locally on this device only (Kodi only)**. **Kijk Later** (Watch Later) holds episodes and movies, while **Mijn Series** (My Series) follows whole series — each item shows the matching action in its context menu. Both Kijk Later and My Series can optionally **synchronise both ways with your NLZiet account** (Settings → Synchronization) through the cloud watchlist and tracked-series list respectively, including manual **Sync Watch Later now** / **Sync My Series now** actions.
- **Profile Management**: Switch between user profiles from the Kodi UI.
- **Localization**: All user-facing text resolves through Kodi's language system (Dutch and English included); English is the fallback for languages without a translation file.
- **DRM Support**: Widevine-protected streams via `inputstream.adaptive` with automatic `inputstreamhelper` verification.
- **Placement Rows**: Home screen rows mirror the official NLZiet app (e.g., "Recommended", "Popular Series").
- **Episode Numbering**: Accurate SxxExx and Dutch soap (Afl. N) parsing, with season mapping. **Kijk Later** additionally shows the episode number and the remaining availability as compact, subtly coloured lines in the item description.
- **Search**: Find series, movies, and episodes by title.
- **Trakt Scrobbling**: Movies and episodes expose playback metadata to the official Kodi `script.trakt` add-on, with movie title/year resolution, named-episode matching, cached-URL recovery, and explicit live-TV exclusion. The Trakt add-on must be installed and authorized separately.
- **Robust Handshake**: Automatic manifest/license extraction and fallback logic.
- **Clean subtitles**: NPO's teletext-derived subtitles are cleaned before playback, so Kodi shows its normal subtitle overlay instead of the teletext page number ("888") and yellow/white teletext colours.
- **Debug Logging**: Easy log collection for troubleshooting.
---

### New in v1.4.3

- **Kijk Later series folders**: when you add all episodes of a series to Kijk Later (or have two or more episodes of the same series), they appear in a folder with season subfolders. Episodes are ordered by season and episode number (via NLZiet codes or TVmaze), and labels show "Aflevering X: ..." for easier browsing.
- **Add all episodes to Watch Later**: right-click a series or episode to queue every episode of that series into Kijk Later as one collection.
- **Auto-add new episodes**: optionally add new episodes for series in Mijn Series and episodes already in Kijk Later. The first time you enable it, only new episodes added after that will be queued.
- **Expiry notifications**: get notified when items in Kijk Later or Mijn Series are about to expire, with a configurable time window and per-list toggles (Settings → Meldingen).
- **TVmaze integration**: missing season/episode numbers are resolved via TVmaze so ordering and labels work for series where NLZiet omits them (e.g. Blue Murder Motel).
- **Improved Kijk Later ordering**: episodes of the same series are grouped and sorted by broadcast time, and episode subtitles are shown even for items added in bulk.

### New in v1.4.2

- **Episode info in Kijk Later**: each item now shows its episode numbering ("Afl. 3 van 12") and how long it stays available ("nog 5 dagen beschikbaar") as two subtly coloured lines at the top of its description, in both the info dialog and the outline. Numbering is resolved from the season catalogue (fetched once per series/season) and falls back to the episode subtitle when no catalogue data is available.
- **Fixed**: saved lists showed the **broadcaster logo** instead of the real poster. The raw NLZiet payload for Kijk Later / My List items only carries the channel logo, which the artwork picker preferred over the actual artwork; real posters and stills now always win, and broadcaster logos are only used as a last resort (such as the channel list).
- **Fixed**: **NPO teletext subtitles** are cleaned up. NPO publishes teletext-derived WebVTT files that start with the teletext page number ("888") and colour the dialogue yellow/white, which Kodi rendered literally. External NPO subtitles are now stripped of the page-number cue, the service banner and the teletext colour tags (and cached locally) before playback, so Kodi shows its normal subtitle overlay. RTL and SBS subtitles are untouched.
- **Fixed**: the availability line used an invalid colour value and was rendered without colour; it now uses a warm amber that stands out subtly.

### New in v1.4.1

- **Fixed**: cloud-synced lists were capped at 10 items. The NLZiet watchlist endpoints (`/v9/watchlist` and `/v9/trackedseries`) only return the first 10 entries unless a `limit` is sent, so **Kijk Later** and **Mijn Series** synced at most 10 items. The addon now requests pages of 500 and follows `offset` until the list is complete, so all items sync both ways.

### New in v1.4.0

- **Two-way list sync**: **Kijk Later** and the new **Mijn Series** list now sync both ways with your NLZiet account. Episodes and movies sync through the cloud watchlist, followed series sync through the tracked-series list. Enable it under **Settings → Synchronization → Sync Watch Later and My Series with NLZiet**; manual buttons **Sync Watch Later now** and **Sync My Series now** are available too. A three-way merge ("additions win") prevents concurrent changes from being lost.
- **Mijn Series (My Series)**: a new main-menu entry and local list that follows whole series; a series saved here reopens its detail page.
- **Per-type context menu**: each item shows the action that fits its type — **Add to Watch Later** for episodes and movies, **Add to My Series** for series, **Add to My List** for everything.
- **My List is local (Kodi only)**: all My List labels (menu, add/remove actions, notifications, empty message, logout prompt) now state in both Dutch and English that My List is stored on this device only. Kijk Later and Mijn Series are the cloud-synced lists.
- **Fixed**: followed series are no longer silently dropped during cloud sync — because the NLZiet watchlist API accepts but discards series ids, series are now routed to `/v9/trackedseries` so they appear in the NLZiet app.

### New in v1.3.0

- **My List subsections**: My List now groups entries into a subsection per category (Series, TV Shows, Documentaires, Films, Kanalen) instead of a single generic list.
- **Any content type in My List**: TV Shows, Documentaires, Kanalen and individual episodes can now be saved to My List too, matching Kijk Later.
- **Full localization**: every user-facing string — notifications, dialogs, the search prompt, grouped My List / search folder labels and count labels — now resolves through Kodi's translation system, so a Dutch Kodi shows the whole add-on in Dutch (English is the fallback).
- **Fixed**: live channels saved to My List / Kijk Later now play correctly by opening them with the live stream context.

### New in v1.2.0

- Added a local **Kijk Later** (Watch Later) queue with its own main-menu entry; any content can be added via the context menu.
- Added a dedicated menu icon for the Kijk Later queue.
- Saved list entries now keep the full content metadata (title, description/plot and artwork) so My List / Watch Later render rich items.
- Runtime UI strings now use Kodi's translation system (`strings.po`); any language with a translation file works and English is the fallback for languages without one.
- Fixed the series-detail context menu so My List and "Add to library" both appear (previously the library action overwrote the My List action).

### New in v1.1.0

- Added privacy-safe diagnostics export under Settings → Debugging.
- Added Kodi watched/resume indicators when viewing-progress data is available.
- Added Dutch/English runtime localization based on Kodi's configured language.
- Masked password input and added network timeouts.
- Removed the unused background service.

### New in v1.0.3

- Added verified scrobbling for NLZiet movies and TV episodes through the official Kodi `script.trakt` add-on.
- Added playback-time Trakt metadata recovery when NLZiet omits a movie release year or a cached Kodi URL lacks episode details.
- Added canonical Trakt matching for named episodes when NLZiet and Trakt use different season/episode orders.
- Preserved series, season, episode, and title metadata in exported `.strm` library entries.
- Prevented broadcast/availability dates from being used as production years.
- Excluded live channels from Trakt scrobbling.

> **Episode-title limitation:** Some broadcasters provide only a generic label such as `Afl. 61`. If that broadcaster's season order differs from Trakt and no original episode title is supplied, the episode cannot be matched safely.

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
- **Protected menu items**: Manage profiles, Search, My List, Kijk Later, Series, Movies and Channels are shown only when authenticated to avoid errors for anonymous users.
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
3. Open the add-on and use **Inloggen** to authenticate with NLZiet.
4. Install and authorize the official Kodi **Trakt** add-on if you want movie and episode scrobbling.
5. Install `inputstream.adaptive` for DRM playback. The addon verifies it automatically through `inputstreamhelper`.

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
- **Playback History UI**: Show Trakt-backed watched status directly inside NLZiet menus.
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
- [X] **Add unit tests for routing, playback metadata, and Trakt scrobbling**

## 💖 Support the Project

All donations go towards your chosen charity. You can pick any charity you'd like, and 5% is retained due to Ko-Fi fees. As a thank you, your name will be listed as a supporter/donor in a GitHub project. Feel free to email me at thedjskywalker@gmail.com for proof! :)

[![Ko-Fi](https://img.shields.io/badge/Ko--Fi-Support%20me-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/nigel1992)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?hosted_button_id=KYV9ARF99ZSCE)

---

## 🤝 Contributing

Pull requests, bug reports, and feature suggestions are welcome. Open an issue or pull request in this repository.

---

## 📄 License

MIT. See [LICENSE](LICENSE).

---

## ⚠️ Disclaimer

This project is not affiliated with or endorsed by NLZiet. Use at your own risk. For personal, non-commercial use only.