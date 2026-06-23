---
title: Pipeline frame-a-frame e mecanismo de resume
type: concept
created: 2026-06-14
updated: 2026-06-14
sources: ["pipeline.py"]
tags: [concept, pipeline, resume, video]
status: stable
migrated-from: wiki/concepts/video-frame-pipeline.md
original-date: 2026-06-13
---
# Pipeline frame-a-frame e mecanismo de resume

A pipeline processa vídeo como uma **sequência de frames PNG** que fluem por
diretórios. Cada estágio lê de um diretório e escreve em outro, o que torna a
execução **idempotente e resumível** — essencial porque o Colab gratuito
desconecta. Orquestração em [[entities/pipeline]].

## Fluxo de diretórios (no Drive)
```
input/video.mp4
  → frames/raw/    (extracao, ffmpeg)
  → frames/nobg/   (remocao, rembg — RGBA)
  background/bg.png (geracao_fundo SD 1.5  |  ou fundo próprio)
  → relit/         (relighting, IC-Light)
  → output/video_final.mp4 (exportacao, ffmpeg + áudio original)
pipeline_log.json  (metadados + erros por etapa)
```

## Mecanismo de resume
Os agentes por-frame ([[entities/remocao]], [[entities/relighting]], [[entities/composicao]]) checam
se o output já existe antes de processar:

```python
if os.path.exists(output_path):
    continue   # resume automático
```

Consequências:
- Reexecutar a célula 7 do notebook **continua de onde parou** — não reprocessa
  frames prontos. (Documentado no [[index]] / README.)
- Os outputs são **nomeados de forma estável** (`frame_%05d.png`), então o nome
  do frame é a chave de idempotência.
- [[entities/extracao]] e [[entities/exportacao]] **não** têm resume granular
  (operam o vídeo inteiro), mas são baratos e seguros de reexecutar.

## Tratamento de erros
- Agentes por-frame usam `try/except` por frame: registram `{frame, erro}` em
  `erros` e **não abortam** o lote.
- Erros são persistidos em `pipeline_log.json` (`remocao_fundo_erros`,
  `relighting_erros`) para reprocessamento manual.
- O orquestrador soma `erros_total` e avisa ao final.

## Custo por etapa (T4, ~1 min de vídeo)
| Etapa | Por frame | Dominância |
|---|---|---|
| extração | ~1ms | desprezível |
| rembg | ~0.3s | média |
| SD 1.5 fundo | único (~15s) | desprezível (uma vez) |
| **IC-Light** | **~1.5s** | **gargalo** |
| export | ~2ms | desprezível |

## Relacionados
[[entities/pipeline]] · [[entities/extracao]] · [[entities/remocao]] ·
[[entities/relighting]] · [[entities/exportacao]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[index]]
