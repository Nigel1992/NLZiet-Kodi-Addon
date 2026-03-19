<div align="center">

<img src="https://raw.githubusercontent.com/Nigel1992/NLZiet-Kodi-Addon/master/icon.png" width="120" alt="NLZiet Kodi Addon Logo"/>

# <span style="color:#E60000;">NLZiet Kodi Addon</span>

[![GitHub stars](https://img.shields.io/github/stars/Nigel1992/NLZiet-Kodi-Addon?style=social)](https://github.com/Nigel1992/NLZiet-Kodi-Addon)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)

<sub><sup>Unofficial NLZiet Kodi Addon &mdash; Watch live TV, series, movies, and more from NLZiet directly in Kodi. Supports profiles, DRM, and a modern UI.</sup></sub>

</div>

---

## 💬 Community

Join our friendly Discord to discuss the add-on, get help, suggest features, and meet other users — everyone is welcome. Click below to join:

[Join our Discord](https://discord.gg/GHAxWChXpn)

---

> ⚠️ **Warning:** This add-on is under constant development. Some features may be broken or incomplete. Please see the To-Do section below for known issues and planned improvements. Use at your own risk and check back for frequent updates!
>
> 🚧 **Known Limitations:**
> - **Search**: implemented for Series and Movies (v0.0.2). Episodes and edge cases may still require improvements.
> - **Categories for movies and series** will be added in a future update.
> - **Full EPG guide** and advanced TV features are planned but not yet available.

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

---

## 🖼️ Screenshots

<p align="center">
  <img src="docs/screenshot_main.png" width="400" alt="Main Menu"/>
  <img src="docs/screenshot_series.png" width="400" alt="Series View"/>
</p>

---

## 🚀 Installation

Quick install (recommended)

1. Download the latest release from [GitHub Releases](https://github.com/Nigel1992/NLZiet-Kodi-Addon/releases).
2. If this is a third-party add-on for you, enable installation from unknown sources: go to Settings → System → Add-ons and enable **Unknown sources**.
3. In Kodi, go to **Add-ons > Install from zip file** and select the downloaded ZIP to install the add-on.
4. Open the NLZiet add-on, go to its Settings, enter your NLZiet credentials and press **Login** from the main menu.

Enable DRM playback (InputStream Adaptive + Widevine)

1. Enable InputStream Adaptive
  - Go to **Add-ons > My add-ons > VideoPlayer InputStream**.
  - Select **InputStream Adaptive**. If it is not installed, install it from the Kodi Add-on Repository.
  - Click **Enable** (or **Open**) so Kodi can use it for adaptive DRM streams.

2. Install Widevine CDM (use InputStream Helper — recommended)
  - Install **InputStream Helper**: go to **Add-ons > Install from repository > Kodi Add-on Repository > Program add-ons > InputStream Helper** and install it.
  - Open **InputStream Helper** (Add-ons > Program add-ons > InputStream Helper) and choose **Install/Update Widevine CDM**.
  - Follow the on-screen prompts. InputStream Helper will download the correct Widevine CDM for your device and install it in the right location for Kodi.
  - Reboot Kodi after installation if prompted.

3. Test playback
  - Play a DRM-protected title from NLZiet. The add-on will automatically use `inputstream.adaptive` and Widevine for playback when available.

Notes & troubleshooting
- Widevine availability depends on your device and OS. InputStream Helper will report if Widevine cannot be installed for your platform.
- If playback fails, enable debug logging (Settings → System → Logging), reproduce the issue, and check the Kodi log for lines mentioning `inputstream.adaptive` or `widevine`.
- InputStream Helper also shows the path where the CDM was installed; use that information if you need to perform an advanced/manual install.
- For headless or minimal systems (LibreELEC/CoreELEC), prefer InputStream Helper or consult your distribution's wiki for device-specific Widevine instructions.

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

- [ ] **Fix issue where only 50 movies/series are shown** (pagination/limit handling)
- [ ] **Episodes use episode title instead of count** (show SxxExx or Afl. N when possible)
- [ ] **Fix subfolders in series option** (better season/episode navigation)
- [ ] **Improve error messages and user feedback**
- [ ] **Add Dutch/English language toggle**
- [ ] **Better artwork and fanart for all content**
- [ ] **Settings: allow custom API endpoint for advanced users**
- [ ] **Add more debug and diagnostic tools**
- [ ] **Accessibility improvements for screen readers**
- [ ] **Add more unit/integration tests**

---

## 🤝 Contributing

Pull requests, bug reports, and feature suggestions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📄 License

Creative Commons Attribution-NonCommercial 4.0 International. See [LICENSE](LICENSE).

---

## ⚠️ Disclaimer

This project is not affiliated with or endorsed by NLZiet. Use at your own risk. For personal, non-commercial use only.
