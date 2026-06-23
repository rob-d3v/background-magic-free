---
title: Source — plano_iclight_comfyui_colab.md (design plan)
type: source
created: 2026-06-14
updated: 2026-06-14
sources: ["plano_iclight_comfyui_colab.md"]
tags: [source, design-plan, colab, architecture]
---

# Source: plano_iclight_comfyui_colab.md

The **original design plan** (pt-BR) for the Colab pipeline, addressed to Claude Code as the implementer. It is the architectural seed of the project: it defines the 5-agent pipeline, the Colab/Drive environment, the file structure, and the per-agent responsibilities that became `pipeline.py` + `agentes/*.py`.

## What it specifies
- **Goal:** an automated pipeline that takes a recorded video, removes the background frame-by-frame, generates a new SD background, and reapplies coherent lighting with IC-Light — all on free Colab T4 GPU.
- **5-agent flow:** extração (ffmpeg) → remoção (rembg CUDA, RGBA) → geração de fundo (ComfyUI + SD 1.5 API) → relighting (IC-Light foreground-conditioned) → composição/exportação (ffmpeg + original audio).
- **Environment:** Colab T4 (~15GB VRAM), Google Drive mounted for persistence, Ubuntu 22.04.
- **File layout** under `/content/drive/MyDrive/iclight_pipeline/` (`input/`, `frames/raw`, `frames/nobg`, `background/bg.png`, `relit/`, `output/video_final.mp4`) — the hardcoded Colab paths now in `pipeline.py` (see [[entities/pipeline]] gotchas).

## How it relates to the code
This plan describes IC-Light as **foreground-conditioned (fc)**, which is what the current [[entities/relighting]] implements — including the limitation that the generated background isn't fed into denoising. The fc → fbc migration ([[decisions/migrate-fc-to-fbc]], [[concepts/ic-light]]) is the evolution beyond this original plan.

## Backs these pages
[[entities/pipeline]] and all 5 agent entities; [[concepts/ic-light]].

## Relacionados
[[overview/background-magic-free]] · [[sources/readme]] · [[sources/lumina-bg-notebook]] · [[index]]
