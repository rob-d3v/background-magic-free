---
title: "Gradio App — Live Tab"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - gradio
  - live
  - webcam
  - virtual-camera
  - obs
---

The Live tab (`🔴 Live — OBS / Meet / stream`) enables real-time webcam background replacement via [[gradio-app-app-py]], publishing to an OBS Virtual Camera that can be selected in Meet, Zoom, or OBS.

## Purpose

Runs `live.py` as a child subprocess with the background configuration chosen in the UI. The Gradio tab itself is a control panel — the actual frame pipeline runs outside the Gradio process.

## Layout

Two-column `gr.Row`:

- **Left column**: background mode, blur slider, resolution picker, edge tuning sliders, quality checkbox, mirror/preview checkboxes.
- **Right column**: webcam snapshot widget for testing, preview result image, start/stop buttons, status text.

## Controls Reference

| Control | Type | Default | Notes |
|---|---|---|---|
| `live_bg_modo` | `gr.Radio` | "Imagem de fundo" | "Desfocar fundo" skips image upload |
| `live_bg` | `gr.Image` | — | Background image (numpy), only used with "Imagem de fundo" |
| `live_blur` | `gr.Slider` | 45 (range 5–75, step 2) | Blur kernel size; forced odd with `\| 1` |
| `live_res` | `gr.Radio` | "960x540" | Three presets with FPS hints; maps to `--width`/`--height` for `live.py` |
| `live_feather` | `gr.Slider` | 3 (range 0–15) | Edge feather in px for alpha blend |
| `live_cmatch` | `gr.Slider` | 0.12 (range 0–1) | Color-match strength between subject and background |
| `live_alta` | `gr.Checkbox` | True | High-quality guided-filter edge refinement; reduces FPS |
| `live_mirror` | `gr.Checkbox` | True | Horizontal flip for selfie orientation |
| `live_prev` | `gr.Checkbox` | True | Open OpenCV preview window in `live.py` |

## Webcam Snapshot Test

`live_snap` (`gr.Image`, source=webcam) + `btn_live_test` → `cb_live_preview`: runs a single-frame cutout using `_live_matter()` (lazy `LiveMatter`) on the snapshot, returning the composited result without starting the subprocess.

## Subprocess Lifecycle

- **Start**: `cb_live_iniciar` calls `_live_cmd()` to build args list, then `subprocess.Popen(args)`. Stores PID in `_LIVE_PROC`. Returns status markdown including PID and the equivalent shell command.
- **Stop**: `cb_live_parar` calls `terminate()`, waits up to 5 seconds, then `kill()` if still running.
- Guard: re-start is blocked if `_LIVE_PROC.poll() is None` (process still alive).

## Background File Handoff

When using an image background, the UI saves it to `LIVE_BG_PATH` (`{workspace}/background/live_bg.png`) and passes `--background <path>` to `live.py`. This decouples the Gradio process from the subprocess's file I/O.

## Limitations

- No IC-Light relight in Live mode (documented inline with a note pointing users to Studio for that).
- Windows prerequisite: OBS Studio must be installed once to register the virtual camera driver (does not need to be running).
