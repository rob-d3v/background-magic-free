---
tags: [component, agent, ffmpeg, extraction]
date: 2026-06-13
status: stable
source: agentes/extracao.py
---

# extracao — Agente 1 (Extração de Frames)

`agentes/extracao.py` → `extrair_frames(video_path, output_dir)`. Converte o vídeo
de entrada em frames PNG e devolve metadados usados pelo resto da pipeline.

## O que faz
1. `ffprobe` lê `r_frame_rate`, `width`, `height`, `nb_frames` do stream `v:0`.
2. Calcula `fps` resolvendo a fração (`"30000/1001"` → `29.97`).
3. `ffmpeg` extrai frames para `frame_%05d.png` com `-q:v 1` e `-pix_fmt rgb24`.

## Inputs / Outputs
- **Input:** `video_path` (`.mp4`).
- **Output:** PNGs em `output_dir` (`frames/raw/`) e um `dict`:
  `{fps, total_frames, width, height, tempo_s}`.

## Parâmetros-chave
- `-q:v 1` — qualidade máxima na extração.
- `-pix_fmt rgb24` — saída RGB.
- Nomeação `frame_%05d.png` — 5 dígitos; padrão consumido por todos os agentes
  e pela exportação.

## Gotchas
- Roda local **e** no Colab (não precisa de GPU) — verificado local nesta sessão.
  Ver [[concepts/gpu-vram-local-vs-colab]].
- **Não tem resume granular:** `-y` sobrescreve. Reexecutar reextrai tudo (rápido).
- `nb_frames` do ffprobe pode vir ausente/impreciso; o `total_frames` reportado é
  contado a partir dos arquivos no diretório, não do metadado.
- Depende de `ffmpeg`/`ffprobe` no PATH (no Colab é instalado via `apt-get`).

## Relacionados
[[components/pipeline]] · [[components/remocao]] · [[components/exportacao]] ·
[[concepts/video-frame-pipeline]] · [[index]]
