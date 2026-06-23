---
title: "Source: config.py — configuração central de paths e device"
type: source
created: 2026-06-22
updated: 2026-06-22
sources: ["config.py"]
tags: [source, config, paths, gpu-detection]
---
# Source: config.py

`config.py` é o módulo de configuração central da pipeline. Introduzido para de-hardcodar os paths Colab (ver [[decisions/pipeline-orchestrator-paths-refactor]]).

## O que o arquivo contém

### `_em_colab() -> bool`
Detecta Google Colab tentando `import google.colab`. Não usa variáveis de ambiente.

### `resolver_base(base) -> str`
Cascata de resolução de workspace. Documentada em [[entities/pipeline-orchestrator-config]].

### `Paths`
Dataclass-like que deriva todos os caminhos do workspace a partir de `base`. Todos os diretórios listados como strings simples. `criar_dirs()` materializa a estrutura de diretórios.

### `detectar_device() -> dict`
Retorna capacidade de compute. O campo `pode_relight` (bool) é o critério usado pelo orquestrador para `--modo auto`. Limiar: 5 GB VRAM.

## Relação com o orquestrador

`pipeline.py` importa apenas `Paths` e `detectar_device` de `config`:

```python
from config import Paths, detectar_device
```

Os agentes em `agentes/` não importam `config.py` — recebem os paths já resolvidos via parâmetros de função do orquestrador.

## Relacionados

[[entities/pipeline-orchestrator-config]] · [[entities/pipeline]] · [[decisions/pipeline-orchestrator-paths-refactor]] · [[index]]
