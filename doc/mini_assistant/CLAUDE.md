# CLAUDE.md — EchoEar (ESP32-S3) ESPHome configs

Findings from getting the Espressif **EchoEar** voice assistant working with ESPHome
Device Builder (ESPHome 2026.10.1, HA 2026.9.2). The board here is a **V1.0/V1.1** unit.
Upstream reference: [RealDeco/xiaozhi-esphome](https://github.com/RealDeco/xiaozhi-esphome)
(`devices/Espressif/echoear1.0.yaml` and `echoear1.2.yaml`) — `ref.md` links to the repo.
Forum thread: <https://community.home-assistant.io/t/espressifs-echoear-esp32-s3-voice-controlled-ai-chatbot-runs-esp-brookesia/934573>

## Files in this folder

| File | Purpose |
|---|---|
| `echoear.yaml` | Full xiaozhi-style single-file config (display, clock, touch, timers, images). Fixed for V1.0/V1.1 pins + api key. |
| `minimum_assistant.yaml` | Minimal working assistant: mic, speaker, mww `okay_nabu`, VA, BOOT button. Plain `api:` (no key). Serial-log oriented. |
| `with_status_displayed.yaml` | `minimum_assistant.yaml` + 360x360 QSPI display showing the VA state as text. Device name `echoear-status`. Status flow (4 states): **Waiting for wake word** (boot / `on_idle` / after `on_end` waits) → **Listening...** (`on_listening`) → **Thinking...** (`on_stt_end`) → **Replying...** (`on_tts_start` and `on_announcement`, kept until playback ends) → back to idle. Errors show `Error: <code>`. |
| `with_images_displayed.yaml` | Same but the status is the **Eyes 360x360 image set** from upstream (**compile-time `image:` + `file:` URL** — the same approach as upstream `echoear.yaml`: ESPHome Builder downloads the PNGs during the build and bakes them in; no runtime HTTP. Do NOT use `online_image` here: runtime downloads from `on_boot`/`on_connect` blocked the main loop for ~35 s, TLS connections failed (`ESP_ERR_HTTP_CONNECT`), and HA disconnected. ~1.5 MB flash for 6 images — if the app is too large, set `flash_size: 32MB`.) Phase global: 0 idle / 1 listening / 2 thinking / 3 replying / 4 error / 5 loading. Device name `echoear-images`. **Touch (CST816, irq GPIO10 on `bus_a`, `display: main_display`): `on_touch` starts the assistant if idle, stops it if running** (with `set_use_wake_word(false)` + `micro_wake_word.stop` first, to free the I2S bus). |
| `cat_assistant_v1.yaml` | v1: `with_images_touch_sound.yaml` behaviors + advanced cat set (`img_base: images/advanced`, 13 images, `flash_size: 32MB`). Phase 0 = awake idle with sporadic slow glance (`idle_f1..f3`, 2-3 frames out/back at 450 ms, 30% every 2 s — same as the HTML preview); phase 6 = sleeping (`idle_sleep_f0..f3` at 5 fps) after 3 min in awake idle; wake word / touch / BOOT -> awake idle (phase 0). Device name `cat-assistant-v1`. |
| `with_images_touch_sound.yaml` | Previous: `with_images_displayed.yaml` + **touch stops any running task first** (`media_player.stop` before starting VA, on both touch and BOOT button) + **wake sound**: `media_player.files` entry `wake_word_triggered_sound` (upstream `sounds/wake_word_triggered.flac`, URL verified 200) played via `media_player.speaker.play_on_device_media_file` (announcement: true) both in `on_wake_word_detected` **and on screen touch — but only when touch STARTS listening**; when touch stops a running session (`else` branch), no ding and `media_player.stop` cuts any playing sound first (after `media_player.stop` + `micro_wake_word.stop`, then 300 ms delay, then `voice_assistant.start`). Device name `echoear-touch`. Fix for "image changes a lot and is slow on ok nabu": the status image is owned by `voice_assistant` events only (`media_player.on_announcement`/`on_idle` just start/stop mww — the wake ding is an announcement too and used to flash the replying/idle images), and the display uses `update_interval: never` + `component.update: main_display` inside `set_status` (guarded by a `drawn_phase` global), so each phase change renders instantly, exactly once, like upstream. |
| `test_echoear_v10.yaml` | Earlier diagnostic variant of the minimum config (kept for reference). |
| `images/` | Custom 360x360 cat-style status PNGs, two sets: `simple/` (procedural, `generate_images.py`: idle/idle2/idle3 sleeping frames with crescent moon + animated Zzz, listening/thinking/replying/error/loading) and `advanced/` (`esp32-cat-eyes-360x360-pngs.html` = the downloaded source page; `generate_advanced.py` renders that page in headless Chrome and saves each gallery canvas as a PNG — pixel-identical to the page, no re-implementation to keep aligned; needs Chrome/Chromium, override with `CHROME_BIN`, fallback: open the HTML and click its Download buttons. Set contents: gradient-shaded eyes, almond pupils, nose+w mouth, plus listening-mic/thinking-?/replying-bubble/error/loading. Two idle animations, with different runtime behavior (see the page's previews): `idle_sleep_f0..f3` = continuous sleep loop with a rising Z (~5 fps); `idle_f0..f3` = NOT a loop — pupils rest centered on `idle_f0`, and only every few seconds play 2-3 frames slowly to one side and back to `idle_f0` (sporadic slow glance). When wiring this set into the yaml, implement that sporadic behavior instead of a continuous frame cycle. Both render at 4x supersampling. `with_images_touch_sound.yaml` sets `img_base: images/simple` (local, relative to the yaml — copy `images/` next to the yaml when building from HA's esphome dir; upstream Eyes URL kept as a comment). To switch to the advanced set: `img_base: images/advanced` and rename the image entries to the advanced names (sleep animation = `idle_sleep_f0..f3`, 4 frames -> interval `mod 4`). The simple-set Zzz animation is runtime: a 700 ms interval advances an `idle_frame` global (mod 3) and redraws, only while phase 0. |
| `ref.md` | Link to upstream repo. |

## Hardware: EchoEar V1.0/V1.1 vs V1.2 (the root cause of "ok nabu does nothing")

The two revisions differ ONLY in these pins (verified by diffing the upstream 1.0/1.2 yamls):

| Signal | V1.0 / V1.1 (this board) | V1.2 |
|---|---|---|
| Mic I2S DIN (ES7210 → S3) | **GPIO15** | GPIO3 |
| Speaker amp enable (NS4150B) | **GPIO4** | GPIO15 |
| Display reset | **GPIO3** | GPIO4 |
| `codec_3v3` power supply | **absent** | GPIO48 |

Common to both: I2C `scl GPIO1 / sda GPIO2` (ES8311 `0x18`, ES7210 `0x40`, BQ27220 `0x55`, CST816 `0x15`, plus `0x68`); I2S `lrclk 39 / bclk 40 / mclk 42`, mic DIN as above, speaker DOUT GPIO41; `vcc3v3_sw` GPIO9 (inverted); QSPI display clk 18, data [46,13,11,12], CS 14; backlight GPIO44 (LEDC); BOOT button GPIO0; touch CST816 interrupt GPIO10.

With the V1.2 mic pin (GPIO3) on a V1.0 board the mic captures silence → `micro_wake_word` never fires, while touch/display/TTS still work. That was the original symptom.

## API / encryption key

- ESPHome ≥2025.2 removed the plaintext legacy API; Device Builder 2026.1.1+ refuses to build `api:` without `encryption: key: !secret api_encryption_key`.
- If the device was created via the dashboard "New device" wizard, `api_encryption_key` already exists in `/config/esphome/secrets.yaml`; otherwise generate with `openssl rand -base64 32`.
- The full `echoear.yaml` requires the key. The `minimum_assistant.yaml` / `with_status_displayed.yaml` variants deliberately use a bare `api:` (plain) for testing — HA 2026.9.2 connected fine with `Noise encryption: NO`.
- In the full config, `micro_wake_word.start` only runs from `voice_assistant.on_client_connected` → no API connection = wake word engine never starts. The minimal configs start mww at boot instead, so detection works even without HA.

## ESPHome 2026.10.x API gotchas (compile errors hit and fixed)

- `voice_assistant` `on_error` params are **`code` and `message`** (not `x`). `on_stt_end`/`on_tts_start` use `x`. mww `on_wake_word_detected` param is `wake_word`.
- Microphone has **no public `read()`**. 2026.10.x: `add_data_callback([](const std::vector<uint8_t> &data){...})` + `start()`/`stop()`; `is_running()` (there is no `is_capturing()` method).
- **Never call `mic.start()`/`stop()` from a lambda that then `delay()`s**: the i2s mic start/stop is a counting semaphore serviced in the main `loop()`; `stop()` early-returns if the state is still STOPPED, so blocking the loop leaks a token → mic driver runs forever → I2S bus locked → speaker logs `Parent bus is busy` forever. (This caused the persistent bus errors in early tests.)
- `micro_wake_word` mic + speaker share one I2S bus. Race: the TTS announcement starts ~15 ms AFTER `voice_assistant.on_end`. Restarting mww directly in `on_end` grabs the bus first → speaker stuck. Fix (same as upstream): in `on_end`, first `wait_until media_player.is_announcing` (timeout 0.5s), then `wait_until not announcing AND not speaker.is_playing` (timeout 30s), then `micro_wake_word.start`. Plus `media_player.on_announcement: micro_wake_word.stop` and `on_idle:` restart mww if VA not running.
- `stop_after_detection` (default true) stops mww after a detection; if VA then fails to start (`No API client connected` when HA hasn't connected yet), mww stays stopped and later "ok nabu" does nothing. Fix: in `on_wake_word_detected`, after `voice_assistant.start`, `delay: 2s` then if `not voice_assistant.is_running` → `micro_wake_word.start`. Same guard in `on_error`.

## Audio tuning (EchoEar amp chain: ES8311 DAC → NS4150B)

- ES8311 DAC hardware volume defaults to 0.75; set via `id(es8311_dac)->set_volume(...)` in `on_boot`.
- Media player `volume_initial` defaults to **0.5** → quiet announcements. Raise it, but keep `volume_max` ≤ 0.8 (upstream comment: "don't go higher than 0.8") — 0.9 software × 1.0 DAC saturates the amp. Working combo: DAC 0.8 + `volume_initial: 0.7`, `volume_max: 0.8`, `volume_min: 0.3`.
- `announcement_pipeline.buffer_size: 100000` (down from 250000) so playback starts sooner while the TTS FLAC streams.

## Latency notes (from serial logs)

Wake word → STT result ≈ 4 s (VAD end-of-speech + STT, normal). The big gap is TTS: HA generates the `tts_proxy` FLAC **on demand when the device fetches the URL** (`Reading FLAC file type` → `Decoded audio` took 8–16 s) — that is HA-side Piper synthesis time, not the device. To cut it, use a faster voice in HA's Assist pipeline.

## Verified working (serial log evidence)

- I2C scan finds 0x15/0x18/0x40/0x55/0x68 at boot.
- `Detected 'Okay Nabu' ... probability 0.98–0.99` → full pipeline → `Speech recognised as: ...` → TTS reply played on the speaker with no bus errors after the fixes above.
