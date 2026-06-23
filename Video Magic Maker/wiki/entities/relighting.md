---
title: relighting — Agente 4 (Relighting com IC-Light fbc)
type: entity
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [component, agent, ic-light, fbc, relighting]
status: stable
migrated-from: wiki/components/relighting.md
original-date: 2026-06-13
---
# relighting — Agente 4 (Relighting com IC-Light fbc)

`agentes/relighting.py` → `carregar_iclight(...)` + `relight_frame(...)` + `aplicar_relighting(...)`. Reilumina a pessoa para combinar com o fundo. Etapa mais cara da pipeline (~1.5s/frame na T4). Requer GPU CUDA.

> **Migração fbc concluída.** Esta página descreve a implementação atual (fbc, 12 canais, offset-merge correto). A versão antiga (fc, bugs documentados) está em [[decisions/migrate-fc-to-fbc]].

## O que faz

1. `carregar_iclight`: expande `conv_in` para **12 canais** (4 noisy + 4 fg + 4 bg), aplica **offset-merge** correto dos pesos IC-Light sobre o SD 1.5 base, configura scheduler `DPMSolverMultistepScheduler` (sde-dpmsolver++ / Karras).
2. `relight_frame`: processa **um frame** — compõe RGBA sobre cinza neutro, encode fg e bg no latent (VAE deterministico), loop de denoising com 12 canais (`cat([noisy, fg_latent, bg_latent])`), CFG manual. Retorna PIL RGB da pessoa já composta no fundo.
3. `aplicar_relighting`: batch com **resume automático**, dimensões fixas derivadas do primeiro frame (múltiplo de 64), callback de progresso opcional para UIs.

Internos detalhados em [[concepts/pipeline-orchestrator-iclight-fbc-internals]].

## Inputs / Outputs
- **Inputs:** `frames_nobg_dir` (RGBA de [[entities/remocao]]),
  `background_path` (`bg.png` de [[entities/geracao_fundo]] ou fundo próprio),
  `prompt`, `negative_prompt`, `steps`, `cfg`, `seed`, `log_path`.
- **Output:** PNGs RGB relitados em `relit/`; `dict` `{processados, erros, tempo_s, largura, altura}`;
  erros em `pipeline_log.json` (chave `relighting_erros`).

## Parâmetros-chave
| Param | Default | Nota |
|---|---|---|
| `steps` | 20 | inference steps |
| `cfg` | 7.0 | CFG scale (--cfg-relight) |
| `seed` | 12345 | gerador CPU (`torch.Generator("cpu")`) |
| `low_vram` | `vram_gb < 8.0` | ativa offload sequencial para GPUs 5–7 GB |

## Pesos e modelos
```
FBC_REPO = "lllyasviel/ic-light"
FBC_FILE = "iclight_sd15_fbc.safetensors"
BASE_SD15 = "stablediffusionapi/realistic-vision-v51"
```
Download automático via HuggingFace Hub se não houver cópia local.

## Gotchas
- Requer **GPU CUDA** com ≥5 GB VRAM. O orquestrador não chama este agente quando `pode_relight=False`; ver [[concepts/pipeline-orchestrator-mode-selection]].
- O `generator` usa `device="cpu"` mesmo em GPU para reprodutibilidade determinística entre execuções.
- `relight_frame` é exposto diretamente para uso no preview da UI Gradio (processa 1 frame, não o batch).
- **`gerar_fundo_diffusers`** em [[entities/geracao_fundo]] também usa SD 1.5; rodar os dois simultaneamente requer VRAM suficiente para dois pipelines.

## Relacionados
[[entities/pipeline]] · [[entities/remocao]] · [[entities/geracao_fundo]] · [[entities/composicao]] ·
[[entities/agent-relighting-module]] · [[concepts/ic-light]] ·
[[concepts/agent-relighting-load-flow]] · [[concepts/agent-relighting-denoising-loop]] ·
[[concepts/agent-relighting-channel-layout]] · [[concepts/agent-relighting-vram]] ·
[[concepts/pipeline-orchestrator-iclight-fbc-internals]] ·
[[decisions/migrate-fc-to-fbc]] · [[decisions/agent-relighting-fbc-completed]] · [[index]]
