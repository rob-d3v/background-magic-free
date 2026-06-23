---
title: "Decision: lazy LiveMatter init in worker thread (camera-app-gui)"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py"]
tags: [decision, performance, startup, threading, camera-app-gui]
status: stable
---
# Decision: lazy LiveMatter init in worker thread (camera-app-gui)

## Context

`LiveMatter.__init__` (MediaPipe Tasks `ImageSegmenter`) takes approximately 1.8 s
to load the `.tflite` model and initialise the XNNPACK delegate. Previously,
`CameraApp.__init__` called `LiveMatter()` synchronously before `root.mainloop()`.

## Problem

The window was invisible for ~1.8 s after the user ran the app. On slower machines
or when the model was not yet cached, this extended further. Users reported "the app
doesn't open" — in reality it was opening but too slowly and sometimes behind other
windows.

## Decision

Set `self.matter = None` in `__init__`. Initialise `LiveMatter` at the top of
`_loop` (the worker daemon thread) immediately before the main loop starts:

```python
def _loop(self):
    if self.matter is None:
        self.matter = LiveMatter()
    ...
```

The main thread calls `_build_ui()` and `root.mainloop()` without waiting for the
matter. During the ~1.8 s init the status bar shows "Carregando recorte... (alguns
segundos)" and the frame area is blank — the user sees the window immediately.

## Consequences

- Window appears instantly.
- The worker blocks internally for ~1.8 s before the first frame appears, which is
  acceptable (status bar communicates this).
- Any code that calls `self.matter` before the worker starts must guard against
  `None`. `_compose_base` does this explicitly:
  ```python
  if self.matter is None:
      self.matter = LiveMatter()
  ```
- The window is raised to the foreground via `lift()` + `attributes("-topmost", True)`
  (released after 900 ms) + `focus_force()` to prevent it opening behind other
  windows.

## Status

Stable. Verified: window opens instantly; "Carregando recorte..." shows during model
load; video appears once the worker is ready.

## Related
[[entities/camera-app]] · [[concepts/camera-app-gui-dual-thread-frame-pipeline]] ·
[[concepts/realtime-matting]] · [[index]]
