# Changelog

> **Latest Version:** v2.1.0 (November 14, 2026)

## [2.1.0] - 2026-11-14

### Added
- **Binge-modus**: nieuwe schakelaar "Volgende aflevering automatisch afspelen" (Instellingen → Afspelen). Als een bibliotheek-aflevering eindigt, start de volgende vanzelf. Heb je Up Next, laat dit uit en laat Up Next het doen.
- **Stop na deze aflevering**: via het contextmenu/een actie kun je de automatische volgende aflevering voor die avond uitzetten.
- **Willekeurige aflevering (shuffle)**: contextmenu op een serie in je bibliotheek → "Willekeurige aflevering afspelen".
- **Vaste taal- en ondertitelvoorkeur**: kies een gesproken taal en/of ondertiteltaal die automatisch gekozen wordt als een video start (Instellingen → Afspelen).
- **Kijkgeschiedenis**: een lokale lijst (alleen op dit apparaat) van wat je gekeken hebt, in het hoofdmenu en als widget; met een knop om te wissen.

### Development
- Nieuwe gedeelde module `watch_history.py` en uitbreiding van `playback_extras.py` (taalkeuze), gedeeld met Videoland. Extra tests.
## [2.0.0] - 2026-11-14

### Added
- **Watched status back to NLZiet**: when you watch something (almost) to the end, or mark it as watched/unwatched in Kodi's own library, NLZiet gets the same status. Turn it off under Settings → Synchronisation. Uses NLZiet's own "watched" feature.
- **Next episode (Up Next)**: with the Up Next add-on installed, the next episode is offered near the end of a library episode so it starts by itself (Settings → Playback → While watching; includes an install button).
- **Skip intro/recap**: during playback "Skip the intro?" or "Skip the recap?" appears when NLZiet sends chapter times for the video. Whether they are present is logged per video ("chapters ... markers found").
- **Widgets for the home screen**: ready-made lists (Continue watching, Watch later, My series, My list) for your skin's home-screen widgets, under a new "Widgets" menu. "Continue watching" is also added to the main menu.
- **Backup and restore of your lists**: a button that saves My list, Watch later, My series, the library list and your settings (without password) to one file, and a button to restore them (Settings → Library → Backup and restore).
- **Daily automatic check**: once a day the add-on checks in the background whether everything still works and notifies you only when something needs attention (Settings → Library → Maintenance).
- **Search both services**: when Videoland is installed, a search also offers the same search in Videoland at the top of the results.

### Development
- New shared modules `playback_extras.py` (chapters/markers + Up Next) and `watch_sync.py` (watched-status logic), kept identical with Videoland via `scripts/sync-shared.py`.
- 39 new unit tests (watch_sync, chapter markers, next-episode selection).

## [1.9.3] - 2026-11-14

### Fixed
- **No TMDb match for some series** (e.g. Chateau Meiland): when the title on NLZiet's series page finds nothing on TMDb, the title of the card you added the series from is tried as well.

## [1.9.2] - 2026-11-14

### Fixed
- **No TMDb match for some series**: site suffixes such as " - Kijk online ..." and trailing years are stripped before searching TMDb; the Kodi log shows per series which match was found ("metadata for ...").

## [1.9.1] - 2026-11-14

### Changed
- **Settings → Library** is now right below Account and split into groups with a heading: Folders, Lists to the library, Automatic updates, Extra metadata and Maintenance.

### Development
- Modules shared with the other add-on are listed in `scripts/sync-shared.py` and pinned in `SHARED.lock`; a test fails when one is changed without copying it to the other add-on.

## [1.9.0] - 2026-11-14

### Added
- **Posters and backgrounds: TMDb first** (Settings → Library → Extra metadata, on by default): posters and backgrounds come from TMDb when it has them, with the service's own images as fallback; descriptions stay service-first. Artwork the add-on set earlier in Kodi is replaced when a better image is known (Kodi gets the image url, so the change shows at once); artwork you chose yourself in Kodi is never replaced.
- **Choose the right TMDb title** (Library menu, context menu of a title): pick the matching TMDb series or film by hand, or search with another term, when the automatic match missed it. Titles with a trailing year or "- Seizoen N" now also match automatically.
- **Season posters**: each season gets its own poster from TMDb (`season01-poster.jpg`), also for seasons Kodi already scanned.
- **Logos in the menus**: logos of titles outside the library are looked up on TMDb in the background and appear the next time a list is opened (setting "Show logos in the menus too", needs the TMDb key).
- **My Series and Watch Later in the library**: "Add My Series and Watch Later to the library now" (Library menu and settings), plus an automatic option and an optional removal of titles that left these lists. An episode in Watch Later adds its series.

