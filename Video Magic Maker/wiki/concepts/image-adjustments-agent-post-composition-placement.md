---
title: "Post-composition placement of image adjustments"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/ajustes.py
  - camera_app.py
tags:
  - pipeline
  - composition
  - image-processing
---

Image adjustments (zoom, brightness, contrast, saturation, sharpness) are applied **after** full frame composition so that they affect the final output exactly as a real camera app's post-processing would.

## Why Post-Composition

Applying adjustments before matting or compositing would create color and luminance mismatches between the subject and the new background. By running `aplicar_ajustes` on the already-composited frame, every pixel — subject and background alike — receives identical treatment, which preserves visual coherence.

The module docstring states this explicitly:

> "Operam sobre frames BGR (OpenCV), aplicados **depois** da composição — afetam o quadro final como um app de câmera faria."

## Pipeline Position in Live Mode

```
webcam frame
  └─ (mirror flip, if enabled)
       └─ matter.compor(frame, bg)     ← composition (matting + background blend)
            └─ aplicar_ajustes(out)    ← THIS MODULE
                 └─ write to VideoWriter / pyvirtualcam / screen
```

## Pipeline Position in Video-Edit Mode

```
video frame (seek to position)
  └─ _compose_base(raw_frame)          ← expensive: matting + composition
       └─ _video_base (cached)
            └─ aplicar_ajustes(_video_base)   ← applied on dirty_adj only
                 └─ _frame (displayed on screen)
```

The video-edit mode introduces a two-layer cache (see [[image-adjustments-agent-dirty-flag-cache]]) precisely because post-composition placement means the composition step (slow) can be separated from the adjustment step (fast).

## bg_mode = "none" Special Case

When `bg_mode == "none"` the raw webcam frame bypasses composition entirely and is passed directly to `aplicar_ajustes`. Adjustments still apply because they represent camera-level corrections, not background-blending corrections.

## Related Entities

- [[image-adjustments-agent-ajustes-module]] — the module itself
- [[composicao]] — composition agent that runs just before adjustments
