---
title: "Decisão: detecção de áudio por substring ffprobe vs. -map opcional"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/exportacao.py", "agentes/render_video.py"]
tags: [decision, exportacao, ffmpeg, audio, ffprobe, robustness]
status: divergence
inferred: true
---
# Decisão: detecção de áudio por substring ffprobe vs. -map opcional

## Contexto

O [[entities/exportacao]] precisa saber se o vídeo original tem áudio antes de
tentar fazer o mux — se não tiver áudio e tentar mapear `-map 1:a:0`, o ffmpeg
aborta com erro. A decisão é: como detectar a presença de áudio de forma confiável?

## Duas abordagens no mesmo projeto

### exportacao.py — ffprobe + substring check

```python
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "a",
     "-show_entries", "stream=codec_type", "-of", "json", video_original],
    capture_output=True, text=True,
)
has_audio = '"codec_type": "audio"' in probe.stdout
```

Roda `ffprobe` separado e verifica presença da substring no JSON de saída.

**Problemas identificados:**
1. **Fragilidade de string matching.** O JSON pode estar formatado diferentemente
   (ex: `"codec_type":"audio"` sem espaços, embora improvável com `-of json`).
2. **Dois subprocessos.** ffprobe + ffmpeg (caso áudio presente). Menor, mas
   desnecessário.
3. **Comentário no render_video.py** confirma que a abordagem anterior "falhava
   em alguns casos": `# a sonda por string falhava em alguns casos`.

### render_video.py — `-map 1:a:0?` (stream opcional)

```bash
ffmpeg ... -map 1:a:0? ...
```

O sufixo `?` em ffmpeg torna o stream **opcional**: se não existir, o ffmpeg
ignora silenciosamente em vez de abortar. Sem ffprobe, sem verificação prévia.

**Vantagens:**
- Um subprocesso a menos.
- Lida corretamente com ausência de áudio sem lógica Python adicional.
- Não depende de parsing de saída de texto.

## Divergência entre os dois agentes

`render_video.py` adota a abordagem mais robusta (com base em experiência de
falha documentada em comentário), mas `exportacao.py` ainda usa a abordagem
antiga de ffprobe. Isso é uma inconsistência entre os dois caminhos de exportação.

## Recomendação (inferred)

Migrar `exportacao.py` para usar `-map 1:a:0?` em vez de ffprobe. O comentário
em `render_video.py` documenta explicitamente que a abordagem baseada em string
"falhava em alguns casos", sugerindo que a migração foi feita intencionalmente
naquele módulo mas não replicada para `exportacao.py`.

## Relacionados

[[entities/exportacao]] · [[entities/render-video]] ·
[[concepts/agent-composition-export-ffmpeg-reassembly]] · [[index]]
