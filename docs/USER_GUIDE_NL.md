# NLZiet Kodi Addon — Gebruikershandleiding

> Eenvoudige taal. Alles wat je moet weten om de add-on te gebruiken.

**Versie:** 2.0.0 · [Changelog](../CHANGELOG.md) · [Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases)

---

## 📥 Installeren

### Optie A — via de Kodi repository (aanbevolen, automatische updates)

**Via een URL (geen handmatige download):**

1. In Kodi: **Instellingen → Bestandsbeheer → Bron toevoegen** → voer `https://nigel1992.github.io/kodi-repository/` in → geef een naam (bijv. "Nigel1992") → OK.
2. **Add-ons → Installeer vanuit zip-bestand** → selecteer de toegevoegde bron → `repository.nigel1992-*.zip`.
3. **Add-ons → Installeer vanuit repository → Nigel1992 Kodi Repository → Video add-ons → NLZiet → Installeer**.
4. Kodi houdt de add-on daarna automatisch up-to-date.

**Of download de repo-zip direct** van de [Kodi repository releases](https://github.com/Nigel1992/kodi-repository/releases/latest) en installeer via **Add-ons → Installeer vanuit zip-bestand** (schakel eerst "Onbekende bronnen" in indien gevraagd).

### Optie B — handmatige zip (geen automatische updates)

1. Download de nieuwste release-zip van [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).
2. In Kodi: **Add-ons → Installeer vanuit zip-bestand** → selecteer de zip.

### Na installatie (beide opties)

3. Open de add-on en log in met je NLZiet-account (knop **Inloggen**).
4. Installeer `inputstream.adaptive` (voor DRM-afspelen) — de add-on controleert dit automatisch.
5. (Optioneel) Installeer en autoriseer de officiële Kodi **Trakt**-add-on voor scrobbling.

Na het opstarten configureert de add-on zichzelf: bibliotheekmappen, content-type en scan. Je hoeft niets handmatig in te stellen.

---

## 📺 Live TV kijken

- Open de add-on → **Live TV** (of **TV Gids**).
- Je ziet alle zenders met de huidige en komende programma's (7 dagen vooruit).
- Klik op een programma om te kijken. Afspelen start via `inputstream.adaptive` (DRM).
- **EPG-herinnering**: zet in de TV Gids een herinnering voor een toekomstig programma; je krijgt een melding vlak voor de start.
- **Favoriete kanalen**: markeer kanalen als favoriet; die komen vooraan te staan.

## 📺 Series

- **Bladeren**: open **Series** → kies een categorie of genre.
- **Zoeken**: typ een titel; resultaten kunnen gefilterd worden op periode en genre.
- **Aflevering afspelen**: klik op een aflevering. De add-on onthoudt waar je gebleven bent.
- **Verder kijken**: op het startscherm staat een widget "Verder kijken" met series die je bezig bent.
- **Hele serie als bekeken markeren**: contextmenu → "Hele serie als bekeken markeren".

## 🎬 Films

- **Bladeren**: open **Films** → kies een categorie of genre.
- **Zoeken**: typ een titel.
- **Afspelen**: klik op een film. Resume-positie wordt onthouden.

## ⏸️ Afspelen — extra functies

- **Up Next / Volgende aflevering**: bij het einde van een aflevering kun je automatisch of met een knop de volgende starten (instelling: Up Next / eigen prompt / automatisch / uit).
- **Intro/recap overslaan**: op basis van hoofdstukken (als NLZiet ze levert) verschijnt een "Overslaan"-knop.
- **Binge-modus**: automatisch door naar de volgende aflevering.
- **Stop na deze aflevering**: zet een vlag zodat er niet verder wordt gegaan.
- **Shuffle**: willekeurige aflevering van een serie.
- **Vaste taal/ondertitels**: stel je voorkeur in; wordt automatisch toegepast. Optioneel opent Kodi's ondertitelzoeker als de stream er geen heeft.
- **Resume (verder kijken)**: positie wordt lokaal opgeslagen en gesynchroniseerd met NLZiet (zodat je op telefoon/tablet verder kunt kijken).

## 📋 Lijsten

### Kijk Later (Watch Later)
- Afleveringen en films die je wilt bewaren.
- Toevoegen: contextmenu → "Toevoegen aan Kijk Later".
- Synchroniseert tweerichtings met je NLZiet-account (Instellingen → Synchronisatie).
- Widget op het startscherm.

### Mijn Series (My Series)
- Volg hele series. Elke serie toont of er nieuwe afleveringen zijn.
- Toevoegen: contextmenu → "Toevoegen aan Mijn Series".
- Synchroniseert met je NLZiet-account.

### Mijn Lijst (My List)
- Verwijderd in v2.0.0; bestaande items zijn gemigreerd naar **Kijk Later**.

## 📚 Kodi-bibliotheek (automatisch)

De add-on schrijft series en films als `.strm` + `.nfo` naar een map in je Kodi-profiel. Vanaf v2.0.0 gebeurt dit **volledig automatisch**:

- **Bronnen**: de mappen worden automatisch als videobron in Kodi geregistreerd (sources.xml + content-type + scraper "Lokale informatie").
- **Scan**: Kodi scant de mappen automatisch; series verschijnen onder **Video's → Series**, films onder **Video's → Films**.
- **Updates**: nieuwe afleveringen worden automatisch toegevoegd, verlopen afleveringen verwijderd (standaard elke 12 uur).
- **Metadata**: ontbrekende gegevens (beschrijving, plaatjes, genres, titels) worden aangevuld via TMDb (gratis API-sleutel, optioneel) en TVmaze. NLZiet's eigen gegevens gaan altijd voor.
- **Seizoensposters en logo's** (clearlogo) worden ook in de bladerlijsten getoond.

### Handmatig toevoegen
- Contextmenu op een serie/film → "Toevoegen aan bibliotheek".

### Bulk-actie
- Instellingen → Bibliotheek → "Mijn series en Kijk later nu naar de bibliotheek" (of automatisch via de instelling "Mijn series en Kijk later automatisch in de bibliotheek").

### Trakt-kijklijst importeren
- Instellingen → Bibliotheek → "Trakt-kijklijst importeren": matcht titels op NLZiet en voegt ze toe.

## 🔒 Ouderlijk toezicht

- Stel een pincode in per profiel (Instellingen → Ouderlijk toezicht).
- Kies welke profielen vergrendeld zijn.
- Optioneel: pincode voor live tv.
- Kinderprofielen worden gemarkeerd.

## 📊 Trakt-integratie

- **Bekeken-status tonen**: in menu's zie je of een titel op Trakt als bekeken is gemarkeerd.
- **Live scrobbling**: tijdens het kijken wordt de voortgang naar Trakt gestuurd.
- **Watchlist importeren**: je Trakt-kijklijst importeren naar de bibliotheek.
- Vereist de officiële Kodi `script.trakt` add-on (geïnstalleerd en geautoriseerd).

## 💾 Backup en herstel

- Instellingen → Bibliotheek → Backup/Herstel: sla je lijsten en instellingen op en herstel ze later.

## 🔍 Zoeken

- Zoek op titel (series, films, afleveringen).
- Filter resultaten op periode en genre.
- "Zoekopdracht ook in Videoland aanbieden" — dezelfde zoekterm in de Videoland-add-on.

## 🩺 Diagnose en betrouwbaarheid

- **Diagnosescherm**: Instellingen → Bibliotheek → Onderhoud → "Diagnose uitvoeren".
  - Toont inlogstatus, InputStream/Widevine, verbindingen, TMDb-sleutel, bibliotheekbronnen, Kodi-vs-bibliotheek aantallen.
  - Privacy-vriendelijk rapport opslaan.
- **Dagelijkse achtergrondcontrole**: melding bij problemen.
- **Duidelijke foutmeldingen**: bij offline, timeout, sessie verlopen, geen abonnement, niet gevonden, druk, storing — één duidelijke zin, details in het logboek.
- **Toegankelijkheid**: tekst in plaats van emoji/kleur-only markers, statuswoorden in diagnose.

## ⚙️ Belangrijke instellingen

| Instelling | Waar | Uitleg |
|---|---|---|
| Kijkstatus naar NLZiet sturen | Afspelen | Stuurt bekeken-status terug naar NLZiet |
| Percentage bekeken | Afspelen | Wanneer een video als "bekeken" telt |
| Volgende aflevering | Afspelen | Up Next / eigen prompt / automatisch / uit |
| Binge-modus | Afspelen | Automatisch door naar volgende aflevering |
| Vaste taal/ondertitels | Afspelen | Voorkeur voor gesproken taal en ondertitels |
| Mijn series en Kijk later automatisch in de bibliotheek | Bibliotheek | Automatisch toevoegen (standaard aan) |
| Titels die uit deze lijsten verdwijnen ook verwijderen | Bibliotheek | Opruimen bij veranderingen |
| Bibliotheek automatisch bijwerken | Bibliotheek | Interval in uren |
| TMDb API-sleutel | Bibliotheek → Metadata | Gratis sleutel voor extra metadata/plaatjes |
| Ouderlijk toezicht | Ouderlijk toezicht | Pincode/profielslot |
| Backup/Herstel | Bibliotheek → Onderhoud | Lijsten en instellingen opslaan/herstellen |
| Melding bij achtergrond-synchronisatie | Synchronisatie | Alleen als er iets gewijzigd is |

## 🐛 Problemen?

- **Diagnose-rapport**: Instellingen → Bibliotheek → Onderhoud → Diagnose uitvoeren → Rapport opslaan.
- **Issues**: https://github.com/Nigel1992/NLZiet-Kodi-Addon/issues
- **Discord**: https://discord.gg/9F2NZuydXT

## 📄 Licentie

MIT. Zie [LICENSE](LICENSE).

---

## 🙏 Dankwoord

- **[@djdirty](https://github.com/djdirty60) (Wilfried)** — auteur van pull request #48, die de Kodi-bibliotheek, afspeelfuncties, widgets, diagnose, ouderlijk toezicht, Trakt-integratie, backup/herstel en nog veel meer bracht, plus Nederlandse/Engelse vertalingen en ~299 unit-tests. Enorm bedankt! 🙏
- Icons: Lucide (https://lucide.dev)

## ⚠️ Disclaimer

Dit project is niet gelieerd aan of onderschreven door NLZiet. Gebruik op eigen risico. Alleen voor persoonlijk, niet-commercieel gebruik.
```