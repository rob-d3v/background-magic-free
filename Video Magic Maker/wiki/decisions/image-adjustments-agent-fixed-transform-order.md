---
title: "Fixed transform order: spatial → tone → color → sharpness"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/ajustes.py
tags:
  - architecture
  - image-processing
  - design-decision
---

The four transform stages inside `aplicar_ajustes` follow a fixed order (zoom/pan → brightness/contrast → saturation → sharpness) that is non-configurable by the caller.

> ⚠️ Inferred — no ADR found; reasoning derived from code structure.

## Decision

The order is hard-coded in the function body. Callers cannot reorder stages.

## Rationale (Inferred)

1. **Spatial first**: Zoom/pan crops and resamples the image. Running it first means subsequent pixel-level operations work on the final pixel grid rather than on a larger (then discarded) region. This saves computation and avoids sharpening details that will later be discarded by the crop.

2. **Brightness/contrast before saturation**: `convertScaleAbs` operates on BGR (luma-coupled). Running it before the HSV saturation step ensures the S-channel scaling operates on pixels that already have their intended luminance. The reverse order would over-saturate bright regions.

3. **Sharpness last**: Unsharp masking amplifies edges. Applying it after all colour corrections means the edge amplification is not then washed out by a tone or saturation adjustment. This matches standard photographic post-processing convention.

## Trade-offs

The order is opinionated. Advanced users who want, for example, to sharpen before adjusting contrast cannot do so without modifying the function. For the live-camera use case this is an acceptable constraint.

## Related

- [[image-adjustments-agent-transform-internals]]
- [[image-adjustments-agent-ajustes-module]]
