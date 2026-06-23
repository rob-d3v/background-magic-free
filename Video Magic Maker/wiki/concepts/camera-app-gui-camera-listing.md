---
title: camera-app-gui — Camera detection and listing (listar_cameras)
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py"]
tags: [concept, camera, detection, directshow, pygrabber, windows, camera-app-gui]
status: stable
---
# camera-app-gui — Camera detection and listing (listar_cameras)

`listar_cameras()` (module-level function in `camera_app.py`) enumerates available
physical cameras and returns their indices and display names before any capture is
opened, with a fallback for non-Windows platforms.

## Return type

`list[tuple[int, str]]` — list of `(device_index, display_name)` pairs, e.g.:

```python
[(0, "HD User Facing"), (1, "UGREEN Camera")]
```

## Primary path: pygrabber / DirectShow (Windows)

```python
from pygrabber.dshow_graph import FilterGraph
nomes = FilterGraph().get_input_devices()
cams = [(i, n) for i, n in enumerate(nomes) if "OBS Virtual" not in n]
```

`pygrabber` wraps Windows DirectShow (`FilterGraph`) and **enumerates device names
without opening them**. This is important: probing with `cv2.VideoCapture` would
briefly open each device (slow, and may fail on in-use cameras). `get_input_devices`
returns a list of strings ordered by DirectShow device index; the list comprehension
pairs each with its index.

### OBS Virtual Camera exclusion

Any device whose name contains `"OBS Virtual"` is filtered out. If the OBS Virtual
Camera appeared in the dropdown and the user selected it while the virtual output was
also active, the app would create a feedback loop (capturing its own composited
output). The exclusion prevents this at the data level.

## Fallback path: probe indices 0..3

If `pygrabber` is not installed or raises any exception, the function falls back to
opening `cv2.VideoCapture(i, cv2.CAP_DSHOW)` for `i in range(4)` and checking
`cap.isOpened()`:

```python
for i in range(4):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if sys.platform == "win32" else 0)
    if cap.isOpened():
        cams.append((i, f"Câmera {i}"))
        cap.release()
```

This path:
- Uses generic names (`"Câmera 0"`, `"Câmera 1"`, …) instead of friendly device names.
- Is slower because it opens each device briefly.
- Does not exclude the OBS Virtual Camera (since it has no name to check).
- On non-Windows, passes `0` as the backend (letting OpenCV choose).

Ultimate fallback: if no cameras are found at all, returns `[(0, "Câmera 0")]`.

## Camera switching in the app

`listar_cameras()` is called once in `CameraApp.__init__` and the result stored in
`self.cams`. The current camera index is tracked in two attributes:

| Attribute | Role |
|---|---|
| `self.req_cam` | Index requested by the user (set by `_on_cam` combobox callback) |
| `self.cur_cam` | Index currently open in the worker thread |

The worker (`_loop`) detects `req_cam != cur_cam`, releases the old `VideoCapture`,
and opens a new one via `_abrir(idx)`:

```python
def _abrir(self, idx):
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
    cap = cv2.VideoCapture(idx, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_W)    # 960
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_H)   # 540
    cap.set(cv2.CAP_PROP_FPS, FPS)              # 20
    return cap
```

Camera switching is seamless and does not restart the worker thread.

## Saved camera preference

The selected camera index (`req_cam`) is saved to `camera_app_config.json`. On next
launch it is validated: if the saved index is not in the current `cam_ids` list (the
camera was unplugged), the app silently falls back to `cams[0]`. See
[[entities/camera-app-gui-config-persistence]].

## Related

[[entities/camera-app]] · [[entities/camera-app-gui-config-persistence]] ·
[[concepts/camera-app-gui-dual-thread-frame-pipeline]] · [[index]]
