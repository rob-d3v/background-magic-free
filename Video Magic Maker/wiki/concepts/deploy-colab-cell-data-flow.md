---
title: "Colab deploy: cell-by-cell data flow"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb"]
tags: [concept, colab, deploy, data-flow, pipeline]
---

# Colab deploy: cell-by-cell data flow

How data enters, transforms, and exits through the 9 notebook cells of [[entities/deploy-colab-notebook]], from raw video to final download.

## Data flow diagram

```
[User: GPU T4 runtime]
        │
Cell 1  │  drive.mount('/content/drive')
        │  → creates MyDrive/iclight_pipeline/ dirs
        ▼
Cell 2  │  apt-get + pip install
        │  → runtime has ffmpeg, rembg[gpu], diffusers, etc.
        ▼
Cell 3  │  git clone ComfyUI, IC-Light
        │  → /content/ComfyUI/, /content/IC-Light/
        ▼
Cell 4  │  hf_hub_download
        │  → /content/ComfyUI/models/checkpoints/v1-5-pruned-emaonly.safetensors
        │  → /content/IC-Light/models/iclight_sd15_fc.safetensors
        ▼
Cell 5  │  files.upload() → video.mp4 (required)
        │  files.upload() → bg_custom.png (optional)
        │  → Drive: input/video.mp4, background/bg_custom.png
        │  → sets USAR_FUNDO_PROPRIO flag
        ▼
Cell 6  │  Colab form widgets
        │  → Python vars: PROMPT, STEPS, SEED, CRF, CFG_BG, CFG_RELIGHT
        ▼
Cell 7  │  [5-stage pipeline]
        │
        │  Stage 1 (extracao): ffmpeg → Drive/frames/raw/frame_00001.png …
        │  Stage 2 (remocao):  rembg GPU → Drive/frames/nobg/frame_00001.png …
        │  Stage 3a (fundo IA): ComfyUI subprocess + SD 1.5 API → Drive/background/bg.png
        │  Stage 3b (fundo próprio): resize bg_custom.png → Drive/background/bg.png
        │  Stage 4 (relighting): IC-Light per frame → Drive/relit/frame_00001.png …
        │                        del pipe; torch.cuda.empty_cache()
        │  Stage 5 (exportacao): ffmpeg → Drive/output/video_final.mp4
        │
        │  → Drive/pipeline_log.json
        ▼
Cell 8  │  matplotlib 4-up preview
        │  reads: frames/raw/, frames/nobg/, background/bg.png, relit/
        │  → inline figure (original / no-bg / background / IC-Light result)
        ▼
Cell 9  │  files.download(video_final.mp4)
        │  → user browser download
```

## Key branch: AI background vs. custom background

The `USAR_FUNDO_PROPRIO` boolean is set in cell 5 if the user uploads `bg_custom.png`. Cell 7 reads it:

- **False (default):** ComfyUI is started as a subprocess (`iniciar_comfyui()`), a JSON workflow is POSTed to `http://127.0.0.1:8188/prompt`, and the result image is polled and saved. ComfyUI is then `terminate()`d. `PROMPT` drives both the background generation (`CFG_BG`) and the IC-Light relighting step.
- **True:** `bg_custom.png` is resized to match the video dimensions and saved as `bg.png`. The SD stage is entirely skipped; IC-Light still uses `PROMPT` to adjust the lighting description.

## VRAM management in cell 7

After the IC-Light stage completes, the pipeline explicitly calls `del pipe` and `torch.cuda.empty_cache()` before starting the ffmpeg export stage. This frees ~8–10 GB of VRAM used by the diffusion model, avoiding OOM on the ffmpeg/PIL operations that follow.

## ComfyUI as transient subprocess

ComfyUI is launched in cell 7, not at startup, and is terminated immediately after background generation completes. It is never exposed to the user as a running server. Communication is via its REST API on `localhost:8188`. See [[entities/geracao_fundo]] for the JSON workflow format.

## Timing reference (T4 free, 1 min of video ≈ 1800 frames)

| Stage | Per-frame time | 1800-frame total |
|---|---|---|
| ffmpeg extraction | ~1 ms | ~2 s |
| rembg (GPU) | ~0.3 s | ~9 min |
| SD 1.5 background (once) | — | ~15 s |
| IC-Light relighting | ~1.5 s | ~45 min |
| ffmpeg export | ~2 ms | ~4 s |
| **Total** | | **~55 min** |

## Related

[[entities/deploy-colab-notebook]] · [[entities/deploy-colab-drive-workspace]] · [[concepts/deploy-colab-resume-mechanism]] · [[concepts/deploy-colab-module-bootstrap]] · [[entities/geracao_fundo]] · [[entities/relighting]] · [[index]]
