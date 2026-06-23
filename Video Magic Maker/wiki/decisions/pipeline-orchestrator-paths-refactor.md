---
title: "Decisão: de-hardcodar paths → config.py (Paths + resolver_base)"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["config.py", "pipeline.py"]
tags: [decision, config, paths, orchestrator, colab, local]
status: completed
---
# Decisão: de-hardcodar paths → config.py (Paths + resolver_base)

## Contexto

O `pipeline.py` original fixava todos os caminhos para o Google Colab:

```python
BASE_DIR = "/content/drive/MyDrive/iclight_pipeline"
FRAMES_RAW = f"{BASE_DIR}/frames/raw"
# ...etc
```

Isso impedia rodar a pipeline localmente ou com um workspace em qualquer outra localização. Era o gotcha documentado em [[entities/pipeline]] e [[decisions/local-vs-colab]] como "tarefa aberta".

## Decisão

Extrair toda a lógica de paths para `config.py` como [[entities/pipeline-orchestrator-config]]:

- `resolver_base()` com cascata de prioridades (arg → env → Colab → ./workspace).
- `Paths` como container derivado — um único ponto de verdade para todos os caminhos.
- `detectar_device()` centralizado para GPU detection (antes inexistente; o modo era fixo "relight").

## Justificativa

- O orquestrador passa `paths.*` para todos os agentes — nenhum agente precisa construir paths próprios.
- `LUMINA_BASE` como env var é o padrão para desenvolvimento local sem mudar código.
- Detectar Colab pelo import `google.colab` é o método padrão (mais robusto que `COLAB_GPU` env var que pode vir vazia).
- Criar os diretórios em `Paths.criar_dirs()` com `exist_ok=True` torna a inicialização idempotente.

## Consequências

- `pipeline.py` deixou de ter qualquer path hardcoded — roda local e no Colab sem mudança de código.
- Introduziu `--base` como flag CLI e `LUMINA_BASE` como override de ambiente.
- Habilitou o `--modo auto` (antes impossível sem `detectar_device`).
- A variável `output` default deixou de ser hardcoded para `{paths.output_dir}/video_final.mp4`.

## Status

**Concluído.** `config.py` existe, `pipeline.py` usa `Paths` em toda referência de caminho.

## Relacionados

[[entities/pipeline-orchestrator-config]] · [[entities/pipeline]] · [[concepts/pipeline-orchestrator-mode-selection]] · [[decisions/local-vs-colab]] · [[index]]
