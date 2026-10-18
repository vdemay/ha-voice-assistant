# LEDs on the ReSpeaker 2-Mic HAT

The KEYESTUDIO ReSpeaker 2-Mic Pi HAT carries 3 APA102 RGB LEDs. [linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant) (LVA) exposes a **peripheral WebSocket API** (default `ws://localhost:6055`) that broadcasts assistant state events in real time. The script [`src/script/led_ws.py`](../../src/script/led_ws.py) connects to that API and drives the HAT LEDs with Google-Home-style patterns.

Event → LED mapping:

| LVA event | LED pattern |
|-----------|-------------|
| `wake_word_detected` | Wake-up fade-in (blue/green) |
| `listening` | Listening fade-in |
| `thinking` | Rotating "thinking" animation while Home Assistant processes |
| `tts_speaking` | Pulsing "speaking" animation |
| `idle`, `tts_finished`, `error` | LEDs off |

## Prerequisites

- Steps 1 and 2 done: sound cards working, LVA [installed and running](../linux_voice_assistant/README.md).
- LVA started **without** `--disable-peripheral-api` (the API is enabled by default on port `6055`). Since the script runs on the same Pi, it connects to `ws://localhost:6055`.
- SPI enabled on the Pi (the APA102 LEDs are on the SPI bus):

  ```bash
  sudo raspi-config   # Interface Options → SPI → enable
  sudo reboot
  ```

## Installation

### 1. System packages

```bash
sudo apt update
sudo apt install -y liblgpio-dev swig
```

### 2. Create a folder with its own virtual environment

The script runs in its own venv, separate from LVA:

```bash
mkdir -p ~/voice-leds
cd ~/voice-leds
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Copy the script and its requirements

Copy `src/script/led_ws.py` and `src/script/requirements.txt` from this repository onto the Pi (e.g. from your workstation, using the SSH access noted in `local/voice-pi.md`):

```bash
scp src/script/led_ws.py src/script/requirements.txt doume@<voice-pi-ip>:~/voice-leds/
```

### 4. Install Python dependencies

```bash
cd ~/voice-leds
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Run

Keep LVA running in another session (or via its systemd service), then:

```bash
cd ~/voice-leds
source .venv/bin/activate
python3 led_ws.py
```

Expected output:

```
Connexion à LVA…
Connecté
→ snapshot
→ wake_word_detected
→ listening
...
```

Say the wake word: the LEDs should light up, animate during listening/thinking/speaking, and turn off when the assistant goes back to idle.

If you get an SPI permission error, run the script with `sudo` or add your user to the `spi`/`gpio` groups and re-login.

## Autostart with systemd

```bash
sudo systemctl edit --force --full voice-leds.service
```

```ini
[Unit]
Description=Voice assistant LED controller (LVA peripheral API)
After=linux-voice-assistant.service network-online.target
Wants=network-online.target

[Service]
Type=simple
User=doume
WorkingDirectory=/home/doume/voice-leds
ExecStart=/home/doume/voice-leds/.venv/bin/python led_ws.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now voice-leds
sudo systemctl status voice-leds
```

## Extending the script

The [peripheral API](https://github.com/OHF-Voice/linux-voice-assistant/blob/main/docs/peripheral_api.md) emits more events than the script currently handles, e.g. `stt_text` / `tts_text` (conversation text), `pipeline_error`, `muted`, `disconnected`, `timer_ticking` / `timer_ringing` (timer countdowns), and `media_player_playing`. It also accepts commands (`start_listening`, `volume_up`, `stop_timer_ringing`, ...) — useful if you later add a hardware button to the HAT.
