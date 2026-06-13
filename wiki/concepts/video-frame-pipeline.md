---
tags: [concept, pipeline, resume, video]
date: 2026-06-13
status: stable
source: pipeline.py
---

# Pipeline frame-a-frame e mecanismo de resume

A pipeline processa vídeo como uma **sequência de frames PNG** que fluem por
diretórios. Cada estágio lê de um diretório e escreve em outro, o que torna a
execução **idempotente e resumível** — essencial porque o Colab gratuito
desconecta. Orquestração em [[components/pipeline]].

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
Os agentes por-frame ([[components/remocao]], [[components/relighting]]) checam
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
- [[components/extracao]] e [[components/exportacao]] **não** têm resume granular
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
[[components/pipeline]] · [[components/extracao]] · [[components/remocao]] ·
[[components/relighting]] · [[components/exportacao]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[index]]
