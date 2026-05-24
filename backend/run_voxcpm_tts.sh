#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

MODEL_DIR="pretrained_models/VoxCPM2"

echo "[VoxCPM2] Downloading/resuming model from ModelScope into ${MODEL_DIR}"
.tts-venv/bin/python - <<'PY'
from modelscope import snapshot_download

path = snapshot_download("OpenBMB/VoxCPM2", local_dir="pretrained_models/VoxCPM2")
print(path)
PY

echo "[VoxCPM2] Starting OpenAI-compatible TTS server on :8001"
VOXCPM_MODEL_PATH="${MODEL_DIR}" exec .tts-venv/bin/python -m uvicorn voxcpm_tts_server:app --host 0.0.0.0 --port 8001
