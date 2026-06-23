---
title: "Image adjustment transform internals"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/ajustes.py
tags:
  - opencv
  - image-processing
  - algorithms
---

Detailed mechanics of each transform stage inside `aplicar_ajustes`, including parameter ranges, OpenCV calls used, and edge-case behaviour.

## Stage 1 — Zoom + Pan (crop-and-rescale)

**Active when**: `zoom > 1.0`

**Mechanics**:
```python
cw, ch = int(w / zoom), int(h / zoom)   # crop window size
max_x, max_y = w - cw, h - ch           # max allowed top-left corner
x = int((max_x / 2) * (1 + pan_x))      # pan_x=0 → centred
y = int((max_y / 2) * (1 + pan_y))      # pan_y=-1 → top edge, +1 → bottom edge
img = cv2.resize(img[y:y+ch, x:x+cw], (w, h), interpolation=cv2.INTER_LINEAR)
```

Pan values are clamped to `[0, max_x]` / `[0, max_y]` to prevent out-of-bounds slices. Output dimensions are identical to input. Interpolation is `INTER_LINEAR` (bilinear), chosen for speed over quality.

**Parameter ranges**:
- `zoom`: 1.0 (no zoom) → 4.0 (4× magnification). At `zoom=4.0` the crop window is 25% of original area.
- `pan_x` / `pan_y`: −1 (full left/top) → 0 (centred) → +1 (full right/bottom).

## Stage 2 — Brightness + Contrast

**Active when**: `contraste != 1.0 OR brilho != 0`

**Mechanics**:
```python
img = cv2.convertScaleAbs(img, alpha=float(contraste), beta=float(brilho))
```

`convertScaleAbs` computes `saturate(alpha * pixel + beta)` per channel, saturating to [0, 255]. Both adjustments are combined into one pass for efficiency.

**Parameter ranges**:
- `brilho`: −100 → 0 (no change) → +100. Integer addition per pixel.
- `contraste`: 0.5 (half range) → 1.0 (identity) → 2.0 (doubled range).

## Stage 3 — Saturation

**Active when**: `saturacao != 1.0`

**Mechanics**:
```python
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
hsv[..., 1] = np.clip(hsv[..., 1] * float(saturacao), 0, 255)
img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
```

Only the S (saturation) channel of HSV is scaled. H and V are untouched. The float32 upcast prevents overflow during multiplication before clipping back to uint8.

**Parameter ranges**:
- `saturacao`: 0.0 (greyscale) → 1.0 (identity) → 2.0 (double saturation).

**Note**: The round-trip BGR→HSV→BGR introduces minor quantisation error because OpenCV's 8-bit HSV encodes H as [0–179] and S, V as [0–255]. This is negligible for preview use but means pure-white pixels can drift slightly at high saturation values.

## Stage 4 — Sharpness (Unsharp Mask)

**Active when**: `nitidez > 0`

**Mechanics**:
```python
blur = cv2.GaussianBlur(img, (0, 0), 3)
img = cv2.addWeighted(img, 1.0 + float(nitidez), blur, -float(nitidez), 0)
```

Classic unsharp mask: `output = original * (1 + k) - blurred * k`. The Gaussian radius is fixed at σ=3 (kernel auto-sized). Higher `nitidez` increases edge amplification linearly.

**Parameter ranges**:
- `nitidez`: 0.0 (no effect) → 2.0 (strong edge amplification).

**Edge cases**: At high `nitidez` values combined with high-contrast edges, pixel values can overflow/underflow. `addWeighted` clips to [0, 255] automatically.

## No-op Fast Paths

The function checks each stage's identity condition before executing:
- `zoom > 1.0` — skips spatial crop at 1.0
- `contraste != 1.0 or brilho != 0` — skips tone adjustment at defaults
- `saturacao != 1.0` — skips HSV round-trip at 1.0
- `nitidez > 0` — skips sharpening at 0.0

All four conditions simultaneously at defaults means the function returns the input array with no copies and no transforms (aside from the function call overhead).

## Related

- [[image-adjustments-agent-ajustes-module]]
- [[image-adjustments-agent-post-composition-placement]]
