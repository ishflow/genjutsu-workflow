# Magnific provider (local addition)

Set `SEEDANCE_PROVIDER=magnific` in `.env` to send generation and vocal isolation to the Magnific API
instead of Enhancor and Replicate. Implemented in `magnific_bridge.py`; routed by `generation.py`.
Derived from the Magnific documentation (docs.magnific.com, read 2026-10-12). **No paid request has
been made with this adapter yet**: request shapes are covered by `tests/test_magnific.py` with fakes only.

## Configuration

```
SEEDANCE_PROVIDER=magnific
MAGNIFIC_API_KEY=            # the key itself, or leave empty and use the two lines below
MAGNIFIC_KEY_FILE=           # a KEY=value file that already holds the key
MAGNIFIC_KEY_NAME=           # the name of its line
MAGNIFIC_DRAFT_RESOLUTION=720p   # 480p or 720p
```

No webhook, no cloudflared tunnel and no public media host are used. Media goes to Magnific's own
staging uploads (`POST /v1/ai/uploads/request-url`, then `PUT`), which expire on their own.

## What changes compared with Enhancor

| | Enhancor | Magnific |
|---|---|---|
| Draft | `mode: edit`, `is_draft: true` | reference-to-video at 480p/720p: `POST /v1/ai/video/seedance-2-5-pro-<res>` |
| 1080p | upgrades the approved draft (`draft_id`) | **a new 1080p generation** with the same request and seed; the result can differ from the draft |
| Source video | `videos[0]` | `reference_videos[0]` (upload `file_id`), cited as `@Video1` |
| Identity image | `images[]` | `reference_images[]` (upload URL), cited as `@Image1`… |
| Identity video | `multi_reference` | `reference_videos[1]`, cited as `@Video2` |
| Vocal isolation | Replicate Demucs | SAM Audio: `POST /v1/ai/audio-isolation`, description "A person speaking" |
| Depth and SAM masks | Replicate | not available: depth modes still need `REPLICATE_API_TOKEN` |
| Poll | `POST /status` | `GET /v1/ai/video/seedance-2-5-pro-<res>/<task-id>`; result in `data.generated[0]` |

Only **Fast · Face mesh** mode runs on a Magnific key alone.

## Limits and billing (from the documentation)

- Reference videos: MP4 or MOV, 2–30 s each and 30 s combined, 24–60 fps, up to 200 MB.
- Output duration: whole seconds, 4–30. The adapter rounds the source duration into that range;
  `finish_preview` refuses a result whose length differs from the source audio by more than 0.25 s.
- A request with reference videos is billed for the output length **plus** the reference length,
  capped at 30 s. A 10 s clip is billed as 20 s.
- `enable_safety_checker` is left at the provider default (on). Whether real faces in the source
  pass it is untested.

## Not retried

A rejected or ambiguous paid POST is never repeated. `submission-error.json` holds the provider's
answer; check the Magnific dashboard before preparing a new job.
