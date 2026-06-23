---
title: camera-app-gui — Gallery, recording, and photo capture
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py"]
tags: [concept, gallery, recording, photo, virtualcam, output, camera-app-gui]
status: stable
---
# camera-app-gui — Gallery, recording, and photo capture

`CameraApp` writes all generated media — video recordings, photos, and offline
renders — into a single gallery directory. Recording and photo capture are driven
by flag-based signalling from the main thread to the worker thread.

## Gallery directory

```python
self.galeria = os.path.join(self.paths.base, "galeria")
os.makedirs(self.galeria, exist_ok=True)
```

`Paths().base` resolves to `./workspace` by default (or `LUMINA_BASE` env var).
All three output types land here with timestamped filenames:

| File pattern | Output type | Codec/format |
|---|---|---|
| `video_<YYYYmmdd_HHMMSS>.mp4` | Live recording | `cv2.VideoWriter`, fourcc `mp4v` |
| `foto_<YYYYmmdd_HHMMSS>.png` | Photo snapshot | `cv2.imwrite` (lossless PNG) |
| `render_<YYYYmmdd_HHMMSS>.mp4` | Offline render | `render_arquivo` via [[entities/render-video]] |

## Video recording (`_toggle_rec`)

Recording is toggled by the **● Gravar** / **■ Parar** button (`Rec.TButton`):

```
_toggle_rec()
  if not recording:
    path = galeria/video_<ts>.mp4
    self.writer = cv2.VideoWriter(path, fourcc=mp4v, fps=FPS, size=(CAP_W, CAP_H))
    self.recording = True
    btn_rec → "■ Parar"
  else:
    self.recording = False
    btn_rec → "● Gravar"
    self.writer.release()
    messagebox.showinfo("Gravado", path)
```

The worker writes to `self.writer` on every processed frame while `self.recording`
is `True`:

```python
if self.recording and self.writer:
    self.writer.write(out)
```

`out` is the fully composited + adjusted BGR frame at 960×540. The recording
captures exactly what the user sees on screen (person + background + all adjustments).

**Codec note:** `mp4v` (MPEG-4 Part 2) is used for compatibility. The output
container is `.mp4`. Audio is not recorded (live capture has no audio source; for
video-with-audio use the offline render path which remuxes the source audio).

**Cleanup:** `fechar()` calls `self.writer.release()` if a recording is in progress
when the window is closed, ensuring the file is properly finalised.

## Photo capture (`_photo`, `req_photo`)

The **📷 Foto** button sets a boolean flag:

```python
def _photo(self):
    self.req_photo = True
```

The worker checks and clears the flag each frame:

```python
if self.req_photo:
    self.req_photo = False
    ts = time.strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(os.path.join(self.galeria, f"foto_{ts}.png"), out)
```

This flag pattern avoids locking: the GIL makes bool reads/writes atomic in CPython,
and a one-frame delay before the snapshot is taken is imperceptible. The photo is
saved as a lossless PNG of the current composited + adjusted frame.

## Virtual camera stream (`_toggle_vcam`, `_handle_vcam`)

The **🔴 Iniciar câmera virtual (stream)** button toggles `self.req_virtual`. The
actual `pyvirtualcam.Camera` lifecycle is managed by `_handle_vcam(out)` called
every frame from the worker:

```
req_virtual=True, virtualcam is None
  → pyvirtualcam.Camera(width=960, height=540, fps=20, fmt=PixelFormat.BGR)
  → on error: req_virtual=False, messagebox via root.after(0, ...)

req_virtual=False, virtualcam is not None
  → virtualcam.close(); virtualcam = None

virtualcam is not None
  → virtualcam.send(out)   [BGR frame, every frame]
```

`pyvirtualcam` requires **OBS Studio installed once** (it registers the OBS Virtual
Camera device). The app does not require OBS to be running — only the device
registration matters. If the device is unavailable, the error is shown to the user
and the stream is not started.

The status bar shows `🔴 stream ativo` while the virtual camera is active. The button
label toggles between `🔴 Iniciar câmera virtual (stream)` and `■ PARAR stream
(câmera virtual)` to make the current state unambiguous.

**Loop prevention:** `listar_cameras` excludes any device named `"OBS Virtual ..."`,
so the virtual camera output cannot be selected as an input source. See
[[concepts/camera-app-gui-camera-listing]].

## Gallery opener (`_open_galeria`)

The **🖼 Galeria** button opens the gallery directory in the OS file manager:

```python
os.startfile(self.galeria)          # Windows
subprocess.Popen(["open", ...])     # macOS
subprocess.Popen(["xdg-open", ...]) # Linux
```

## Cleanup on close (`fechar`)

`fechar()` (bound to `WM_DELETE_WINDOW`) performs an ordered shutdown:

1. `_save_config()` — persist current settings.
2. `self.running = False` — signals worker to stop.
3. `time.sleep(0.1)` — brief wait for the worker's current frame to finish.
4. `self.writer.release()` if recording.
5. `self.virtualcam.close()` if streaming.
6. `self.bg_video.close()` if a video background is open.
7. `self._vcap.release()` if a video-edit capture is open.
8. `self.matter.close()` — releases MediaPipe/RVM resources.
9. `self.root.destroy()`.

## Related

[[entities/camera-app]] · [[concepts/camera-app-gui-dual-thread-frame-pipeline]] ·
[[concepts/camera-app-gui-video-edit-mode]] · [[entities/render-video]] · [[index]]
