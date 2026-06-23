---
title: "Source: agentes/ajustes.py — image adjustment pipeline"
type: source
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/ajustes.py"]
tags: [source, image-processing, adjustments, opencv, camera-app-gui]
status: stable
---
# Source: agentes/ajustes.py — image adjustment pipeline

`agentes/ajustes.py` — single public function `aplicar_ajustes` that applies
post-composition image adjustments to a BGR frame. Used exclusively by
[[entities/camera-app]] (both live and video-edit modes) and [[entities/render-video]].

## `aplicar_ajustes` signature

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
) -> np.ndarray:
```

Input and output: **BGR ndarray uint8**, same shape. Applied **after**
matting+compositing — affects the full composited frame (person + background).

## Operations (in order)

### 1. Zoom + pan (crop-and-resize)

Only runs when `zoom > 1.0`.

```
crop_w = w / zoom
crop_h = h / zoom
max_x = w - crop_w
max_y = h - crop_h
x = int((max_x / 2) * (1 + pan_x))   # pan_x = 0 → centre, -1 → left edge, +1 → right edge
y = int((max_y / 2) * (1 + pan_y))
img = cv2.resize(img[y:y+crop_h, x:x+crop_w], (w, h), INTER_LINEAR)
```

Pan is only meaningful with zoom > 1 (at zoom=1 the full frame is used). The crop
origin is clamped to `[0, max_x]` / `[0, max_y]`.

### 2. Brightness + contrast

Only runs when `contraste != 1.0` or `brilho != 0`.

`cv2.convertScaleAbs(img, alpha=contraste, beta=brilho)`

- `alpha` is a multiplicative gain (contrast).
- `beta` is an additive offset (brightness).
- `convertScaleAbs` clips to `[0, 255]` automatically.

### 3. Saturation

Only runs when `saturacao != 1.0`.

Converts to HSV float32, scales the S channel by `saturacao`, clips to `[0, 255]`,
converts back to BGR.

### 4. Sharpness (unsharp mask)

Only runs when `nitidez > 0`.

```
blur = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
img = cv2.addWeighted(img, 1.0 + nitidez, blur, -nitidez, 0)
```

Standard unsharp mask: adds a scaled difference between original and blurred.
`nitidez=1.0` roughly doubles the edge contrast; `nitidez=2.0` is very aggressive.

## No-op fast paths

Each step is guarded by its neutral-value check, so if all parameters are at their
defaults (`zoom=1`, `brilho=0`, `contraste=1`, `saturacao=1`, `nitidez=0`) the
function returns the input array unchanged with minimal overhead.

## Slider ranges in the GUI

| Param | Slider range | Resolution |
|---|---|---|
| zoom | 1.0–4.0 | 0.05 |
| pan_x | -1.0–1.0 | 0.05 |
| pan_y | -1.0–1.0 | 0.05 |
| brilho | -100–100 | 1 |
| contraste | 0.5–2.0 | 0.05 |
| saturacao | 0.0–2.0 | 0.05 |
| nitidez | 0.0–2.0 | 0.05 |

## Related
[[entities/camera-app]] · [[concepts/camera-app-gui-dual-thread-frame-pipeline]] ·
[[concepts/camera-app-gui-video-edit-mode]] · [[index]]
