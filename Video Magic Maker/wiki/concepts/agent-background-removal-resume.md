---
title: "Resume automático por frame — Agente 2"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/remocao.py", "pipeline.py"]
tags: [concept, resume, idempotency, colab, per-frame, pipeline]
---
# Resume automático por frame — Agente 2

O Agente 2 suporta resume granular por frame: ao reexecutar a pipeline após uma interrupção (desconexão do Colab, crash), frames já processados são pulados e o processamento continua do primeiro frame ainda ausente.

## Mecanismo

```python
output_path = os.path.join(output_dir, frame_name)

if os.path.exists(output_path):
    continue   # resume automático — frame já existe
```

O nome do arquivo de saída (`frame_NNNNN.png`) é **idêntico** ao nome de entrada —
o `frame_name` vem de `os.listdir(frames_dir)` e é reutilizado como `output_path`.
Isso torna o nome do frame a **chave de idempotência**: se o arquivo existe em
`frames/nobg/`, o frame está concluído.

## Por que isso importa (contexto Colab)

O Colab gratuito desconecta após 30–90 minutos de inatividade. Um vídeo de 60 segundos
a 30fps tem 1800 frames; a ~0.3s/frame (GPU T4) leva ~9 minutos. Um vídeo de 10 minutos
(18.000 frames, ~90 minutos) pode ultrapassar o timeout.

Com resume, o operador simplesmente reexecuta a célula 7 do notebook:
- Frames em `frames/nobg/` são pulados instantaneamente.
- Apenas frames ausentes são processados.
- O total de trabalho perdido por desconexão é no máximo um frame (o que estava sendo
  processado no momento da queda).

## Garantia de completude

Após uma execução sem erros, `processados == len(frames)`. Com erros, os frames com
falha **não** geram arquivo de saída (a exceção é capturada antes do `open(..., "wb")`),
então uma reexecução **tentará reprocessar os frames com erro**.

> Isso é distinto do comportamento de resume normal: frames com erro não são pulados
> na reexecução — são retentados automaticamente.

## Integração com o orquestrador

`pipeline.py` não tem lógica própria de resume para o agente 2 — delega inteiramente
para `remover_fundo()`. O orquestrador apenas coleta o dict de resultado e registra
em `pipeline_log.json`:

```python
pipeline_log["etapas"].append({"etapa": "remocao_fundo", **result_rembg})
pipeline_log["erros_total"] += result_rembg["erros"]
```

## Comportamento em execução limpa (primeira vez)

Nenhum arquivo existe em `frames/nobg/`, então todos os frames são processados.
O `os.makedirs(output_dir, exist_ok=True)` no início da função garante que o diretório
exista antes do primeiro write.

## Relacionados

[[entities/agent-background-removal-remocao]] · [[concepts/video-frame-pipeline]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[index]]
