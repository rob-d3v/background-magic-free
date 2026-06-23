---
title: background-magic-free (lumina-bg) — Overview
type: overview
created: 2026-06-14
updated: 2026-06-14
sources: ["README.md", "pipeline.py", "app.py", "camera_app.py", "live.py", "plano_iclight_comfyui_colab.md", "lumina_bg.ipynb"]
tags: [overview, video, background-removal, relighting, matting, diffusion]
---

# background-magic-free (lumina-bg)

**background-magic-free** (internal name **lumina-bg**) is a free, no-green-screen tool that swaps the background of a person video and optionally relights the person to match the new environment. It runs free on Google Colab (GPU) for the heavy path, and locally on CPU for the lightweight paths. Repo by [@rob-d3v](https://github.com/rob-d3v), MIT-licensed.

> **Start here:** read [[overview/background-magic-free-quickref]] first — dense operating contract (stack, run/build/deploy, subsystems, gotchas). This page is the long-form front door.

> Migrated from a pre-existing `wiki/` brain at the repo root (19 pages: 10 components, 7 concepts, 2 decisions). See [[#Migration note]]. Original brain language is **pt-BR** — most detail pages are in Portuguese; this overview front door is in English.

## What it does

You record a video (phone, webcam, anything) and the tool:
1. **Cuts you out** of every frame with AI matting (no green screen).
2. **Puts a new background** behind you — either AI-generated from a text prompt (Stable Diffusion 1.5) or your own uploaded image/video.
3. **Optionally relights you** (IC-Light) so it looks like you're really in that environment.
4. **Exports the final video** with the original audio.

## Two operating modes

| | **Studio** (recorded / offline) | **Live** (real-time) |
|---|---|---|
| Use | YouTube / recorded content | Meet, Zoom, OBS, streaming |
| How | matte + new background, optionally **relight** | matte + new background, **no relight** |
| Relights you? | Yes (IC-Light, GPU) | No — per-frame relight can't hit 30fps on 4GB VRAM |
| Speed | seconds/frame (batch) | ~real-time on webcam (CPU) |
| Where | GPU (Colab T4) for relight; RVM path runs CPU | local PC (CPU) |

The honest two-mode split — relight only in offline mode — is a core design fact (per [[decisions/local-vs-colab]], [[concepts/gpu-vram-local-vs-colab]]).

## Pipeline (Studio batch)

The original Colab pipeline (`pipeline.py`, the [[entities/pipeline|orchestrator]]) chains **5 agents**:

[[entities/extracao|extração]] (ffmpeg → frames) → [[entities/remocao|remoção]] (rembg `u2net_human_seg` → RGBA) → [[entities/geracao_fundo|geração_fundo]] (ComfyUI + SD 1.5 → bg.png) → [[entities/relighting|relighting]] (IC-Light) → [[entities/exportacao|exportação]] (ffmpeg + original audio).

CPU fallback without relight: [[entities/composicao|composição]] (Agente 4b, Pillow alpha compositing).

## Three Studio modes (Gradio `app.py`)

- **HD** (`MODO_HD`) — RVM frame-by-frame matte, no rembg, no relight; best CPU edge → [[entities/render-video]].
- **Compor** (`MODO_COMPOR`) — rembg + CPU compositing → [[entities/composicao]].
- **Relight** (`MODO_RELIGHT`) — IC-Light, needs GPU → [[entities/relighting]].

Default = Relight if a GPU is present, else HD.

## Live mode

Real-time webcam background swap published to a **virtual camera** (OBS Virtual Camera) so Meet/Zoom/OBS see it. CLI is [[entities/live-mode]]; the recommended front-end is the desktop GUI [[entities/camera-app]] (Tkinter: record/photo/gallery, zoom/framing, brightness/contrast, virtual cam, embedded video-render mode). Two matte engines: MediaPipe (fast, default — [[concepts/realtime-matting]]) and RVM (true alpha, keeps hair — [[concepts/rvm-matting]]).

## Stack

- **Matting:** rembg `u2net_human_seg` (ONNX) · MediaPipe Selfie Segmenter · RVM (RobustVideoMatting, torch.hub)
- **Background gen:** Stable Diffusion 1.5 via ComfyUI API ([[concepts/sd15-background-generation]])
- **Relight:** IC-Light over SD 1.5 ([[concepts/ic-light]])
- **Video I/O:** ffmpeg / ffprobe ([[entities/extracao]], [[entities/exportacao]])
- **Virtual cam:** pyvirtualcam → OBS Virtual Camera (Windows)
- **GUI:** Tkinter + PIL ImageTk · **Web UI:** Gradio
- **Compute:** torch CPU-only locally (Win, GTX 1650 Ti 4GB, Python 3.13); SD + IC-Light require Colab T4 GPU

## Current state & known issues

- **Relighting has 2 verified bugs** in the current `fc` implementation: (1) the generated background is loaded but never used in denoising; (2) IC-Light weights are loaded as a state_dict instead of being offset-merged onto the base UNet. Both tracked in [[entities/relighting]], [[concepts/ic-light]] and the migration decision [[decisions/migrate-fc-to-fbc]] (fc → fbc).
- **Colab paths are hardcoded** (`/content/drive/MyDrive/iclight_pipeline`) in `pipeline.py` — needs parametrizing to run the batch pipeline locally.
- The local-runnable, no-GPU path (HD/RVM + live) is the actively developed surface; the Colab IC-Light path is the original notebook flow.

## Key concepts

[[concepts/ic-light]] · [[concepts/rembg-background-removal]] · [[concepts/sd15-background-generation]] · [[concepts/realtime-matting]] · [[concepts/rvm-matting]] · [[concepts/video-frame-pipeline]] · [[concepts/gpu-vram-local-vs-colab]]

## Decisions

[[decisions/migrate-fc-to-fbc]] · [[decisions/local-vs-colab]]

## Sources

[[sources/readme]] · [[sources/plano-iclight-comfyui-colab]] · [[sources/lumina-bg-notebook]]

## Detailed subsystem pages

- **Live desktop GUI (`camera_app.py`):** [[concepts/camera-app-gui-dark-theme]] · [[concepts/camera-app-gui-gallery-recording]] · [[concepts/camera-app-gui-dual-thread-frame-pipeline]] · [[concepts/camera-app-gui-video-edit-mode]]
- **Image adjustments:** [[concepts/image-adjustments-agent-render-video-gap]] · [[decisions/image-adjustments-agent-stateless-pure-function]] · [[decisions/image-adjustments-agent-fixed-transform-order]]
- **Composition / render-video (CPU):** [[decisions/composicao-render-video-dois-caminhos-cpu]] · [[decisions/composicao-render-video-ffmpeg-audio-mux]]
- **Source pages:** [[sources/gradio-app-source-app-py]] (`app.py`) · [[sources/gradio-app-source-config-py]] (`config.py` for Gradio) · [[sources/pipeline-orchestrator-config-py]] (`config.py`) · [[sources/agent-background-generation-geracao-fundo-py]] (`geracao_fundo.py`) · [[sources/agent-background-removal-remocao-py]] (`remocao.py`) · [[sources/image-adjustments-agent-ajustes-py]] (`ajustes.py`)

## Generic knowledge → shared base

This is an ML/video project, so most knowledge is project-specific. The LLM-wiki maintenance pattern itself lives once in the shared base: `agents/second-brain/shared/wiki/concepts/llm-wiki-pattern.md`.

## Migration note

This brain was migrated on 2026-06-14 from a pre-existing, well-maintained `wiki/` at the **repo root** (`background-magic-free/wiki/`) into this Obsidian vault under the second-brain layout. Mapping: `components/` → `entities/`, `concepts/` → `concepts/`, `decisions/` → `decisions/`. Wikilinks `[[components/x]]` were rewritten to `[[entities/x]]`. Original frontmatter (`status`, `source`, `date`) is preserved under `status` / `original-date` / `migrated-from`. The old root `wiki/` was left untouched (not deleted) — it can be removed once this vault is confirmed as the canonical brain.