## [1.8.2] - 2026-11-14

### Added
- **Series and film logos (clearlogo)**: with a TMDb key, every series and film in the library gets its logo (Dutch first, then English, then one without text) as `clearlogo.png` (films: `<name>-clearlogo.png`) and in the `.nfo`. Titles Kodi already scanned get the logo through the artwork repair. Skins that show logos instead of titles (widgets, info screens) now use them; browse lists in the add-on show the logo for titles that are in the library.

## [1.8.1] - 2026-11-14

### Fixed
- **Diagnostics**: a library folder is no longer reported as "not a Kodi source" when Kodi already has titles from it (for example when the parent folder was added as the source). The hint now also says which content type and scraper to choose.

## [1.8.0] - 2026-11-14

### Added
- **Parental control** (Settings → Parental control): set a PIN, choose per profile (Profiles → long press) whether switching to it needs the PIN, and optionally require the PIN for live tv and the TV guide. Kids profiles are marked. The PIN is stored only as a salted hash; after a correct PIN the lock stays open for 30 minutes.
- **Search filters**: a Filter entry on top of search results narrows them by period (2020 and later, 2010s, 2000s, 1990s, before 1990) and genre, when NLZiet supplies that information.
- **Trakt watched status in menus** (Settings → Synchronization, opt-in): films and episodes watched on Trakt show as watched, using the account connected in script.trakt. Episodes are matched by show title, season and episode number; nothing is guessed.
- The diagnostics button moved to Settings → Library.

## [1.7.5] - 2026-11-14

### Fixed
- **Library titles missing from Kodi**: Kodi ignores a scan request while it is still scanning, so titles added in quick succession were written to the library folder but never scanned. Such a request now waits and runs as soon as Kodi's scan is finished, and **Update library now** always lets Kodi scan, so titles that were skipped before get in too.

### Added
- **Diagnostics** (Settings): one screen that checks sign-in, InputStream Adaptive, Widevine, the connection to the service, TMDb and TVmaze, the TMDb key, whether the library folders are Kodi sources, and how many library titles Kodi really has. A privacy-safe report with a log excerpt is saved for bug reports.

## [1.7.4] - 2026-11-14

### Added
- **Sorting**: list pages offer Kodi's sort options (default order, title, year; episode and date inside seasons).
- **Clear error messages**: unexpected problems show one sentence that says what happened (no internet, slow response, session expired, not in your subscription, no longer available, too many requests, service outage); the details go to the Kodi log.
- **GitHub Actions**: tests and an installable zip on every push and pull request; pushing a `v*` tag publishes a release with the zip.

### Fixed
- **TMDb key test**: the button now saves the settings first (Kodi only saves when the settings window closes, so the test used to see an empty key) and says exactly what is wrong: no key saved, key not accepted, or TMDb not reachable. Connections retry with a bundled certificate list on devices without system certificates.
- **Menu icons not changing**: the new icons now live in `resources/media/menu/`. Kodi caches images by file name, so with the old names it kept showing the previous icons.

## [1.7.3] - 2026-11-14

### Changed
- **Menu icons**: a new consistent icon set: coloured tiles per menu group (blue = browse, purple = your own lists, red = live tv, grey = account) with white line glyphs. No text is baked into the images any more, so labels are not shown twice and follow Kodi's language. The unused Live TV image was removed; `scripts/build-menu-icons.py` rebuilds the set.
- **Main menu order**: search and browsing first, then your own lists and the library, then profiles and sign out at the bottom.

### Fixed
- **Library posters**: series and films now get their poster and background in Kodi's library. The images are picked the same way as when browsing, the poster of the item you added is remembered when the detail page has none, and the images are saved as `poster.jpg`/`fanart.jpg` (films: `<name>-poster.jpg`/`<name>-fanart.jpg`) next to the files, which Kodi always uses.
- **Library posters**: titles Kodi had already scanned without artwork get their poster and background filled in after every library update and after every Kodi library scan. Artwork you chose yourself in Kodi is never replaced. Settings → Library has a "Repair artwork in the Kodi library" button.

