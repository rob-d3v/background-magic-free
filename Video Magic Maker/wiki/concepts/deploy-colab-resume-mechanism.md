---
title: "Colab deploy: frame-level resume mechanism"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb", "plano_iclight_comfyui_colab.md"]
tags: [concept, colab, deploy, resume, reliability]
---

# Colab deploy: frame-level resume mechanism

The notebook pipeline is designed to survive Colab free-tier disconnections (which occur after ~30–90 min) by writing all intermediate outputs to Google Drive and skipping already-completed work on re-run.

## How it works

Every per-frame processing loop in the `agentes/` modules checks for the existence of the output file before processing:

```python
if os.path.exists(output_path):
    continue  # resume automático se interrompido
```

This pattern is present in:
- `agentes/remocao.py` — `frames/nobg/` PNGs
- `agentes/relighting.py` — `relit/` PNGs

Model downloads (cell 4) also check existence before calling `hf_hub_download`. ComfyUI and IC-Light clones (cell 3) skip if the target directory already exists. The video upload (cell 5) checks if `input/video.mp4` is already on Drive.

## Resume granularity

| Stage | Resume unit | Persisted where |
|---|---|---|
| Extraction (ffmpeg) | entire stage | Drive/frames/raw/ |
| Background removal (rembg) | per frame | Drive/frames/nobg/ |
| Background generation (SD) | entire stage (one image) | Drive/background/bg.png |
| Relighting (IC-Light) | per frame | Drive/relit/ |
| Export (ffmpeg) | entire stage | Drive/output/video_final.mp4 |

## User workflow for resume

1. Colab disconnects mid-relighting.
2. User reopens the notebook and reconnects.
3. Cells 1–4 (mount, install, clone, download) re-run; they skip all existing work.
4. Cell 5 detects `video.mp4` already on Drive and skips upload.
5. Cell 7 re-runs; extraction and rembg find all frames complete and skip; relighting resumes from the first unprocessed frame.

## Caveats

- **No atomic writes:** if a frame write is interrupted mid-write, a corrupt partial PNG may exist at `output_path`. The skip-if-exists check would then pass over it silently. In practice this is rare because frame writes are fast (~1.5 s for relighting), but a corrupted frame would produce a glitch in the output video.
- **Background generation is not resumable:** if ComfyUI crashes after generating `bg.png`, cell 7 will find `bg.png` and skip regeneration. If `bg.png` is corrupt, the user must delete it manually from Drive.
- **Model files are NOT persisted to Drive:** SD 1.5 checkpoint (~4GB) and IC-Light weights are re-downloaded each session from Hugging Face. This adds ~5 min per session. Caching them to Drive would save this time but is not implemented.

## Related

[[entities/deploy-colab-notebook]] · [[entities/deploy-colab-drive-workspace]] · [[concepts/deploy-colab-cell-data-flow]] · [[concepts/video-frame-pipeline]] · [[index]]
