# HA Voice Assistant

Documentation for building a voice assistant on a dedicated Raspberry Pi that controls a **separate** Home Assistant instance running on another Pi.

The voice-assistant Pi does not run Home Assistant itself. It captures audio, streams it over the network to the Home Assistant Pi, and plays back the spoken response. All intent processing and entity control happen in Home Assistant.

## Architecture

```
+---------------------+        network (local LAN)       +--------------------------+
|  Voice Assistant Pi |  mic audio / Wyoming protocol   |   Home Assistant Pi      |
|                     | ----------------------------->   |                          |
|  - Microphone (USB) |                                 |  - Assist pipeline       |
|  - Speaker (jack/USB)|  <----------------------------- |  - Speech-to-Text (STT)  |
|  - Wake word         |        TTS audio reply          |  - Intent recognition    |
|  - LED/button (opt.) |                                 |  - Text-to-Speech (TTS)  |
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
| USB microphone | Or a microphone HAT (e.g. ReSpeaker 2-Mic) |
| Speaker | 3.5mm jack, USB, or HAT output |
| microSD card | 8 GB minimum |
| (optional) LED + button | Status/ mute control, e.g. via GPIO |

### Home Assistant Pi

| Component | Notes |
|-----------|-------|
| Raspberry Pi 4 / 5 | STT and intent processing are the heavy parts; 4 GB RAM minimum |
| microSD card | 32 GB minimum, or SSD via USB for better Whisper performance |
| (existing) radio | Zigbee/Z-Wave stick if you already have one — no change needed |

## Setup overview

1. **[Prepare the voice assistant Pi](docs/voice-pi-setup.md)** — flash the OS, configure audio in/out, install the satellite software.
2. **[Configure Home Assistant](docs/home-assistant-setup.md)** — enable the Assist pipeline, install Whisper and Piper add-ons, expose entities to Assist.
3. **[Connect the two](docs/network-setup.md)** — point the satellite at your Home Assistant URL, handle discovery/authentication, and open the Wyoming ports.
4. **[Tune wake word and pipeline](docs/pipeline-tuning.md)** — pick/ train a wake word, choose STT/TTS models sized for your hardware.

## Network requirements

- Both Pis must be on the same LAN, or connected via a routable VPN (e.g. Tailscale/WireGuard).
- Home Assistant must be reachable over `http://homeassistant.local:8123` (or your configured URL).
- Wyoming protocol ports (default `10400` and up, one per satellite service) must be reachable from the voice Pi.
- mDNS/Avahi must not be blocked if you rely on `.local` hostnames.

## Status

- [x] Hardware chosen
- [ ] Voice assistant Pi built and running
- [ ] Home Assistant Assist pipeline configured
- [ ] Satellite connected and responding
- [ ] Wake word reliable at typical distance
- [ ] Response latency acceptable (target: < 2 s end-to-end)
- [ ] Documentation complete

## References

- [Home Assistant Voice](https://www.home-assistant.io/voice_control/)
- [Wyoming protocol](https://www.home-assistant.io/voice_control/remote_wyoming/)
- [Whisper add-on (STT)](https://www.home-assistant.io/integrations/whisper/)
- [Piper add-on (TTS)](https://www.home-assistant.io/integrations/piper/)
