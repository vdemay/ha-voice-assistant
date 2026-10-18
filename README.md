# HA Voice Assistant

Documentation for building a voice assistant on a dedicated Raspberry Pi that controls a **separate** Home Assistant instance running on another Pi.

The voice-assistant Pi does not run Home Assistant itself. It runs [linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant), which does on-device wake word detection and audio capture/playback, and talks to Home Assistant over its ESPHome-compatible API. All speech-to-text, intent processing, and entity control happen in Home Assistant.

## Architecture

```
+---------------------+     network (local LAN)          +--------------------------+
|  Voice Assistant Pi |  mic audio / ESPHome API:6053    |   Home Assistant Pi      |
|                     | ----------------------------->   |                          |
|  - Microphone (USB) |                                 |  - Assist pipeline       |
|  - Speaker (HAT/USB) |  <----------------------------- |  - Speech-to-Text        |
|  - Wake word (local) |        TTS audio reply          |  - Intent recognition    |
|  - LED/button (opt.) |                                 |  - Text-to-Speech        |
+---------------------+                                 |  - Zigbee/Z-Wave/etc.    |
                                                        +--------------------------+
```

**Voice Assistant Pi** — audio capture/playback and wake word detection only. Low CPU requirements; a Pi Zero 2 W or Pi 3 is enough.

**Home Assistant Pi** — runs Home Assistant (OS or Container) with the Assist pipeline and add-ons: Whisper (STT), Piper (TTS), and an intent engine (built-in Assist or LLM-based like Home LLM/Ollama).

## Hardware

### Voice Assistant Pi

| Component | Notes |
|-----------|-------|
| Raspberry Pi (Zero 2 W / 3 / 4) | The satellite does little processing — any model works |
| USB microphone | Input — see [sound cards](doc/sound_cards/README.md) |
| ReSpeaker 2-Mic HAT | Output (speaker jack) — see [sound cards](doc/sound_cards/README.md) |
| microSD card | 8 GB minimum |
| (optional) LED + button | Status/ mute control, e.g. via GPIO |

### Home Assistant Pi

| Component | Notes |
|-----------|-------|
| Raspberry Pi 4 / 5 | STT and intent processing are the heavy parts; 4 GB RAM minimum |
| microSD card | 32 GB minimum, or SSD via USB for better Whisper performance |
| (existing) radio | Zigbee/Z-Wave stick if you already have one — no change needed |

Start with **[SETUP.md](SETUP.md)** for the full tutorial:

1. **[Sound cards](doc/sound_cards/README.md)** — configure the USB mic and ReSpeaker HAT under PipeWire, set them as defaults.
2. **[Software installation](doc/linux_voice_assistant/README.md)** — install and run [linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant) on the Pi, then **[connect it to Home Assistant](doc/linux_voice_assistant/home-assistant.md)**.
3. **[HAT LEDs](doc/leds/README.md)** — drive the ReSpeaker 2-Mic HAT's 3 APA102 LEDs from the LVA peripheral WebSocket API with [`src/script/led_ws.py`](src/script/led_ws.py).

Also in this repo:

- **[doc/open_wake_word/tutorial.md](doc/open_wake_word/tutorial.md)** — training a custom wake word ("michel", model in [`oww/michel`](oww/michel)).
- **`local/`** — private setup notes (IPs, SSH), git-ignored.

## Network requirements

- Both Pis must be on the same LAN, or connected via a routable VPN (e.g. Tailscale/WireGuard).
- Home Assistant must reach the voice Pi's ESPHome API on TCP port `6053` (default).
- mDNS/Avahi must not be blocked if you rely on `.local` hostnames and automatic discovery.

## Status

- [x] Hardware chosen
- [ ] Voice assistant Pi built and running
- [ ] Home Assistant Assist pipeline configured
- [ ] Satellite connected and responding
- [ ] Wake word reliable at typical distance
- [ ] Response latency acceptable (target: < 2 s end-to-end)
- [ ] Documentation complete

## References

- [linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant)
- [Home Assistant Voice](https://www.home-assistant.io/voice_control/)
- [Whisper add-on (STT)](https://www.home-assistant.io/integrations/whisper/)
- [Piper add-on (TTS)](https://www.home-assistant.io/integrations/piper/)
