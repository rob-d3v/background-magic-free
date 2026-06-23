---
title: "Decision — Single-User Global State in app.py"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - architecture
  - state
  - single-user
  - inferred
---

`app.py` uses module-level global variables for all session state and model handles rather than Gradio's `gr.State` or a session-scoped object.

**Inferred decision.**

## What Was Chosen

All mutable state — `ESTADO` dict, `_REMBG_SESSION`, `_RELIGHT_PIPE`, `_LIVE_MATTER`, `_OFFLINE_MATTER`, `_LIVE_PROC` — is stored as module globals, initialized once and mutated in place by callbacks.

## Likely Rationale

- The tool targets single-user local execution (or single-user Colab sessions). Multi-user isolation is not a requirement.
- GPU models are expensive to load; lazy-loading into globals avoids reloading on every callback invocation.
- `RVMMatter` is a stateful recurrent model that must be reset before each video — `_offline_matter()` calls `.reset()` on each access, handled internally.
- Simplicity: no Gradio session state serialization overhead for large objects (model pipelines cannot be serialized).

## Trade-offs

- If multiple browser tabs or users connect to the same Gradio server, state will be shared and corrupted.
- `_LIVE_PROC` global means only one Live subprocess can run at a time per process.
- Disk-cached frame cutouts (frames_nobg/) are keyed by frame index only — a second video uploaded without restarting the server could reuse stale cutout frames from the first video if frame counts overlap.

## Related

- [[gradio-app-app-py]]
- [[gradio-app-processing-modes]] (lazy model loading)
