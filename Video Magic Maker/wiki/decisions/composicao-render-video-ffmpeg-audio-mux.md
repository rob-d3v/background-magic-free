---
title: "Decisão: FFmpeg com -map 1:a:0? para áudio opcional"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/render_video.py
tags:
  - decisão
  - ffmpeg
  - áudio
  - robustez
---

# Decisão: FFmpeg com -map 1:a:0? para áudio opcional

> Inferred from source code comments.

O remux do áudio original após o render usa `-map 1:a:0?` (stream specifier opcional) em vez de sondar com `ffprobe` se o vídeo tem áudio.

## Contexto

Após o render do vídeo sem áudio (via `cv2.VideoWriter`), o sistema precisa remutar o áudio original do arquivo de entrada. Nem todo vídeo tem faixa de áudio (gravações de tela, loops GIF etc.).

## Decisão

```bash
ffmpeg -y -i tmp_noaudio.mp4 -i input.mp4 \
  -map 0:v:0 -map 1:a:0? \
  -c:v copy -c:a aac -shortest output.mp4
```

O `?` no stream specifier torna o áudio opcional: se não existir, o FFmpeg ignora silenciosamente.

## Rationale

A alternativa seria sondar com `ffprobe` antes e decidir o comando. O código comenta que essa abordagem "falhava em alguns casos" — provavelmente por variações no output textual do ffprobe. O `?` é mais robusto: resolve no próprio motor de remux.

## Fallback

Se o FFmpeg falhar por qualquer razão (não instalado, codec incompatível), o bloco `except` entrega o vídeo sem áudio via `os.replace(tmp, output)` — o resultado é degradado mas o arquivo sempre existe.

## Relações

- [[composicao-render-video-render-video]] — onde esta lógica está implementada.
