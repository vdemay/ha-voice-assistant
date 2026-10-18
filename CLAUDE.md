# CLAUDE.md

Repository documentation for building a voice assistant on a dedicated Raspberry Pi that controls a **separate** Home Assistant instance (also on a Pi).

The satellite runs [OHF-Voice/linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant) (LVA) bare metal with on-device wake word detection, talks to Home Assistant via its ESPHome-compatible API (port 6053), and drives the ReSpeaker 2-Mic HAT LEDs through LVA's peripheral WebSocket API (port 6055).

## Repository structure

```
ha-voice-assistant/
├── SETUP.md                      # Root tutorial: Step 1 sound cards, Step 2 LVA + Home Assistant, Step 3 LEDs
├── README.md                     # Overview, architecture, hardware, network requirements
├── .gitignore                    # Ignores local/ (private info) and Python bytecode
├── doc/
│   ├── sound_cards/README.md     # Step 1: USB mic (Jieli) + ReSpeaker 2-Mic HAT under PipeWire, troubleshooting
│   ├── linux_voice_assistant/
│   │   ├── README.md             # Step 2: LVA bare-metal install, run command, systemd
│   │   └── home-assistant.md     # Step 2: connect LVA to Home Assistant (ESPHome integration, port 6053)
│   ├── leds/README.md            # Step 3: LED script setup (clone repo, venv in src/script, run, systemd)
│   └── open_wake_word/tutorial.md  # Training the custom "michel" wake word
├── src/
│   └── script/
│       ├── led_ws.py             # LED controller: listens to LVA WebSocket events, drives 3 APA102 pixels
│       └── requirements.txt     # RPi.GPIO, websockets, apa102-pi
├── oww/
│   └── michel/                   # Custom openWakeWord model files (onnx/pt/metrics)
└── local/                        # GIT-IGNORED: private local setup info (voice Pi IP, SSH access)
```

## Conventions

- All documentation, code comments, and log messages are in **English**.
- `local/` is git-ignored and never committed: it holds private info (IPs, credentials). The voice Pi's IP and SSH access are in `local/voice-pi.md`. Public docs reference `<voice-pi-ip>` instead of the real IP.
- Documentation links between files with relative paths; keep them intact when moving files.
- The LED script (`src/script/led_ws.py`) is kept verbatim from the working setup; prefer minimal edits.

## Setup summary (details in SETUP.md)

- **Sound cards**: USB conference mic (Jieli "UACDemoV1.0", input) + KEYESTUDIO ReSpeaker 2-Mic HAT (output, 3 APA102 LEDs). Both set as PipeWire defaults; the Jieli mic needs the WirePlumber override documented in `doc/sound_cards/`.
- **Software**: LVA cloned to `~/linux-voice-assistant` on the Pi, venv via `script/setup`, run with `python3 -m linux_voice_assistant --name "Michel"`; systemd service `linux-voice-assistant`.
- **Home Assistant**: ESPHome integration → `<voice-pi-ip>:6053`. Requires a working Assist pipeline (Whisper/Piper) and entities exposed to Assist.
- **LEDs**: this repo cloned on the Pi, venv in `src/script/`, run `python3 led_ws.py`; systemd service `voice-leds`. Requires SPI enabled and `liblgpio-dev swig` apt packages.

## Useful commands

```bash
# Syntax-check the LED script (clean up __pycache__ afterwards, it is git-ignored anyway)
python3 -m py_compile src/script/led_ws.py

# On the Pi: check the audio defaults
wpctl status

# On the Pi: test the LVA peripheral WebSocket
python3 src/script/led_ws.py   # prints each event name as it arrives
```
