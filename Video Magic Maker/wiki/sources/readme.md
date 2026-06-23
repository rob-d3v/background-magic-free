---
title: Source — README.md (user guide, pt-BR)
type: source
created: 2026-06-14
updated: 2026-06-14
sources: ["README.md"]
tags: [source, readme, user-guide]
---

# Source: README.md

End-user usage guide for **lumina-bg / background-magic-free** (pt-BR), at the repo root. Marketing-light, task-focused: explains the two modes (Studio recorded vs Live), the Colab notebook flow, the local Gradio interface, and the camera GUI.

## What it covers
- **Pitch:** swap your video background and auto-adjust lighting, no green screen, free on Colab GPU.
- **Studio (recorded)** vs **Live (real-time)** comparison table — why Live doesn't relight (physics of 30fps on 4GB VRAM, not laziness).
- **Local interface:** `pip install -r requirements.txt; python app.py` → Gradio at `127.0.0.1:7860`, two tabs (Studio / Live), three Studio modes (HD-RVM / Compor / Relight-IC-Light).
- **Camera GUI:** `python camera_app.py` — cameras, record/photo/gallery, zoom/framing, mirror, brightness/contrast/saturation/sharpness, background (none/blur/image/looping video), virtual camera, settings persisted to `workspace/camera_app_config.json`.
- **Live CLI:** `python live.py --background fundo.jpg`, `--blur 45`, `--camera 1`, `--engine rvm`. Output is the **OBS Virtual Camera** (requires OBS Studio installed once on Windows).
- **Colab step-by-step:** 9-cell notebook (mount Drive → install → clone ComfyUI+IC-Light → download models ~4GB → upload video/bg → set prompt → run pipeline → preview → download). Resume-safe.
- **Perf tables:** matte fps by resolution (CPU); Colab T4 processing time by video duration (relight ~1.5s/frame is the bottleneck).
- **Tech list:** rembg, IC-Light, SD 1.5, ComfyUI, ffmpeg. MIT license.

## Backs these pages
[[overview/background-magic-free]] · [[entities/pipeline]] · [[entities/live-mode]] · [[entities/camera-app]] · [[entities/render-video]] · all agent entities.

## Relacionados
[[overview/background-magic-free]] · [[sources/plano-iclight-comfyui-colab]] · [[sources/lumina-bg-notebook]] · [[index]]
