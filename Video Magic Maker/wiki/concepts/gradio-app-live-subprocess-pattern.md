---
title: "Gradio App — Live Subprocess Pattern"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - live
  - subprocess
  - virtual-camera
  - obs
---

The Live tab in [[gradio-app-app-py]] uses a subprocess pattern rather than running the camera loop inside the Gradio event loop, because `live.py` is a blocking OpenCV/pyvirtualcam loop that cannot share a thread with Gradio's asyncio server.

## Pattern

```
Gradio process (app.py)
  └─ cb_live_iniciar()
       builds args list via _live_cmd()
       subprocess.Popen(args, cwd=<repo root>)
       stores handle in _LIVE_PROC

live.py (subprocess)
  └─ reads webcam
  └─ performs RVM matting per frame
  └─ writes to virtual camera device
  └─ optionally opens OpenCV preview window
```

## Argument Construction (_live_cmd)

`_live_cmd` translates Gradio widget values to CLI flags for `live.py`:

| Widget value | CLI arg |
|---|---|
| Resolution preset string | `--width W --height H` |
| `feather` | `--feather N` |
| `color_match` | `--color-match F` |
| `alta_qual=False` | `--fast` |
| `bg_modo=="Desfocar fundo"` | `--blur N` (forced odd) |
| `bg_modo=="Imagem de fundo"` | saves PIL to `LIVE_BG_PATH` + `--background <path>` |
| `mirror=True` | `--mirror` |
| `preview=True` | `--preview` |

The blur kernel is forced to an odd integer with `int(blur) | 1` before passing to both the subprocess args and the in-process `fundo_desfocado` call.

## State Guards

- `cb_live_iniciar` checks `_LIVE_PROC.poll() is None` before spawning; returns an error string if already running.
- `cb_live_parar` uses `terminate()` then waits 5 seconds, escalating to `kill()` on timeout.
- After stop, `_LIVE_PROC = None` to allow restart.

## Snapshot Test vs Full Run

The "Testar recorte neste snapshot" button (`cb_live_preview`) runs in-process using `_live_matter()` on a single webcam capture, without spawning `live.py`. This allows the user to validate the look without starting the virtual camera.
