---
title: live-mode-engine-selection — MediaPipe vs RVM para matting em tempo real
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["live.py", "agentes/matting_live.py", "agentes/matting_rvm.py"]
tags: [decision, live, matting, mediapipe, rvm, performance, quality]
---
# live-mode-engine-selection — MediaPipe vs RVM para matting em tempo real

**Decisão (inferida):** oferecer dois motores de matting selecionáveis com diferentes tradeoffs de fps/qualidade em vez de se comprometer com um único, com o MediaPipe como default.

## Opções consideradas

### Opção A — apenas MediaPipe Selfie Segmenter (original)
- Rápido (~21fps @540p com `--fast`, ~15fps com guided filter).
- Confidence mask em resolução interna ~256² — não é um alpha matte verdadeiro.
- Requer pipeline de pós-processamento ([[concepts/live-mode-edge-refinement]]) para ser usável: guided filter, threshold, erosão, feather.
- Artefatos residuais em casos difíceis: cabelo "comido" em fundo claro, bolhas de ombro com confiança 0.55, halo remanescente.
- Não requer GPU, roda via XNNPACK em CPU.

### Opção B — apenas RVM (RobustVideoMatting)
- Alpha matte verdadeiro — alinhado à silhueta real incluindo fios de cabelo.
- Foreground descontaminado (`fgr`) elimina o artefato de aura branca nas bordas do cabelo.
- Recorrência temporal (estado GRU) fornece coerência natural entre frames.
- Mais lento: ~9.6fps @540p em CPU (torch).
- Requer `torch` + `torchvision`; modelo ~15MB baixado na primeira carga.
- Não necessita pós-processamento morfológico.

### Opção C (escolhida) — ambos os motores, selecionáveis pelo usuário
Default: MediaPipe (mais rápido, sem dependência de GPU, ampla compatibilidade).
Opt-in: RVM via `--engine rvm` (CLI) ou dropdown "Motor de recorte" na [[entities/camera-app]] (GUI).

`RVMMatter.compor()` é uma **substituição drop-in** de `LiveMatter.compor()` — aceita e ignora params específicos do MediaPipe (`refine`, `threshold`, `erode`, `abertura`) via `**_ignored`. O loop de `live.py` não muda entre os motores.

## Justificativa

- A maioria dos usuários tolera a qualidade do MediaPipe a 21fps; o caminho do guided filter a 15fps é aceitável para a maioria das webcams a 540p.
- Usuários que encontram o problema de "rosto sendo comido" em fundos claros/complexos obtêm uma solução real (RVM), não um workaround.
- O default de 540p equilibra fps e nitidez: 640×360 é grosseiro demais, 720p é lento demais em CPU sem GPU.
- A interface drop-in do RVM significa que a GUI e o CLI não precisam de lógica de bifurcação para os dois motores.

## Resolução e fps defaults

| Resolução | MediaPipe refine ON | MediaPipe `--fast` | RVM |
|---|---|---|---|
| 640×360 | ~33fps | ~42fps | — |
| **960×540 (default)** | **~15fps** | **~21fps** | **~9.6fps** |
| 1280×720 | ~9fps | ~13fps | — |

540p escolhido como default por atingir ~21fps (`--fast`) / ~15fps (qualidade) em CPU — fluidez adequada mantendo a imagem nítida o suficiente para uso em câmera virtual no Meet/Zoom.

## Diferença de downsample_ratio: live vs render offline

No modo **live**, `RVMMatter` usa `downsample_ratio=0.4` (mira ~512px no lado longo — otimizado para velocidade).

No **render offline** ([[entities/render-video]]), o ratio é calculado como `clamp(720/max(w,h), 0.35, 0.7)` (mira ~720px — otimizado para qualidade). A mesma classe `RVMMatter` é reutilizada; o ratio é passado na instanciação.

## Relacionados
[[entities/live-mode]] · [[entities/live-mode-cli]] · [[concepts/realtime-matting]] · [[concepts/rvm-matting]] · [[concepts/live-mode-frame-pipeline]] · [[concepts/live-mode-edge-refinement]] · [[index]]
