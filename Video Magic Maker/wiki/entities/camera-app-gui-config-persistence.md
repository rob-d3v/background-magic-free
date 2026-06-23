---
title: camera-app-gui — Config persistence (camera_app_config.json)
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py"]
tags: [component, gui, config, persistence, json, camera-app-gui]
status: stable
---
# camera-app-gui — Config persistence (camera_app_config.json)

Every user preference set in [[entities/camera-app]] is persisted to a JSON file and
restored on next launch; the app never loses its last state between sessions.

## File location

`<workspace base>/camera_app_config.json` — resolved as
`os.path.join(Paths().base, "camera_app_config.json")`. The `Paths().base` defaults to
`./workspace` locally and `LUMINA_BASE` env var if set (see `config.py`).

## Keys saved

| Key | Type | Default | Notes |
|---|---|---|---|
| `camera` | int | first camera index | Validated against present cameras on load |
| `engine` | str | `"mediapipe"` | `"mediapipe"` or `"rvm"` |
| `bg_mode` | str | `"blur"` | `"none"` / `"blur"` / `"image"` / `"video"` |
| `blur` | int | 45 | Blur kernel size (forced odd via `\| 1`) |
| `bg_image_path` | str/null | null | Absolute path; validated on load |
| `bg_video_path` | str/null | null | Absolute path; validated on load |
| `mirror` | bool | true | Selfie flip |
| `refine` | bool | true | High-quality edge refine |
| `zoom` | float | 1.0 | 1.0–4.0 |
| `pan_x` | float | 0.0 | -1..1 |
| `pan_y` | float | 0.0 | -1..1 |
| `brilho` | int | 0 | -100..100 |
| `contraste` | float | 1.0 | 0.5–2.0 |
| `saturacao` | float | 1.0 | 0–2.0 |
| `nitidez` | float | 0.0 | 0–2.0 |

## Load sequence (`__init__`)

1. `_load_config()` reads the JSON (`json.load`); returns `{}` on any error.
2. Each attribute is set as `c.get("key", default)`.
3. Camera index is validated: if the saved index is not in the current camera list,
   the first available camera is used instead (handles removed/unplugged cameras).
4. `_build_ui()` initialises all widgets with the loaded values (comboboxes,
   radiobuttons, sliders, checkboxes) before the window is shown.
5. `_restaurar_fundo()` reloads the saved background image/video from disk; if the
   file is gone, falls back to `bg_mode = "blur"`.

## Save triggers

Config is saved (via `_save_config`) immediately on:
- Camera or engine combobox change (`_on_cam`, `_on_engine`)
- Background radio change or file pick (`_on_bg`, `_pick_bg`, `_pick_bg_video`)
- Mirror / refine checkbox toggle
- Slider `<ButtonRelease-1>` (on mouse-up, not every drag tick)
- Reset button (`_reset`)
- Window close (`fechar()`) — ensures final state is always written

## Robustness

Both `_load_config` and `_save_config` are wrapped in `try/except`: a corrupt JSON
or full disk does not crash the app; it silently continues with defaults or last
known values.

## Gotchas

- The saved `bg_image_path` / `bg_video_path` are absolute paths. If the user moves
  the background file, `_restaurar_fundo` detects `not os.path.exists(path)` and
  silently falls back to blur mode.
- Sliders save on `<ButtonRelease-1>`, not on every `command` event, to avoid
  hammering disk IO during drag.

## Related
[[entities/camera-app]] · [[sources/camera-app-gui-ajustes]] · [[index]]
