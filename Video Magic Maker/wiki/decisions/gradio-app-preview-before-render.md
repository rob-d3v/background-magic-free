---
title: "Decision — Single-Frame Preview Before Full Render"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - ux
  - preview
  - performance
  - inferred
---

The Studio tab requires the user to preview the result on a single frame before committing to a full-video render.

**Inferred decision.**

## What Was Chosen

Step 5 ("Pre-visualizar neste frame") is a separate button from Step 6 ("Aplicar a todos os frames"). The preview runs the same processing pipeline on a single chosen frame and shows the result inline before any batch work begins.

## Likely Rationale

Full video rendering (especially IC-Light relight) is slow — potentially minutes on a GPU for a short clip, much longer on CPU. Running the full pipeline to discover a bad background choice or wrong lighting prompt would waste significant time. A per-frame preview lets users iterate the look in seconds.

The comment in `app.py` states this explicitly:
> "A ideia do preview de 1 frame é justamente acertar o look num frame só antes de gastar tempo processando o video inteiro."

## Implication for UX Design

- The "middle frame" heuristic (`meio = total_frames // 2`) is used as the default preview frame on video load, on the assumption it tends to show the subject well-positioned.
- The frame slider lets users pick a representative frame (e.g., one where the subject is fully visible and well-lit) for a more meaningful preview.

## Related

- [[gradio-app-guided-flow]]
- [[gradio-app-studio-tab]]
