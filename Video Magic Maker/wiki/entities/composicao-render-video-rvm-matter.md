---
title: "RVMMatter — Matting com RobustVideoMatting"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/matting_rvm.py
tags:
  - rvm
  - matting
  - torch
  - alpha-matte
  - coerência-temporal
---

# RVMMatter — Matting com RobustVideoMatting

Motor de matting de vídeo de alta qualidade (RVM) que mantém estado recorrente entre frames, eliminando tremor de borda e halo causados por abordagens frame-isoladas.

## Por que RVM em vez de MediaPipe

O MediaPipe Selfie Segmentation produz uma "confidence mask" de baixa resolução, não um alpha matte real. Problemas práticos:
- "Come" o rosto em alguns ângulos.
- Cria bolhas de falso-positivo no ombro (~0.55 de confiança).
- Deixa franja de halo branca na borda do cabelo.

O RVM produz `fgr` (foreground descontaminado) + `pha` (alpha matte real). A borda do cabelo no `fgr` não carrega a cor do fundo antigo — isso elimina a aura.

Custo: torch em CPU, ~10 fps a 540p.

## Modelo

`rvm_mobilenetv3.pth` (~15 MB), variante `mobilenetv3`. Carregado via `torch.hub.load("PeterL1n/RobustVideoMatting", ...)`. Baixado e cacheado pelo torch.hub na primeira carga.

## Estado recorrente

O RVM é uma rede recorrente — mantém `rec = [None] * 4` (4 tensores de estado). O estado é passado como `*self.rec` na chamada e atualizado a cada frame:

```python
fgr, pha, *self.rec = self.model(src, *self.rec, downsample_ratio=self.dr)
```

O estado é zerado automaticamente se a resolução mudar entre frames (`_last_shape`). `reset()` permite zerar manualmente (usar entre clipes ou em preview de 1 frame isolado).

## Método `compor`

Usa o `fgr` descontaminado (não o frame bruto) na composição final:

1. `_infer(frame_bgr)` → `(fgr_bgr float, pha float HxW [0,1])`.
2. Feather opcional: `GaussianBlur` no alpha.
3. `_color_match` opcional (importado de [[composicao-render-video-matting-live]]).
4. Blending: `fg * a + bg * (1-a)`.

Interface drop-in com `LiveMatter.compor`: aceita e ignora params MediaPipe (`refine`, `threshold`, `erode`, etc.) via `**_ignored`.

## Relações

- Usado por [[composicao-render-video-render-video]] como engine padrão.
- Interface compartilhada com `LiveMatter` de [[composicao-render-video-matting-live]].
- `downsample_ratio` calculado por [[composicao-render-video-dr-qualidade]].
