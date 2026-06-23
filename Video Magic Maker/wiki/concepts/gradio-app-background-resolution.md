---
title: "Gradio App — Background Resolution Flow (_obter_bg)"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
tags:
  - background
  - diffusion
  - upload
  - _obter_bg
---

`_obter_bg` is the internal helper in [[gradio-app-app-py]] that resolves the background PIL image for both preview and render, abstracting over "upload" vs "generate with AI" modes.

## Logic

```
_obter_bg(bg_modo, bg_upload, bg_prompt, steps, cfg, seed)
  if bg_modo == "Enviar imagem":
      open bg_upload (str path or PIL Image) → convert to RGB
      save to PATHS.bg_output
      return bg_pil
  else ("Gerar com IA"):
      if not DEV["cuda"]: raise gr.Error (GPU required)
      gerar_fundo_diffusers(
          prompt=bg_prompt,
          width=meta["width"], height=meta["height"],   # match source video resolution
          output_path=PATHS.bg_output,
          steps, cfg, seed
      )
      return generated PIL
```

## Key Behaviours

- Always saves the resolved background to `PATHS.bg_output` (`{workspace}/background/bg.png`). This is the single canonical background file consumed by all pipeline steps.
- Dimensions are always taken from `ESTADO["meta"]` (the source video), ensuring the background matches the video frame size before any compositing.
- The same `_obter_bg` call is made in both `cb_preview` (single frame) and `cb_aplicar` (full render). The second call re-saves the same file — idempotent for the upload path; for AI generation it re-runs diffusion unless the user has not changed params.
- No caching of generated backgrounds between preview and render: the background is regenerated (or re-saved) on every cb_aplicar call.
