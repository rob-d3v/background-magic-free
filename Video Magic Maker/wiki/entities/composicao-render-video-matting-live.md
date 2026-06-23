---
title: "LiveMatter — Matting em tempo real (MediaPipe)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/matting_live.py
tags:
  - mediapipe
  - matting
  - realtime
  - segmentation
---

# LiveMatter — Matting em tempo real (MediaPipe)

Segmentador de pessoa em tempo real usando MediaPipe Tasks ImageSegmenter, rodando a ~30 fps em CPU; também fornece utilitários de fundo compartilhados pelo pipeline offline.

## Uso no contexto offline

Embora desenhado para o modo ao vivo (webcam), o `matting_live.py` exporta helpers usados pelo [[composicao-render-video-render-video]]:

- `cobrir(img, w, h)` — resize+crop cobrindo dimensões alvo (mesmo padrão do [[composicao-render-video-composicao]]).
- `VideoFundo(path, w, h)` — iterador de frames de vídeo em loop como fundo.
- `fundo_desfocado(frame, blur)` — retorna o próprio frame desfocado como fundo.
- `_color_match(fg, bg, alpha, strength)` — casamento de cor por média ponderada pela alpha.

## Modelo

`selfie_segmenter.tflite` (~250 KB), baixado de `storage.googleapis.com/mediapipe-models` e cacheado em `./models/`. Carregado como buffer em memória (não por path) para contornar bug do loader C++ do MediaPipe com caminhos com acento no Windows.

## Pipeline `compor` (MediaPipe)

1. `mask(frame_bgr)` → confidence mask float32 [0,1] com suavização temporal opcional (mistura frame atual com anterior).
2. Refinamento de borda via `refinar_borda` (guided filter ou bilateral fallback) se `refine=True`.
3. Binarização com `threshold` (0.6 descarta bolhas de ombro ~0.55 sem afetar corpo ~1.0).
4. Abertura morfológica opcional (default 0 — desligada por cortar detalhes finos).
5. Limpeza de ilhas via `_maior_componente` (mantém componentes >= 10% da maior).
6. Erosão e feather gaussiano.
7. Blending com `color_match` opcional.

## Relações

- [[composicao-render-video-render-video]] importa `cobrir`, `VideoFundo`, `fundo_desfocado` deste módulo.
- [[composicao-render-video-rvm-matter]] importa `_color_match` deste módulo.
- `LiveMatter` e `RVMMatter` compartilham interface `compor(frame, bg, ...)`.
