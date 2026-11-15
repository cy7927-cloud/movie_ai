#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! python3 -c 'import cv2,numpy,PIL,skimage' 2>/dev/null; then
  echo "Installing missing offline-only Python dependencies..."
  python3 -m pip install -r requirements.txt || { echo 'Install dependencies manually (offline wheel cache is also supported).'; exit 1; }
fi
command -v ffmpeg >/dev/null || echo 'WARNING: FFmpeg not found; new video imports need FFmpeg + FFprobe.'
python3 production_cli.py status
printf '\nInteractive director console: http://127.0.0.1:8766\nEvidence review: http://127.0.0.1:8766/evidence\nCut review: http://127.0.0.1:8766/cuts\n'
printf 'Director craft workspace: http://127.0.0.1:8766/director\n'
printf 'Director editing and narrative learning lab: http://127.0.0.1:8766/editing\n'
printf 'Full 12:56 film storyboard: http://127.0.0.1:8766/longform\n'
python3 studio_product.py --port 8766
