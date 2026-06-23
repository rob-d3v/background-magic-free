---
title: camera-app-gui — Dual-thread frame pipeline
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py", "agentes/matting_live.py", "agentes/ajustes.py"]
tags: [concept, architecture, threading, gui, tkinter, camera-app-gui]
status: stable
---
# camera-app-gui — Dual-thread frame pipeline

`camera_app.py` splits all work across two threads to keep Tkinter responsive while
running a CPU-heavy matting + compositing loop.

## Why two threads

Tkinter is single-threaded: any blocking call on the main thread freezes the UI
(controls stop responding, window goes grey). The matting + CV2 pipeline at 540p
takes 47–100 ms per frame depending on the engine. The two-thread split keeps the
UI alive and lets the worker run as fast as the hardware allows.

## Worker thread (`_loop`, daemon)

Started via `threading.Thread(target=self._loop, daemon=True)`. Runs until
`self.running = False` (set by `fechar()`).

### Camera live pipeline (per frame)

```
cv2.VideoCapture.read()
  → cv2.resize(frame, (CAP_W=960, CAP_H=540))
  → cv2.flip(frame, 1)          [if self.mirror]
  → background resolution:
      none   → pass frame through
      blur   → fundo_desfocado(frame, blur)
      image  → self.bg_img  (pre-cropped via cobrir())
      video  → self.bg_video.proximo()  [VideoFundo loop; fallback blur]
  → matter.compor(frame, bg, color_match=0.12, refine=self.refine)
      [matter is LiveMatter or RVMMatter — same interface]
  → aplicar_ajustes(out, zoom, pan_x, pan_y, brilho, contraste, saturacao, nitidez)
  → write VideoWriter  [if self.recording]
  → cv2.imwrite galeria/foto_<ts>.png  [if self.req_photo]
  → _handle_vcam(out)  [if self.req_virtual]
  → self._lock: self._frame = out
  → FPS meter: every 10 frames, _fps = 10 / elapsed
```

### Camera switching

The worker detects `self.req_cam != self.cur_cam`: releases the old `VideoCapture`,
opens a new one with `cv2.CAP_DSHOW` (Windows), sets resolution + FPS properties,
and updates `self.cur_cam`. No restart of the thread is required.

### Engine switching (paused protocol)

`_on_engine` (main thread):
1. Sets `self._paused = True` — worker skips frames (`time.sleep(0.05)` loop).
2. Instantiates the new matter object (may download model on first use).
3. Swaps `self.matter`, closes the old one.
4. Sets `self._paused = False` — worker resumes.

This avoids the worker calling a partially-constructed matter.

### Virtual camera (`_handle_vcam`)

Called every frame from the worker. Manages a `pyvirtualcam.Camera` lifecycle:
- `req_virtual=True` and no camera open → create (`pyvirtualcam.Camera`, BGR format,
  OBS Virtual Camera backend). On error: disables `req_virtual`, shows `messagebox`
  via `root.after(0, ...)`.
- `req_virtual=False` and camera open → `close()`.
- Open camera → `send(out)` (BGR frame).

`pyvirtualcam` requires OBS Studio installed once (registers the virtual device).

## Main thread (`_tick`)

Scheduled with `root.after(33, self._tick)` (~30 fps display rate). Never called
from the worker.

```
with self._lock: f = self._frame.copy()   # snapshot under lock
  → cv2.cvtColor(BGR → RGB)
  → PIL.Image.fromarray(rgb)
  → scale to fit video widget (maintain aspect ratio, BILINEAR)
  → ImageTk.PhotoImage(pil)    [MUST be created on main thread]
  → video_label.configure(image=img)
  → video_label.image = img    [keep reference or GC drops it]
  → update status bar text
root.after(33, self._tick)     # reschedule
```

The `ImageTk.PhotoImage` object **must** be created on the main thread; creating it
in the worker corrupts the display or raises a Tcl error.

## Shared state and synchronisation

- **`self._frame` (numpy BGR array):** protected by `threading.Lock()`. Worker
  writes; main thread reads a copy.
- **All other state** (`mirror`, `zoom`, `bg_mode`, `refine`, etc.) is read by the
  worker and written by main-thread callbacks. These are simple Python attribute
  assignments (GIL-atomic) and the slight staleness (one frame lag) is acceptable
  for interactive controls.
- **`req_photo`:** flag set `True` by main thread; cleared `False` by worker after
  saving the file. Not locked — the GIL provides enough protection for a bool.

## Constants

| Name | Value | Role |
|---|---|---|
| `CAP_W` | 960 | Capture + output width (px) |
| `CAP_H` | 540 | Capture + output height (px) |
| `FPS` | 20 | `VideoWriter` target fps and `pyvirtualcam` fps |

The 540p / 20 fps trade-off balances visual quality against CPU budget. The display
`_tick` runs at ~30 fps independently of the capture fps.

## Related
[[entities/camera-app]] · [[concepts/realtime-matting]] · [[concepts/rvm-matting]] ·
[[concepts/camera-app-gui-video-edit-mode]] · [[index]]
