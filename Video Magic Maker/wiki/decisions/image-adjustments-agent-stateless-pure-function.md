---
title: "Image adjustments implemented as a stateless pure function"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/ajustes.py
tags:
  - architecture
  - design-decision
  - stateless
---

`aplicar_ajustes` was designed as a single stateless function rather than a class with instance state, keeping it side-effect-free and trivially testable.

> ⚠️ Inferred — no ADR found; reasoning derived from code structure.

## Decision

The module exposes one function with all parameters as keyword arguments with identity defaults. There is no `AjustesConfig` class, no constructor, and no mutable shared state.

## Rationale (Inferred)

1. **No temporal coupling**: each frame is independent. Unlike the RVM matting engine, which maintains recurrent state across frames for temporal coherence, image adjustments are per-pixel operations that carry no memory between frames. Statefulness would add complexity for zero benefit.

2. **Thread safety at no cost**: `camera_app.py` runs adjustments on the worker thread. A stateless function can be called from any thread without locks.

3. **Easy slider integration**: the caller (`camera_app.py`) holds all parameter values as instance attributes. Passing them as keyword arguments at call time is idiomatic and makes the sliders' effect on output transparent.

4. **No-op at defaults**: by choosing identity values as defaults (`zoom=1.0`, `brilho=0`, etc.), callers can pass only the parameters they care about; any combination of defaults results in a no-op, which pairs naturally with fast-path skip conditions inside the function.

## Trade-offs

**Downside**: Because state is owned by the caller (`CameraApp`), the offline render path (`render_arquivo`) has no access to the slider values unless they are explicitly passed through the call chain — and currently they are not (see [[image-adjustments-agent-render-video-gap]]).

## Related

- [[image-adjustments-agent-ajustes-module]]
