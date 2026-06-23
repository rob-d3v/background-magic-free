---
title: Studio Mode — Five-Agent Pipeline
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - "agentes/extracao.py"
  - "agentes/remocao.py"
  - "agentes/geracao_fundo.py"
  - "agentes/relighting.py"
  - "agentes/exportacao.py"
tags: [pipeline, studio-mode, agents, overview]
---
# Studio Mode — Five-Agent Pipeline

The studio-mode pipeline processes an input video through five sequential agents — frame extraction, background removal, background generation, relighting, and final export — each implemented as a single Python module under `agentes/`.

## Agent roster

| # | Module | Key function(s) | Runtime | Resume |
|---|---|---|---|---|
| 1 | `agentes/extracao.py` | `extrair_frames(video_path, output_dir)` | CPU / ffmpeg | No |
| 2 | `agentes/remocao.py` | `remover_fundo(frames_dir, output_dir, log_path)` | GPU (onnxruntime) | Yes |
| 3 | `agentes/geracao_fundo.py` | `gerar_fundo(...)` / `gerar_fundo_diffusers(...)` | GPU (CUDA) | N/A (one image) |
| 4 | `agentes/relighting.py` | `carregar_iclight(...)` + `relight_frame(...)` + `aplicar_relighting(...)` | GPU (CUDA, ≥5 GB VRAM) | Yes |
| 5 | `agentes/exportacao.py` | `exportar_video(frames_dir, video_original, output_path, fps, crf)` | CPU / ffmpeg | No |

## Directory layout produced

```
<workspace>/
  frames/
    raw/          ← Agent 1: frame_00001.png … frame_NNNNN.png (RGB24)
    nobg/         ← Agent 2: frame_00001.png … (RGBA, background removed)
  bg.png          ← Agent 3: single static background image
  relit/          ← Agent 4: frame_00001.png … (RGB, person composited+relit)
  output/
    video_final.mp4  ← Agent 5: H.264 + AAC, original audio reattached
```

## Data flow summary

1. `extracao` → returns `{fps, total_frames, width, height, tempo_s}`. FPS is threaded through to `exportacao` to preserve A/V sync.
2. `remocao` → consumes `frames/raw/`, produces `frames/nobg/` (RGBA PNGs). Supports per-frame resume.
3. `geracao_fundo` → produces a single `bg.png` from a text prompt. Either via ComfyUI HTTP API (pipeline/Colab) or diffusers (Gradio UI). May be skipped entirely when the user supplies their own background.
4. `relighting` — the costliest step (~1.5 s/frame on T4) — composites each RGBA frame over `bg.png` using IC-Light fbc (12-channel UNet conditioned on both foreground and background). Supports per-frame resume. Returns `{processados, erros, tempo_s, largura, altura}`.
5. `exportacao` → encodes `relit/` frames as H.264 (`crf=18`, `preset=slow`), then muxes the original audio (AAC) via a two-pass ffmpeg strategy.

For full per-agent detail see:
- [[entities/extracao]] · [[entities/remocao]] · [[entities/geracao_fundo]] · [[entities/relighting]] · [[entities/exportacao]]

## Execution contexts

The same five modules are called in two different orchestration contexts:

| Context | Orchestrator | Notes |
|---|---|---|
| CLI / Colab | `pipeline.py` | Sequential, runs all 5 steps; uses `gerar_fundo` (ComfyUI backend) |
| Gradio UI | `app.py` | User-driven, steps invoked via button callbacks; uses `gerar_fundo_diffusers` |

## Related

[[concepts/studio-mode-agents-data-flow]] · [[concepts/studio-mode-agents-resume-strategy]] · [[decisions/studio-mode-agents-agent-boundaries]] · [[concepts/video-frame-pipeline]] · [[entities/pipeline]] · [[index]]
