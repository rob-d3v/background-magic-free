---
title: "Image Adjustments Module (agentes/ajustes.py)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/ajustes.py
  - camera_app.py
tags:
  - image-processing
  - opencv
  - post-composition
  - live-camera
---

Single-function OpenCV module that applies zoom/pan, brightness, contrast, saturation, and sharpness to a composed BGR frame as the final post-processing step.

## Overview

`agentes/ajustes.py` exposes exactly one public function, `aplicar_ajustes`, which receives a composed BGR `np.ndarray` and returns a new `np.ndarray` of identical dimensions. All operations are **non-destructive of frame dimensions**: the output is always the same width/height as the input.

The module has no class, no state, and no I/O — it is a pure image-transform pipeline.

## Public API

```python
def aplicar_ajustes(
    img: np.ndarray,
    zoom: float = 1.0,       # 1.0–4.0
    pan_x: float = 0.0,      # -1..1
    pan_y: float = 0.0,      # -1..1
    brilho: int = 0,          # -100..100
    contraste: float = 1.0,  # 0.5–2.0
    saturacao: float = 1.0,  # 0–2.0
    nitidez: float = 0.0,    # 0–2.0
) -> np.ndarray
```

All parameters are optional with identity defaults so callers can pass only the parameters they care about.

## Transform Order

Operations are applied in a fixed sequence:

1. **Zoom + Pan** (spatial crop-and-rescale)
2. **Brightness + Contrast** (combined in one `convertScaleAbs` call)
3. **Saturation** (HSV channel manipulation)
4. **Sharpness** (unsharp mask)

Each stage is skipped at its identity value (e.g., `zoom == 1.0`, `contraste == 1.0`), so there is no redundant computation when an adjustment is unused.

## Dependencies

- `cv2` (OpenCV) — all spatial transforms and pixel arithmetic
- `numpy` — float32 intermediate for saturation channel

## Callers

- [[camera-app]] (`camera_app.py`) — called on every live frame in the worker loop and on every dirty frame in video-edit mode
- [[image-adjustments-agent-render-video-gap]] — `render_arquivo` in `agentes/render_video.py` does **not** call `aplicar_ajustes`; adjustments are absent from the offline batch render path

## Related Concepts

- [[image-adjustments-agent-post-composition-placement]] — why adjustments run after composition
- [[image-adjustments-agent-dirty-flag-cache]] — how the two dirty flags optimize video-edit mode
