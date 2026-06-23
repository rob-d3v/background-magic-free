---
title: "Source: agentes/ajustes.py"
type: source
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/ajustes.py
tags:
  - source
  - image-processing
---

Reference summary of `agentes/ajustes.py` — the Image Adjustments module.

## File Facts

| Property | Value |
|----------|-------|
| Path | `agentes/ajustes.py` |
| Lines | 53 |
| Dependencies | `cv2`, `numpy` |
| Public symbols | `aplicar_ajustes` (function) |
| Private symbols | none |
| State | none |

## Function Signature

```python
def aplicar_ajustes(
    img: np.ndarray,
    zoom: float = 1.0,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    brilho: int = 0,
    contraste: float = 1.0,
    saturacao: float = 1.0,
    nitidez: float = 0.0,
) -> np.ndarray
```

Input and output are both BGR `np.ndarray` (dtype uint8). Dimensions are preserved.

## Module-Level Docstring (summary)

> "Ajustes de imagem para o app de câmera ao vivo (zoom, enquadramento, brilho, contraste, saturação, nitidez). Operam sobre frames BGR (OpenCV), aplicados **depois** da composição — afetam o quadro final como um app de câmera faria."

## Callers (as of 2026-06-22)

| File | Call site | Mode |
|------|-----------|------|
| `camera_app.py:642` | `_loop` — video-edit branch | video-edit preview |
| `camera_app.py:685` | `_loop` — live camera branch | live camera |

## Notable Gaps

`agentes/render_video.py` does **not** import or call this function. See [[image-adjustments-agent-render-video-gap]].

## Related Pages

- [[image-adjustments-agent-ajustes-module]] — entity page
- [[image-adjustments-agent-transform-internals]] — algorithm detail
- [[image-adjustments-agent-dirty-flag-cache]] — caller optimization
