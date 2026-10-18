# Training a Custom Wake Word (openWakeWord / livekit-wakeword)

A step-by-step tutorial for training a custom wake word detection model, based on the pipeline actually used to train the **"Michel"** model (a French wake word) with the [livekit-wakeword](https://github.com/livekit/livekit-wakeword) tool.

The final model is a **~100 KB ONNX file** that runs comfortably on a Raspberry Pi (Zero 2 W / 3 / 4) — detection uses very little CPU.

## Model architecture

```
16 kHz audio (~2 s)
      │
      ▼
┌──────────────────────┐
│ Melspectrogram       │  (bundled base model)
├──────────────────────┤
│ Google speech        │  (bundled base model)
│ embeddings (16×96)   │
├──────────────────────┤
│ Custom classifier    │  ← THIS is what we train (our .onnx)
│ (conv_attention)     │
└──────────────────────┘
      │
      ▼
Confidence score [0..1]
```

Only the small classifier head is trained; the base models (mel + embeddings) are provided and frozen. Exported model contract:

- **Input**: `embeddings` — tensor `(batch, 16, 96)` float32
- **Output**: `score` — tensor `(batch, 1)` between 0 and 1

This is the same contract as openWakeWord custom models, so the `.onnx` file can also be loaded by openWakeWord on the Pi.

## What to expect before you start

| Step | Observed duration (Mac, CPU only) |
|------|----------------------------------|
| `setup` | ~5-10 min (downloads) |
| `generate` | ~30-45 min (TTS synthesis of 10,000 samples) |
| `augment` | ~10-20 min (augmentation + feature extraction) |
| `train` | **~2 h 30** (60,000 steps in 3 phases) |
| `export` | < 1 min |
| `eval` | ~2-3 min |

Training happens on a dev machine (Mac/Linux). The Pi is only used at inference time.

---

## Step 1 — Install the training tool

### System dependencies

macOS:

```bash
brew install espeak-ng ffmpeg portaudio
```

Ubuntu/Debian:

```bash
sudo apt install espeak-ng libsndfile1 ffmpeg sox portaudio19-dev
```

### The livekit-wakeword project

```bash
git clone https://github.com/livekit/livekit-wakeword
cd livekit-wakeword
uv sync --all-extras        # or: python3.11 -m venv .venv && pip install -e ".[train,eval,export]"
```

> **French**: for French speech synthesis you need the **VoxCPM** TTS backend: `pip install livekit-wakeword[train,eval,export,voxcpm]`. VoxCPM requires PyTorch >= 2.5; on version conflicts: `pip install --no-deps voxcpm`.

### Download the base data

```bash
.venv/bin/python -m livekit.wakeword setup --config configs/my_wake_word.yaml
```

This command downloads:

- the base models (melspectrogram + speech embeddings);
- background noises (MUSAN) and room impulse responses (RIRs) for augmentation.

> **ACAV100M (optional)**: a ~16 GB corpus of general speech used as negatives. With `--skip-acav`, training still works but the model will have a **higher false positive rate** (there is a warning in the logs). That is the trade-off we took for Michel — you then compensate with a higher detection threshold at runtime (see Step 7).

---

## Step 2 — Create the YAML config

Create `configs/my_wake_word.yaml`. Below is the file actually used for Michel (`configs/michel.yaml`), to adapt:

```yaml
model_name: michel                      # output model name (michel.onnx)

target_phrases: ["Michel"]              # the word/phrase to detect

tts_backend: voxcpm                     # voxcpm for French, piper_vits for English

# --- Data volume ---
n_samples: 10000            # training samples per class
n_samples_val: 2000         # validation samples
n_background_samples: 2000
n_background_samples_val: 500
tts_batch_size: 30

# --- Adversarial negatives ---
# Phonetically close phrases that must NOT trigger detection.
# GOLDEN RULE: no negative may CONTAIN the wake word.
custom_negative_phrases:
  - "Nicolas"
  - "Michou"
  - "Mickaël"
  - "Nathalie"
  - "Nathanaël"
  - "Matthieu"
  - "Michaël"
  - "micheline"
  - "un micmac"
  - "des miches"
  - "la miche"
  - "micher"

# --- Voice diversity (VoxCPM) ---
# 20-30 different prompts: age, gender, tone, pace.
voxcpm_tts:
  n_voice_design_prompts: 30
  voice_design_prompts:
    - "Un homme adulte, voix claire, ton modéré, pace normal"
    - "Une femme adulte, voix douce, ton calme, pace lent"
    - "Un jeune homme, voix aiguë, ton énergique, pace rapide"
    - "Une jeune femme, voix cristalline, ton joyeux, pace modéré"
    - "Un homme âgé, voix grave, ton sérieux, pace lent"
    - "Une femme âgée, voix rauque, ton sage, pace très lent"
    - "Un enfant, voix haute, ton excité, pace très rapide"

# --- Paths ---
data_dir: ./data
output_dir: ./output_michel

# --- Augmentation ---
augmentation:
  clip_duration: 2.0
  batch_size: 16
  rounds: 3
  background_paths: [./data/backgrounds]
  rir_paths: [./data/rirs]

# --- Architecture ---
model:
  model_type: conv_attention   # conv_attention (accurate) | dnn (TFLite-compatible)
  model_size: small            # tiny | small | medium | large

# --- Training ---
steps: 50000
learning_rate: 0.0001
weight_decay: 0.01
label_smoothing: 0.05
max_negative_weight: 2000      # negative weight: higher = fewer false positives
target_fp_per_hour: 0.2        # target false positives per hour

batch_n_per_class:
  positive: 50
  adversarial_negative: 50
  ACAV100M_sample: 512         # ignored when ACAV100M is skipped
  background_noise: 50
```

### Key points for choosing negatives

- **Forbidden**: a negative that contains the wake word ("michel", "Michelle", "Micheline"...) — otherwise the model learns to detect... and to ignore the very same sound.
- **Prefer**: phonetically close words (same consonants/vowels, same rhythm).
- Also add everyday words likely to trigger false detections in your home (family first names, frequently spoken object names).

---

## Step 3 — Generate synthetic data

```bash
.venv/bin/python -m livekit.wakeword generate configs/michel.yaml
```

Generates with the TTS (VoxCPM):

- **positives**: the wake word spoken with all the voices;
- **adversarial negatives**: the phrases from `custom_negative_phrases`.

Output goes to `output_michel/michel/positive_train/` and `negative_train/` (wav files).

---

## Step 4 — Augment and extract features

```bash
.venv/bin/python -m livekit.wakeword augment configs/michel.yaml
```

This step:

1. applies augmentations (background noise, reverb, pitch shift);
2. runs every clip through the frozen pipeline (mel + embeddings);
3. saves the features as `.npy`:
   - `positive_features_train.npy` (30,000 × 16 × 96)
   - `negative_features_train.npy` (19,440 × 16 × 96)
   - matching `_test` files for validation.

---

## Step 5 — Train

### Launch (recommended: in the background with a log)

Training takes hours: run it in the background with a log file.

```bash
mkdir -p output_michel
nohup .venv/bin/python -m livekit.wakeword train configs/michel.yaml \
    > output_michel/train.log 2>&1 &
echo "PID: $!"
```

### What training looks like (observed on Michel)

Training is **adaptive, in 3 phases**:

| Phase | Steps | Role |
|-------|-------|------|
| 1 | 50,000 | main learning (lr 1e-4 with cosine decay) |
| 2 | 5,000 | fine-tuning with progressive negative hardening (`neg_w` climbs to ~3000) |
| 3 | 5,000 | consolidation + best-threshold selection |

Reference points from the Michel run (Mac, CPU):

- total duration: **~2 h 30** (9,150 s);
- highly variable speed: 1 to 22 steps/s (slower batches during cosine decay — normal, not a hang);
- loss drops to ~0.08-0.10 in phase 1, ~0.17 in phase 2 (negative hardening pushes it back up: expected);
- at the end: `Training complete! Model saved to output_michel/michel/michel.pt`.

### Tracking progress

Intermediate metrics are written to `output_michel/michel/<model>_metrics.json` (fpph, recall, accuracy, threshold — measured every 2,500 steps on the validation set).

Progress script (`check_train.sh`):

```bash
#!/bin/bash
LOG=output_michel/train.log

if ! pgrep -f "livekit.wakeword train" > /dev/null; then
  echo "Process NOT running"
  grep -q "Training complete" "$LOG" && echo "✅ TRAINING COMPLETED" || echo "⚠️ Training interrupted?"
  exit 0
fi

LAST=$(tail -c 5000 "$LOG" | grep -oE "Phase [0-9]+: +[0-9]+%\|[^|]*\| [0-9]+/[0-9]+ \[[^]]*\]" | tail -1)
echo "⏳ $(date '+%H:%M:%S') — $LAST"
```

```bash
watch -n 900 bash check_train.sh   # ETA every 15 min
```

---

## Step 6 — Export to ONNX

### The opset 18 trap

The official command fails with:

```
RuntimeError: Unrecognized attribute: axes for operator ReduceMean
```

Cause: `torch.onnx.export` is called with `opset_version=18`, unsupported by the installed PyTorch version (max: 17). **Workaround**: export with opset 17.

```bash
.venv/bin/python - <<'EOF'
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from livekit.wakeword.config import load_config
from livekit.wakeword.export.onnx import export_onnx

config = load_config(Path('configs/michel.yaml'))
model_dir = config.model_output_dir
export_onnx(
    config,
    model_dir / f"{config.model_name}.pt",
    model_dir / f"{config.model_name}.onnx",
    opset_version=17,   # ← the fix
)
print("Export OK")
EOF
```

### Verify the exported model

```bash
.venv/bin/python - <<'EOF'
import numpy as np, onnxruntime as ort

session = ort.InferenceSession("output_michel/michel/michel.onnx",
                               providers=["CPUExecutionProvider"])
x = np.random.randn(1, 16, 96).astype(np.float32)
y = session.run(None, {"embeddings": x})[0]
print(f"input (1,16,96) -> output {y.shape}, score={y[0,0]:.4f}")
EOF
```

Expected output: `output (1, 1)` and a score between 0 and 1. The file is ~97 KB.

### What does not work (to save you time)

- **INT8 quantization** (`quantize_onnx`): the file is produced, but onnxruntime CPU refuses to load it (`Could not find an implementation for ConvInteger`). For a 97 KB model, quantization is pointless anyway — stay FP32.
- **TFLite**: not supported for the `conv_attention` head (the attention block and LSTM do not convert to builtin TFLite ops). Only the `dnn` head is TFLite-exportable. → On a Pi, use **ONNX Runtime**; TFLite is not needed.

### numpy version conflict (single-command pipeline)

If you chain everything in one venv: generation/training want `numpy<2` (and **without** `ml-dtypes`), while export wants `numpy>=2` + `ml-dtypes`. Hence the sequence used in `run_full_pipeline.sh`:

```bash
pip install --force-reinstall "numpy<2" && pip uninstall -y ml-dtypes onnxscript
# ... generate / augment / train ...
pip install --force-reinstall "numpy>=2" ml-dtypes
# ... export ...
```

Running the steps one by one (as here) and only importing the exporter after training usually avoids this problem entirely.

---

## Step 7 — Evaluate and pick the detection threshold

```bash
.venv/bin/python -m livekit.wakeword eval configs/michel.yaml
```

Produces the DET curve (`michel_det.png`) and prints AUT / FPPH / recall. Real numbers from the Michel run, **without ACAV100M**:

| Threshold | Recall | False positives/hour | Accuracy |
|-----------|--------|---------------------:|----------|
| 0.5 (default) | 99.5 % | ~128 | 96.2 % |
| **0.98 (optimal)** | **97.9 %** | **~25** | 98.3 % |

How to read this: at 0.5 the model detects nearly everything but also fires on random speech. **Without the ACAV100M corpus you need a high threshold (0.8-0.9+) at runtime** to avoid false wakes. If FPPH stays too high after threshold tuning, the real fix is to run `setup` **with** ACAV100M (~16 GB) and retrain.

Recommended tuning order:

1. deploy with a high threshold (0.9);
2. if the wake word is missed at distance, lower by 0.05 steps;
3. if false wakes appear, raise it again and/or enrich `custom_negative_phrases` and retrain.

---

## Step 8 — Test locally (microphone)

```bash
.venv/bin/python - <<'EOF'
import asyncio
from livekit.wakeword import WakeWordModel, WakeWordListener

model = WakeWordModel(models=["output_michel/michel/michel.onnx"])

async def main():
    # threshold = the threshold picked in Step 7; debounce = refractory window
    async with WakeWordListener(model, threshold=0.9, debounce=2.0) as listener:
        while True:
            det = await listener.wait_for_detection()
            print(f"Detected: {det.name} (confidence {det.confidence:.2f})")

asyncio.run(main())
```

`WakeWordModel.predict()` expects a chunk of about 2 s of 16 kHz mono audio; it returns `{"michel": 0.87}`.

---

## Step 9 — Deploy to the Raspberry Pi

The single file to copy is:

```
output_michel/michel/michel.onnx    (~97 KB)
```

In this project the trained model lives at `oww/michel/michel.onnx`.

On the Pi:

1. Copy `michel.onnx` to the card (e.g. `/home/pi/wakewords/michel.onnx`).
2. The classifier consumes **embeddings** (16×96), not raw audio: the runtime must include the two bundled base models (mel + embeddings). Two options:
   - **livekit-wakeword as runtime** (`pip install livekit-wakeword` on the Pi, then `WakeWordModel` as in Step 8);
   - **openWakeWord**: the (1, 16, 96) input contract is the same as openWakeWord custom models — drop the ONNX into the models folder and reference it in the config (e.g. a `wyoming-openwakeword` satellite with `--custom-model-dir`).
3. Set the **threshold** (Step 7) in the satellite config.

Quick check on the Pi:

```bash
python3 - <<'EOF'
import numpy as np, onnxruntime as ort
s = ort.InferenceSession("/home/pi/wakewords/michel.onnx")
print(s.run(None, {"embeddings": np.random.randn(1,16,96).astype(np.float32)}))
EOF
```

---

## Command recap

```bash
# 0. Install
git clone https://github.com/livekit/livekit-wakeword && cd livekit-wakeword
uv sync --all-extras          # + voxcpm for French

# 1. Base data
python -m livekit.wakeword setup configs/my_wake_word.yaml          # --skip-acav to avoid 16 GB

# 2. Config: create configs/my_wake_word.yaml (see Step 2)

# 3. TTS generation
python -m livekit.wakeword generate configs/my_wake_word.yaml

# 4. Augmentation + features
python -m livekit.wakeword augment configs/my_wake_word.yaml

# 5. Training (in the background, ~2h30)
nohup python -m livekit.wakeword train configs/my_wake_word.yaml \
    > output/train.log 2>&1 &

# 6. ONNX export (opset 17!)
python -m livekit.wakeword export configs/my_wake_word.yaml     # if it fails: workaround in Step 6

# 7. Evaluation + threshold choice
python -m livekit.wakeword eval configs/my_wake_word.yaml

# 8. Local mic test, then copy the .onnx to the Pi
```

There is also an all-in-one command, `python -m livekit.wakeword run configs/my_wake_word.yaml` (generate → augment → train → export) — convenient, but it runs the export with the default opset and fails on that step; prefer the separate steps.

## Pre-training checklist

- [ ] No `custom_negative_phrases` entry contains the wake word
- [ ] At least 20 different voice prompts (`voice_design_prompts`)
- [ ] `tts_backend: voxcpm` for French
- [ ] `model_type: conv_attention` + ONNX export (TFLite impossible with this head)
- [ ] ACAV100M downloaded, OR a high runtime threshold planned
- [ ] Training launched in the background with a log, monitoring in place
- [ ] Threshold chosen from `eval` before deploying to the Pi
