# Connecting to Home Assistant

The assistant Pi runs on a separate machine from Home Assistant. LVA exposes an ESPHome-compatible API server (default port `6053`); Home Assistant connects to it with the ESPHome integration and then treats the Pi as an [Assist satellite](https://www.home-assistant.io/voice_control/).

Prerequisites:

- LVA is [installed and running](README.md) on the voice Pi.
- The Home Assistant instance can reach the voice Pi on TCP port `6053` over the LAN (both machines on the same network, port not blocked by a firewall).
- The voice Pi's IP address (private info) is noted in `local/voice-pi.md` — this folder is git-ignored.

## 1. Prepare Home Assistant

Assist needs a working pipeline before adding the satellite:

1. **Speech-to-Text and Text-to-Speech** — install the **Whisper** (STT) and **Piper** (TTS) add-ons (or use another STT/TTS integration, e.g. Home Assistant Cloud).
2. **Pipeline** — Settings → Devices & services → **Assist**: check that the preferred pipeline processes a typed command successfully ("Respond" test).
3. **Expose entities** — Settings → Devices & services → **Assist** → Expose: select the entities you want to control by voice (lights, switches, timers, ...).

## 2. Add the satellite

1. In Home Assistant, go to **Settings → Devices & services**.
2. Click **Add integration**, choose **ESPHome**, then **Set up another instance of ESPHome**.
3. Enter the voice Pi's address with the port: `<voice-pi-ip>:6053` (find the IP in `local/voice-pi.md`; e.g. `192.168.1.67:6053`).
4. Click **Submit**. The integration connects to the LVA API server and creates the device.

The satellite may also be discovered automatically via mDNS as `Michel.local` — accepting the discovery is equivalent.

## 3. Verify

- The new ESPHome device ("Michel") appears under Settings → Devices & services → ESPHome, with entities including an **Assist satellite** entity.
- Say the wake word (default `okay_nabu`, or the custom one if configured). LVA plays the wake sound, listens, and Home Assistant runs the pipeline: STT → intent → response spoken through the ReSpeaker.
- From the device page in Home Assistant you can also:
  - change the active **wake word** at runtime,
  - run **Announce** / **Start conversation** actions,
  - use the **stop** word to interrupt a response, announcement, or timer.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Integration cannot connect | Is LVA running on the Pi? `systemctl status linux-voice-assistant` or check the foreground process. Is port 6053 reachable (`nc -zv <voice-pi-ip> 6053` from the HA machine)? |
| Wake word detected but no answer | Pipeline misconfigured — test it in Settings → Devices & services → Assist with a typed command. |
| Assistant hears itself / cuts off | Echo from the speaker into the mic; keep mic and speaker apart, lower volume, or enable `--mic-noise-suppression` and AEC. |
| Audio devices wrong | Re-check that the USB mic and ReSpeaker are still the [system defaults](../sound_cards/README.md). |
