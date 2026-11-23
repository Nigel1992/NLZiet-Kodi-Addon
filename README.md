[![Discord](https://img.shields.io/discord/1468295714961494029?color=7289da&label=Join%20Our%20Discord&logo=discord&logoColor=white&style=for-the-badge)](https://discord.gg/9F2NZuydXT)

<div align="center">

<img src="https://raw.githubusercontent.com/Nigel1992/NLZiet-Kodi-Addon/master/icon.png" width="220" alt="NLZiet Kodi Addon Logo"/>

# NLZiet Kodi Addon

[![GitHub stars](https://img.shields.io/github/stars/Nigel1992/NLZiet-Kodi-Addon?style=social)](https://github.com/Nigel1992/NLZiet-Kodi-Addon)
[![Latest release](https://img.shields.io/github/v/release/Nigel1992/NLZiet-Kodi-Addon?label=latest%20release&style=for-the-badge)](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Vibe Coded](https://img.shields.io/badge/Vibe_Coded-✨-8A2BE2?style=for-the-badge)](https://github.com)

**Latest release:** v2.1.0 — 2026-11-23 · [Changelog](CHANGELOG.md) · [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases) · [Wiki](https://github.com/Nigel1992/NLZiet-Kodi-Addon/wiki)

<sub>Unofficial NLZiet Kodi Addon — watch live TV, series, movies and more from NLZiet directly in Kodi. Supports profiles, DRM and a modern UI.</sub>

</div>

---

> ⚠️ **Warning:** This add-on is under constant development. Some features may be broken or incomplete. Use at your own risk and check back for frequent updates.

---

<details>
<summary>🇬🇧 <b>English</b> — click to expand</summary>

## 📚 Documentation

Choose the version that fits you:

- **📖 [Simple language — for everyone](docs/USER_GUIDE.md)** — everything explained step by step, in plain words, no technical knowledge needed.
- **🔧 [Technical version — for developers](docs/TECHNICAL.md)** — architecture, modules, API, testing, build & release.

---

## ✨ Features

- **Live TV** — stream all supported NLZiet channels with EPG info. Includes a custom full-screen EPG (TV Gids) with channel names, current-programme indicator and 7-day browse.
- **Series** — browse, search and play series with full season/episode navigation.
- **Movies** — discover and watch movies from the NLZiet catalog.
- **Saved lists** — add content to **Watch Later** (kept in sync with your NLZiet account) via the item context menu, or add series and films to the **Kodi library**. *Kijk Later* holds episodes and movies; *Mijn Series* follows whole series. Each item shows the matching action in its context menu.
- **Profile management** — switch between user profiles from the Kodi UI.
- **Localization** — all user-facing text resolves through Kodi's language system (Dutch and English included); English is the fallback for languages without a translation file.
- **DRM support** — Widevine-protected streams via `inputstream.adaptive` with automatic `inputstreamhelper` verification.
- **Placement rows** — home-screen rows mirror the official NLZiet app (e.g. "Recommended", "Popular Series").
- **Episode numbering** — accurate SxxExx and Dutch soap (Afl. N) parsing, with season mapping.
- **Search** — find series, movies and episodes by title, with filters for period and genre.
- **Kodi library** — add series and movies through the context menu ("Add to library"), or automatically via **My Series** and **Watch Later** (enabled by default). The addon writes `.strm` + `.nfo` files, keeps episode numbers stable, adds new episodes and removes expired ones automatically, and registers the TV shows / movies folders as Kodi video sources with the "Local information only" scraper — **no manual setup needed**. Missing details (description, artwork, genres, episode titles) are filled in from TMDb (free API key, optional) and TVmaze; NLZiet's own data always comes first.
- **Trakt scrobbling** — movies and episodes expose playback metadata to the official Kodi `script.trakt` add-on (movie title/year resolution, named-episode matching, cached-URL recovery, explicit live-TV exclusion). The Trakt add-on must be installed and authorized separately.
- **Robust handshake** — automatic manifest/license extraction and fallback logic.
- **Clean subtitles** — NPO's teletext-derived subtitles are cleaned before playback, so Kodi shows its normal subtitle overlay instead of the teletext page number ("888") and yellow/white teletext colours.
- **Search history** — recent searches can be reused or selectively removed.
- **New-episode tracking** — My Series highlights series with new episodes; Kijk Later can follow only episodes released from now on.
- **Responsive navigation** — background sync and maintenance never blocks menu transitions or returning from playback.
- **Debug logging** — easy log collection for troubleshooting.

---

## 🚀 Installation

### Option A — via the Kodi repository (recommended, auto-updates)

**Using a URL (no manual download):**

1. In Kodi: **Settings → File manager → Add source** → enter `https://nigel1992.github.io/kodi-repository/` → give it a name (e.g. "Nigel1992") → OK.
2. **Add-ons → Install from zip file** → select the source you just added → `repository.nigel1992-*.zip`.
3. **Add-ons → Install from repository → Nigel1992 Kodi Repository → Video add-ons → NLZiet → Install**.
4. Kodi now keeps the add-on updated automatically.

**Or download the repo zip directly** from the [Kodi repository releases](https://github.com/Nigel1992/kodi-repository/releases/latest) and install it via **Add-ons → Install from zip file** (enable "Unknown sources" first if prompted).

### Option B — manual zip (no auto-updates)

1. Download the latest release from [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).
2. In Kodi: **Add-ons → Install from zip file** and select the downloaded zip.

### After installing (both options)

3. Open the add-on and use **Inloggen** to authenticate with NLZiet.
4. Install and authorize the official Kodi **Trakt** add-on if you want movie/episode scrobbling.
5. Install `inputstream.adaptive` for DRM playback — the addon verifies it automatically via `inputstreamhelper`.

---

## 🛠️ Development

Some modules are shared with the Videoland add-on (`metadata.py`, `library_art.py`, `errors.py`, `diagnostics.py`, `search_filters.py`, `logo_cache.py` in `resources/lib/`). After changing one, copy it to the other add-on with `python3 scripts/sync-shared.py <path to the other add-on>`; `tests/test_shared_modules.py` fails until you do. Menu icons are rebuilt with `python3 scripts/build-menu-icons.py`, the installable zip with `python3 scripts/build-release.py`.

---

## 💖 Support the Project

I build this project in my free time and don't need donations for myself. If you'd like to give something back, I'd kindly ask you to donate to a charity of your choice instead — they need it far more than I do. If you still prefer to support me directly in private, thank you so much; it's genuinely appreciated, and I'll be happy to list you as a donor on GitHub and, where applicable, in a donors section of the project, as a small thank you.

[![Ko-Fi](https://img.shields.io/badge/Ko--Fi-Support%20me-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/nigel1992)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?hosted_button_id=KYV9ARF99ZSCE)

</details>

---

<details>
<summary>🇳🇱 <b>Nederlands</b> — klik om uit te klappen</summary>

## 📚 Documentatie

Kies de versie die bij je past:

- **📖 [Eenvoudige taal — voor iedereen](docs/USER_GUIDE_NL.md)** — alles stap voor stap uitgelegd, in gewone woorden, geen technische kennis nodig.
- **🔧 [Technische versie — voor ontwikkelaars](docs/TECHNICAL.md)** — architectuur, modules, API, testen, bouwen en releasen.

---

## ✨ Functionaliteit

- **Live TV** — stream alle ondersteunde NLZiet-kanalen met EPG-info. Inclusief een aangepaste volledige EPG (TV Gids) met kanaalnamen, indicator voor het huidige programma en 7 dagen vooruit/achteruit bladeren.
- **Series** — blader, zoek en speel series met volledige seizoen/aflevering-navigatie.
- **Films** — ontdek en kijk films uit de NLZiet-catalogus.
- **Opgeslagen lijsten** — voeg content toe aan **Kijk Later** (gesynchroniseerd met je NLZiet-account) via het contextmenu, of voeg series en films toe aan de **Kodi-bibliotheek**. *Kijk Later* bevat afleveringen en films; *Mijn Series* volgt hele series. Elk item toont de bijbehorende actie in zijn contextmenu.
- **Profielbeheer** — wissel tussen gebruikersprofielen in de Kodi-UI.
- **Lokalisatie** — alle gebruikerstekst loopt via Kodi's taalsysteem (Nederlands en Engels inbegrepen); Engels is de fallback voor talen zonder vertaalbestand.
- **DRM-ondersteuning** — Widevine-beschermde streams via `inputstream.adaptive` met automatische `inputstreamhelper`-verificatie.
- **Placement rows** — startscherm-rijen spiegelen de officiële NLZiet-app (bijv. "Aanbevolen", "Populaire series").
- **Afleveringsnummering** — nauwkeurige SxxExx- en Nederlandse soap (Afl. N)-parsing, met seizoensmapping.
- **Zoeken** — vind series, films en afleveringen op titel, met filters voor periode en genre.
- **Kodi-bibliotheek** — voeg series en films toe via het contextmenu ("Toevoegen aan bibliotheek"), of automatisch via **Mijn Series** en **Kijk Later** (standaard ingeschakeld). De add-on schrijft `.strm` + `.nfo`-bestanden, houdt afleveringsnummers stabiel, voegt nieuwe afleveringen toe en verwijdert verlopen, en registreert de TV-shows/films-mappen als Kodi-videobronnen met de "Local information only"-scraper — **geen handmatige setup nodig**. Ontbrekende details (beschrijving, artwork, genres, afleveringstitels) worden aangevuld vanuit TMDb (gratis API-sleutel, optioneel) en TVmaze; NLZiet's eigen data heeft altijd voorrang.
- **Trakt-scrobbling** — films en afleveringen geven afspeelmetadata door aan de officiële Kodi `script.trakt`-add-on. De Trakt-add-on moet apart geïnstalleerd en geautoriseerd zijn.
- **Robuuste handshake** — automatische manifest-/licentie-extractie en fallback-logica.
- **Schone ondertiteling** — NPO's teletekst-ondertitels worden opgeschoond vóór afspelen, zodat Kodi zijn normale ondertitel-overlay toont in plaats van het teletekst-paginanummer ("888") en gele/witte teletekstkleuren.
- **Zoekgeschiedenis** — recente zoekopdrachten kunnen worden hergebruikt of selectief verwijderd.
- **Nieuwe-aflevering-tracking** — Mijn Series markeert series met nieuwe afleveringen; Kijk Later kan alleen afleveringen vanaf nu volgen.
- **Responsieve navigatie** — achtergrondsync en onderhoud blokkeren nooit menu-transities of terugkeer vanaf afspelen.
- **Debug-logging** — eenvoudige logverzameling voor probleemoplossing.

---

## 🚀 Installatie

### Optie A — via de Kodi-repository (aanbevolen, automatische updates)

**Met een URL (geen handmatige download):**

1. In Kodi: **Instellingen → Bestandsbeheer → Bron toevoegen** → voer `https://nigel1992.github.io/kodi-repository/` in → geef een naam (bijv. "Nigel1992") → OK.
2. **Add-ons → Installeren vanuit zipbestand** → selecteer de zojuist toegevoegde bron → `repository.nigel1992-*.zip`.
3. **Add-ons → Installeren vanuit repository → Nigel1992 Kodi Repository → Video add-ons → NLZiet → Installeren**.
4. Kodi houdt de add-on nu automatisch up-to-date.

**Of download de repo-zip direct** van de [Kodi repository releases](https://github.com/Nigel1992/kodi-repository/releases/latest) en installeer via **Add-ons → Installeren vanuit zipbestand** (schakel "Onbekende bronnen" in indien gevraagd).

### Optie B — handmatige zip (geen automatische updates)

1. Download de laatste release van [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).
2. In Kodi: **Add-ons → Installeren vanuit zipbestand** en selecteer de gedownloade zip.

### Na installatie (beide opties)

3. Open de add-on en gebruik **Inloggen** om te authenticeren bij NLZiet.
4. Installeer en autoriseer de officiële Kodi **Trakt**-add-on als je film/aflevering-scrobbling wilt.
5. Installeer `inputstream.adaptive` voor DRM-afspeel — de add-on verifieert dit automatisch via `inputstreamhelper`.

---

## 🛠️ Ontwikkeling

Enkele modules worden gedeeld met de Videoland-add-on (`metadata.py`, `library_art.py`, `errors.py`, `diagnostics.py`, `search_filters.py`, `logo_cache.py` in `resources/lib/`). Na het wijzigen van één module, kopieer je hem naar de andere add-on met `python3 scripts/sync-shared.py <pad naar de andere add-on>`; `tests/test_shared_modules.py` faalt tot je dat doet. Menupictogrammen worden herbouwd met `python3 scripts/build-menu-icons.py`, de installeerbare zip met `python3 scripts/build-release.py`.

---

## 💖 Steun het project

Ik maak dit project in mijn vrije tijd en heb zelf geen donaties nodig. Wil je toch iets terugdoen, dan vraag ik je vriendelijk om in plaats daarvan te doneren aan een goed doel naar keuze — zij hebben het veel harder nodig dan ik. Wil je me toch persoonlijk steunen in privé, dan heel erg bedankt; dat wordt oprecht gewaardeerd, en ik vermeld je graag als donor op GitHub en, waar van toepassing, in een donorsectie van het project, als klein bedankje.

[![Ko-Fi](https://img.shields.io/badge/Ko--Fi-Support%20me-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/nigel1992)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?hosted_button_id=KYV9ARF99ZSCE)

</details>
