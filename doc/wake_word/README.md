# Custom Wake Word — Train (Optional) and Deploy to the Assistant

LVA supports custom wake word models added as **TFLite** files plus a small JSON config. This page covers:

1. **(Optional)** Training a new wake word on a Mac → [`doc/open_wake_word/tutorial.md`](../open_wake_word/tutorial.md)
2. **Deploying the existing "Michel" model** to the assistant so it becomes selectable as the wake word.

## Important: LVA only loads TFLite models

Both wake word engines inside LVA (`pymicro-wakeword` and `pyopen-wakeword`) run models through the TensorFlow Lite C API — **`.onnx` files are not loadable**. This matters for the existing model in [`oww/michel`](../../oww/michel):

| Model | Format | Usable with LVA? |
|-------|--------|------------------|
| `michel.onnx` (the only model in `oww/michel/` today) | ONNX, `conv_attention` head | No — loadable by standard openWakeWord runtimes (e.g. `wyoming-openwakeword`), but not by LVA |
| a future `michel.tflite` | TFLite, `dnn` head | Yes — but this file **does not exist yet**: it must be created by retraining with the `dnn` head (see [Part A](#part-a--optional-train-a-wake-word-on-a-mac)) |

The `conv_attention` head cannot be converted to TFLite (see the [tutorial](../open_wake_word/tutorial.md), Step 6). So to use "Michel" with this assistant, the model must be **retrained with `model_type: dnn`**, which is TFLite-exportable. The input contract is identical (16×96 speech embeddings), so the retrained model plugs into LVA's openWakeWord engine.

## Part A — (Optional) Train a wake word on a Mac

Follow the full training tutorial: **[doc/open_wake_word/tutorial.md](../open_wake_word/tutorial.md)** (based on the actual "Michel" training run with [livekit-wakeword](https://github.com/livekit/livekit-wakeword), ~2.5 h on a Mac CPU).

For a model destined for LVA, apply **one change** to the config in Step 2 of the tutorial:

```yaml
model:
  model_type: dnn          # dnn (TFLite-exportable, required for LVA) | conv_attention (ONNX only)
  model_size: small
```

Everything else is unchanged. Since the extracted features do not depend on the classifier head, you can skip the `generate`/`augment` steps and only re-run `train` on the existing features, then export the TFLite model:

```bash
# install the optional TFLite extra (onnx2tf + TensorFlow)
pip install "livekit-wakeword[tflite]"        # or: uv sync --extra tflite

# retrain with the dnn head (~2.5 h)
.venv/bin/python -m livekit.wakeword train configs/michel.yaml

# export as TFLite (ONNX is exported first, then converted ONNX → TFLite)
.venv/bin/python -m livekit.wakeword export configs/michel.yaml --format tflite
# → output_michel/michel/michel.tflite
```

If the export fails with the opset error described in the tutorial (Step 6), apply the same workaround (export with opset 17) — the TFLite exporter runs the ONNX export first.

Commit the resulting `.tflite` to this repository under `oww/<name>/` for safekeeping (like `oww/michel/`), then continue with Part B.

The evaluation step (Step 7 of the tutorial) gives you the detection threshold to use at runtime — note it down, it goes into the JSON config below.

## Part B — Deploy a wake word to the assistant

### 1. Create the custom wake word directory

LVA automatically scans `<download-dir>/external_wake_words` (default: `local/external_wake_words` inside the LVA checkout) in addition to its built-in models:

```bash
mkdir -p ~/linux-voice-assistant/local/external_wake_words
```

This is the recommended place for custom models — it survives `git pull` in the LVA repo.

### 2. Copy the model

`michel.tflite` **does not exist yet in this repository** — `oww/michel/` only contains the ONNX export (conv_attention head). Produce it first with the `dnn` retraining + TFLite export described in [Part A](#part-a--optional-train-a-wake-word-on-a-mac), commit it to `oww/michel/`, then copy it to the Pi from your workstation (SSH access in `local/voice-pi.md`):

```bash
scp oww/michel/michel.tflite doume@<voice-pi-ip>:~/linux-voice-assistant/local/external_wake_words/
```

### 3. Create the JSON config

On the Pi, create `michel.json` next to the model:

```bash
cat > ~/linux-voice-assistant/local/external_wake_words/michel.json << 'EOF'
{
  "type": "openWakeWord",
  "wake_word": "Michel",
  "trained_languages": ["fr"],
  "model": "michel.tflite",
  "openWakeWord": {
    "probability_cutoff": 0.9
  }
}
EOF
```

- `probability_cutoff` = the detection threshold. For the "Michel" evaluation (trained **without** ACAV100M), start at **0.9**; the eval curve showed **0.98** as optimal (97.9 % recall, ~25 false positives/hour). Lower it by 0.05 steps if the wake word is missed at distance; raise it if the assistant wakes on its own.
- `wake_word` is the display name shown in Home Assistant.

### 4. Restart and select

```bash
sudo systemctl restart linux-voice-assistant
# check the registration in the logs:
journalctl -u linux-voice-assistant -n 50 | grep -i wake
```

Then activate it, either:

- **At runtime** (no restart needed after the initial registration): open the "Michel" device page in Home Assistant → Devices & services → ESPHome, and select the wake word in the dropdown, **or**
- **At startup**: add `--wake-model michel` to the LVA command line / systemd `ExecStart`.

### 5. Verify

Say the wake word. Expected chain:

- the wake sound plays and the HAT LEDs run the wake pattern ([Step 3](../leds/README.md)),
- the LVA logs show the wake word detection,
- Home Assistant starts the Assist pipeline.

If nothing is detected, run LVA in the foreground with `--debug` — at startup it logs every wake word directory it scans and every model it registers (`Successfully registered wake word: michel`).

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Model does not appear in the dropdown | The JSON or model is in a subdirectory — LVA only scans the top level of each wake word dir. Check the exact path `~/linux-voice-assistant/local/external_wake_words/`. |
| `Failed to load` / crash on startup | You deployed an `.onnx` file — LVA only loads TFLite (see the table above). Retrain with `model_type: dnn`. |
| Wake word missed at distance | Lower `probability_cutoff` by 0.05; also check mic gain (`--mic-auto-gain`). |
| Assistant wakes on random speech | Raise `probability_cutoff` (up to 0.98), or retrain with more `custom_negative_phrases` / the ACAV100M corpus (see the tutorial). |
