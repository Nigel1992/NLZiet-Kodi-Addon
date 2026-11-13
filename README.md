[![Discord](https://img.shields.io/discord/1468295714961494029?color=7289da&label=Join%20Our%20Discord&logo=discord&logoColor=white&style=for-the-badge)](https://discord.gg/UbPRh74PzV)


<div align="center">

<img src="https://raw.githubusercontent.com/Nigel1992/NLZiet-Kodi-Addon/master/icon.png" width="300" alt="NLZiet Kodi Addon Logo"/>

# NLZiet Kodi Addon

[![Vibe Coded](https://img.shields.io/badge/Vibe_Coded-✨-8A2BE2?style=for-the-badge)](https://github.com)

[![GitHub stars](https://img.shields.io/github/stars/Nigel1992/NLZiet-Kodi-Addon?style=social)](https://github.com/Nigel1992/NLZiet-Kodi-Addon)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Latest release:** v1.6.4 — 2026-11-13. See the [Changelog](CHANGELOG.md) or [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).

<sub>Unofficial NLZiet Kodi Addon - Watch live TV, series, movies, and more from NLZiet directly in Kodi. Supports profiles, DRM, and a modern UI.</sub>

</div>

---

> ⚠️ **Warning:** This add-on is under constant development. Some features may be broken or incomplete. Please see the To-Do section below for known issues and planned improvements. Use at your own risk and check back for frequent updates!

---

<details>
<summary>🇬🇧 <b>English</b> — click to expand</summary>


## ✨ Features

- **Live TV**: Stream all supported NLZiet channels with EPG info.  
Includes a custom full-screen EPG (TV Gids) with channel names, current programme indicator, and 7-day browse.  
- **Series**: Browse, search, and play series with full season/episode navigation.  
- **Movies**: Discover and watch movies from the NLZiet catalog.  
- **Saved lists**: Add **any** content (Series, TV Shows, Documentaires, Films, Kanalen, episodes) to **My List** via the item context menu; My List groups items into a subsection per category and is stored **locally on this device only (Kodi only)**.  
**Kijk Later** (Watch Later) holds episodes and movies, while **Mijn Series** (My Series) follows whole series — each item shows the matching action in its context menu.  
Both Kijk Later and My Series can optionally **synchronise both ways with your NLZiet account** (Settings → Synchronization) through the cloud watchlist and tracked-series list respectively, including manual **Sync Watch Later now** / **Sync My Series now** actions. An optional auto-sync interval runs in the background; its result can be shown as a notification (toggle "Show notification after automatic sync"), which only appears when something changed and never during playback.  
- **Profile Management**: Switch between user profiles from the Kodi UI.  
- **Localization**: All user-facing text resolves through Kodi's language system (Dutch and English included); English is the fallback for languages without a translation file.  
- **DRM Support**: Widevine-protected streams via `inputstream.adaptive` with automatic `inputstreamhelper` verification.  
- **Placement Rows**: Home screen rows mirror the official NLZiet app (e.g., "Recommended", "Popular Series").  
- **Episode Numbering**: Accurate SxxExx and Dutch soap (Afl.  
N) parsing, with season mapping.  
**Kijk Later** additionally shows the episode number and the remaining availability as compact, subtly coloured lines in the item description.  
- **Search**: Find series, movies, and episodes by title.  
- **Trakt Scrobbling**: Movies and episodes expose playback metadata to the official Kodi `script.trakt` add-on, with movie title/year resolution, named-episode matching, cached-URL recovery, and explicit live-TV exclusion.  
The Trakt add-on must be installed and authorized separately.  
- **Robust Handshake**: Automatic manifest/license extraction and fallback logic.  
- **Clean subtitles**: NPO's teletext-derived subtitles are cleaned before playback, so Kodi shows its normal subtitle overlay instead of the teletext page number ("888") and yellow/white teletext colours.  
- **Search history**: recent searches can be reused or selectively removed.  
- **New episode tracking**: My Series highlights series with new episodes, and Kijk Later can follow only episodes released from now on.  
- **Responsive navigation**: background sync and maintenance work does not block menu transitions or returning from playback.  
- **Debug Logging**: Easy log collection for troubleshooting.  
---
---

See the [Changelog](CHANGELOG.md) for the full version history.  

## 🚀 Installation

1. Download the latest release from [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases), or install via the [Kodi repository](https://github.com/Nigel1992/kodi-repository) (recommended for automatic updates).  
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
- [X] **Episodes use episode title instead of count** (show SxxExx or Afl.  
N when possible)  
- [X] **Fix subfolders in series option** (better season/episode navigation)  
- [ ] **Improve error messages and user feedback**  
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
<summary>🇳🇱 <b>Nederlands</b> — klik om uit te klappen</summary>

## ✨ Functies

- **Live TV**: Stream alle ondersteunde NLZiet-zenders met EPG-info.  
Bevat een aangepaste volledig-scherm EPG (TV Gids) met zendernamen, huidige-programma-indicator en 7 dagen bladeren.  
- **Series**: Blader, zoek en speel series af met volledige seizoen/aflevering-navigatie.  
- **Films**: Ontdek en kijk films uit de NLZiet-catalogus.  
- **Opgeslagen lijsten**: Voeg **elke** content (Series, TV Shows, Documentaires, Films, Kanalen, afleveringen) toe aan **Mijn Lijst** via het contextmenu; Mijn Lijst groepeert items per categorie en wordt **alleen lokaal op dit apparaat opgeslagen (alleen Kodi)**.  
**Kijk Later** bevat afleveringen en films, terwijl **Mijn Series** hele series volgt — elk item toont de bijpassende actie in het contextmenu.  
Zowel Kijk Later als Mijn Series kunnen optioneel **tweerichtings synchroniseren met je NLZiet-account** (Instellingen → Synchronisatie) via de cloud-watchlist en tracked-series-lijst, inclusief handmatige acties **Sync Watch Later now** / **Sync My Series now**. Een optionele automatische synchronisatie draait op de achtergrond; het resultaat kan als melding getoond worden (instelling "Melding tonen na automatische synchronisatie"). Die melding verschijnt alleen als er iets gewijzigd is en nooit tijdens afspelen.  
- **Profielbeheer**: Schakel tussen gebruikersprofielen vanuit de Kodi-UI.  
- **Lokalisatie**: Alle gebruikerstekst wordt opgelost via Kodi's taalsysteem (Nederlands en Engels inbegrepen); Engels is de fallback voor talen zonder vertaalbestand.  
- **DRM-ondersteuning**: Widevine-beschermde streams via `inputstream.adaptive` met automatische `inputstreamhelper`-verificatie.  
- **Placement Rows**: Home-schermrijen spiegelen de officiële NLZiet-app (bijv. "Aanbevolen", "Populaire series").  
- **Afleveringsnummering**: Nauwkeurige SxxExx- en Nederlandse soap (Afl.  
N)-parsing, met seizoensmapping.  
**Kijk Later** toont daarnaast het afleveringsnummer en de resterende beschikbaarheid als compacte, subtiel gekleurde regels in de itembeschrijving.  
- **Zoeken**: Vind series, films en afleveringen op titel.  
- **Trakt Scrobbling**: Films en afleveringen tonen afspeelmetadata aan de officiële Kodi `script.trakt`-add-on, met film titel/jaar-resolutie, benoemde-aflevering-matching, herstel van gecachte URL's en expliciete live-TV-uitsluiting.  
De Trakt-add-on moet apart worden geïnstalleerd en geautoriseerd.  
- **Robuuste Handshake**: Automatische manifest/license-extractie en fallback-logica.  
- **Schone ondertitels**: NPO's teletekst-afgeleide ondertitels worden vóór afspelen opgeschoond, zodat Kodi zijn normale ondertiteloverlay toont in plaats van het teletekst-paginanummer ("888") en gele/witte teletekstkleuren.  
- **Zoekgeschiedenis**: recente zoekopdrachten kunnen worden hergebruikt of selectief verwijderd.  
- **Nieuwe-aflevering-tracking**: Mijn Series markeert series met nieuwe afleveringen, en Kijk Later kan alleen afleveringen volgen die vanaf nu worden uitgezonden.  
- **Responsieve navigatie**: achtergrond-sync en onderhoud blokkeert geen menunavigatie of terugkeer vanaf afspelen.  
- **Debug Logging**: Eenvoudige logverzameling voor probleemoplossing.  

Zie de [Changelog](CHANGELOG.md) of [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases) voor de volledige versiegeschiedenis.  

---

## 🚀 Installatie

1. Download de nieuwste release van [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases), of installeer via de [Kodi repository](https://github.com/Nigel1992/kodi-repository) (aanbevolen voor automatische updates).  
2. In Kodi: **Add-ons > Install from zip file** en selecteer de gedownloade zip.  
3. Open de add-on en gebruik **Inloggen** om je te authenticeren bij NLZiet.  
4. Installeer en autoriseer de officiële Kodi **Trakt**-add-on als je film- en aflevering-scrobbling wilt.  
5. Installeer `inputstream.adaptive` voor DRM-afspelen. De add-on verifieert het automatisch via `inputstreamhelper`.  

---

### Local Addon Check (Filtered Source)

Om addon-check lokaal te draaien zonder lokale omgeving/cache-mappen te scannen, gebruik:

```bash
scripts/run-addon-check-local.sh
```

Alleen een specifieke branch:

```bash
scripts/run-addon-check-local.sh --branch omega
```

---

## 🛣️ Roadmap / Binnenkort

- **Kids Profile Support**: Volledige kids-modus en ouderlijk toezicht.
- **Verbeterd zoeken**: Filteren op genre, jaar, releasedatum en meer.
- **Afspeelgeschiedenis-UI**: Toon Trakt-backed kijkstatus direct in NLZiet-menu's.
- **Geavanceerd sorteren**: Sorteer series op nieuwste, oudste, alfabetisch, populariteit.
- **UI Polish**: Verbeterde skin-integratie, aangepaste infodialogen en animaties.
- **Geautomatiseerd testen**: CI/CD-pipeline voor codekwaliteit en geautomatiseerde releases.

---

## 📝 To-Do

- [X] **Fix issue waarbij maar 50 films/series worden getoond** (paginering/limit-afhandeling)
- [X] **Afleveringen gebruiken afleveringstitel in plaats van telling** (toon SxxExx of Afl. N indien mogelijk)
- [X] **Fix submappen in series-optie** (betere seizoen/aflevering-navigatie)
- [ ] **Verbeter foutmeldingen en gebruikersfeedback**
- [ ] **Betere artwork en fanart voor alle content**
- [X] **Instellingen: aangepast API-endpoint toestaan voor gevorderde gebruikers**
- [ ] **Meer debug- en diagnostische tools toevoegen**
- [ ] **Toegankelijkheidsverbeteringen voor schermlezers**
- [X] **Unit tests voor routing, afspeelmetadata en Trakt scrobbling**

## 💖 Steun het project

Alle donaties gaan naar een door jou gekozen goed doel. Je kunt elk goed doel kiezen, en 5% wordt ingehouden vanwege Ko-Fi-kosten. Als dank wordt je naam vermeld als supporter/donor in een GitHub-project. Stuur gerust een e-mail naar thedjskywalker@gmail.com voor bewijs! :)

[![Ko-Fi](https://img.shields.io/badge/Ko--Fi-Support%20me-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/nigel1992)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?hosted_button_id=KYV9ARF99ZSCE)

---

## 🤝 Bijdragen

Pull requests, bugrapporten en featuresuggesties zijn welkom. Open een issue of pull request in deze repository.

---

## 📄 Licentie

MIT. Zie [LICENSE](LICENSE).

---

## ⚠️ Disclaimer

Dit project is niet gelieerd aan of onderschreven door NLZiet. Gebruik op eigen risico. Alleen voor persoonlijk, niet-commercieel gebruik.

</details>
