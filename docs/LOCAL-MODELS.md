# Local preparation (local addition)

`LOCAL_PREPARATION=1` in `.env` runs the three jobs Replicate did on this machine. Nothing is uploaded
and nothing is billed during preparation. Install with `bash setup-local-models.sh`.

| Job | Hosted | Local | License |
|---|---|---|---|
| Vocal separation | Replicate Demucs | Demucs `htdemucs` (same model) | MIT |
| Depth | Replicate / Hugging Face Space | Video-Depth-Anything **Small** | Apache-2.0 (Base and Large are non-commercial and not used) |
| Subject masks | Replicate SAM 3, text prompt | COCO detector (torchvision Faster R-CNN) finds the subjects, SAM 2.1 base+ follows them | BSD / Apache-2.0 |

Code: `local_models.py` starts the workers in `local_workers/`, which run in `.venv-local`.
Model files and download caches live in `models/` (not in `~/.cache`).

## Differences from the hosted path

- **Subject:** a COCO category name, not free text. `person` (default) covers every person in frame;
  `dog`, `car`, `bottle` and the other 80 COCO names work; anything else is refused with the list.
- **Masks come from the original picture**, not from the depth video.
- **A subject who enters later** is picked up at the next run boundary (every 192 frames, 8 s), not at once.
- **Depth quality:** the Small model; the hosted default may be a larger one.
- **The depth provider choice in the UI is ignored** while local preparation is on.

## Speed (Apple M5, 24 GB, measured 2026-10-12 on a 960×900 clip with two people)

| Step | Time |
|---|---|
| Vocals, 6 s of audio | about 10 s |
| Depth, 144 frames | about 40 s (0.15 s per frame) |
| Masks, 144 frames, two subjects | about 3 min (1.25 s per frame) |

A 30 s clip takes roughly 15–20 minutes, almost all of it in the mask step. The SAM 2 model size made
no difference (small and base+ took the same time), and the CPU was slower than the GPU.
