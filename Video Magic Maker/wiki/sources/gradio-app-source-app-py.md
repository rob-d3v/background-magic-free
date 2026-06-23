---
title: "Source — app.py"
type: source
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - source
  - gradio
  - entry-point
---

`app.py` is the Gradio web UI entry point for the lumina-bg project (background-magic-free repo).

## File Summary

- **Lines**: ~509
- **Framework**: Gradio 4.x (`gr.Blocks`, `gr.Tabs`, `gr.Tab`, `gr.Row`, `gr.Column`)
- **Theme**: `gr.themes.Soft(primary_hue="indigo")`
- **Run command**: `python app.py` → serves at `http://127.0.0.1:7860`

## Key Sections

| Lines | Content |
|---|---|
| 1–18 | Module docstring — full flow description and run instructions |
| 19–47 | Imports and global state / constants |
| 50–98 | Lazy model loaders (`_offline_matter`, `_rembg_session`, `_relight_pipe`) |
| 101–267 | Callback functions (`cb_preparar`, `cb_mostrar_frame`, `cb_recortar`, `_obter_bg`, `cb_preview`, `cb_aplicar`, `cb_guardar_video`) |
| 270–343 | Live mode helpers (`_live_matter`, `cb_live_preview`, `_live_cmd`, `cb_live_iniciar`, `cb_live_parar`) |
| 346–497 | Gradio UI definition (`gr.Blocks` context, Studio tab, Live tab, event wiring) |
| 500–508 | `__main__` launch block |

## Pages Derived From This Source

- [[gradio-app-app-py]] (entity)
- [[gradio-app-studio-tab]] (entity)
- [[gradio-app-live-tab]] (entity)
- [[gradio-app-guided-flow]] (concept)
- [[gradio-app-processing-modes]] (concept)
- [[gradio-app-background-resolution]] (concept)
- [[gradio-app-live-subprocess-pattern]] (concept)
- [[gradio-app-gpu-gating]] (concept)
- [[gradio-app-single-user-global-state]] (decision)
- [[gradio-app-preview-before-render]] (decision)
