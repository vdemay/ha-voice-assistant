# Linux Voice Assistant — Installation and Run

How to run the [OHF-Voice linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant) (LVA) on the voice assistant Raspberry Pi, bare metal (no Docker). LVA is a voice satellite for Home Assistant: it does on-device wake word detection and audio capture/playback, and exposes an ESPHome-compatible API that Home Assistant connects to.

Prerequisites:

- **Step 1 done**: sound cards configured and set as [default input/output](../sound_cards/README.md) — LVA autodetects audio devices and uses the PulseAudio/PipeWire defaults.
- Python 3.11 or later (`python3 --version`).
- A user that also runs the PipeWire session (same user, so LVA can reach the audio socket).

## 1. Install system packages

```bash
sudo apt update
sudo apt-get install \
  avahi-utils \
  pulseaudio-utils \
  alsa-utils \
  pipewire-bin \
  pipewire-alsa \
  pipewire-pulse \
  build-essential \
  libmpv-dev \
  libasound2-plugins \
  ca-certificates \
  iproute2 \
  procps \
  git \
  jq \
  curl \
  wget \
  vim \
  python3-venv \
  python3-dev
```

Optionally add your user to the `audio` group:

```bash
sudo usermod -a -G audio $USER
```

## 2. Clone and install

```bash
cd ~
git clone https://github.com/OHF-Voice/linux-voice-assistant.git
cd linux-voice-assistant
chmod +x docker-entrypoint.sh
script/setup
```

`script/setup` creates a Python virtual environment (`.venv/`) and installs the dependencies. On low-power hardware the build can be slow; the script accepts custom flags if needed:

```bash
script/setup --cxxflags="-O1 -g0" --makeflags="-j1"
```

## 3. Run

Activate the venv and start the assistant from the repository root:

```bash
cd ~/linux-voice-assistant
source .venv/bin/activate
python3 -m linux_voice_assistant --name "Michel"
```

- `--name "Michel"` is the device name Home Assistant will show.
- Audio input and output devices are autodetected from the system defaults — make sure the USB mic is the default **source** and the ReSpeaker is the default **sink** (see [sound cards](../sound_cards/README.md)).
- To list the devices LVA sees: `python3 -m linux_voice_assistant --list-input-devices` / `--list-output-devices`.
- Add `--debug` for verbose logging while testing.

Useful options (full list in the [upstream README](https://github.com/OHF-Voice/linux-voice-assistant#parameter-overview)):

| Option | Description |
|--------|-------------|
| `--wake-model <id>` | Wake word model (default `okay_nabu`) |
| `--wake-word-dir <dir>` | Extra directory with wake word models and configs |
| `--mic-auto-gain` / `--mic-noise-suppression` | WebRTC mic processing |
| `--listen-during-wake-sound` | Listen while the wake sound plays (say the command in one breath) |

### Custom wake word (openWakeWord)

A custom-trained openWakeWord model ("michel") lives in [`oww/michel`](../../oww/michel) — see the [training tutorial](../open_wake_word/tutorial.md). To use custom wake word models, pass the directory containing the model and its JSON config:

```bash
python3 -m linux_voice_assistant --name "Michel" --wake-word-dir /path/to/wakewords
```

The wake word can also be switched at runtime from the Home Assistant device page.

## 4. Autostart with systemd

To have the assistant start on boot, create a service (adjust the user and paths to your setup):

```bash
sudo systemctl edit --force --full linux-voice-assistant.service
```

```ini
[Unit]
Description=Linux-Voice-Assistant
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=doume
WorkingDirectory=/home/doume/linux-voice-assistant
Environment=PATH=/home/doume/linux-voice-assistant/.venv/bin:/usr/bin:/bin
Environment=PULSE_SERVER=/run/user/1000/pulse/native
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=PREFERENCES_FILE=/home/doume/linux-voice-assistant/preferences.json
ExecStart=/home/doume/linux-voice-assistant/docker-entrypoint.sh --name "Michel"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now linux-voice-assistant
sudo systemctl status linux-voice-assistant
```

Replace `1000` with your user's UID (`id -u`) if different. LVA must run as the same user as the PipeWire session, otherwise it cannot reach the audio socket.

## Next step

Connect the running assistant to Home Assistant: [home-assistant.md](home-assistant.md)
