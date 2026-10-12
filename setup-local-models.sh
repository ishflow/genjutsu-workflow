#!/usr/bin/env bash
# Installs the models that replace Replicate: depth, masks and vocal separation on this machine.
# About 1 GB of packages and 0.9 GB of model files, all inside this folder. See docs/LOCAL-MODELS.md.
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null 2>&1 || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }
[ -d .venv-local ] || uv venv --python 3.12 .venv-local
uv pip install --python .venv-local/bin/python torch torchvision torchaudio "numpy<2.3" opencv-python-headless av pillow matplotlib einops easydict imageio imageio-ffmpeg tqdm sam2 demucs soundfile
mkdir -p models
[ -d models/vda-src ] || git clone --depth 1 https://github.com/DepthAnything/Video-Depth-Anything.git models/vda-src
# The Small depth model is Apache-2.0; the Base and Large models are non-commercial and are not used.
[ -s models/video_depth_anything_vits.pth ] || curl -fL -o models/video_depth_anything_vits.pth "https://huggingface.co/depth-anything/Video-Depth-Anything-Small/resolve/main/video_depth_anything_vits.pth"
[ -s models/sam2.1_hiera_base_plus.pt ] || curl -fL -o models/sam2.1_hiera_base_plus.pt "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt"
grep -q '^LOCAL_PREPARATION=' .env 2>/dev/null || echo 'LOCAL_PREPARATION=1' >> .env
.venv/bin/python doctor.py
printf '\nSet LOCAL_PREPARATION=1 in .env if it is not already. The detector and Demucs weights download on first use.\n'
