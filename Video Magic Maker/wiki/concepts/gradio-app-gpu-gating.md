---
title: "Gradio App — GPU Gating and Degraded-Mode Behaviour"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - app.py
  - config.py
tags:
  - gpu
  - cpu-fallback
  - colab
  - degraded-mode
---

`app.py` uses `detectar_device()` from [[gradio-app-config-device-detection]] at startup to build a `DEV` dict that gates which features are available, and displays a banner in the UI indicating the current compute capability.

## Gates

| Feature | Gate condition | Fallback |
|---|---|---|
| IC-Light Relight mode | `DEV["pode_relight"]` (vram >= 5 GB) | Mode hidden from default; user can still select it but will get `gr.Error` |
| AI background generation | `DEV["cuda"]` | `gr.Error` if selected without CUDA |
| Default mode | `MODO_RELIGHT` if `pode_relight` else `MODO_HD` | CPU users default to HD (RVM) |

## Banner Messages

Three distinct banner texts displayed under the app title:

1. **Full GPU** (`pode_relight=True`): "GPU detectada: {name} ({vram}GB) — relight IC-Light disponivel."
2. **Low VRAM GPU** (`cuda=True, pode_relight=False`): warns about insufficient VRAM for relight, suggests Colab.
3. **No GPU** (`cuda=False`): directs to Google Colab T4 for relight.

## Low VRAM Handling in IC-Light

`_relight_pipe()` reads `DEV["vram_gb"]` to decide:

```python
low_vram = (DEV["vram_gb"] or 99) < 8.0
_RELIGHT_PIPE = carregar_iclight(device="cuda", low_vram=low_vram)
```

`or 99` ensures that `None` (detection failure) is treated as high VRAM (no forced low-vram mode), rather than always triggering low-vram path. This is a safe default since `pode_relight` would already be False in that case.

## Colab-Specific Behaviour

- `share=True` passed to `demo.launch()` only in Colab → generates public ngrok URL.
- Workspace base resolves to `/content/drive/MyDrive/iclight_pipeline` on Colab.
- Live tab is usable in Colab UI but `live.py` subprocess requires a webcam device — effectively a local-only feature.
