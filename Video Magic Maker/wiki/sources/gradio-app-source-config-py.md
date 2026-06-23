---
title: "Source — config.py"
type: source
created: 2026-06-22
updated: 2026-06-22
sources:
  - config.py
tags:
  - source
  - config
  - paths
  - gpu
---

`config.py` provides centralized workspace path resolution and GPU capability detection for lumina-bg, consumed by `app.py` at startup.

## File Summary

- **Lines**: ~109
- **Public API**: `resolver_base(base)`, `Paths`, `detectar_device()`
- **No side effects at import time** — all logic is in functions/class.

## Key Sections

| Lines | Content |
|---|---|
| 1–12 | Module docstring — describes 3 supported environments (local, Colab, custom) |
| 18–24 | `_em_colab()` — Colab detection via `google.colab` import |
| 27–49 | `resolver_base()` — 4-priority workspace root resolution |
| 52–73 | `Paths` class — path attributes + `criar_dirs()` |
| 76–108 | `detectar_device()` — GPU probe returning capability dict |

## Pages Derived From This Source

- [[gradio-app-config-device-detection]] (entity)
- [[gradio-app-gpu-gating]] (concept)
