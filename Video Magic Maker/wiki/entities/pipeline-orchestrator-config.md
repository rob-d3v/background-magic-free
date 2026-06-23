---
title: config.py — Paths e detecção de device
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["config.py"]
tags: [component, config, paths, gpu-detection]
status: stable
---
# config.py — Paths e detecção de device

`config.py` centraliza duas responsabilidades anteriormente espalhadas em `pipeline.py`: resolução dinâmica do workspace (substitui paths hardcoded Colab) e detecção de capacidade de GPU para selecionar o modo de execução.

## `resolver_base(base)` — prioridade de workspace

Resolve em cascata:

1. Argumento explícito `base` (via `--base` no CLI).
2. Variável de ambiente `LUMINA_BASE`.
3. `/content/drive/MyDrive/iclight_pipeline` se rodando no Google Colab com Drive montado.
4. `./workspace` como fallback local.

Retorna um caminho absoluto (`os.path.abspath`). A detecção de Colab tenta `import google.colab` — se o import falha, não é Colab.

## `Paths` — container de paths derivados

```python
Paths(base=None)   # chama resolver_base internamente
```

Todos os caminhos são construídos como strings simples (sem `pathlib`) a partir de `self.base`:

| Atributo | Caminho |
|---|---|
| `base` | raiz do workspace |
| `input` | `{base}/input` |
| `frames_raw` | `{base}/frames/raw` |
| `frames_nobg` | `{base}/frames/nobg` |
| `frames_relit` | `{base}/relit` |
| `background_dir` | `{base}/background` |
| `bg_output` | `{base}/background/bg.png` |
| `preview_dir` | `{base}/preview` |
| `output_dir` | `{base}/output` |
| `log_path` | `{base}/pipeline_log.json` |

`criar_dirs()` cria todos os diretórios com `os.makedirs(exist_ok=True)` e retorna `self` (fluent).

## `detectar_device()` — capacidade de compute

Retorna um `dict` com:

```python
{
  "device": "cuda" | "cpu",
  "cuda": bool,
  "gpu_name": str | None,
  "vram_gb": float | None,
  "pode_relight": bool,   # True se vram_gb >= 5.0
}
```

`pode_relight` usa limiar de **5 GB**: IC-Light SD 1.5 fp16 precisa ~6 GB confortável; 4 GB é arriscado. O limiar de 5 GB marca o ponto em que o relighting é tentado (com ou sem `low_vram`). Qualquer exceção no `import torch` ou na consulta CUDA é silenciada — o resultado cai para CPU.

## Uso no orquestrador

```python
paths = Paths(args.base).criar_dirs()
output = args.output or f"{paths.output_dir}/video_final.mp4"
dev = detectar_device()
```

O `pipeline.py` passa `paths.*` para cada agente — nenhum agente precisa construir seus próprios caminhos.

## Gotchas

- `Paths.bg_output` é um arquivo único reutilizado para todos os frames (fundo estático).
- `Paths.log_path` é sobrescrito ao final do pipeline (não append); erros acumulados durante a execução são mergeados em memória.
- `_em_colab()` testa presença do pacote `google.colab`, não de `COLAB_GPU` ou variáveis de ambiente alternativas — pode falhar em ambientes customizados que montam Drive sem o pacote.

## Relacionados

[[entities/pipeline]] · [[concepts/pipeline-orchestrator-mode-selection]] · [[decisions/pipeline-orchestrator-paths-refactor]] · [[index]]
