---
title: "Coerência temporal via estado recorrente RVM"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/matting_rvm.py
  - agentes/render_video.py
tags:
  - rvm
  - coerência-temporal
  - estado-recorrente
  - matting
---

# Coerência temporal via estado recorrente RVM

O RobustVideoMatting mantém 4 tensores de estado entre frames, o que produz bordas temporalmente estáveis — menos tremor — diferente de processar cada frame isoladamente.

## O problema que o estado resolve

Segmentadores frame-isolados (MediaPipe, rembg) tomam cada frame sem contexto. Resultado: a máscara "treme" entre frames consecutivos — a borda do cabelo oscila pra dentro/fora de maneira incoerente. Em vídeo isso aparece como ruído visual na borda.

O RVM foi treinado como rede recorrente: os tensores de estado `rec[0..3]` carregam informação dos frames anteriores para o próximo. A borda do frame N informa onde provavelmente vai estar a borda do frame N+1.

## Implementação

```python
fgr, pha, *self.rec = self.model(src, *self.rec, downsample_ratio=self.dr)
```

- Na primeira chamada `rec = [None, None, None, None]` — o modelo inicializa internamente.
- A partir do segundo frame, os tensores reais são passados e atualizados.
- Reset automático se a resolução mudar (`_last_shape`).
- `reset()` para zerar manualmente entre clipes.

## Implicação no resume parcial de render_video.py

`render_matting` pula frames já existentes em `output_dir` (resume automático). Mas se frames iniciais já existem e são pulados, o estado RVM começa do zero no primeiro frame não existente — a coerência temporal fica quebrada naquele ponto. O docstring da função avisa: *"pra um render limpo apague a saída antes"*.

## Relações

- [[composicao-render-video-rvm-matter]] — implementação do estado recorrente.
- [[composicao-render-video-render-video]] — usa o estado via processamento em ordem.
- [[composicao-render-video-dr-qualidade]] — controla a qualidade do matte relacionada ao downsample.
