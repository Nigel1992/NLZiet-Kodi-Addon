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
- **Kodi library**: add series and movies to the Kodi library through the context menu ("Add to library"). The addon writes `.strm` + `.nfo` files, keeps episode numbers stable, adds new episodes and removes expired ones automatically (Settings → Library), and can scan/clean the Kodi library afterwards. The **Library** menu shows everything you added. Add the TV shows and movies folders once as Kodi video sources with the scraper "Local information only". Missing details (description, artwork, genres, episode titles) are filled in from TMDb (free API key, optional) and TVmaze; NLZiet's own data always comes first.  
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

- ✅ **Parental control**: PIN for chosen profiles and optionally for live tv; kids profiles are marked (v1.8.0).  
- ✅ **Improved search**: filter results by period and genre (v1.8.0).  
- ✅ **Trakt watched status in menus**: opt-in, uses the account connected in script.trakt (v1.8.0).  
- ✅ **Sorting**: Kodi's sort menu (default order, title, year, episode) on list pages (v1.7.4).  
- ✅ **Automated testing**: GitHub Actions run the tests and build the zip; `v*` tags publish a release (v1.7.4).  
- **UI polish**: new icon set done (v1.7.3). Custom info dialogs and animations are left to the skin: Kodi's own info screen shows the data, and a custom window would look different in every skin.  

---

## 📝 To-Do

- [X] **Fix issue where only 50 movies/series are shown** (pagination/limit handling)  
- [X] **Episodes use episode title instead of count** (show SxxExx or Afl.  
N when possible)  
- [X] **Fix subfolders in series option** (better season/episode navigation)  
- [X] **Improve error messages and user feedback** (one clear sentence per problem, details in the log)  
- [X] **Better artwork and fanart for all content** (library posters/backgrounds, TMDb/TVmaze fill-in)  
- [X] **Settings: allow custom API endpoint for advanced users**  
- [X] **Add more debug and diagnostic tools** (Settings → Library → Run diagnostics)  
- [X] **Accessibility improvements for screen readers** (text instead of emoji/colour-only markers, status words in diagnostics)  
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
- **Kodi-bibliotheek**: voeg series en films toe aan de Kodi-bibliotheek via het contextmenu ("Toevoegen aan bibliotheek"). De addon schrijft `.strm`- en `.nfo`-bestanden, houdt afleveringsnummers vast, voegt nieuwe afleveringen automatisch toe en ruimt verlopen afleveringen op (Instellingen → Bibliotheek), en kan daarna de Kodi-bibliotheek scannen en opschonen. Het menu **Bibliotheek** toont alles wat je hebt toegevoegd. Voeg de mappen voor series en films één keer toe als videobron in Kodi, met de scraper "Lokale informatie". Ontbrekende gegevens (beschrijving, plaatjes, genres, afleveringstitels) worden aangevuld via TMDb (gratis API-sleutel, optioneel) en TVmaze; de gegevens van NLZiet gaan altijd voor.  
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

- ✅ **Ouderlijk toezicht**: pincode voor gekozen profielen en optioneel voor live tv; kinderprofielen worden gemarkeerd (v1.8.0).
- ✅ **Verbeterd zoeken**: resultaten filteren op periode en genre (v1.8.0).
- ✅ **Trakt-kijkstatus in de menu's**: optioneel, via het account dat in script.trakt is gekoppeld (v1.8.0).
- ✅ **Sorteren**: Kodi's sorteermenu (standaardvolgorde, titel, jaar, aflevering) in lijsten (v1.7.4).
- ✅ **Geautomatiseerd testen**: GitHub Actions draaien de tests en bouwen de zip; een `v*`-tag publiceert een release (v1.7.4).
- **UI polish**: nieuwe pictogrammen klaar (v1.7.3). Eigen infoschermen en animaties laten we aan de skin: Kodi's eigen infoscherm toont de gegevens, en een eigen venster ziet er in elke skin anders uit.

---

## 📝 To-Do

- [X] **Fix issue waarbij maar 50 films/series worden getoond** (paginering/limit-afhandeling)
- [X] **Afleveringen gebruiken afleveringstitel in plaats van telling** (toon SxxExx of Afl. N indien mogelijk)
- [X] **Fix submappen in series-optie** (betere seizoen/aflevering-navigatie)
- [X] **Verbeter foutmeldingen en gebruikersfeedback** (één duidelijke zin per probleem, details in het logboek)
- [X] **Betere artwork en fanart voor alle content** (posters en achtergronden in de bibliotheek, aanvulling via TMDb/TVmaze)
- [X] **Instellingen: aangepast API-endpoint toestaan voor gevorderde gebruikers**
- [X] **Meer debug- en diagnostische tools toevoegen** (Instellingen → Bibliotheek → Diagnose uitvoeren)
- [X] **Toegankelijkheidsverbeteringen voor schermlezers** (tekst in plaats van emoji of alleen kleur, statuswoorden in de diagnose)
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
