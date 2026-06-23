---
title: Source — lumina_bg.ipynb (Colab notebook)
type: source
created: 2026-06-14
updated: 2026-06-14
sources: ["lumina_bg.ipynb"]
tags: [source, notebook, colab]
---

# Source: lumina_bg.ipynb

The **9-step Colab notebook** that runs the full Studio (batch, GPU) pipeline end-to-end. It is the user-facing driver of `pipeline.py` on Colab; the README's step-by-step maps to its cells.

## Cells (9 logical steps)
1. **Mount Google Drive** — creates the `iclight_pipeline/` folder tree on Drive.
2. **Install dependencies** — `apt-get ffmpeg` + pip installs.
3. **Clone ComfyUI + IC-Light** repos into `/content/`.
4. **Download models** — SD 1.5 checkpoint (`v1-5-pruned-emaonly.safetensors`) for ComfyUI + IC-Light weights (~4GB total) via `hf_hub_download`.
5. **Upload video + optional background** — video required; own background optional (skips SD generation if provided).
6. **Configure prompt + params** (Colab form UI) — prompt drives background generation and/or IC-Light lighting description; steps/seed/quality.
7. **Run pipeline** — the main cell; imports torch/PIL and runs the orchestrator. Resume-safe (re-run continues from existing frames).
8. **Preview** — 4-up matplotlib: original, no-bg, generated bg, final result.
9. **Download** final video (also saved to `Drive/.../output/video_final.mp4`).

## Notes
- Requires GPU runtime (T4); SD + IC-Light won't run on CPU.
- The notebook is the GPU/Colab entry point; the local CPU paths (HD/RVM, live, camera GUI) are driven instead by `app.py` and `camera_app.py` (see [[sources/readme]]).
- Resume: re-running cell 7 skips already-processed frames ([[concepts/video-frame-pipeline]]).
- > ⚠️ Cells 3–4 are outdated post fc→fbc migration: cell 4 downloads `iclight_sd15_fc.safetensors` (unused) and clones the IC-Light repo (unused); the agent uses `fbc` via HF Hub cache. See [[concepts/ic-light-integration-notebook-agent-mismatch]].

## Backs these pages
[[entities/pipeline]] · [[overview/background-magic-free]] · [[concepts/video-frame-pipeline]].

## Relacionados
[[overview/background-magic-free]] · [[sources/readme]] · [[sources/plano-iclight-comfyui-colab]] ·
[[concepts/ic-light-integration-colab-setup]] ·
[[concepts/ic-light-integration-notebook-agent-mismatch]] · [[index]]
