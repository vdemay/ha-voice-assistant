# Setup Tutorial

Complete setup for the voice assistant satellite Pi (the Home Assistant Pi is assumed to be already running on a separate machine).

**Step 1 — Sound cards** → [doc/sound_cards](doc/sound_cards/README.md)

Configure the USB microphone (input) and the ReSpeaker 2-Mic HAT (output) under PipeWire, and set both as the **default** source and sink. The assistant relies on the system defaults for audio.

**Step 2 — Software installation** → [doc/linux_voice_assistant](doc/linux_voice_assistant/README.md)

Install the [OHF-Voice linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant) on the Pi, run it as `python3 -m linux_voice_assistant --name "Michel"`, and connect it to Home Assistant → [doc/linux_voice_assistant/home-assistant.md](doc/linux_voice_assistant/home-assistant.md)

**Step 3 — LEDs on the sound HAT** → [doc/leds](doc/leds/README.md)

Drive the 3 APA102 LEDs of the ReSpeaker 2-Mic HAT from a custom Python script ([`src/script/led_ws.py`](src/script/led_ws.py)) connected to LVA's peripheral WebSocket API (`ws://localhost:6055`), with Google-Home-style light patterns for wake/listen/think/speak.

## Summary

```
Step 1: sound cards configured + set as defaults
Step 2: linux-voice-assistant installed and running, connected to Home Assistant
Step 3: HAT LEDs react to assistant events
Final:  assistant discovered by Home Assistant, responds to the wake word, LEDs show its state
```

Local, non-public details (IPs, SSH access) live in `local/` — that folder is git-ignored.
