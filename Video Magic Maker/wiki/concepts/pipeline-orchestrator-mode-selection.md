---
title: Seleção de modo — auto / relight / compose
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["pipeline.py", "config.py"]
tags: [concept, pipeline, mode-selection, gpu, orchestrator]
status: stable
---
# Seleção de modo — auto / relight / compose

O [[entities/pipeline]] escolhe entre dois caminhos de processamento no passo 4 da pipeline: **relight** (IC-Light fbc, GPU) ou **compose** (alpha composite, CPU). A lógica de seleção usa `--modo` + resultado de `detectar_device()`.

## Os três valores de `--modo`

| Valor | Comportamento |
|---|---|
| `auto` (default) | decide baseado em `dev["pode_relight"]` |
| `relight` | força IC-Light fbc; cai para `compose` com aviso se não há GPU |
| `compose` | força composição CPU; nunca usa IC-Light |

## Fluxo de decisão

```
args.modo == "auto"
    └─ dev["pode_relight"] → modo = "relight"
    └─ não                  → modo = "compose"

args.modo == "relight"
    └─ dev["pode_relight"] falso → aviso + modo = "compose"  (fallback silencioso)

args.modo == "compose"
    └─ usa composicao.py diretamente (CPU, sem torch)
```

A sobrescrita de `"relight"` para `"compose"` ocorre **depois** do print do cabeçalho, então o log exibe o modo final correto.

## `pode_relight` — limiar de 5 GB

`detectar_device()` em [[entities/pipeline-orchestrator-config]] marca `pode_relight = vram_gb >= 5.0`. Isso é conservador: IC-Light SD 1.5 fp16 precisa ~6 GB confortável; 4 GB é arriscado mas tentável com offload. O limiar de 5 GB deixa a máquina local (GTX 1650 Ti, 4 GB) sempre em modo `compose`.

## Agentes invocados por modo

### Modo `relight`
- Agente 4: [[entities/relighting]] → `carregar_iclight` + `aplicar_relighting`
- Ativa `low_vram = (vram_gb < 8.0)`: GPUs de 5–7 GB usam `enable_sequential_cpu_offload` + `enable_attention_slicing` + `enable_vae_slicing`
- Após o batch: `del pipe` + `torch.cuda.empty_cache()` libera VRAM antes da exportação

### Modo `compose`
- Agente 4b: [[entities/composicao]] → `compor_batch`
- Sem torch, sem GPU, 100% Pillow
- Entrega "troca de ambiente" sem relighting — iluminação original da pessoa é mantida

## Parâmetros CLI relevantes

| Flag | Relevância |
|---|---|
| `--modo auto\|relight\|compose` | override manual |
| `--base <dir>` | altera o workspace (passa para `Paths`) |
| `--steps` | inference steps; só usado em modo `relight` |
| `--cfg-relight` | CFG para IC-Light fbc; só modo `relight` |
| `--cfg-bg` | CFG para geração de fundo SD 1.5 (Agente 3) |
| `--seed` | reprodutibilidade; tanto relight quanto bg |
| `--negative` | negative prompt; só modo `relight` |

## Gotchas

- `--modo relight` sem GPU não aborta — faz fallback silencioso para `compose`. O log JSON registra `"modo": "compose"` mas o usuário pode não notar se não ler o aviso no terminal.
- A decisão de modo acontece **antes** de qualquer import de `torch`/`diffusers`, então a detecção não trava em ambientes sem CUDA instalado.
- O fundo (Agente 3) é independente do modo — tanto `relight` quanto `compose` usam o mesmo `bg.png`.

## Relacionados

[[entities/pipeline]] · [[entities/pipeline-orchestrator-config]] · [[entities/relighting]] · [[entities/composicao]] · [[concepts/video-frame-pipeline]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
