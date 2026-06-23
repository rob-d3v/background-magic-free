---
title: "Image adjustments absent from offline video render"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/render_video.py
  - camera_app.py
tags:
  - render
  - gap
  - image-processing
---

The offline batch render path (`agentes/render_video.py`) does not call `aplicar_ajustes`, meaning zoom/pan/brightness/contrast/saturation/sharpness settings are silently ignored when rendering a video file.

## What Happens

When the user clicks "Aplicar (renderizar tudo)", `camera_app.py` calls `render_arquivo` in `agentes/render_video.py`. That function performs matting and compositing frame-by-frame but **never imports or calls `aplicar_ajustes`**. The current slider values (`zoom`, `brilho`, etc.) are not passed through and have no effect on the rendered MP4.

In contrast, the live camera loop and the video-edit preview both call `aplicar_ajustes` on every frame.

## Contrast With Live Mode

| Path | Calls `aplicar_ajustes` |
|------|------------------------|
| Live camera loop (`_loop`, camera source) | Yes |
| Video-edit preview (`_loop`, video source) | Yes |
| Offline render (`render_arquivo`) | **No** |
| Frame-based render (`render_matting`) | **No** |

## Consequence

A user who dials in a zoom, brightness boost, or saturation adjustment in the live preview and then clicks "Renderizar" will receive an output that does not match what they saw on screen.

> ⚠️ Contradiction: the UI presents image-adjustment sliders alongside the video-edit controls, strongly implying adjustments will carry through to the render output. The current implementation does not honour this expectation.

## Likely Fix

Pass adjustment parameters through `_aplicar_render` and into `render_arquivo`, then call `aplicar_ajustes(out, ...)` after each `matter.compor(...)` call inside the render loop.

## Related

- [[image-adjustments-agent-ajustes-module]]
- [[image-adjustments-agent-dirty-flag-cache]]
- [[render-video]]
