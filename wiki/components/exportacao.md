---
tags: [component, agent, ffmpeg, export]
date: 2026-06-13
status: stable
source: agentes/exportacao.py
---

# exportacao — Agente 5 (Composição e Exportação)

`agentes/exportacao.py` → `exportar_video(frames_dir, video_original,
output_path, fps, crf=18)`. Compila os frames relitados no `.mp4` final,
reanexando o áudio do vídeo original.

## O que faz
1. `ffmpeg` monta o vídeo a partir de `frame_%05d.png` (`libx264`, `-crf`,
   `yuv420p`, `-preset slow`) num arquivo temporário `*_noaudio.mp4`.
2. `ffprobe` checa se o vídeo original tem stream de áudio.
3. Se tem: remuxa vídeo (`-c:v copy`) + áudio reencodado (`-c:a aac`) com
   `-map 0:v:0 -map 1:a:0 -shortest`. Se não tem: apenas renomeia o temp.

## Inputs / Outputs
- **Inputs:** `frames_dir` (`relit/`), `video_original` (para o áudio), `fps`
  (de [[components/extracao]]), `crf`.
- **Output:** `output/video_final.mp4`; `dict` `{output, tempo_s}`.

## Parâmetros-chave
- `fps` — deve casar com o `fps` da extração para sincronizar áudio/vídeo.
- `crf` (default 18) — qualidade H.264 (18=alta, 23=média, 28=menor).
- `-preset slow` — melhor compressão, mais lento.

## Gotchas
- Roda local e no Colab (sem GPU) — verificado local nesta sessão. Ver
  [[concepts/gpu-vram-local-vs-colab]].
- **Detecção de áudio é frágil:** baseia-se em encontrar a substring
  `'"codec_type": "audio"'` na saída do ffprobe.
- `-shortest` corta o vídeo no menor stream — se a contagem de frames divergir do
  áudio, o resultado pode ficar mais curto.
- Sem resume: reexecutar regenera o `.mp4` do zero (rápido).

## Relacionados
[[components/pipeline]] · [[components/extracao]] · [[components/relighting]] ·
[[components/render-video]] · [[concepts/video-frame-pipeline]] · [[index]]
