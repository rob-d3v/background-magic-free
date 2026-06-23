---
title: "Deploy: Google Drive workspace (iclight_pipeline/)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb", "plano_iclight_comfyui_colab.md"]
tags: [entity, colab, deploy, google-drive, storage]
---

# Deploy: Google Drive workspace (iclight_pipeline/)

The Google Drive directory tree mounted at `/content/drive/MyDrive/iclight_pipeline/` serves as the persistent workspace for the Colab pipeline; it survives runtime disconnections and enables frame-level resume.

## Directory layout

```
MyDrive/iclight_pipeline/
├── input/
│   └── video.mp4                  ← user-uploaded source video
├── frames/
│   ├── raw/                       ← PNG frames extracted by ffmpeg (frame_00001.png …)
│   └── nobg/                      ← RGBA PNGs after rembg (same filenames)
├── background/
│   ├── bg.png                     ← active background (generated or resized custom)
│   └── bg_custom.png              ← user-uploaded background (optional; triggers bypass of SD step)
├── relit/
│   └── frame_00001.png …          ← IC-Light output frames (RGB)
├── output/
│   └── video_final.mp4            ← final exported video
└── pipeline_log.json              ← per-stage log with error counts
```

## Why Drive and not /content/ (ephemeral)

Colab free sessions disconnect after ~30–90 minutes. Storing frames and outputs on `/content/` (ephemeral) would lose all progress on disconnect. By writing to Drive, each completed frame is persisted; the agent-level skip-if-exists checks ([[concepts/deploy-colab-resume-mechanism]]) resume from the last completed frame on reconnect.

Model files (SD 1.5 checkpoint ~4GB, IC-Light weights ~0.5GB) are NOT stored on Drive — they live in `/content/ComfyUI/models/` and `/content/IC-Light/models/` and must be re-downloaded each session. Storing them on Drive would work but is not implemented; this is a known trade-off.

## Path constants in pipeline code

The notebook hardcodes `BASE_DIR = "/content/drive/MyDrive/iclight_pipeline"`. In the standalone `pipeline.py` (local/CLI use), paths are resolved dynamically via [[entities/pipeline-orchestrator-config]] using `LUMINA_BASE` env var or `--base` flag.

## Video upload logic

Cell 5 checks `os.path.exists(VIDEO_PATH)` first. If a video already exists on Drive from a previous session, upload is skipped and its metadata (resolution, fps, estimated frame count) is displayed. This prevents accidental re-upload and lets users resume without re-uploading large files.

## Related

[[entities/deploy-colab-notebook]] · [[concepts/deploy-colab-resume-mechanism]] · [[concepts/deploy-colab-cell-data-flow]] · [[entities/pipeline-orchestrator-config]] · [[index]]
