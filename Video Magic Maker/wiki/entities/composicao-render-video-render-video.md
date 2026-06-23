---
title: "Agente Render Video (RVM offline)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/render_video.py
tags:
  - render
  - rvm
  - offline
  - background-swap
  - ffmpeg
---

# Agente Render Video (RVM offline)

Render offline de troca de fundo usando RVM ou MediaPipe, aplicado frame-a-frame sem pressão de tempo real — caminho "poderoso sem GPU".

## Papel no sistema

Diferente do modo live (webcam), aqui não há limite de FPS: o RVM roda em qualidade total com `downsample_ratio` calculado para ~720px no lado longo (ver [[composicao-render-video-dr-qualidade]]). A coerência temporal do RVM (estado recorrente entre frames) entrega bordas mais estáveis que o live frame-isolado.

Exporta: frames compostos (PNG) via `render_matting`, ou vídeo MP4 com áudio remuxado via `render_arquivo`.

## Funções

### `render_matting(frames_dir, background_path, output_dir, engine, ...)`

Processa um diretório de frames PNG já extraídos:

1. Detecta se o fundo é vídeo (`.mp4/.mov/...`) ou imagem — usa `VideoFundo` ou `cobrir` do [[composicao-render-video-matting-live]].
2. Instancia o matter (`RVMMatter` ou `LiveMatter`) via `_build_matter`.
3. Loop em ordem (essencial para o estado recorrente do RVM).
4. **Resume parcial**: pula frames existentes, mas o estado RVM reinicia — para render limpo, apagar a saída antes.
5. Chama `matter.compor(frame, fundo, color_match, feather)` por frame.

### `render_arquivo(input_path, output_path, engine, bg_mode, ...)`

Renderiza um arquivo de vídeo inteiro diretamente (sem extrair frames):

1. Lê FPS, dimensões, total de frames via `cv2.VideoCapture`.
2. Suporta `bg_mode`: `none` | `blur` | `image` | `video`.
3. Escreve vídeo sem áudio em arquivo temp `_noaudio.mp4` via `cv2.VideoWriter` (codec `mp4v`).
4. Remuxa o áudio original com FFmpeg: `-map 1:a:0?` torna o áudio opcional — se o vídeo não tiver áudio, o FFmpeg ignora sem erro.
5. Se o mux falhar, entrega o vídeo sem áudio (fallback `os.replace`).

## Parâmetros notáveis

| Param | Default | Significado |
|---|---|---|
| `engine` | `"rvm"` | Motor de matting: `"rvm"` ou `"mediapipe"` |
| `color_match` | `0.12` | Casamento de cor pessoa→fundo (0=off) |
| `feather` | `2` | Raio de blur gaussiano na borda (px) |
| `bg_mode` | `"blur"` | `none`/`blur`/`image`/`video` |
| `blur` | `45` | Raio do desfoque do próprio frame (bg_mode=blur) |

## Relações

- [[composicao-render-video-rvm-matter]] — motor de matting primário.
- [[composicao-render-video-matting-live]] — fornece `cobrir`, `VideoFundo`, `fundo_desfocado`, `LiveMatter`.
- Alternativa mais pesada e de maior qualidade ao [[composicao-render-video-composicao]].
