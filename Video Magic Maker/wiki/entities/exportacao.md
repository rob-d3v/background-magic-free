---
title: exportacao — Agente 5 (Exportação de Vídeo Final)
type: entity
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/exportacao.py", "pipeline.py", "agentes/render_video.py"]
tags: [component, agent, ffmpeg, export, audio, h264]
status: stable
migrated-from: wiki/components/exportacao.md
original-date: 2026-06-13
---
# exportacao — Agente 5 (Exportação de Vídeo Final)

`agentes/exportacao.py` → `exportar_video(...)`. Compila os frames processados
(relitados ou compostos) num `.mp4` final H.264, reanexando o áudio do vídeo
original sem reencoding de vídeo na etapa de mux.

## Papel na pipeline

Último agente da [[entities/pipeline]] (etapa 5/5). Consome os PNGs de `relit/`
(gerados por [[entities/relighting]] ou [[entities/composicao]]) e produz o
arquivo de entrega em `output/video_final.mp4`.

```
relit/frame_%05d.png  +  input/video_original.mp4
    ↓ exportar_video
output/video_final.mp4  (H.264 + AAC, áudio original)
```

## Assinatura

```python
def exportar_video(
    frames_dir: str,
    video_original: str,
    output_path: str,
    fps: float,
    crf: int = 18,
) -> dict:
```

## Algoritmo em dois passes ffmpeg

### Passo 1 — Frames → vídeo sem áudio

```bash
ffmpeg -y \
  -framerate <fps> \
  -i <frames_dir>/frame_%05d.png \
  -c:v libx264 \
  -crf <crf> \
  -pix_fmt yuv420p \
  -preset slow \
  <output>_noaudio.mp4
```

Detalhes:
- `-framerate` é passado **antes** de `-i` (input option), não como output
  option — isso instrui ffmpeg a ler os frames na taxa correta.
- `-pix_fmt yuv420p` garante compatibilidade com players que não suportam
  yuv444 (padrão de saída do libx264 para imagens RGBA).
- `-preset slow` melhora a compressão sem impacto perceptível em qualidade;
  o export raramente é o gargalo (dominado pelo [[entities/relighting]]).
- `check=True` — qualquer erro do ffmpeg lança `subprocess.CalledProcessError`.
- `capture_output=True` — stdout/stderr do ffmpeg não polui o console do pipeline.

### Passo 2 — Detecção de áudio e mux

Usa `ffprobe` para detectar stream de áudio no vídeo original:

```bash
ffprobe -v error -select_streams a \
  -show_entries stream=codec_type \
  -of json <video_original>
```

Detecção por substring: `'"codec_type": "audio"' in probe.stdout`.

> ⚠️ Fragilidade: a detecção é baseada em presença de substring no JSON de saída
> do ffprobe. Em vídeos com múltiplos streams ou formatação JSON incomum isso
> pode falhar silenciosamente. Ver [[decisions/agent-composition-export-ffprobe-audio-detection]].

**Se tem áudio:**
```bash
ffmpeg -y -i _noaudio.mp4 -i video_original \
  -c:v copy -c:a aac \
  -map 0:v:0 -map 1:a:0 \
  -shortest \
  output.mp4
```
- `-c:v copy` — copia o stream H.264 sem reencoding (rápido, sem perda).
- `-c:a aac` — reencoda o áudio original para AAC (compatibilidade universal).
- `-map 0:v:0 -map 1:a:0` — seleciona explicitamente vídeo do temp e áudio do original.
- `-shortest` — encerra quando o stream mais curto terminar (protege contra drift
  de duração entre frames e áudio).
- Remove o arquivo `_noaudio.mp4` após mux bem-sucedido.

**Se não tem áudio:** renomeia `_noaudio.mp4 → output.mp4`.

### Naming do arquivo temporário

```python
temp_video = output_path.replace(".mp4", "_noaudio.mp4")
```

Deriva o nome do temp a partir do output final — não usa `tempfile`. Se o processo
for interrompido entre os dois passes, o arquivo `_noaudio.mp4` fica no disco
como artefato de crash. Não há cleanup automático de arquivos parciais.

## Parâmetros-chave

| Param | Default | Nota |
|---|---|---|
| `fps` | — | **Obrigatório.** Vem de [[entities/extracao]] via `pipeline_log`. Deve casar com a taxa de extração para A/V sync. |
| `crf` | 18 | Qualidade H.264: 0=perfeito, 51=péssimo, 18=alta, 23=média |
| `-preset` | slow | Hardcoded. Não exposto como parâmetro. |

## Output

Retorna `{"output": output_path, "tempo_s": elapsed}`.

O `output_path` padrão quando chamado do [[entities/pipeline]] é
`{workspace}/output/video_final.mp4`. Pode ser sobrescrito com `--output` no CLI.

## Sem resume granular

O agente não tem resume por frame — reexecuta sempre do zero. Isso é aceitável
porque o export é rápido (leitura de PNGs + encoding em CPU): tipicamente
segundos mesmo para vídeos de 1 minuto. Ver [[concepts/video-frame-pipeline]].

## Variante em render_video.py

`agentes/render_video.py` → `render_arquivo` usa uma abordagem diferente para
o mux de áudio:

```bash
ffmpeg -y -i _noaudio.mp4 -i input_path \
  -map 0:v:0 -map 1:a:0? \
  -c:v copy -c:a aac \
  -shortest output_path
```

A diferença chave é `-map 1:a:0?` — o `?` torna o stream de áudio **opcional**:
se o vídeo não tiver áudio, o ffmpeg ignora sem erro em vez de abortar. Isso é
mais robusto que a sonda por substring do `exportacao.py`. Ver
[[decisions/agent-composition-export-ffprobe-audio-detection]].

## Relacionados

[[entities/pipeline]] · [[entities/extracao]] · [[entities/relighting]] ·
[[entities/composicao]] · [[entities/render-video]] ·
[[concepts/agent-composition-export-ffmpeg-reassembly]] ·
[[concepts/video-frame-pipeline]] ·
[[decisions/agent-composition-export-ffprobe-audio-detection]] ·
[[decisions/agent-composition-export-crf-preset]] · [[index]]
