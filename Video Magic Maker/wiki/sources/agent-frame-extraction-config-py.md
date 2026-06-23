---
title: config.py — resolução de paths e detecção de device
type: source
created: 2026-06-22
updated: 2026-06-22
sources: ["config.py"]
tags: [source, config, paths, workspace, gpu, device]
---
# config.py — resolução de paths e detecção de device

`config.py` é o módulo central de configuração da pipeline lumina-bg. Resolve onde os arquivos de trabalho são armazenados e detecta capacidade de GPU. Relevante para o [[entities/extracao]] porque define o `output_dir` (`frames_raw`) passado à função de extração.

## `resolver_base(base=None) -> str`

Retorna o caminho absoluto do diretório raiz do workspace, com prioridade:

1. argumento `base` explícito (usado pelo CLI `pipeline.py --base`)
2. env var `LUMINA_BASE`
3. `/content/drive/MyDrive/iclight_pipeline` (se Colab com Drive montado)
4. `./workspace` (fallback local)

## Classe `Paths`

Inicializada com `Paths(base=None)`, expõe os caminhos derivados:

| Atributo | Caminho |
|---|---|
| `base` | raiz do workspace |
| `input` | `<base>/input` |
| `frames_raw` | `<base>/frames/raw` — **output da extração** |
| `frames_nobg` | `<base>/frames/nobg` |
| `frames_relit` | `<base>/relit` |
| `background_dir` | `<base>/background` |
| `bg_output` | `<base>/background/bg.png` |
| `preview_dir` | `<base>/preview` |
| `output_dir` | `<base>/output` |
| `log_path` | `<base>/pipeline_log.json` |

`criar_dirs()` cria todos os diretórios com `os.makedirs(exist_ok=True)` e retorna `self` (fluent interface).

## `detectar_device() -> dict`

Detecta GPU via PyTorch:

| Chave | Tipo | Significado |
|---|---|---|
| `device` | `"cuda"` \| `"cpu"` | device padrão |
| `cuda` | `bool` | CUDA disponível |
| `gpu_name` | `str \| None` | nome da GPU |
| `vram_gb` | `float \| None` | VRAM total em GB |
| `pode_relight` | `bool` | `vram_gb >= 5.0` |

O threshold de 5GB para `pode_relight` é conservador: IC-Light SD1.5 fp16 precisa ~6GB confortavelmente; 4GB é possível com offload mas arriscado.

## Uso pelos callers

- `pipeline.py` — `paths = Paths(args.base).criar_dirs()`, depois passa `paths.frames_raw` para `extrair_frames`.
- `app.py` — `PATHS = Paths().criar_dirs()` no topo do módulo (singleton de processo), usa `PATHS.frames_raw` no callback `cb_preparar`.

## Relacionados

[[entities/extracao]] · [[entities/pipeline]] · [[concepts/agent-frame-extraction-output-dir-conventions]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
