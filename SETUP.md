# Setup Tutorial

Complete setup for the voice assistant satellite Pi (the Home Assistant Pi is assumed to be already running on a separate machine).

**Step 1 — Sound cards** → [doc/sound_cards](doc/sound_cards/README.md)

Configure the USB microphone (input) and the ReSpeaker 2-Mic HAT (output) under PipeWire, and set both as the **default** source and sink. The assistant relies on the system defaults for audio.

**Step 2 — Software installation** → [doc/linux_voice_assistant](doc/linux_voice_assistant/README.md)

Install the [OHF-Voice linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant) on the Pi, run it as `python3 -m linux_voice_assistant --name "Michel"`, and connect it to Home Assistant → [doc/linux_voice_assistant/home-assistant.md](doc/linux_voice_assistant/home-assistant.md)

## Summary

```
Step 1: sound cards configured + set as defaults
Step 2: linux-voice-assistant installed and running
Final:  assistant discovered by Home Assistant, responds to the wake word
```

Local, non-public details (IPs, SSH access) live in `local/` — that folder is git-ignored.
