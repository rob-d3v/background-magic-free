---
title: "Cálculo dinâmico de downsample_ratio (RVM offline)"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/render_video.py
tags:
  - rvm
  - downsample-ratio
  - qualidade
  - offline
---

# Cálculo dinâmico de downsample_ratio (RVM offline)

No modo offline, o `downsample_ratio` do RVM é calculado para manter ~720px no lado mais longo do frame — mais detalhe que o default 0.4 de tempo real (~512px), custo extra aceitável sem pressão de FPS.

## Fórmula

```python
def _dr_qualidade(w: int, h: int) -> float:
    longo = max(w, h)
    return max(0.35, min(0.7, 720.0 / longo))
```

Exemplos:
- Frame 1920x1080 → longo=1920 → dr = max(0.35, min(0.7, 0.375)) = **0.375** (clamped a 0.35 se menor).
- Frame 1280x720 → longo=1280 → dr = max(0.35, min(0.7, 0.5625)) = **0.5625**.
- Frame 540x960 → longo=960 → dr = max(0.35, min(0.7, 0.75)) = **0.70** (clamped a 0.70).

## Por que não usar dr=1.0

O RVM roda em duas etapas internas (coarse + refine). A etapa coarse roda na resolução `dr * tamanho_original`. Aumentar dr além do necessário aumenta o custo quadraticamente sem ganho proporcional de qualidade — o refine já recupera detalhe fino.

## Comparação com modo ao vivo

| Modo | dr | Alvo de resolução coarse |
|---|---|---|
| Tempo real (padrão) | 0.4 | ~512px |
| Offline (`_dr_qualidade`) | dinâmico | ~720px |

## Relações

- [[composicao-render-video-rvm-matter]] — recebe o `dr` calculado aqui.
- [[composicao-render-video-render-video]] — chama `_dr_qualidade` ao instanciar o matter.
