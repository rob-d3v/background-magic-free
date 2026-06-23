---
title: "Alpha matting — suavização de bordas no rembg"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/remocao.py"]
tags: [concept, alpha-matting, rembg, trimap, segmentation, border]
---
# Alpha matting — suavização de bordas no rembg

Alpha matting é o pós-processamento que suaviza as bordas da máscara gerada pelo U²-Net, produzindo transições naturais em regiões de cabelo, contornos difusos e sobreposições. É habilitado via `alpha_matting=True` na chamada a `remove()`.

## Por que é necessário

O U²-Net gera uma **máscara binária bruta**: cada pixel é classificado como foreground
ou background com um limiar. Em bordas de cabelo, contornos de braços e regiões
de penumbra, essa binarização produz serrilhado visível. O alpha matting refina essas
regiões "indecisas" usando a imagem original como referência de cor.

## Algoritmo (trimap-based matting)

rembg usa o algoritmo **PyMatting** internamente. O fluxo é:

```
máscara U²-Net (float [0,1] por pixel)
    │
    ├─ erosão (erode_size=10) → zona "definitivamente background"
    │
    ├─ dilatação implícita → zona "definitivamente foreground"
    │
    └─ região entre ambas → "unknown" (zona de transição)
         │
         ▼
    trimap: {foreground=1, background=0, unknown=0.5}
         │
         ▼
    PyMatting solver (least-squares sobre cor local)
         │
         ▼
    alpha matte refinado (float per-pixel)
```

Os três parâmetros de `remocao.py` controlam onde a máscara U²-Net é particionada:

| Parâmetro | Valor | Papel no trimap |
|---|---|---|
| `alpha_matting_foreground_threshold` | 240 | Máscara > 240/255 → foreground definitivo |
| `alpha_matting_background_threshold` | 10 | Máscara < 10/255 → background definitivo |
| `alpha_matting_erode_size` | 10 | Pixels de erosão ao redor do foreground (expande a zona unknown) |

Pixels com máscara entre 10 e 240 (e dentro da erosão) caem na zona "unknown" e
são refinados pelo solver.

## Custo

Alpha matting é computacionalmente mais caro que usar a máscara bruta diretamente:
o solver PyMatting resolve um sistema esparso por imagem. Em CPU, pode adicionar
0.5–2s por frame. Em GPU via ONNX Runtime, o custo do solver ainda corre em CPU
(PyMatting é puro Python/NumPy), então a diferença entre CPU e GPU é menor aqui
do que na fase de segmentação.

## Trade-off qualidade × velocidade

| Configuração | Resultado |
|---|---|
| `alpha_matting=False` | Máscara binária bruta — mais rápido, bordas serrilhadas |
| `alpha_matting=True` (configuração atual) | Bordas suaves — mais lento, qualidade melhor |
| `erode_size` maior | Mais zona unknown → mais suavidade, mais tempo |
| `erode_size` menor | Menos zona unknown → mais rápido, bordas mais duras |

A configuração atual (`erode_size=10`) foi escolhida como balanceamento padrão.
Ver [[decisions/agent-background-removal-model-choice]] para a justificativa.

## Saída: canal alpha

O PNG RGBA resultante tem:
- **Canal RGB**: cor do pixel original da pessoa.
- **Canal A**: 0 = totalmente transparente (background), 255 = totalmente opaco
  (foreground seguro), valores intermediários = bordas suaves (resultado do matting).

O downstream ([[entities/relighting]]) não usa o alpha diretamente como máscara —
compõe o RGBA sobre cinza `(127,127,127)` para obter RGB sólido antes do VAE.
Isso evita halos de cor nas bordas quando o IC-Light processa a imagem.

## Gotchas

- `alpha_matting_foreground_threshold=240` é conservador: apenas pixels com máscara
  > 94% são tratados como foreground seguro. Isso reduz falsos foregrounds em regiões
  de sombra sobre a roupa.
- Se a pessoa usa roupa muito clara (próxima de branco), pixels de roupa podem superar
  o threshold 240 mas ser confundidos com background claro — a qualidade do U²-Net
  importa mais que os parâmetros de matting nesses casos extremos.

## Relacionados

[[entities/agent-background-removal-remocao]] · [[concepts/agent-background-removal-onnx-inference]] ·
[[concepts/rembg-background-removal]] · [[decisions/agent-background-removal-model-choice]] · [[index]]
