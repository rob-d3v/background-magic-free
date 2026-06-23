---
title: "Gradio App — Studio Tab"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - gradio
  - studio
  - offline
  - video-processing
---

The Studio tab (`🎬 Studio — gravar video`) is the offline video background-replacement workflow inside [[gradio-app-app-py]], structured as a six-step guided flow.

## Layout

Two-column `gr.Row`:

- **Left column** (controls): steps 1–4 (upload, frame picker, background config, lighting/mode).
- **Right column** (output): preview image, single-frame preview result, apply-all button, video output, download file.

## Six-Step Guided Flow

| Step | UI Element | Callback |
|---|---|---|
| 1 — Upload video | `gr.Video` + "Preparar video" button | `cb_preparar` |
| 2 — Pick a frame | `gr.Slider` (frame index) + "Recortar pessoa" button | `cb_mostrar_frame`, `cb_recortar` |
| 3 — Background | `gr.Radio` (upload vs AI) + `gr.Image` + `gr.Textbox` prompt | resolved in `_obter_bg` |
| 4 — Mode / lighting | `gr.Radio` (3 modes) + prompt/negative/steps/cfg/seed/CRF | controls for `cb_preview` / `cb_aplicar` |
| 5 — Preview | "Pre-visualizar neste frame" button | `cb_preview` |
| 6 — Render + export | "Aplicar a todos os frames" button | `cb_aplicar` |

## UI Controls Reference

| Control | Type | Default | Notes |
|---|---|---|---|
| `video_in` | `gr.Video` | — | Triggers `cb_guardar_video` on change to store path |
| `frame_slider` | `gr.Slider` | 0→1, value=0 | Hidden until video prepared; range set to `total_frames-1` by `cb_preparar` |
| `bg_modo` | `gr.Radio` | "Enviar imagem" | "Gerar com IA" requires CUDA |
| `modo` | `gr.Radio` | HD if GPU available, else Compor | See [[gradio-app-processing-modes]] |
| `steps` | `gr.Slider` | 20 (range 10–40) | SD diffusion steps |
| `cfg` | `gr.Slider` | 7.0 (range 1–12) | Classifier-free guidance scale |
| `seed` | `gr.Number` | 12345 | Deterministic seed for diffusion |
| `crf` | `gr.Slider` | 18 (range 14–28) | FFmpeg CRF for output quality |

## Button Interactivity Gating

Buttons `btn_recortar`, `btn_preview`, and `btn_aplicar` start as `interactive=False`. `cb_preparar` re-enables them once the video is loaded and frames are extracted. This prevents calling downstream steps without valid state.

## Outputs

- `video_out` (`gr.Video`) — embedded playback of final MP4.
- `file_out` (`gr.File`) — download link for the same MP4.

Both are wired to `cb_aplicar` which returns `(out_path, out_path)`.
