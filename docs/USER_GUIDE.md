# NLZiet Kodi Addon — User Guide

> Plain language. Everything you need to use the add-on.

**Version:** 2.0.0 · [Changelog](../CHANGELOG.md) · [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases)

---

## 📥 Installation

### Option A — via the Kodi repository (recommended, auto-updates)

**Using a URL (no manual download):**

1. In Kodi: **Settings → File manager → Add source** → enter `https://nigel1992.github.io/kodi-repository/` → name it (e.g. "Nigel1992") → OK.
2. **Add-ons → Install from zip file** → select the source → `repository.nigel1992-*.zip`.
3. **Add-ons → Install from repository → Nigel1992 Kodi Repository → Video add-ons → NLZiet → Install**.
4. Kodi keeps the add-on updated automatically.

**Or download the repo zip directly** from the [Kodi repository releases](https://github.com/Nigel1992/kodi-repository/releases/latest) and install via **Add-ons → Install from zip file** (enable "Unknown sources" first if prompted).

### Option B — manual zip (no auto-updates)

1. Download the latest release zip from [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).
2. In Kodi: **Add-ons → Install from zip file** → select the zip.

### After installing (both options)

3. Open the add-on and log in with your NLZiet account (button **Inloggen** / Login).
4. Install `inputstream.adaptive` (for DRM playback) — the add-on checks this automatically.
5. (Optional) Install and authorize the official Kodi **Trakt** add-on for scrobbling.

After startup the add-on configures itself: library folders, content type, scan. You don't need to set anything up manually.

---

## 📺 Live TV

- Open the add-on → **Live TV** (or **TV Gids**).
- All channels with current and upcoming programmes (7 days ahead).
- Click a programme to watch. Playback uses `inputstream.adaptive` (DRM).
- **EPG reminder**: set a reminder in the TV Guide for a future programme; you get a notification shortly before it starts.
- **Favourite channels**: mark channels as favourites; they appear first.

## 📺 Series

- **Browse**: open **Series** → pick a category or genre.
- **Search**: type a title; results can be filtered by period and genre.
- **Play an episode**: click it. The add-on remembers where you left off.
- **Continue watching**: a "Verder kijken" widget on the home screen.
- **Mark a whole series as watched**: context menu → "Mark whole series as watched".

## 🎬 Movies

- **Browse**: open **Movies** → pick a category or genre.
- **Search**: type a title.
- **Play**: click a movie. Resume position is remembered.

## ⏸️ Playback — extra features

- **Up Next / Next episode**: at the end of an episode you can auto-start or use a button to play the next one (setting: Up Next / built-in prompt / automatic / off).
- **Skip intro/recap**: based on chapters (when NLZiet provides them) a "Skip" button appears.
- **Binge mode**: automatically plays the next episode.
- **Stop after this episode**: sets a flag so playback stops afterwards.
- **Shuffle**: random episode from a series.
- **Fixed language/subtitles**: set your preference; applied automatically. Optionally opens Kodi's subtitle search if the stream has none.
- **Resume (continue watching)**: position saved locally and synced with NLZiet (so you can continue on phone/tablet).

## 📋 Lists

### Watch Later (Kijk Later)
- Episodes and movies you want to keep.
- Add: context menu → "Add to Watch Later".
- Syncs two-way with your NLZiet account (Settings → Synchronization).
- Widget on the home screen.

### My Series (Mijn Series)
- Follow whole series. Each series shows whether new episodes are available.
- Add: context menu → "Add to My Series".
- Syncs with your NLZiet account.

### My List (Mijn Lijst)
- Removed in v2.0.0; existing items were migrated to **Watch Later**.

## 📚 Kodi library (automatic)

The add-on writes series and movies as `.strm` + `.nfo` into a folder in your Kodi profile. From v2.0.0 this happens **fully automatically**:

- **Sources**: the folders are registered as Kodi video sources automatically (sources.xml + content type + "Local information only" scraper).
- **Scan**: Kodi scans the folders automatically; series appear under **Videos → Series**, movies under **Videos → Movies**.
- **Updates**: new episodes added automatically, expired ones removed (default every 12 hours).
- **Metadata**: missing details (description, artwork, genres, titles) filled in via TMDb (free API key, optional) and TVmaze. NLZiet's own data always comes first.
- **Season posters and logos** (clearlogo) also shown in browse lists.

### Add manually
- Context menu on a series/movie → "Add to library".

### Bulk action
- Settings → Library → "Add My Series and Watch Later to the library now" (or automatically via the setting "Keep My Series and Watch Later in the library automatically").

### Import Trakt watchlist
- Settings → Library → "Import Trakt watchlist": matches titles on NLZiet and adds them.

## 🔒 Parental control

- Set a PIN per profile (Settings → Parental control).
- Choose which profiles are locked.
- Optionally: PIN for live TV.
- Kids profiles are marked.

## 📊 Trakt integration

- **Watched status in menus**: see whether a title is marked watched on Trakt.
- **Live scrobbling**: playback progress sent to Trakt while watching.
- **Watchlist import**: import your Trakt watchlist into the library.
- Requires the official Kodi `script.trakt` add-on (installed and authorized).

## 💾 Backup and restore

- Settings → Library → Maintenance → Backup/Restore: save your lists and settings, restore them later.

## 🔍 Search

- Search by title (series, movies, episodes).
- Filter results by period and genre.
- "Search in Videoland" entry on search results.

## 🩺 Diagnostics and reliability

- **Diagnostics screen**: Settings → Library → Maintenance → "Run diagnostics".
  - Shows login status, InputStream/Widevine, connections, TMDb key, library sources, Kodi-vs-library counts.
  - Save a privacy-friendly report.
- **Daily background check**: notification on problems.
- **Clear error messages**: offline, timeout, session expired, no subscription, not found, busy, outage — one clear sentence, details in the log.
- **Accessibility**: text instead of emoji/colour-only markers, status words in diagnostics.

## ⚙️ Important settings

| Setting | Where | Explanation |
|---|---|---|
| Send watched status to NLZiet | Playback | Sends watched status back to NLZiet |
| Watched percentage | Playback | When a video counts as "watched" |
| Next episode | Playback | Up Next / built-in prompt / automatic / off |
| Binge mode | Playback | Automatically play next episode |
| Fixed language/subtitles | Playback | Preference for spoken language and subtitles |
| Keep My Series and Watch Later in the library automatically | Library | Auto-add (default on) |
| Remove titles that left these lists | Library | Clean up on changes |
| Library auto-update | Library | Interval in hours |
| TMDb API key | Library → Metadata | Free key for extra metadata/artwork |
| Parental control | Parental control | PIN/profile lock |
| Backup/Restore | Library → Maintenance | Save/restore lists and settings |
| Notification on background sync | Synchronization | Only when something changed |

## 🐛 Problems?

- **Diagnostics report**: Settings → Library → Maintenance → Run diagnostics → Save report.
- **Issues**: https://github.com/Nigel1992/NLZiet-Kodi-Addon/issues
- **Discord**: https://discord.gg/9F2NZuydXT

## 📄 License

MIT. See [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

- **[@djdirty](https://github.com/djdirty60) (Wilfried)** — author of pull request #48, which brought the Kodi library, playback extras, widgets, diagnostics, parental controls, Trakt integration, backup/restore and many other features, plus Dutch/English translations and ~299 unit tests. Huge thanks! 🙏
- Icons: [Lucide](https://lucide.dev)

## ⚠️ Disclaimer

This project is not affiliated with or endorsed by NLZiet. Use at your own risk. For personal, non-commercial use only.