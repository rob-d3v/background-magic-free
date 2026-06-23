---
title: "Deploy: lumina_bg.ipynb — Colab GPU notebook"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb", "plano_iclight_comfyui_colab.md"]
tags: [entity, colab, deploy, notebook, gpu]
---

# Deploy: lumina_bg.ipynb — Colab GPU notebook

The primary user-facing distribution artifact for GPU-required pipeline modes; a self-contained 9-cell Jupyter notebook designed to run on Google Colab with a free T4 GPU.

## Role in the system

`lumina_bg.ipynb` is the **only officially supported path** for running the SD 1.5 background generation and IC-Light relighting stages. The local `app.py` / `camera_app.py` entry points expose only GPU-free modes (RVM matting, compose, live camera) on machines with insufficient VRAM. See [[decisions/local-vs-colab]] and [[concepts/gpu-vram-local-vs-colab]].

## Cell sequence

| # | Cell title | What it does |
|---|---|---|
| 1 | Mount Google Drive | Calls `drive.mount('/content/drive')` and creates the `iclight_pipeline/` directory tree under `MyDrive`. |
| 2 | Install dependencies | `apt-get ffmpeg` + pip install (torch cu118, rembg[gpu], onnxruntime-gpu, diffusers, transformers, accelerate, safetensors, opencv-python, Pillow, huggingface_hub). |
| 3 | Clone ComfyUI + IC-Light | `git clone --depth 1` of both repos into `/content/`; installs their `requirements.txt`. Skips if dirs already exist (idempotent). |
| 4 | Download models | `hf_hub_download` for SD 1.5 checkpoint (`runwayml/stable-diffusion-v1-5 → v1-5-pruned-emaonly.safetensors`) and IC-Light weights (`lllyasviel/ic-light → iclight_sd15_fc.safetensors`). Skips if files exist. |
| 5 | Upload video + optional bg | `files.upload()` widget for source video (saved as `input/video.mp4` on Drive). Optionally upload a custom background image (saved as `background/bg_custom.png`) — if provided, SD generation in step 7 is bypassed. Reports video metadata via `ffprobe`. |
| 6 | Configure prompt + params | Colab form widget (`#@param`). Sets `PROMPT`, `STEPS` (10–50), `SEED`, `CRF` (H.264 quality), `CFG_BG` (SD guidance), `CFG_RELIGHT` (IC-Light guidance, default 2.0). |
| 7 | Execute pipeline | The main orchestration cell. Clones the `background-magic-free` repo to get the `agentes/` modules, then runs the 5-stage pipeline: extraction → bg removal → bg generation/passthrough → relighting → export. Writes `pipeline_log.json`. |
| 8 | Preview (before/after) | 4-up matplotlib figure of the middle frame: original, no-bg, background used (generated or custom), IC-Light result. |
| 9 | Download final video | `files.download()` for `output/video_final.mp4`; also prints its Drive path. |

## Runtime requirement

GPU T4 must be selected manually: `Runtime > Change runtime type > GPU (T4)`. The pipeline cell validates `torch.cuda.is_available()` and raises `RuntimeError` if GPU is absent.

## Repo self-cloning in cell 7

Cell 7 dynamically clones `https://github.com/rob-d3v/background-magic-free` into `/content/lumina-bg` to obtain the `agentes/` package. The clone is skipped if `agentes/` is already present in `/content/`. This makes the notebook self-sufficient — the user only opens the `.ipynb`, no manual repo clone needed. See [[concepts/deploy-colab-module-bootstrap]].

## Idempotency and resume

All install and model-download steps check existence before acting; the pipeline cell's agents skip already-processed frames. See [[concepts/deploy-colab-resume-mechanism]].

## Outputs persisted to Drive

- `iclight_pipeline/output/video_final.mp4` — final video
- `iclight_pipeline/background/bg.png` — generated or resized background
- `iclight_pipeline/pipeline_log.json` — per-stage log with error frame counts

## Related

[[concepts/deploy-colab-cell-data-flow]] · [[concepts/deploy-colab-resume-mechanism]] · [[concepts/deploy-colab-module-bootstrap]] · [[decisions/deploy-colab-primary-gpu-path]] · [[sources/lumina-bg-notebook]] · [[entities/pipeline]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
