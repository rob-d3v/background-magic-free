---
title: "Cover-crop de fundo: algoritmo de preenchimento sem distorção"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/composicao.py", "agentes/matting_live.py"]
tags: [concept, composicao, image-processing, cover-crop, pillow]
---
# Cover-crop de fundo: algoritmo de preenchimento sem distorção

O [[entities/composicao]] (Agente 4b) e o [[entities/live-mode]] (modo câmera ao
vivo) precisam sobrepor uma pessoa recortada sobre um fundo que pode ter resolução
e proporção arbitrárias. O algoritmo implementa um **cover-crop**: o fundo cobre
todo o frame sem distorção, com corte centralizado no excesso.

## O problema

- Foreground tem tamanho fixo `(w, h)` — resolução do vídeo de entrada.
- Background pode ser qualquer imagem: quadrada, retrato, paisagem, 4K.
- Objetivo: redimensionar o background para cobrir `(w, h)` exatamente, sem
  barras pretas, sem esticar.

## Algoritmo (Python/Pillow)

```python
iw, ih = bg.size                      # tamanho original do fundo
scale = max(w / iw, h / ih)           # scale que garante cobertura total
nw, nh = int(round(iw * scale)), int(round(ih * scale))
bg = bg.resize((nw, nh), Image.LANCZOS)
left = (nw - w) // 2
top  = (nh - h) // 2
bg = bg.crop((left, top, left + w, top + h))
```

### Por que `max` e não `min`?

- `min` → letterbox: o fundo cabe inteiro, mas sobram barras pretas em uma dimensão.
- `max` → cover: o fundo cobre tudo, mas o excesso numa dimensão é cortado.

Para composição de pessoa sobre fundo, cover é o comportamento correto — barras
pretas são inaceitáveis.

### Central crop

`left = (nw - w) // 2` e `top = (nh - h) // 2` centraliza o crop, descartando
igual de cada lado. Isso preserva o centro da imagem de fundo. Não há opção de
ajustar o ponto de ancoragem (ex: crop no topo para retratos).

### Resampling LANCZOS

`Image.LANCZOS` (Lanczos anti-aliasing) é o filtro de maior qualidade do Pillow
para downscale. Para upscale (fundo menor que o frame) também é boa escolha por
minimizar aliasing.

## Implementações no projeto

| Módulo | Contexto |
|---|---|
| `agentes/composicao.py` → `compor_frame` | pipeline offline (batch) |
| `agentes/matting_live.py` → `cobrir(img, w, h)` | modo câmera ao vivo (cv2) |
| `agentes/render_video.py` → `cobrir(...)` | render offline de matting RVM |

A função `cobrir` em `matting_live.py` implementa a mesma lógica em OpenCV
(`cv2.resize` + slicing NumPy) em vez de Pillow. A lógica matemática é idêntica.

## Relacionados

[[entities/composicao]] · [[entities/live-mode]] · [[entities/render-video]] ·
[[concepts/agent-composition-export-alpha-composite]] · [[index]]
