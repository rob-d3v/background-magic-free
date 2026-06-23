---
title: Studio Mode — Inter-Agent Data Flow
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - "agentes/extracao.py"
  - "agentes/remocao.py"
  - "agentes/geracao_fundo.py"
  - "agentes/relighting.py"
  - "agentes/exportacao.py"
tags: [pipeline, data-flow, studio-mode, frames, latent]
---
# Studio Mode — Inter-Agent Data Flow

End-to-end data flow through the five studio-pipeline agents, covering what each agent consumes, what it produces, and which values are passed in memory vs on-disk.

## Overview

```
video.mp4
  │
  ▼ Agent 1 — extracao (ffprobe + ffmpeg)
  │  produces: frames/raw/frame_%05d.png  (RGB24 PNG)
  │  returns in-memory: {fps, total_frames, width, height}
  │
  ▼ Agent 2 — remocao (rembg / u2net_human_seg)
  │  consumes: frames/raw/  (RGB24 PNGs)
  │  produces: frames/nobg/ (RGBA PNGs — background cut)
  │
  ▼ Agent 3 — geracao_fundo (SD 1.5)      [optional if user supplies bg]
  │  consumes: prompt text, target dimensions
  │  produces: bg.png  (single RGB image, same W×H as video)
  │
  ▼ Agent 4 — relighting (IC-Light fbc, 12-ch UNet)
  │  consumes: frames/nobg/ (RGBA) + bg.png (RGB)
  │  produces: relit/frame_%05d.png  (RGB, person composited + relit)
  │
  ▼ Agent 5 — exportacao (ffmpeg libx264 + aac mux)
     consumes: relit/frame_%05d.png + original video (for audio)
     produces: output/video_final.mp4
```

## In-memory values passed between agents

`fps` (float) — extracted by Agent 1, passed directly to Agent 5's `exportar_video` call. This is critical: if the export uses a different FPS than extraction, the output video plays at wrong speed and audio drifts.

`width`, `height` (int) — extracted by Agent 1; used by Agent 3 to generate the background at matching resolution. Agent 4 independently derives its output dimensions from the first nobg frame (rounded to multiples of 64).

`largura`, `altura` (int, Agent 4 output) — the actual pixel dimensions after rounding to `mult64`, returned by `aplicar_relighting`. Used by the orchestrator to know the true output resolution.

## Pixel format transitions

| Stage | Format | Notes |
|---|---|---|
| Input video | YUV (container) | Any container format |
| frames/raw/ | RGB24 PNG | ffmpeg `-pix_fmt rgb24` strips alpha/YUV |
| frames/nobg/ | RGBA PNG | rembg adds alpha channel (background = transparent) |
| bg.png | RGB PNG | No alpha; static image |
| IC-Light input | float16 latents | fg composited over grey (127,127,127) before VAE-encode |
| relit/ | RGB PNG | IC-Light output is RGB (person+bg composited, no alpha) |
| video_final.mp4 | yuv420p H.264 | ffmpeg `-pix_fmt yuv420p` for player compatibility |

## Agent 4 latent conditioning — the 12-channel concatenation

The key non-obvious data flow is inside Agent 4's denoising loop:

```python
# At each timestep t:
model_in = torch.cat([scaled, fg_latent, bg_latent], dim=1)
# scaled   = 4ch noisy latent (the thing being denoised)
# fg_latent = 4ch VAE encode of (fg RGBA composited over grey 127)
# bg_latent = 4ch VAE encode of (bg RGB, center-cropped to same dims)
# total: 12 channels — this is what the IC-Light fbc UNet expects
```

The foreground is pre-composited over neutral grey before encoding so the model sees a pixel-level hint of the subject shape and colour without a hard alpha edge. This is the "fbc" (foreground + background conditioned) conditioning strategy described in the lllyasviel/IC-Light paper.

## Dimension alignment

Agent 4 normalises all frame dimensions to multiples of 64 (`_mult64(x) = max(64, (x//64)*64)`) and fixes that resolution for the entire batch from the first frame. This ensures all relit frames have the same resolution, which is required for ffmpeg to assemble them into a valid video stream.

Agent 3's background is generated at the original video `width × height` (from Agent 1 metadata). Agent 4 center-crops the background to its own `mult64` target during preprocessing (`_resize_center_crop`), so small dimension mismatches are handled automatically.

## Error isolation

Each agent reports per-frame errors without aborting the batch. Agents 2 and 4 collect errors in a list and write them to `pipeline_log.json` (keys `remocao_fundo_erros` and `relighting_erros` respectively) when `log_path` is provided. A failed frame in Agent 2 means no RGBA output for that frame; Agent 4 will then fail on the same frame for a different reason (missing input). The result is a gap in `relit/` that ffmpeg fills with whatever the last decodable frame was (error concealment).

## Related

[[entities/studio-mode-agents-pipeline]] · [[concepts/studio-mode-agents-resume-strategy]] · [[concepts/agent-relighting-channel-layout]] · [[concepts/agent-relighting-denoising-loop]] · [[concepts/video-frame-pipeline]] · [[index]]