## [1.7.2] - 2026-11-14

### Changed
- **Library folder**: the library now always lives in the add-on's own folder (`special://profile/addon_data/plugin.video.nlziet/library/`). Series exported by older versions to `/storage/emulated/0/KodiNLZietLibrary/TV Shows` are moved there automatically, once (on first library use, or about two minutes after Kodi starts). The empty old folder is removed, and the folder setting is reset if it still pointed to the old location. A notification asks to add the new folder as a Kodi source; Kodi's library is cleaned and rescanned.

## [1.7.1] - 2026-11-14

### Added
- **Library metadata**: NLZiet's own data is always used first; only empty fields are filled in from TMDb (series and films, needs a free TMDb API key) and TVmaze (series, no key needed): description, poster, background, year, genres, rating, network/studio, and per-episode titles, descriptions and images. Placeholder titles such as "Aflevering 3" are replaced by the real episode title.
- **Library metadata**: `.nfo` files now also carry TMDb, TVDB, IMDb and TVmaze ids, so Kodi, skins and Trakt match titles reliably. (TVDB is not queried directly because its API needs a paid key; the id comes from TMDb/TVmaze.)
- **Settings → Library → Extra metadata**: on/off switch, a field for the TMDb API key and a "Test TMDb key" button.
- Only exact title matches are used (films also need a matching year), answers are cached for 7 days, and a slow or unreachable service is skipped for a few minutes so library updates never hang.

## [1.7.0] - 2026-11-14

### Added
- **Library**: movies can now be added to the Kodi library too (context menu "Add to library" on a movie). Movies are written to their own folder (Settings → Library → Folder for movies).
- **Library**: the context menu shows "Remove from library" for series and movies that are already in the library; removing deletes the files and cleans the Kodi library.
- **Library**: added series and movies are remembered and updated automatically in the background (default every 12 hours, never during playback): new episodes are added and episodes or movies that are no longer available are removed.
- **Library**: new main menu entry "Library" with everything that was added, an "Update library now" action and a remove option per item.
- **Library**: new settings category "Library" with folders for TV shows and movies, automatic update and interval, and options to scan and clean the Kodi library after a change.
- **Library**: `.nfo` files now include artwork, a unique NLZiet id and runtime, so Kodi shows posters and thumbnails without an external scraper.

### Changed
- **Library**: episode numbers are assigned once and stored per episode, so file names stay the same when older episodes expire. Kodi keeps watched status and resume points.
- **Library**: series with real season/episode numbers use those numbers; daily programmes keep using the broadcast year as season.
- **Library**: the default library folder is now inside the addon data folder (`special://profile/addon_data/plugin.video.nlziet/library/`), so it works on every platform. (See 1.7.2: the old Android folder is moved there.) Folder settings now open Kodi's folder browser, and network shares (smb://, nfs://) are supported.
- **Library**: a failed or empty answer from NLZiet never deletes library files.

## [1.6.4] - 2026-11-13

### Added
- **Sync**: new setting "Show notification after automatic sync" (Settings → Synchronization, on by default). Turn it off to stop the automatic background sync from showing any notification.

### Changed
- **Automatic sync notifications**: the background sync only shows a notification when something actually changed, and never while video or music is playing.
- **Manual sync**: "Sync now" and the other manual sync actions always show their result, also during playback.

## [1.6.3] - 2026-11-12

### Added
- **Sync**: added a "Sync Now" context-menu action on each item in Kijk Later and Mijn Series for manual cloud sync (the manual sync buttons in Settings → Synchronization already existed).
- **Sync**: added an auto-sync interval setting (background service) to sync Kijk Later and Mijn Series every X minutes.

## [1.6.2.1] - 2026-11-12 (hotfix)

### Fixed
- **EPG**: adding/removing items to/from "Kijk Later" and "Mijn Series" via the EPG program menu no longer fails with a `NameError` (`pgm` not defined); list actions now work again.

## [1.6.2] - 2026-11-09

