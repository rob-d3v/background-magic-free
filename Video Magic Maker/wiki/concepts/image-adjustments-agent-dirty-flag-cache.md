---
title: "Dirty-flag cache for video-edit adjustments"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - camera_app.py
tags:
  - optimization
  - caching
  - video-edit-mode
  - dirty-flag
---

In video-edit mode, `camera_app.py` uses two boolean dirty flags to avoid re-running the expensive matting+composition step when only cheap image adjustments have changed.

## The Two Flags

| Flag | Name | Set when |
|------|------|----------|
| `_dirty_base` | "base is stale" | Frame position changes, engine/background/blur/mirror/refine changes |
| `_dirty_adj` | "adjustment is stale" | Any slider value changes (zoom, pan, brightness, contrast, saturation, sharpness) |

## Cached Intermediate: `_video_base`

`_video_base` stores the composed frame (matting applied, background blended) **before** any image adjustments. It is computed by `_compose_base(raw_frame)`, which is the slow step.

## Decision Logic in the Worker Loop

```python
if self._video_raw is not None and (self._dirty_base or self._dirty_adj):
    if self._dirty_base or self._video_base is None:
        self._video_base = self._compose_base(self._video_raw)
        self._dirty_base = False
    out = aplicar_ajustes(self._video_base, ...)   # always re-applies on any dirty
    self._dirty_adj = False
    self._frame = out
```

Key observations:
- Composition re-runs only when `_dirty_base` is True.
- `aplicar_ajustes` re-runs on **either** flag being True (because `_dirty_adj` alone is enough when the base is clean).
- Both flags are cleared after the frame is produced.

## What Each Slider Touches

The `_set(attr)` factory in `CameraApp` always sets only `_dirty_adj`:

```python
def _set(self, attr):
    def f(v):
        setattr(self, attr, float(v))
        self._dirty_adj = True
    return f
```

Sliders wired through `_set`: `zoom`, `pan_x`, `pan_y`, `brilho`, `contraste`, `saturacao`, `nitidez`.

Changes that set `_dirty_base` (and implicitly `_dirty_adj` too, since base recompute triggers a full redraw):
- Frame scrub (`_video_scrub`)
- Engine change (`_on_engine`)
- Background mode change (`_on_bg`)
- Blur value change (`_set_blur`)
- Mirror toggle
- Refine-edge toggle

## Performance Impact

Without this cache, every slider drag during video-edit mode would trigger a full RVM inference pass (the default offline engine). With the cache, slider drags cost only:
- One `cv2.convertScaleAbs` (brightness/contrast)
- One `cv2.cvtColor` round-trip (saturation, if changed)
- One `GaussianBlur` + `addWeighted` (sharpness, if changed)
- One crop + resize (zoom/pan, if changed)

These are all O(frame pixels) and run in milliseconds.

## Related Entities

- [[image-adjustments-agent-ajustes-module]]
- [[image-adjustments-agent-post-composition-placement]]
