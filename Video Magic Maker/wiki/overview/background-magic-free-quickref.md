---
title: background-magic-free — Quickref (operating contract)
type: overview
created: 2026-06-23
updated: 2026-06-23
sources: ["README.md", "pipeline.py", "app.py", "camera_app.py", "live.py", "config.py", "lumina_bg.ipynb"]
tags: [overview, quickref, operating-contract, video, matting, relighting, diffusion]
---

# background-magic-free — Quickref

**Read this first.** One dense map of the project. For specifics, run `secondbrain.py search "<terms>"` and read the top 1-3 hits — do not bulk-read `wiki/`. See the full front door at [[overview/background-magic-free]].

## What it is

**background-magic-free** (internal name **lumina-bg**) — free, no-green-screen tool that swaps the background behind a person in a video and optionally relights the person to match. Heavy path runs free on Google Colab (GPU T4); light paths run locally on CPU. MIT, by [@rob-d3v](https://github.com/rob-d3v).

Flow: cut person out (AI matting) → put new background (AI-generated SD 1.5 prompt, or uploaded image/video) → optionally relight (IC-Light) → export with original audio.

## Stack

- **Matting:** rembg `u2net_human_seg` (ONNX) · MediaPipe Selfie Segmenter · RVM (RobustVideoMatting, torch.hub)
- **Background gen:** Stable Diffusion 1.5 via ComfyUI API ([[concepts/sd15-background-generation]])
- **Relight:** IC-Light over SD 1.5 ([[concepts/ic-light]])
- **Video I/O:** ffmpeg / ffprobe · **Virtual cam:** pyvirtualcam → OBS Virtual Camera (Windows)
- **UIs:** Tkinter + PIL (desktop) · Gradio 4.x (web) · Jupyter (Colab notebook)
- **Compute:** torch CPU-only locally (Win, GTX 1650 Ti 4GB, Python 3.13); SD + IC-Light need Colab T4

## How to run / build / deploy

- **Web UI (Studio, local):** `python app.py` → Gradio Blocks, indigo Soft theme, ~509 lines. Three modes below. (per [[sources/gradio-app-source-app-py]], [[entities/gradio-app-app-py]])
- **Desktop live GUI:** `python camera_app.py` → Tkinter record/photo/gallery + virtual cam ([[entities/camera-app]]).
- **Live CLI:** `python live.py` → webcam → virtual camera ([[entities/live-mode]], [[entities/live-mode-cli]]).
- **Batch / GPU pipeline:** `lumina_bg.ipynb` on Colab — the primary GPU distribution artifact, self-contained 9 cells, self-clones repo to load `agentes/` ([[entities/deploy-colab-notebook]], [[concepts/deploy-colab-module-bootstrap]]). Persists to Google Drive `iclight_pipeline/` for resume-after-disconnect ([[entities/deploy-colab-drive-workspace]], [[concepts/deploy-colab-resume-mechanism]]).
- **Paths config:** `config.py` central path/device resolution; de-hardcodes the old Colab paths ([[entities/pipeline-orchestrator-config]], [[decisions/pipeline-orchestrator-paths-refactor]], [[sources/pipeline-orchestrator-config-py]]).

## Two operating modes (core design split)

- **Studio** (recorded/offline): matte + new bg, optionally relight (GPU). Seconds/frame batch.
- **Live** (real-time): matte + new bg, **no relight** (per-frame relight can't hit 30fps on 4GB VRAM). ~real-time CPU.

Honest split (per [[decisions/local-vs-colab]], [[concepts/gpu-vram-local-vs-colab]]).

## Studio modes (Gradio `app.py`)

- **HD** (`MODO_HD`) — RVM frame-by-frame matte, no rembg/relight; best CPU edge → [[entities/render-video]]
- **Compor** (`MODO_COMPOR`) — rembg + CPU compositing → [[entities/composicao]]
- **Relight** (`MODO_RELIGHT`) — IC-Light, needs GPU → [[entities/relighting]]

Default = Relight if GPU present, else HD ([[concepts/gradio-app-gpu-gating]], [[concepts/gradio-app-processing-modes]]).

## Studio batch pipeline (5 agents)

[[entities/extracao]] (ffmpeg → frames) → [[entities/remocao]] (rembg → RGBA) → [[entities/geracao_fundo]] (ComfyUI+SD1.5 → bg.png) → [[entities/relighting]] (IC-Light) → [[entities/exportacao]] (ffmpeg + original audio). Orchestrated by [[entities/pipeline]] ([[concepts/pipeline-orchestrator-call-sequence]], [[concepts/pipeline-orchestrator-mode-selection]]). CPU-fallback compositing path: [[entities/composicao]].

## Live mode internals

Webcam → matte → bg swap → virtual camera. Two engines: MediaPipe (fast, default — [[concepts/realtime-matting]]) and RVM (true alpha, keeps hair — [[concepts/rvm-matting]]). See [[entities/live-mode-livematter-class]], [[concepts/live-mode-frame-pipeline]], [[concepts/live-mode-edge-refinement]]. Desktop GUI internals: [[concepts/camera-app-gui-dual-thread-frame-pipeline]], [[concepts/camera-app-gui-dark-theme]], [[concepts/camera-app-gui-gallery-recording]], [[concepts/camera-app-gui-video-edit-mode]].

## Image adjustments

Post-composition brightness/contrast/transform applied as a stateless pure function with a dirty-flag cache: [[entities/image-adjustments-agent-ajustes-module]], [[concepts/image-adjustments-agent-transform-internals]], [[decisions/image-adjustments-agent-stateless-pure-function]], [[decisions/image-adjustments-agent-fixed-transform-order]]. Gap in render-video path: [[concepts/image-adjustments-agent-render-video-gap]].

## Key file paths

- `app.py` — Gradio web UI entry · `camera_app.py` — Tkinter desktop GUI · `live.py` — live CLI
- `pipeline.py` — Studio batch orchestrator · `config.py` — central paths/device
- `agentes/` — pipeline agent package (extração, remoção, geração_fundo, relighting, exportação)
- `lumina_bg.ipynb` — Colab GPU notebook · Colab workspace: `/content/drive/MyDrive/iclight_pipeline/`

## Gotchas (read before editing)

- **Relighting has 2 verified bugs** in the `fc` implementation: (1) generated bg loaded but never used in denoising; (2) IC-Light weights loaded as state_dict instead of offset-merged onto base UNet. Tracked in [[entities/relighting]], [[concepts/ic-light]], [[decisions/migrate-fc-to-fbc]] (fc → fbc).
- **Colab paths were hardcoded** (`/content/drive/MyDrive/iclight_pipeline`); `config.py` de-hardcodes them ([[decisions/pipeline-orchestrator-paths-refactor]]).
- **Notebook ↔ agent mismatch** between Colab IC-Light setup cells and `agentes/relighting.py` ([[concepts/ic-light-integration-notebook-agent-mismatch]]).
- Locally developed surface = HD/RVM + live (no GPU); Colab IC-Light path = original notebook flow.
- Detail pages (`entities/`, `concepts/`, `decisions/`) are **pt-BR**; overview/sources English.

## Don't waste time on (vendored / generated / migration cruft)

- `node_modules/`, `dist/`, `build/` if present — skip.
- The old root brain `background-magic-free/wiki/` — superseded; **this** vault is canonical (see Migration note in [[overview/background-magic-free]]).
- Vendored model weights / ONNX / torch.hub caches — generated, not source.
