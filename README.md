# KEF Wireless Speakers Integration for Unfolded Circle Remote 2/3

Control your **KEF LS50 Wireless** and **KEF LSX** speakers directly from your Unfolded Circle Remote 2 or Remote 3. Power, volume, mute, play/pause, track skipping, source switching, auto-standby, speaker orientation and the full set of DSP / EQ settings - controlled **entirely locally** over your network with **no KEF account or cloud login** required.

![KEF](https://img.shields.io/badge/KEF-LS50%20Wireless%20%7C%20LSX-B40000)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-kef-speakers?style=flat-square)](https://github.com/mase1981/uc-intg-kef-speakers/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-kef-speakers?style=flat-square)](https://github.com/mase1981/uc-intg-kef-speakers/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-kef-speakers/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

## Supported Devices

| Model | Sources |
|-------|---------|
| **KEF LSX** (first generation) | Wi-Fi, Bluetooth, Aux, Optical |
| **KEF LS50 Wireless** (first generation) | Wi-Fi, Bluetooth, Aux, Optical, USB |

These speakers are controlled over their local TCP control port (50001) - the same protocol used by the Home Assistant `kef` integration. Newer models (LS50 Wireless II, LSX II, LS60) use a different HTTP API and are **not** supported by this integration.

## Features

- **🔊 Media player** - power on/off, set volume, volume up/down, mute/unmute, play/pause, next/previous (Wi-Fi and Bluetooth) and source selection, as a speaker media player.
- **🎛️ Full remote entity** - all functions as simple commands for Activities: power, volume, mute, transport, every source, and auto-standby time, with physical button mapping and ready-made button pages.
- **🎚️ DSP switches** - Desk Mode, Wall Mode, Phase Correction and High-Pass Mode.
- **🎵 DSP selectors** - Bass Extension (Less / Standard / Extra), Sub Polarity (+ / -), Desk Mode dB, Wall Mode dB, Treble dB, High-Pass Hz, Sub Out Low-Pass Hz and Sub Gain dB.
- **⏻ Speaker settings** - Auto Standby (20 min / 60 min / Never) and Speaker Orientation (L/R or R/L) selectors.
- **ℹ️ Info sensors** - model, power, current source and raw volume.
- **🔈 Volume limit** - optional maximum volume; the Remote's 0-100 slider is scaled to that limit.
- **🔒 Fully local** - direct LAN control, no KEF account and no cloud in the loop.
- **Multi-device** - add each KEF speaker pair on your network.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

## How It Works

KEF LS50 Wireless and LSX speakers expose a small binary control protocol on TCP port 50001. This integration speaks that protocol directly:

- **No account, no cloud** - control runs entirely over your local network.
- **State follows the speaker** - power, source, volume and mute are polled every 10 seconds; DSP settings are refreshed every minute and right after you change them.
- **Settings are preserved** - power and source commands keep the speaker's current auto-standby time and L/R orientation (they are read from the speaker before every change).

> The speaker accepts only **one controller connection at a time**. The integration connects only for the moment it sends a command and disconnects again after one second, so it can co-exist with the KEF app - but if the KEF app keeps the connection open, commands may be delayed.

> The **LS50 Wireless** only reports its DSP settings while it is switched on; the LSX also reports them in standby.

## Requirements

- A KEF LS50 Wireless or KEF LSX speaker on the same network as your Remote.
- A fixed IP address / DHCP reservation for the speaker (recommended).
- Unfolded Circle Remote 2 / 3 with firmware supporting custom integrations.

## Installation

### Option 1: Remote Web Interface (Recommended)

1. Download the latest `uc-intg-kef_speakers-<version>-aarch64.tar.gz` from the [**Releases**](https://github.com/mase1981/uc-intg-kef-speakers/releases) page.
2. Open your Remote's web interface (`http://your-remote-ip`).
3. Go to **Settings -> Integrations -> Add Integration -> Install Custom** and upload the `.tar.gz`.

### Option 2: Docker (Advanced Users)

**Image**: `ghcr.io/mase1981/uc-intg-kef-speakers:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-kef-speakers:
    image: ghcr.io/mase1981/uc-intg-kef-speakers:latest
    container_name: uc-intg-kef-speakers
    network_mode: host
    volumes:
      - ./config:/config
    environment:
      - UC_CONFIG_HOME=/config
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-intg-kef-speakers --restart unless-stopped --network host -v $(pwd)/config:/config -e UC_CONFIG_HOME=/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-kef-speakers:latest
```

## Configuration

1. Make sure your KEF speaker is powered and on the same network as the Remote.
2. Start setup and enter:
   - **IP Address** of the primary speaker.
   - **Speaker Model** - KEF LSX or KEF LS50 Wireless (determines the source list).
   - **Name** (optional).
   - **Maximum Volume (%)** - the highest volume the integration will set (default 100).
   - **Volume Step (%)** - change per volume up/down press (default 5).
   - **Allow power on** - untick if your speaker cannot be woken over the network.
3. Repeat setup to add additional speakers.

For each speaker the integration creates:

| Entity | Purpose |
|--------|---------|
| **Media player** (`<name>`) | Power, volume, mute, play/pause, next/previous, source selection. |
| **Remote** (`<name> Remote`) | Full command set for Activities, with button mapping and button pages. |
| **Switches** | Desk Mode, Wall Mode, Phase Correction, High-Pass Mode. |
| **Selects** | Bass Extension, Sub Polarity, Auto Standby, Speaker Orientation, Desk/Wall/Treble dB, High-Pass Hz, Sub Out Low-Pass Hz, Sub Gain dB. |
| **Sensors** | Model, Power, Source, Volume. |

### Remote simple commands

`POWER_TOGGLE`, `POWER_ON`, `POWER_OFF`, `VOLUME_UP`, `VOLUME_DOWN`, `MUTE_TOGGLE`, `MUTE`, `UNMUTE`, `PLAY_PAUSE`, `NEXT`, `PREVIOUS`, `SOURCE_WIFI`, `SOURCE_BLUETOOTH`, `SOURCE_AUX`, `SOURCE_OPT`, `SOURCE_USB` (LS50 Wireless only), `STANDBY_20_MIN`, `STANDBY_60_MIN`, `STANDBY_NEVER`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Could not reach a KEF speaker" during setup | Check the IP address, make sure the speaker is powered and on the same network/subnet as the Remote, and close the KEF app. |
| Speaker shows as unavailable | The speaker is unreachable on port 50001 (unplugged or IP changed). Give it a DHCP reservation and re-run setup if the IP changed. |
| Power on does nothing | Some speakers drop off the network in deep standby. Use the auto-standby "Never" setting, or untick **Allow power on** in setup. |
| DSP switches/selects show no value | The LS50 Wireless only reports DSP settings while it is on - switch it on and wait a few seconds. |
| Play/pause or next/previous has no effect | Transport control only works on the Wi-Fi and Bluetooth sources. |

## Credits

- **Developer**: Meir Miyara
- **KEF local protocol**: based on [aiokef](https://github.com/basnijholt/aiokef) and the Home Assistant [KEF integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/kef).
- **Unfolded Circle**: Remote 2/3 integration framework ([ucapi](https://github.com/unfoldedcircle/integration-python-library) / [ucapi-framework](https://github.com/JackJPowell/ucapi-framework)).

## License

Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-kef-speakers/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
