[![Discord](https://img.shields.io/discord/1468295714961494029?color=7289da&label=Join%20Our%20Discord&logo=discord&logoColor=white&style=for-the-badge)](https://discord.gg/UbPRh74PzV)


<div align="center">

<img src="https://raw.githubusercontent.com/Nigel1992/NLZiet-Kodi-Addon/master/icon.png" width="300" alt="NLZiet Kodi Addon Logo"/>

# NLZiet Kodi Addon

[![Vibe Coded](https://img.shields.io/badge/Vibe_Coded-✨-8A2BE2?style=for-the-badge)](https://github.com)

[![GitHub stars](https://img.shields.io/github/stars/Nigel1992/NLZiet-Kodi-Addon?style=social)](https://github.com/Nigel1992/NLZiet-Kodi-Addon)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Latest release:** v1.6.1 — 2026-11-08. See the [Changelog](CHANGELOG.md) or [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).

<sub>Unofficial NLZiet Kodi Addon - Watch live TV, series, movies, and more from NLZiet directly in Kodi. Supports profiles, DRM, and a modern UI.</sub>

</div>

---

> ⚠️ **Warning:** This add-on is under constant development. Some features may be broken or incomplete. Please see the To-Do section below for known issues and planned improvements. Use at your own risk and check back for frequent updates!

---

<details open>
<summary><b>English</b></summary>


## ✨ Features

- **Live TV**: Stream all supported NLZiet channels with EPG info. Includes a custom full-screen EPG (TV Gids) with channel names, current programme indicator, and 7-day browse.
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
- **Search history**: recent searches can be reused or selectively removed.
- **New episode tracking**: My Series highlights series with new episodes, and Kijk Later can follow only episodes released from now on.
- **Responsive navigation**: background sync and maintenance work does not block menu transitions or returning from playback.
- **Debug Logging**: Easy log collection for troubleshooting.
---

### New in v1.6.0

- **TV Gids timeline**: the EPG is a timeline grid with channels down the left and programme blocks across the screen. Past programmes are grey, live programmes blue, and future programmes green. A white line shows the current time.
- **Programme description**: the selected programme's description is shown at the bottom and scrolls automatically.
- **Faster opening and day switching**: the EPG opens immediately from cached data; picking a day refreshes it.
- **Return to position**: after playback started from the EPG stops, the EPG reopens where you were.
- **Clear all cache**: a settings button clears all addon caches, with optional automatic clearing.

### New in v1.5.0

- **Custom EPG**: full-screen EPG dialog with channels on the left and horizontally scrolling programmes on the right. Shows channel names, current programme (● NU), and date/time per programme. Browse today + 7 days back/forward via a day selector (press I / Info).
- **Live TV restart/replay**: "Afspelen (terugkijken)" on live programmes now starts from the beginning instead of jumping to realtime.
- **Context menu**: long-press Enter on any programme for Play / Add to My Series / Add to Watch Later.
- **Auto subtitle cache clearing**: optional periodic clearing of the subtitle cache (configurable hours).
- **Menu icons**: refreshed premium icon set.
- **Live TV resume prompt**: live streams no longer offer "Resume from …"; always start at the live edge.
- **EPG day filtering**: selecting a day now correctly filters programmes to that day.
- **EPG channel highlight**: selected channel stays highlighted while browsing programmes.
- **Subtitle cache settings**: spinner now has min/max/step so a duration can be selected.

### New in v1.4.4.1 (hotfix)

- **Faster Mijn Series loading**: detecting newly added episodes no longer blocks the list from rendering; the check (and any highlight/refresh) now runs in the background.

### New in v1.4.4

- **Search history**: recent searches are saved locally, can be reused, and can be selectively deleted.
- **My Series new-episode indicator**: series with episodes that appeared since the previous check are shown with a green title.
- **Series add mode**: choose between adding all existing episodes to Kijk Later or following only new episodes from now on. The current episodes become the baseline and are not added.
- **Subtitle cache management**: clear cleaned subtitle files from Settings → Debugging.
- **Faster navigation**: backfill, list synchronization, automatic episode checks, expiry checks and token checks no longer unnecessarily block menu transitions or returning from playback.

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

</details>

<details>
<summary><b>Nederlands</b></summary>


## ✨ Functies

- **Live TV**: Stream alle ondersteunde NLZiet-zenders met EPG-info. Bevat een aangepaste volledig-scherm EPG (TV Gids) met zendernamen, huidige-programma-indicator en 7 dagen bladeren.
- **Series**: Blader, zoek en speel series af met volledige seizoen/aflevering-navigatie.
- **Films**: Ontdek en kijk films uit de NLZiet-catalogus.
- **Opgeslagen lijsten**: Voeg **elke** content (Series, TV Shows, Documentaires, Films, Kanalen, afleveringen) toe aan **Mijn Lijst** via het contextmenu; Mijn Lijst groepeert items per categorie en wordt **alleen lokaal op dit apparaat opgeslagen (alleen Kodi)**. **Kijk Later** (Watch Later) bevat afleveringen en films, terwijl **Mijn Series** (My Series) hele series volgt — elk item toont de bijpassende actie in het contextmenu. Zowel Kijk Later als Mijn Series kunnen optioneel **tweerichtings synchroniseren met je NLZiet-account** (Instellingen → Synchronisatie) via de cloud-watchlist en tracked-series-lijst, inclusief handmatige acties **Sync Watch Later now** / **Sync My Series now**.
- **Profielbeheer**: Schakel tussen gebruikersprofielen vanuit de Kodi-UI.
- **Lokalisatie**: Alle gebruikerstekst wordt opgelost via Kodi's taalsysteem (Nederlands en Engels inbegrepen); Engels is de fallback voor talen zonder vertaalbestand.
- **DRM-ondersteuning**: Widevine-beschermde streams via `inputstream.adaptive` met automatische `inputstreamhelper`-verificatie.
- **Placement Rows**: Home-schermrijen spiegelen de officiële NLZiet-app (bijv. "Aanbevolen", "Populaire series").
- **Afleveringsnummering**: Nauwkeurige SxxExx- en Nederlandse soap (Afl. N)-parsing, met seizoensmapping. **Kijk Later** toont daarnaast het afleveringsnummer en de resterende beschikbaarheid als compacte, subtiel gekleurde regels in de itembeschrijving.
- **Zoeken**: Vind series, films en afleveringen op titel.
- **Trakt Scrobbling**: Films en afleveringen tonen afspeelmetadata aan de officiële Kodi `script.trakt`-add-on, met film titel/jaar-resolutie, benoemde-aflevering-matching, herstel van gecachte URL's en expliciete live-TV-uitsluiting. De Trakt-add-on moet apart worden geïnstalleerd en geautoriseerd.
- **Robuuste Handshake**: Automatische manifest/license-extractie en fallback-logica.
- **Schone ondertitels**: NPO's teletekst-afgeleide ondertitels worden vóór afspelen opgeschoond, zodat Kodi zijn normale ondertiteloverlay toont in plaats van het teletekst-paginanummer ("888") en gele/witte teletekstkleuren.
- **Zoekgeschiedenis**: recente zoekopdrachten kunnen worden hergebruikt of selectief verwijderd.
- **Nieuwe-aflevering-tracking**: Mijn Series markeert series met nieuwe afleveringen, en Kijk Later kan alleen afleveringen volgen die vanaf nu worden uitgezonden.
- **Responsieve navigatie**: achtergrond-sync en onderhoud blokkeert geen menunavigatie of terugkeer vanaf afspelen.
- **Debug Logging**: Eenvoudige logverzameling voor probleemoplossing.
---

### Nieuw in v1.6.1

- **Live TV OSD**: de OSD toont nu de titel en beschrijving van het huidige programma in plaats van alleen de zendernaam.
- **Opgeslagen lijsten OSD**: items afgespeeld vanuit Kijk Later / Mijn Lijst tonen hun titel, beschrijving en artwork op de OSD.
- **Mijn Series vanuit EPG**: EPG-programma's (bijv. Pawn Stars) kunnen nu worden toegevoegd aan Mijn Series.
- **Kijk Later vanuit EPG**: alleen programma's die later terug te kijken zijn worden geaccepteerd; toekomstige programma's worden toegevoegd met een duidelijke melding over wanneer ze afgespeeld kunnen worden.
- **Kijk Later-menu**: opgeslagen beschrijvingen komen nu door op de OSD.

### Nieuw in v1.6.0

- **TV Gids-tijdlijn**: de EPG is een tijdlijnrooster met zenders links en programmblokken over het scherm. Afgelopen programma's zijn grijs, live-programma's blauw en toekomstige programma's groen. Een witte lijn toont de huidige tijd.
- **Programmabeschrijving**: de beschrijving van het geselecteerde programma wordt onderaan getoond en scrolt automatisch.
- **Sneller openen en dagwisselen**: de EPG opent direct vanuit gecachte data; het kiezen van een dag ververst deze.
- **Terug naar positie**: nadat afspelen gestart vanuit de EPG stopt, heropent de EPG op dezelfde plek.
- **Alle cache wissen**: een instellingenknop wist alle add-on-caches, met optioneel automatisch wissen.

### Nieuw in v1.5.0

- **Aangepaste EPG**: volledig-scherm EPG-dialoog met zenders links en horizontaal scrollende programma's rechts. Toont zendernamen, huidige programma (● NU) en datum/tijd per programma. Blader vandaag + 7 dagen terug/vooruit via een dagkiezer (druk op I / Info).
- **Live TV herstart/replay**: "Afspelen (terugkijken)" bij live-programma's begint nu vanaf het begin in plaats van naar realtime te springen.
- **Contextmenu**: lang indrukken op Enter bij elk programma voor Afspelen / Toevoegen aan Mijn Series / Toevoegen aan Kijk Later.
- **Automatisch ondertitelcache wissen**: optioneel periodiek wissen van de ondertitelcache (configureerbare uren).
- **Menu-iconen**: vernieuwde premium iconenset.
- **Live TV hervatprompt**: live-streams bieden niet langer "Hervatten van …"; starten altijd aan de live-rand.
- **EPG-dagfiltering**: het kiezen van een dag filtert nu correct programma's naar die dag.
- **EPG-zenderhighlight**: geselecteerde zender blijft gemarkeerd tijdens het bladeren door programma's.
- **Ondertitelcache-instellingen**: spinner heeft nu min/max/stap zodat een duur kan worden gekozen.

### Nieuw in v1.4.4.1 (hotfix)

- **Sneller Mijn Series laden**: detecteren van nieuw toegevoegde afleveringen blokkeert het renderen van de lijst niet langer; de controle (en eventuele highlight/refresh) draait nu op de achtergrond.

### Nieuw in v1.4.4

- **Zoekgeschiedenis**: recente zoekopdrachten worden lokaal opgeslagen, kunnen worden hergebruikt en selectief worden verwijderd.
- **Mijn Series nieuwe-aflevering-indicator**: series met afleveringen die sinds de vorige controle zijn verschenen worden met een groene titel getoond.
- **Series-add-modus**: kies tussen het toevoegen van alle bestaande afleveringen aan Kijk Later of het volgen van alleen nieuwe afleveringen vanaf nu. De huidige afleveringen worden de basislijn en worden niet toegevoegd.
- **Ondertitelcache-beheer**: wis opgeschoonde ondertitelbestanden via Instellingen → Debugging.
- **Snellere navigatie**: backfill, lijstsynchronisatie, automatische afleveringscontroles, vervaldatumcontroles en tokencontroles blokkeren menunavigatie of terugkeer vanaf afspelen niet langer onnodig.

### Nieuw in v1.4.3

- **Kijk Later-seriemappen**: wanneer je alle afleveringen van een serie toevoegt aan Kijk Later (of twee of meer afleveringen van dezelfde serie hebt), verschijnen ze in een map met seizoenssubmappen. Afleveringen worden gesorteerd op seizoen en afleveringsnummer (via NLZiet-codes of TVmaze), en labels tonen "Aflevering X: ..." voor eenvoudiger bladeren.
- **Alle afleveringen toevoegen aan Watch Later**: rechtsklik op een serie of aflevering om elke aflevering van die serie in Kijk Later als één collectie in de wachtrij te zetten.
- **Automatisch nieuwe afleveringen toevoegen**: optioneel nieuwe afleveringen toevoegen voor series in Mijn Series en afleveringen die al in Kijk Later staan. De eerste keer dat je het inschakelt, worden alleen nieuwe afleveringen die na dat moment worden toegevoegd in de wachtrij gezet.
- **Vervaldatummeldingen**: ontvang een melding wanneer items in Kijk Later of Mijn Series bijna verlopen, met een configureerbaar tijdvenster en per-lijst toggles (Instellingen → Meldingen).
- **TVmaze-integratie**: ontbrekende seizoen/afleveringsnummers worden via TVmaze opgelost, zodat sortering en labels werken voor series waar NLZiet ze weglaat (bijv. Blue Murder Motel).
- **Verbeterde Kijk Later-sortering**: afleveringen van dezelfde serie worden gegroepeerd en gesorteerd op uitzendtijd, en afleveringsubtitels worden getoond zelfs voor items die in bulk zijn toegevoegd.

### Nieuw in v1.4.2

- **Afleveringsinfo in Kijk Later**: elk item toont nu zijn afleveringsnummering ("Afl. 3 van 12") en hoe lang het nog beschikbaar is ("nog 5 dagen beschikbaar") als twee subtiel gekleurde regels bovenaan de beschrijving, zowel in de infodialog als in de outline. Nummering wordt opgelost vanuit de seizoenscatalogus (één keer per serie/seizoen opgehaald) en valt terug op de afleveringssubtitel als er geen catalogusdata is.
- **Opgelost**: opgeslagen lijsten toonden het **zenderlogo** in plaats van de echte poster. De ruwe NLZiet-payload voor Kijk Later / Mijn Lijst-items bevat alleen het zenderlogo, dat de artwork-picker prefereerde boven de echte artwork; echte posters en stills winnen nu altijd, en zenderlogo's worden alleen als laatste redmiddel gebruikt (zoals de zenderlijst).
- **Opgelost**: **NPO-teletekst-ondertitels** worden opgeschoond. NPO publiceert teletekst-afgeleide WebVTT-bestanden die beginnen met het teletekst-paginanummer ("888") en de dialogen geel/wit kleuren, wat Kodi letterlijk renderde. Externe NPO-ondertitels worden nu ontdaan van de paginanummer-cue, de servicebanner en de teletekst-kleurcodes (en lokaal gecacht) vóór afspelen, zodat Kodi zijn normale ondertiteloverlay toont. RTL- en SBS-ondertitels blijven onaangeroerd.
- **Opgelost**: de beschikbaarheidsregel gebruikte een ongeldige kleurwaarde en werd zonder kleur gerenderd; deze gebruikt nu een warm amber dat subtiel opvalt.

### Nieuw in v1.4.1

- **Opgelost**: cloud-gesynchroniseerde lijsten waren beperkt tot 10 items. De NLZiet-watchlist-endpoints (`/v9/watchlist` en `/v9/trackedseries`) retourneren alleen de eerste 10 entries tenzij een `limit` wordt meegegeven, waardoor **Kijk Later** en **Mijn Series** maximaal 10 items synchroniseerden. De add-on vraagt nu pagina's van 500 en volgt `offset` totdat de lijst compleet is, zodat alle items beide kanten op synchroniseren.

### Nieuw in v1.4.0

- **Tweerichtings-lijstsynchronisatie**: **Kijk Later** en de nieuwe **Mijn Series**-lijst synchroniseren nu beide kanten op met je NLZiet-account. Afleveringen en films synchroniseren via de cloud-watchlist, gevolgde series via de tracked-series-lijst. Schakel het in onder **Instellingen → Synchronisatie → Sync Watch Later and My Series with NLZiet**; handmatige knoppen **Sync Watch Later now** en **Sync My Series now** zijn ook beschikbaar. Een drieweg-merge ("toevoegingen winnen") voorkomt dat gelijktijdige wijzigingen verloren gaan.
- **Mijn Series (My Series)**: een nieuwe hoofdmenu-ingang en lokale lijst die hele series volgt; een opgeslagen serie heropent zijn detailpagina.
- **Per-type contextmenu**: elk item toont de actie die bij zijn type past — **Toevoegen aan Kijk Later** voor afleveringen en films, **Toevoegen aan Mijn Series** voor series, **Toevoegen aan Mijn Lijst** voor alles.
- **Mijn Lijst is lokaal (alleen Kodi)**: alle Mijn Lijst-labels (menu, toevoeg/verwijder-acties, meldingen, leeg-bericht, uitlogprompt) vermelden nu in zowel Nederlands als Engels dat Mijn Lijst alleen op dit apparaat wordt opgeslagen. Kijk Later en Mijn Series zijn de cloud-gesynchroniseerde lijsten.
- **Opgelost**: gevolgde series worden niet langer stilzwijgend weggegooid tijdens cloud-sync — omdat de NLZiet-watchlist-API series-ids accepteert maar negeert, worden series nu gerouteerd naar `/v9/trackedseries` zodat ze in de NLZiet-app verschijnen.

### Nieuw in v1.3.0

- **Mijn Lijst-subsecties**: Mijn Lijst groepeert entries nu in een subsectie per categorie (Series, TV Shows, Documentaires, Films, Kanalen) in plaats van één generieke lijst.
- **Elk contenttype in Mijn Lijst**: TV Shows, Documentaires, Kanalen en individuele afleveringen kunnen nu ook worden opgeslagen in Mijn Lijst, net als Kijk Later.
- **Volledige lokalisatie**: elke gebruikerstekst — meldingen, dialogen, de zoekprompt, gegroepeerde Mijn Lijst / zoekmaplabels en tellabels — wordt nu opgelost via Kodi's vertaalsysteem, zodat een Nederlandse Kodi de hele add-on in het Nederlands toont (Engels is de fallback).
- **Opgelost**: live-zenders opgeslagen in Mijn Lijst / Kijk Later spelen nu correct af door ze te openen met de live-streamcontext.

### Nieuw in v1.2.0

- Een lokale **Kijk Later** (Watch Later)-wachtrij toegevoegd met een eigen hoofdmenu-ingang; elke content kan via het contextmenu worden toegevoegd.
- Een speciaal menu-icoon voor de Kijk Later-wachtrij toegevoegd.
- Opgeslagen lijstitems bewaren nu de volledige contentmetadata (titel, beschrijving/plot en artwork) zodat Mijn Lijst / Kijk Later rijke items renderen.
- Runtime-UI-strings gebruiken nu Kodi's vertaalsysteem (`strings.po`); elke taal met een vertaalbestand werkt en Engels is de fallback voor talen zonder.
- De series-detail-contextmenu opgelost zodat zowel Mijn Lijst als "Toevoegen aan bibliotheek" verschijnen (eerder overschreef de bibliotheekactie de Mijn Lijst-actie).

### Nieuw in v1.1.0

- Privacy-veilige diagnostiekexport toegevoegd onder Instellingen → Debugging.
- Kodi watched/resume-indicatoren toegevoegd wanneer kijkvoortgangsdata beschikbaar is.
- Nederlandse/Engelse runtime-lokalisatie op basis van Kodi's geconfigureerde taal.
- Wachtwoordinvoer gemaskeerd en netwerk-timeouts toegevoegd.
- De ongebruikte achtergrondservice verwijderd.

### Nieuw in v1.0.3

Zie de [Changelog](CHANGELOG.md) of [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases) voor de volledige versiegeschiedenis.

---

## 🚀 Installatie

1. Download de nieuwste release van [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).
2. In Kodi: **Add-ons > Install from zip file** en selecteer de gedownloade zip.
3. Open de add-on en gebruik **Inloggen** om je te authenticeren bij NLZiet.
4. Installeer en autoriseer de officiële Kodi **Trakt**-add-on als je film- en aflevering-scrobbling wilt.
5. Installeer `inputstream.adaptive` voor DRM-afspelen. De add-on verifieert het automatisch via `inputstreamhelper`.

---

## ⚙️ Instellingen

Zie `resources/settings.xml` voor alle beschikbare instellingen (account, synchronisatie, ondertitels, cache, meldingen, debug).

---

## 🛠️ Ontwikkeling

- Python 3 (Kodi 19+).
- Tests: `python -m pytest` (155 tests).
- Addon-check: `bash scripts/run-addon-check-local.sh`.

---

## 📄 Licentie

MIT — zie [LICENSE](LICENSE).


