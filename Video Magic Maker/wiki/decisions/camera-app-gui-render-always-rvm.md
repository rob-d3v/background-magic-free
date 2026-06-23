---
title: "Decision: render always uses RVM engine (camera-app-gui)"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py"]
tags: [decision, render, rvm, quality, camera-app-gui]
status: inferred
---
# Decision: render always uses RVM engine (camera-app-gui)

> **Inferred** from source code. Not documented as an explicit decision elsewhere.

## Context

`camera_app.py` allows the user to choose between two matting engines for the live
preview: MediaPipe (fast, ~15–21 fps) and RVM (quality, ~9.6 fps). When the user
clicks **Aplicar (renderizar tudo)** the video is rendered offline — no fps
constraint applies.

## Decision

`_aplicar_render` hardcodes `engine = "rvm"` regardless of the user's live preview
engine selection:

```python
engine, bg_mode = "rvm", self.bg_mode  # render final SEMPRE no RVM (melhor qualidade)
```

The in-code comment ("render final SEMPRE no RVM") makes the intent explicit.

## Rationale (inferred)

- **No fps pressure.** Offline render has no real-time constraint; the extra CPU
  cost of RVM (~4× slower than MediaPipe) is acceptable.
- **Better output quality.** RVM produces a true alpha matte: hair is preserved,
  shoulder blobs are eliminated, no halo. The render is the final exportable artefact,
  so quality takes priority over speed.
- **User intent.** A user who previewed with MediaPipe for speed still wants the
  best possible output when they commit to rendering.

## Consequences

- Users cannot choose MediaPipe for the render (no option exposed).
- First-time render triggers the torch.hub model download (~15 MB, ~12 s) if the
  user has only used MediaPipe for previewing.
- The rendered output will look better than the live preview if the user was on
  MediaPipe.

## Related
[[entities/camera-app]] · [[concepts/rvm-matting]] ·
[[concepts/camera-app-gui-video-edit-mode]] · [[entities/render-video]] · [[index]]