### Changed
- **Settings**: cache clearing (subtitle cache and all cache) moved into a new dedicated "Cache" category.
- **Settings**: removed the "Advanced" (API base URL) and "Profiles" categories; the API base URL is now built into the addon.
- **Settings**: Debugging category now only contains debug HTTP and diagnostics export.

## [1.6.1] - 2026-11-08

### Fixed
- **Live TV OSD**: the OSD now shows the current programme's title and description instead of only the channel name.
- **Stored lists OSD**: items played from Watch Later / My List now show their stored title, description and artwork on the OSD.
- **My Series from EPG**: EPG programmes (e.g. Pawn Stars) can now be added to My Series.
- **Watch Later from EPG**: only programmes that can actually be replayed later are accepted; future programmes are added with a clear message about when they can be played.
- **Watch Later menu**: stored descriptions now come through on the OSD.

## [1.6.0] - 2026-11-08

### Added
- **TV Gids timeline**: the EPG is now a timeline grid with a time ruler, one row per channel, and programme blocks sized to their duration. Past programmes are grey, live programmes blue, and future programmes green. The current time is shown as a white line.
- **Programme description**: the selected programme's description is shown at the bottom and scrolls automatically when it is long.
- **Clock and date**: the current time and date are shown in the top right of the EPG.
- **Footer bar**: the day selector (press I / Info) is on the left and the channel count on the right.
- **Return to position**: after playback started from the EPG stops, the EPG reopens on the same channel, programme, day and time window.
- **Clear all cache**: a new settings button clears the EPG, TVmaze and episode caches and the subtitle cache.
- **Automatic cache clearing**: optional periodic clearing of all caches, with a configurable number of hours (off by default).
- **Speel vanaf begin**: on a programme that is live now, the Enter menu offers "Speel vanaf begin" instead of "Afspelen (terugkijken)".

### Changed
- **Menu name**: the main menu entry "EPG" is now "TV Gids", and the EPG title is "NLZiet TV Gids".
- **Faster EPG opening**: the window opens immediately and the channel list is cached for 6 hours, so the EPG no longer waits for the server on every open. Day data is cached for 6 hours and refreshed when you pick a day.
- **Live programme menu**: "Nu live kijken" is only offered for programmes that are on now.

