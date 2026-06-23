---
title: camera-app-gui — Video edit mode (source="video")
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py", "agentes/render_video.py"]
tags: [concept, video, editing, render, dirty-flag, camera-app-gui]
status: stable
---
# camera-app-gui — Video edit mode (source="video")

The camera app embeds a non-destructive video editor into its main window. When a
video file is loaded, it replaces the live webcam feed in the preview area; the user
scrubs frames, adjusts background and effects, and then renders the entire file to
the gallery.

## State machine: `self.source`

| Value | Active input | Webcam | `_vcap` |
|---|---|---|---|
| `"camera"` (default) | Live webcam | Open | None |
| `"video"` | Loaded video file | **Released** | Open on `self.video_path` |

Transition to `"video"` (`_carregar_video`): releases the webcam `cap` inside
`_loop` on the next iteration; opens `self._vcap = cv2.VideoCapture(video_path)`.

Transition back to `"camera"` (`_voltar_camera`): sets `source="camera"`, releases
`_vcap`, sets `cur_cam=None` so the worker re-opens the webcam.

## Two-level dirty cache

The worker maintains a two-level cache to avoid redundant work:

| Flag | Set when | Work triggered |
|---|---|---|
| `_dirty_base` | Frame pos changes; bg mode/file/blur/refine/mirror changes; engine changes | Full recompose: `_compose_base(frame)` → matting + bg compositing |
| `_dirty_adj` | Any image adjustment slider moves (`zoom`, `pan_x`, `pan_y`, `brilho`, etc.) | `aplicar_ajustes()` over cached `_video_base` only |

`_video_base` (BGR ndarray) caches the matted+composited frame before adjustments.
Adjustments are cheap (no matting), so tweaking a slider feels instant.

When both flags are clear and `_video_pos` has not changed, the worker sleeps 30 ms
and returns the existing frame unchanged.

## Worker loop in video mode

```
if source == "video":
    if cap (webcam): cap.release(); cap = None; cur_cam = None
    if _vcap is None: open cv2.VideoCapture(video_path)
    if _video_pos != _video_cur:           # user scrubbed slider
        _vcap.set(CAP_PROP_POS_FRAMES, _video_pos)
        ok, fr = _vcap.read()
        if ok: _video_raw = fr
        _video_cur = _video_pos
        _dirty_base = True
    if _video_raw and (_dirty_base or _dirty_adj):
        if _dirty_base or _video_base is None:
            _video_base = _compose_base(_video_raw)   # matting + bg
            _dirty_base = False
        out = aplicar_ajustes(_video_base, zoom, pan_x, ...)
        _dirty_adj = False
        self._frame = out   # under lock
    sleep(0.03)
```

## `_compose_base(frame)` — matting without adjustments

Called only when `_dirty_base` is set. Steps:

1. Calls `self.matter.reset()` if the matter object has a `reset()` method (RVM
   resets its recurrent state, so preview of a single frame is coherent).
2. If `bg_mode == "none"`: returns `frame.copy()` with no matting.
3. Otherwise: calls `_bg_for_frame(frame)` to resolve the background BGR array,
   then `matter.compor(frame, bg, color_match=0.12, refine=self.refine)`.

`_bg_for_frame(frame)`:
- `"video"`: opens `bg_video_path` with `cv2.VideoCapture`, reads the first frame,
  `cobrir(bf, w, h)`. A fresh `VideoCapture` per call (stateless; fine for preview).
- `"image"`: `cv2.imread(bg_image_path)` + `cobrir(raw, w, h)`.
- Fallback: `fundo_desfocado(frame, blur|1)`.

## Rendering the full file (`_aplicar_render`)

Button **Aplicar (renderizar tudo)** triggers an offline render in a daemon thread:

1. **Snapshot configs** before launching the thread: `bg_mode`, `bg_image_path`,
   `bg_video_path`, `blur`, `refine`. The engine is **forced to `"rvm"`** regardless
   of the live preview engine (best quality for the final export).
2. Sets `self._rendering = True` — the worker `_loop` releases the webcam and enters
   idle (`time.sleep(0.1)`) to free CPU for the render thread.
3. Calls `render_arquivo(src, out, engine="rvm", ...)` from [[entities/render-video]].
   Progress updates go via `root.after(0, status.config(...))`.
4. `fin()` callback: sets `_rendering = False`, re-enables the button, shows a
   `messagebox` (success or error).

Output: `<gallery>/render_<timestamp>.mp4` with original audio remuxed (via ffmpeg
`-map 1:a:0?`).

## UI elements (visible only in video mode)

`self.video_bar` (a `ttk.Frame`) is hidden with `pack_forget()` until a video is
loaded:

- **Frame slider** (`frame_slider`, `tk.Scale`): range `0..total-1`; `_video_scrub`
  sets `self._video_pos`; worker seeks on next iteration.
- **Aplicar (renderizar tudo)** (`btn_aplicar`): triggers `_aplicar_render`; becomes
  disabled + "Renderizando..." during render.
- **Voltar à câmera**: calls `_voltar_camera`.

Status bar during video mode: `MODO VÍDEO — <filename>   frame X/Y`.

## Render vs live preview engine

| Context | Engine | Reason |
|---|---|---|
| Live preview | User selection (MediaPipe or RVM) | Preview speed |
| `_aplicar_render` | Always RVM | Best output quality |

The render always uses RVM regardless of the preview engine choice (inferred
decision, see [[decisions/camera-app-gui-render-always-rvm]]).

## Related
[[entities/camera-app]] · [[entities/render-video]] ·
[[concepts/camera-app-gui-dual-thread-frame-pipeline]] ·
[[concepts/rvm-matting]] · [[index]]
