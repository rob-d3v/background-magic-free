---
title: "config.py — Paths and Device Detection"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - config.py
tags:
  - config
  - paths
  - gpu
  - colab
  - workspace
---

`config.py` provides two facilities used at startup by [[gradio-app-app-py]]: a dynamic workspace path resolver (`Paths`) and a GPU capability probe (`detectar_device`).

## Paths

`Paths(base=None)` resolves the workspace root via `resolver_base()` with this priority:

1. Explicit `base` argument.
2. `LUMINA_BASE` environment variable.
3. `/content/drive/MyDrive/iclight_pipeline` when running in Google Colab with Drive mounted.
4. `./workspace` (local default).

### Subdirectory Layout

| Attribute | Path fragment | Purpose |
|---|---|---|
| `input` | `{base}/input` | Uploaded source videos |
| `frames_raw` | `{base}/frames/raw` | Extracted raw frames (PNG) |
| `frames_nobg` | `{base}/frames/nobg` | Frames with background removed (RGBA PNG) |
| `frames_relit` | `{base}/relit` | Composited / relit frames (PNG) |
| `background_dir` | `{base}/background` | Background image(s) |
| `bg_output` | `{base}/background/bg.png` | Final resolved background used in pipeline |
| `preview_dir` | `{base}/preview` | Preview images (unused in current app.py flow) |
| `output_dir` | `{base}/output` | Final video output |
| `log_path` | `{base}/pipeline_log.json` | Pipeline progress log |

`criar_dirs()` creates all directories with `os.makedirs(..., exist_ok=True)` and returns `self`.

## detectar_device()

Returns a dict:

| Key | Type | Meaning |
|---|---|---|
| `device` | `"cuda"` \| `"cpu"` | PyTorch device string |
| `cuda` | `bool` | CUDA available |
| `gpu_name` | `str \| None` | `torch.cuda.get_device_name(0)` |
| `vram_gb` | `float \| None` | Total VRAM in GB (rounded to 1 decimal) |
| `pode_relight` | `bool` | `vram_gb >= 5.0` — gates IC-Light availability |

The `pode_relight` threshold is set to 5 GB with a note that IC-Light SD1.5 fp16 needs ~6 GB comfortably; 4 GB is risky even with offload. See [[gradio-app-gpu-gating]].
