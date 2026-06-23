---
title: "Gradio App — Three Processing Modes"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
  - config.py
tags:
  - modes
  - rvm
  - rembg
  - ic-light
  - gpu
  - cpu
---

`app.py` offers three processing modes selectable by the user, gated by GPU availability. The default mode at startup depends on what `detectar_device()` reports.

## Mode Definitions

| Constant | Label | Matting | Compositing | GPU Required |
|---|---|---|---|---|
| `MODO_HD` | "Trocar fundo HD (RVM, CPU)" | RVMMatter (RVM) | `render_matting(engine="rvm")` | No |
| `MODO_COMPOR` | "Compor (rapido, CPU)" | rembg u2net_human_seg | `compor_frame` / `compor_batch` | No |
| `MODO_RELIGHT` | "Reiluminar (IC-Light, GPU)" | rembg u2net_human_seg | IC-Light diffusion | Yes (`pode_relight`) |

## Default Mode Selection

```python
MODO_DEFAULT = MODO_RELIGHT if DEV["pode_relight"] else MODO_HD
```

Note that `MODO_COMPOR` is never the default — either relight (best quality, GPU) or HD (best quality CPU path).

## Per-Mode Preview Path (cb_preview)

- **HD**: reads raw frame → `cobrir` (resize/crop BG) → `RVMMatter.compor` with `color_match=0.12, feather=2`.
- **Relight**: `_remover_fundo_um` (rembg, cached) → `_obter_bg` → `relight_frame(pipe, fg, bg, ...)`.
- **Compor**: `_remover_fundo_um` → `_obter_bg` → `compor_frame(fg, bg)`.

## Per-Mode Render Path (cb_aplicar)

- **HD**: `_obter_bg` + wipes `frames_relit` dir (RVM is stateful, needs clean run) → `render_matting(engine="rvm")` → `exportar_video`.
- **Compor**: batch `remover_fundo` (rembg all frames) → `_obter_bg` → `compor_batch` → `exportar_video`.
- **Relight**: batch `remover_fundo` → `_obter_bg` → `aplicar_relighting` → `exportar_video`.

## GPU Error Handling

If the user selects "Gerar com IA" background without CUDA, `_obter_bg` raises `gr.Error`. If the user selects Relight without `pode_relight`, `cb_preview` and `cb_aplicar` both raise `gr.Error` with a Colab suggestion.

## Lazy Model Loading

All heavy models are loaded on first use (lazy globals), not at import time:

- `_rembg_session()` → `new_session("u2net_human_seg")`
- `_relight_pipe()` → `carregar_iclight(device="cuda", low_vram=(vram < 8.0))`
- `_offline_matter()` → `RVMMatter()` + `.reset()` per call
- `_live_matter()` → `LiveMatter()` (singleton, not reset between calls)