### Fixed
- **EPG hang on close** (issue #36): closing the EPG no longer leaves Kodi's loading spinner running, and the plugin no longer keeps running in the background.
- **Missing programme blocks**: rows with more than 12 programmes in the visible window now show all of them.
- **Blocks missing after changing day**: switching to another day now shows its programmes straight away.
- **Text outside blocks**: text on very short programmes no longer spills outside its block.
- **Day dialog on Enter**: pressing Enter on a programme opens its menu instead of the day picker.
- **Placeholder text**: the grid no longer briefly shows "Vandaag" before the date.

## [1.5.0] - 2026-11-08

### Added
- **Custom EPG**: full-screen EPG dialog with channels on the left and horizontally scrolling programmes on the right. Shows channel logos, current programme (● NU), and date/time per programme. Browse today + 7 days back/forward via a day selector (press I / Info).
- **Live TV restart/replay**: "Afspelen (terugkijken)" on live programmes now starts from the beginning instead of jumping to realtime.
- **Context menu**: long-press Enter on any programme for Play / Add to My Series / Add to Watch Later.
- **Auto subtitle cache clearing**: optional periodic clearing of the subtitle cache (configurable hours).
- **Menu icons**: refreshed premium icon set.
- **Live TV resume prompt**: live streams no longer offer "Resume from …"; always start at the live edge.
- **EPG day filtering**: selecting a day now correctly filters programmes to that day.
- **EPG channel highlight**: selected channel stays highlighted while browsing programmes.
- **Subtitle cache settings**: spinner now has min/max/step so a duration can be selected.
- **EPG return after playback**: returns to EPG when playback stops.
- **EPG OSD info**: title, plot, and icon now shown during playback.
- **EPG layout**: professional date/time layout on programme cards.
- **Live TV via EPG**: fixed blue spinning circle; playback starts correctly.

All notable changes to this project are recorded in this file.

## [1.4.5] - 2026-11-06

### Added
- **Premium menu icons**: refreshed all main-menu icons with a consistent gradient icon set (squared, no rounded-corner clipping).

### Fixed
- **Live TV watched status**: items under Channels/Kanalen no longer show a watched/checkmark indicator, since they are live streams.
- **Icon cropping**: menu icons are now cropped to a clean square so rounded corners are not clipped by the skin.

All notable changes to this project are recorded in this file.

## [1.4.4.2] - 2026-11-06 (hotfix)

### Fixed
- **Episodes not loading**: `ZoneInfo('Europe/Amsterdam')` failed on systems without tzdata, raising `KeyError: 'Europe/Amsterdam'` and breaking episode loading. Now falls back to UTC.

## [1.4.4.1] - 2026-11-06 (hotfix)

### Fixed
- **Slow Mijn Series loading**: detecting newly added episodes previously fetched every series' episodes synchronously while rendering the list. This now runs in the background, so Mijn Series opens immediately; the new-episode highlight/refresh follows after the list is shown.

## [1.4.4] - 2026-11-05

### Added
- **Search history**: recent searches are saved locally, can be reused, and can be selectively deleted.
- **My Series new-episode indicator**: series with episodes that appeared since the previous check are shown with a green title.
- **Series add mode**: adding a series to Kijk Later now lets you choose between all existing episodes or following only new episodes from now on.
- **Subtitle cache action**: clear cleaned subtitle files from Settings → Debugging.

### Fixed
- **Blue spinner on menu navigation**: non-essential backfill, list sync, auto-add and expiry checks now run after the directory is displayed, without blocking menu transitions or returning from playback.
- **Auto-add baseline**: following a series from now on records the current episode list as a baseline, preventing the existing back catalogue from being added.

### Changed
- Token expiry checks are throttled to avoid repeated refresh work during rapid menu navigation.

## [1.4.3] - 2026-10-28

### Added
- **Kijk Later series folders**: episodes of the same series are grouped into a folder with season subfolders. Ordering uses NLZiet's `Sx:Ax` codes first, with TVmaze as fallback. Episode labels show "Aflevering X: ..." with a muted prefix.
- **Add all episodes to Watch Later**: context menu on a series or episode adds every episode of that series to Kijk Later as one collection.
- **Automatically add new episodes**: new setting under Settings → Synchronization to queue new episodes for series in **Mijn Series** and episodes already in **Kijk Later**. On first enable it establishes a baseline (no back-catalogue dump).
- **Expiry notifications**: new **Meldingen** settings category to alert when items in Kijk Later or Mijn Series are about to expire, with configurable hours and per-list toggles.
- **TVmaze lookup**: resolves missing season/episode numbers and titles for better ordering when NLZiet provides incomplete metadata.

### Fixed
- **Bulk-added episodes grouped correctly**: episodes added via "add all episodes" are now grouped under the series folder and sorted properly, even when stored with incomplete top-level metadata.
- **Nested payloads respected**: Kijk Later renders subtitles and broadcast times from nested API payloads (fixes missing episode titles for bulk-added items).

### Changed
- **Settings help text**: clarified what "Automatically add new episodes" does.

## [1.4.2] - 2026-10-19

### Added
- **Episode info in Kijk Later**: every item in **Kijk Later** now shows its episode numbering ("Afl. 3 van 12") and how long it is still available ("nog 5 dagen beschikbaar" / "nog 3 uur beschikbaar" / "niet meer beschikbaar") as two subtly coloured lines at the top of its description — in the info dialog (plot) as well as in the outline (plotoutline). The numbering comes from the season catalogue, fetched once per series/season while the list renders, and falls back to parsing the episode subtitle when the API returns no catalogue data.

### Fixed
- **Saved lists showed the broadcaster logo instead of the poster**: the raw NLZiet payload of Kijk Later / My List items only carries the channel logo (`logoUrl`), which the artwork picker preferred over real artwork, so rows showed an NPO/RTL logo instead of the film or series poster. Real posters and stills now always win, and broadcaster logos are only used as a last resort (for example in the channel list).
- **NPO teletext subtitles**: NPO publishes teletext-derived WebVTT files that open with the teletext page number ("888") and colour the dialogue with yellow/white class tags, which Kodi rendered literally instead of using its own subtitle overlay. External NPO subtitles are now cleaned before playback — the page-number cue, the "TT888"/`service.npo.nl` banner and the teletext colour tags are stripped — and cached locally. RTL and SBS subtitles are left untouched, and anything that cannot be cleaned is passed through unchanged.
- **Availability line colour**: the "nog X dagen beschikbaar" line used an invalid colour value (`ffoooo66`) that Kodi silently ignored; it is now a warm amber that stands out subtly on dark skins.

### Changed
- Added Dutch and English strings for the episode numbering and availability lines.

## [1.4.1] - 2026-10-16

### Fixed
- **Cloud list sync no longer truncated to 10 items**: the NLZiet watchlist endpoints (`/v9/watchlist` and `/v9/trackedseries`) return only the first 10 entries unless a `limit` is sent. My Series and Watch Later now request pages of 500 and follow `offset` until a short page is returned, so every followed series / watch-later item syncs both ways instead of silently dropping anything beyond the 10th.

## [1.4.0] - 2026-10-16

### Added
- **Two-way list sync**: **Kijk Later** and the new **Mijn Series** list can each be kept in sync both ways (local + cloud) with your NLZiet account. Episodes and movies sync through the cloud watchlist, while followed series sync through the tracked-series list, so a series you add in Kodi shows up under *Mijn Series* in the NLZiet app and vice versa. Enable **Settings → Synchronization → Sync Watch Later and My Series with NLZiet**; the **Sync Watch Later now** and **Sync My Series now** buttons perform a manual sync, and a three-way merge (with an "additions win" rule) prevents concurrent changes from being lost.
- **Mijn Series (My Series)**: a dedicated main-menu entry and local list that follows whole series, backed by the cloud tracked-series list. Series saved here reopen their detail page.
- **Per-type context menu**: each item now shows the action that fits its content type — **Add to Watch Later** for episodes and movies, **Add to My Series** for series, and **Add to My List** for everything.
- New strings for the My Series set and the manual sync action.

### Changed
- **My List is now clearly labelled as local (Kodi only)** in both Dutch and English — main menu, add/remove context-menu actions, add/remove notifications, the empty-list message and the logout prompt all state that My List is stored on this device only. Kijk Later and Mijn Series are the cloud-synced lists.
- The Login/Logout items on the main menu are now plain action commands instead of being marked as playable media.
- **Settings → Synchronization** now reads "Sync Watch Later and My Series with NLZiet" and includes a separate **Sync My Series now** button alongside **Sync Watch Later now**.

### Fixed
- Followed series are no longer silently dropped during cloud sync: because the NLZiet watchlist API accepts but discards series ids, series are now routed to `/v9/trackedseries`, so adding a series in Kodi is correctly reflected in the NLZiet app.

## [1.3.0] - 2026-10-13

### Added
- My List now has its own subsection per category (Series, TV Shows, Documentaires, Films, Kanalen) instead of a single generic list.
- My List accepts every content type (TV Shows, Documentaires, Kanalen and episodes too), matching Kijk Later.

### Changed
- Every user-facing string (notifications, dialogs, keyboard prompt, grouped search/My List folder labels and count labels) now resolves through Kodi's translation system, so a Dutch Kodi shows the whole add-on in Dutch.

### Fixed
- Live channels saved to My List / Kijk Later now play correctly (they are opened with the live stream context).

## [1.2.0] - 2026-10-12

### Added
- **Kijk Later** (Watch Later): a local queue with its own main-menu entry and an "Add to Kijk Later" / "Remove from Kijk Later" context-menu action available on any content.
- New menu icon for the Kijk Later queue.
- Saved list entries now persist the full content metadata (title, description/plot and artwork) so My List / Watch Later show rich items instead of bare titles.
- Runtime UI strings now resolve through Kodi's translation system (`strings.po`), so any language with a translation file works; English is the universal fallback.

### Fixed
- Series detail now shows both the My List and "Add to library" context-menu actions (previously the second overwrote the first).
- Saved series now reopen their detail page from My List / Watch Later even when the content type was not supplied.

## [1.1.0] - 2026-09-02

### Added
- Privacy-safe diagnostic report export from the Debugging settings category.
- Kodi watched and resume indicators when NLZiet supplies viewing-progress metadata.

### Changed
- Runtime menu text now follows Kodi's Dutch or English language setting.
- Password entry is masked during login.
- EPG HTTP and IPTV Manager socket calls now have bounded timeouts.

### Removed
- Unused background service and unsafe daemon account-refresh thread.

## [1.0.3] - 2026-08-24

### Added
- **Official Trakt Scrobbling Compatibility**: On-demand movies and episodes now publish Kodi playback metadata used by `script.trakt`, including media type, title, series title, season/episode numbers, and release year when available.
- Library-exported episode `.strm` URLs now retain the same Trakt-compatible metadata during playback.
- Playback-time metadata recovery for cached or legacy Kodi URLs that contain only an NLZiet content ID.
- Movie title/year resolution and named-episode matching through the installed official Trakt add-on when NLZiet metadata is incomplete or uses a different episode order.

### Fixed
- Live NLZiet channels are explicitly excluded from Trakt scrobbling so broadcasts cannot be misidentified as on-demand content.
- NLZiet broadcast and availability dates are no longer treated as movie release years or TV-series production years.
- Series titles and season numbers now survive season navigation and library export.
- Missing episode numbers can be inferred from adjacent numbered entries in the same newest-first NLZiet season list.

### Notes
- The official Kodi `script.trakt` add-on must be installed, authorized, enabled, and configured to allow HTTP/plugin playback scrobbling.
- Entries whose only episode label is `Afl. N` cannot always be translated when NLZiet and Trakt use different season orders; named episodes are matched against Trakt's canonical order.

## [1.0.2] - 2026-08-19

### Fixed
- **LibreELEC Compatibility**: Resolved `The dependency on script.module.charset-normalizer version 2.0.12 could not be satisfied` by bundling `charset-normalizer` 2.0.12 locally in `resources/lib/` instead of relying on the external `script.module.charset-normalizer` Kodi addon, which is not available in minimal distributions like LibreELEC. The same self-contained approach was applied to `certifi` to prevent similar installation failures.

### Removed
- External `script.module.charset-normalizer` and `script.module.certifi` dependencies from `addon.xml` — both libraries are now self-contained in the addon's `resources/lib/`.

## [1.0.1] - 2026-04-20

### New
- Bundled urllib3 1.26.12 directly into addon `resources/lib/` for reliable dependency resolution on minimal Kodi distributions like LibreELEC.

### Updated
- Enhanced `nlziet_api.py` to add local `resources/lib` directory to Python path before importing requests, ensuring urllib3 is located first.

### Fixed
- **LibreELEC Compatibility**: Resolved `ModuleNotFoundError: No module named 'urllib3'` by bundling urllib3 locally instead of relying on external `script.module.urllib3` addon dependency, which may not be available on minimal Kodi systems.
- Improved addon check script to clean up pip-installed artifacts (`.pyc`, `__pycache__`, `.so` files) that shouldn't be included in releases.

### Removed
- External `script.module.urllib3` dependency from `addon.xml` — urllib3 is now self-contained in the addon.


## [1.0.0] - 2026-04-06

### Added
- **Token-Based OAuth2 Authentication**: Secure PKCE-based login flow with automatic token refresh. Sessions persist across Kodi restarts via cookie storage.
- **Dialog-Based Login**: Modern Kodi dialog login interface — credentials are never exposed in addon settings menu for better security and UX.
- **Optional Credential Storage**: Users choose between "Save tokens only" (recommended, requires login only when tokens expire) or "Save email+password" (auto-refresh convenience).
- **Auto-Token Refresh**: Sessions automatically refresh when tokens expire with 60-second proactive buffer. Fallback to form login if refresh fails, with user re-login prompt.
- **Dynamic Login/Sign Out Button**: Main menu displays "Login" when not authenticated and "Sign Out" when user has active session.
- **Protected Content Menu**: Series, Movies, TV Shows, Search, and My List menu items hidden for unauthenticated users.
- **Logout Confirmation Flow**: Two-step logout with optional "Keep My List" to preserve favorites after sign out.
- **Live TV EPG Display**: Current program ("Nu live") and next program ("Straks") now display in channel descriptions with broadcast times (HH:MM-HH:MM).
- **Global API Instance Caching**: 5-minute TTL cache reduces initialization overhead and disk I/O on every menu interaction.
- **Fast EPG Channel Cache**: 45-second cache for channel menu EPG to reduce load time while keeping data fresh.
- **Smart Artwork by Aspect Ratio**: Automatically separates and assigns images based on aspect ratio — landscape (16:9) for fanart, portrait (2:3) for covers, preventing face-cutting.
- **High-Resolution Fanart Images**: Image URLs now request 3840px width from the NLZiet image service, rendering crisp 4K-quality artwork instead of pixelated thumbnails.
- **Kodi Fanart Support**: Added addon fanart metadata and menu-level fanart assignment so skins can render `resources/media/background.jpg` when opening/browsing the addon.
- **Logout Icon Asset**: Added dedicated `menu_logout.png` and wired main menu logout item to prefer this asset.
- **Converted Localization Catalogs**: Added `resource.language.en_gb/strings.po` and `resource.language.nl_nl/strings.po` for converted settings string resolution.
- **InputStream Helper Integration**: Uses `script.module.inputstreamhelper` v0.6.0 for DRM verification before playback. Ensures `inputstream.adaptive` and Widevine CDM are properly installed.

### Changed
- Authentication workflow completely redesigned: moved from settings-based credentials to secure dialog-based OAuth2 flow.
- API instance creation now centralized via `get_api_instance()` function with caching logic for 15+ menu functions.
- Image optimization function now requests 3840px width instead of stripping parameters, ensuring high-quality fanart display.
- Context menu items now use cached API instances instead of creating new NLZietAPI objects per item interaction.
- Settings now run in Dutch-only mode for addon settings UI: removed language switch controls and language-dependent branching in settings label paths.
- Localization layout migrated from legacy `resources/language/English|Dutch/strings.xml` to Kodi resource language folders.
- Service wrapper simplified to a minimal monitor loop; removed language-change monitor/state persistence logic.
- Addon metadata now keeps Dutch summary/description only.
- EPG labels now use Dutch localization ("Nu live" and "Straks") for consistency with user preferences.

### Fixed
- **EPG Data Missing on Live TV**: Fixed parsing of nested channel/programLocations API response structure. Program titles, times, and descriptions now correctly extract from nested content objects.
- **Wrong Program Showing on Live TV**: Fixed EPG selection logic to prioritize currently-playing programs over future/past programs.
- **Context Menu on Live TV**: Prevented Kodi's "Resume from" and "Play from beginning" context menu options from appearing on live channels. Live streams now play directly via `ResumeTime`, `TotalTime`, and `IsLive` properties.
- **Performance Delay on Live TV Cancel**: Removed unnecessary 1-second sleep and per-channel fallback logic that caused delays when canceling playback.
- **Channel Menus 404 Errors**: Channel menus no longer generate 404 errors from unsupported `/v9/content/detail` endpoint.
- **Image Aspect Ratio Issues**: Image aspect ratio correctly preserved in Kodi artwork keys — landscape images no longer assigned to portrait keys and vice versa.
- **Pixelated Fanart Images**: Small fanart now requests higher resolution from API (3840px), eliminating zoom/crop appearance on large screens.
- **Slow Menu Response**: Menu response time reduced from 2-3 seconds to near-instant for context operations (Add/Remove My List).
- **Undefined Variable References (#8)**: Fixed undefined reference to series_detail() in series listing; removed erroneous per-series season fallback attempt from functions that don't operate on individual series IDs.
- **Missing/Blank Settings Labels**: Fixed by keeping converted `version="1"` settings structure and providing matching string IDs in resource language catalogs.
- **Inconsistent Settings Language Rendering**: Fixed by using Dutch labels in both fallback catalogs.
- **Token Refresh Without Refresh_Token**: Implemented PKCE-based fallback renewal when refresh_token is unavailable, using preserved cookie session to silently re-authorize.

### Notes
- OAuth2 PKCE flow ensures secure token exchange without exposing client secrets.
- Cookie-based session persistence uses HTTP LWP format for cross-session recognition with ~30 day lifetime (idsrv cookie).
- Token expiry buffer set to 60 seconds for proactive refresh before actual expiration.
- `resources/settings.xml` remains in converted format (`<settings version="1">` + section/category/group/setting/control hierarchy) per Kodi conversion guidance.
- InputStream Helper checks are performed before DRM playback to ensure dependencies are available.

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
