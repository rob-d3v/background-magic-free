---
title: "ffmpeg reassembly: dois passes para vídeo final com áudio original"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/exportacao.py", "agentes/render_video.py"]
tags: [concept, exportacao, ffmpeg, audio, h264, mux, reassembly]
---
# ffmpeg reassembly: dois passes para vídeo final com áudio original

O [[entities/exportacao]] (Agente 5) e a variante `render_arquivo` em
[[entities/render-video]] reconstroem o vídeo final em dois passes ffmpeg
separados: (1) frames PNG → vídeo mudo H.264 e (2) mux do áudio original.

## Por que dois passes?

O vídeo de saída é **reconstruído a partir de PNGs** — não é uma transcodificação
direta do vídeo original. Isso significa que o áudio não está disponível na etapa
de encoding dos frames. A separação em dois passes permite:

1. Encoding de vídeo com opções de qualidade específicas (`crf`, `preset`).
2. Mux de áudio com `-c:v copy` (copia o H.264 sem reencoding), minimizando
   degradação e tempo de processamento.

## Passo 1 — Encoding dos frames

```bash
ffmpeg -y
  -framerate <fps>
  -i <frames_dir>/frame_%05d.png
  -c:v libx264
  -crf <crf>
  -pix_fmt yuv420p
  -preset slow
  <output>_noaudio.mp4
```

### Input pattern `frame_%05d.png`

O ffmpeg interpreta `%05d` como sequência numérica com zero-padding de 5 dígitos
(`frame_00001.png`, `frame_00002.png`, …). O padrão é definido pela
[[entities/extracao]] que extrai os frames com esse mesmo nome. Se os frames
forem numerados diferentemente ou com gaps, o ffmpeg para na primeira ausência.

### `-framerate` como input option

Colocar `-framerate` **antes de `-i`** define a taxa de leitura do image2
demuxer. Se fosse output option (depois de `-i`), o ffmpeg interpretaria como
taxa de saída e poderia duplicar/descartar frames para adaptar, causando drift
de A/V sync.

### `-pix_fmt yuv420p`

Por padrão `libx264` pode escolher `yuv444p` quando o input tem 4 canais
(RGBA). `yuv420p` força subsampling de croma 4:2:0, que é o único formato
suportado por players Apple (QuickTime, iOS) e muitos hardware decoders. Necessário
para compatibilidade universal.

### Naming do temporário

`output_path.replace(".mp4", "_noaudio.mp4")` — sem uso de `tempfile`. Isso
significa que o arquivo temporário fica no mesmo diretório que o output final e
com nome previsível. Se o processo for interrompido entre os dois passes, o
`_noaudio.mp4` fica no disco como artefato.

## Passo 2 — Detecção de áudio e mux

### exportacao.py — detecção por ffprobe

```bash
ffprobe -v error -select_streams a \
  -show_entries stream=codec_type \
  -of json <video_original>
```

Checa `'"codec_type": "audio"' in probe.stdout`. Ver
[[decisions/agent-composition-export-ffprobe-audio-detection]] para análise de
robustez desta abordagem.

**Se tem áudio:**
```bash
ffmpeg -y
  -i _noaudio.mp4 -i video_original
  -c:v copy -c:a aac
  -map 0:v:0 -map 1:a:0
  -shortest
  output.mp4
```

**Se não tem áudio:** `os.rename(_noaudio.mp4, output.mp4)`.

### render_video.py — abordagem mais robusta

```bash
ffmpeg -y -i _noaudio.mp4 -i input_path
  -map 0:v:0 -map 1:a:0?
  -c:v copy -c:a aac
  -shortest output_path
```

O sufixo `?` em `-map 1:a:0?` torna o stream opcional — sem áudio, o ffmpeg
apenas ignora sem erro. Não precisa de ffprobe separado. Mais robusto e um
subprocesso a menos.

## `-shortest` e sincronização

`-shortest` encerra a saída quando o stream mais curto terminar. Isso protege
contra cenários onde a contagem de frames extraídos diverge da duração do áudio
original (ex: vídeo com frame rate variável, VFR). O risco é que um drift
significativo produz vídeo mais curto que o original.

## Reencoding de áudio para AAC

`-c:a aac` reencoda o áudio. O áudio original pode estar em qualquer codec (AAC,
MP3, AC-3, PCM, Opus). Reencoding garante compatibilidade do container `.mp4`
com AAC, mas adiciona uma geração de compressão. Para preservação de qualidade,
`-c:a copy` seria preferível — mas só funciona se o codec original já for
compatível com o container mp4 (AAC, MP3 sim; Opus não).

## Relacionados

[[entities/exportacao]] · [[entities/render-video]] · [[entities/extracao]] ·
[[decisions/agent-composition-export-ffprobe-audio-detection]] ·
[[decisions/agent-composition-export-crf-preset]] ·
[[concepts/video-frame-pipeline]] · [[index]]
