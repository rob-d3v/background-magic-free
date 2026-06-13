---
tags: [concept, rembg, segmentation, alpha-matting]
date: 2026-06-13
status: stable
source: agentes/remocao.py
---

# rembg — Remoção de fundo

[rembg](https://github.com/danielgatis/rembg) é a biblioteca que recorta a pessoa
de cada frame, usada pelo [[components/remocao]]. Saída: PNG **RGBA** com a pessoa
no foreground e o fundo transparente (alpha).

## Modelo: `u2net_human_seg`
- Sessão criada com `new_session("u2net_human_seg")` — variante do U²-Net
  treinada para **segmentação de pessoas** (melhor que `u2net` genérico para o
  caso de uso "pessoa em vídeo").
- Backend de inferência: **ONNX Runtime** (`onnxruntime-gpu` no Colab). É
  **independente do torch** — por isso roda em CPU local mesmo com torch CPU-only.
  Ver [[concepts/gpu-vram-local-vs-colab]].

## Alpha matting
Pós-processamento que suaviza as bordas da máscara (cabelo, contornos). Custa
tempo mas melhora a qualidade do recorte:

| Param | Valor | Papel |
|---|---|---|
| `alpha_matting` | `True` | liga o matting |
| `alpha_matting_foreground_threshold` | 240 | pixels acima ⇒ foreground certo |
| `alpha_matting_background_threshold` | 10 | pixels abaixo ⇒ background certo |
| `alpha_matting_erode_size` | 10 | erosão da máscara trimap |

## Consumo a jusante
O [[components/relighting]] não usa o alpha diretamente: compõe o RGBA sobre um
fundo **cinza neutro `(127,127,127)`** para obter um foreground RGB antes de
codificar no VAE. Isso evita halos de cor preta/branca nas bordas.

## Dicas de qualidade (do README)
- Boa iluminação no vídeo original melhora o recorte.
- Fundo original uniforme ⇒ máscara mais limpa.

## Relacionados
[[components/remocao]] · [[components/relighting]] ·
[[concepts/video-frame-pipeline]] · [[index]]
