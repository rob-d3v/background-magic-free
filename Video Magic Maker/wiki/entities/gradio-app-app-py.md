---
title: "Gradio App — app.py (lumina-bg Web UI)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
  - config.py
tags:
  - gradio
  - ui
  - entry-point
  - studio
  - live
---

`app.py` is the Gradio 4.x web UI entry point for lumina-bg, exposing a guided two-tab interface (Studio and Live) served at `http://127.0.0.1:7860` locally or via a public share link on Colab.

## Responsibilities

- Constructs and serves the full Gradio `Blocks` layout.
- Owns global in-process state (`ESTADO`, lazy model handles).
- Wires all UI component events to Python callbacks (`cb_*`).
- Detects GPU capability at startup via [[gradio-app-config-device-detection]] and adjusts default mode and banner text accordingly.
- Launches `live.py` as a subprocess for the Live tab's virtual camera.

## Global State

| Variable | Type | Purpose |
|---|---|---|
| `ESTADO` | `dict` | Holds `meta` (frame count, fps, dimensions) and `video_path` for the current session |
| `_REMBG_SESSION` | rembg session | Lazy-loaded u2net_human_seg model for single-frame cutout |
| `_RELIGHT_PIPE` | diffusers pipe | Lazy-loaded IC-Light pipeline (GPU only) |
| `_LIVE_MATTER` | LiveMatter | Lazy-loaded RVM for webcam preview in Live tab |
| `_OFFLINE_MATTER` | RVMMatter | Lazy-loaded RVM for Studio HD-mode and batch render |
| `_LIVE_PROC` | subprocess.Popen | Handle for the running `live.py` subprocess |
| `LIVE_BG_PATH` | str | Fixed path where the background image is written for `live.py` |

All state is module-level (single-user process). No session isolation.

## Tabs

- **Studio** (`🎬 Studio — gravar video`): offline video processing, see [[gradio-app-studio-tab]].
- **Live** (`🔴 Live — OBS / Meet / stream`): real-time webcam virtual camera, see [[gradio-app-live-tab]].

## Launch Behaviour

```python
demo.launch(share=em_colab, theme=gr.themes.Soft(primary_hue="indigo"))
```

- `share=True` only when running inside Google Colab (auto-detected via `google.colab` import).
- Theme: `Soft` with indigo primary.

## Dependencies Imported

- `config.Paths`, `config.detectar_device` — workspace paths and GPU detection.
- `agentes.extracao.extrair_frames` — frame extraction.
- `agentes.exportacao.exportar_video` — final MP4 assembly.
- `agentes.matting_rvm.RVMMatter` (lazy) — HD matting.
- `agentes.matting_live.LiveMatter`, `cobrir`, `fundo_desfocado` (lazy) — live/webcam matting.
- `agentes.relighting.carregar_iclight`, `relight_frame`, `aplicar_relighting` (lazy) — IC-Light relight.
- `agentes.composicao.compor_frame`, `compor_batch` (lazy) — fast composite.
- `agentes.remocao.remover_fundo` (lazy) — batch rembg.
- `agentes.geracao_fundo.gerar_fundo_diffusers` (lazy) — AI background generation.
- `agentes.render_video.render_matting` (lazy) — RVM batch render.
