---
title: "Gradio App — Guided Studio Flow (call sequence)"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - flow
  - call-sequence
  - studio
  - callbacks
---

The Studio tab in [[gradio-app-app-py]] implements a linear six-step guided flow where each step unlocks the next via button interactivity gating and shared in-memory state (`ESTADO`).

## Call Sequence

```
User uploads video
  └─ video_in.change → cb_guardar_video
       stores video_path in ESTADO (for audio extraction at export)

User clicks "1. Preparar video"
  └─ cb_preparar(video_path)
       extrair_frames → {total_frames, fps, width, height} stored in ESTADO["meta"]
       → unlocks frame_slider (visible, interactive)
       → unlocks btn_recortar, btn_preview, btn_aplicar
       → sets slider to middle frame
       → returns frame image for frame_preview

User drags frame_slider
  └─ frame_slider.change → cb_mostrar_frame(idx)
       opens _frame_path(idx) → updates frame_preview

User clicks "Recortar pessoa (preview)"
  └─ btn_recortar → cb_recortar(idx)
       calls _remover_fundo_um(idx) [rembg u2net_human_seg, disk-cached]
       → updates frame_preview with RGBA cutout

User configures background (upload or AI) + mode + lighting params

User clicks "5. Pre-visualizar neste frame"
  └─ btn_preview → cb_preview(idx, modo, bg_*, prompt, ...)
       _obter_bg → resolves/generates background PIL image
       branch on modo:
         MODO_HD  → RVMMatter.compor (no rembg, directly from raw frame)
         MODO_RELIGHT → _remover_fundo_um + relight_frame (IC-Light)
         MODO_COMPOR  → _remover_fundo_um + compor_frame (alpha composite)
       → updates resultado_preview

User iterates steps 2–5 until satisfied

User clicks "Aplicar a todos os frames"
  └─ btn_aplicar → cb_aplicar(idx, modo, bg_*, ..., crf, progress)
       branch on modo:
         MODO_HD  → _obter_bg + render_matting(engine="rvm") + exportar_video
         others   → remover_fundo (batch rembg) + _obter_bg
                    + aplicar_relighting OR compor_batch
                    + exportar_video
       → updates video_out + file_out
```

## Frame Index Convention

Frames on disk are named `frame_00001.png` (1-based, 5-digit zero-padded). The slider is 0-based. Helper functions `_frame_path(idx)` and `_nobg_path(idx)` add 1 internally.

## Disk Cache for Single-Frame Cutout

`_remover_fundo_um(idx)` checks for an existing file at `frames_nobg/frame_{idx+1:05d}.png` before running rembg. This means iterating the frame slider re-uses previously cut frames without re-inference.

## Progress Reporting

`cb_aplicar` accepts `gr.Progress()` and calls `progress(fraction, desc=...)` at key milestones:

| Milestone | Fraction |
|---|---|
| Start background removal | 0.0 |
| Background resolved | 0.4 |
| Per-frame processing | 0.4 + 0.5 * (done/total) |
| Video assembly | 0.92 |
| Done | 1.0 |
