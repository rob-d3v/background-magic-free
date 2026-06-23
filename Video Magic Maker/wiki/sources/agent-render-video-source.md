---
title: "Fonte: agentes/render_video.py"
type: source
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/render_video.py"]
tags: [source, render, offline, rvm, mediapipe, ffmpeg, cpu]
---
# Fonte: agentes/render_video.py

`agentes/render_video.py` — **~175 linhas**. Render offline de troca de fundo
usando os motores de matting do modo live (RVM ou MediaPipe), aplicado a um vídeo
ou a um diretório de frames PNG.

## Síntese

O módulo resolve o problema: *"quero trocar o fundo de um vídeo gravado com
qualidade máxima, sem GPU e sem instalar nada pesado"*. É o caminho **poderoso
sem GPU**: melhor que `compor` (rembg) e dispensa a GPU/Colab do relight IC-Light.

## Símbolos exportados

| Símbolo | Tipo | Descrição curta |
|---|---|---|
| `render_matting(...)` | função pública | render de diretório de frames PNG |
| `render_arquivo(...)` | função pública | render de arquivo de vídeo com remux de áudio |
| `_build_matter(engine, dr)` | helper privado | instancia RVMMatter ou LiveMatter |
| `_dr_qualidade(w, h)` | helper privado | calcula downsample_ratio mirando ~720px |
| `_VIDEO_EXT` | constante | extensões de vídeo reconhecidas para fundo animado |

## Dependências diretas

| Import | Origem | Para quê |
|---|---|---|
| `cv2` | opencv-python | leitura/escrita de vídeo e imagem |
| `subprocess` | stdlib | chamada `ffmpeg` para remux de áudio |
| `time`, `os` | stdlib | métricas e IO |
| `agentes.matting_live` | local | `cobrir`, `VideoFundo`, `fundo_desfocado` |
| `agentes.matting_rvm` | local (lazy) | `RVMMatter` (importado apenas se `engine=="rvm"`) |

## Notas de implementação relevantes

- **Lazy import do RVM:** `_build_matter` só faz `from agentes.matting_rvm import
  RVMMatter` quando `engine=="rvm"`. Isso evita o custo de carga do torch em
  contextos que só usam MediaPipe.

- **`_dr_qualidade` para render offline:** em vez de usar o `downsample_ratio=0.4`
  default do RVM (mira ~512px no maior lado, bom pro live), o render usa
  `clamp(720/max(w,h), 0.35, 0.7)` — mira ~720px, mais detalhe de cabelo, custo
  aceitável offline. Detalhes em [[concepts/rvm-matting]].

- **Formato de vídeo temporário:** `cv2.VideoWriter_fourcc(*"mp4v")` produz um
  mp4 SEM stream de áudio. O áudio é adicionado depois via ffmpeg subprocess (não
  há como misturar áudio com `cv2.VideoWriter`).

- **`-map 1:a:0?` no ffmpeg:** o `?` torna o mapeamento de áudio opcional — sem
  ele, o ffmpeg retornaria erro se o vídeo de entrada não tiver áudio.

- **Path temporário:** `output_path[:-4] + "_noaudio.mp4"` (assumindo que
  `output_path` termina em `.mp4`); o try/except no mux garante que qualquer
  falha entrega o temporário renomeado para o path final, sem deixar lixo.

## Chamadores conhecidos

- `camera_app.py` → `_aplicar_render` → `render_arquivo` (botão "Aplicar")
- `app.py` (Studio Gradio) → `cb_aplicar` modo HD → `render_matting`

## Páginas relacionadas

[[entities/render-video]] · [[concepts/agent-render-video-offline-pipeline]] ·
[[decisions/agent-render-video-engine-forced-rvm]] · [[concepts/rvm-matting]] ·
[[entities/camera-app]] · [[index]]
