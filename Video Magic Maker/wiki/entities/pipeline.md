---
title: pipeline — Orquestrador
type: entity
created: 2026-06-14
updated: 2026-06-22
sources: ["pipeline.py"]
tags: [component, orchestrator, pipeline]
status: stable
migrated-from: wiki/components/pipeline.md
original-date: 2026-06-13
---
# pipeline — Orquestrador

`pipeline.py`. Script CLI que encadeia os 5 agentes em ordem e monta o
`pipeline_log.json` final. Roda local e no Colab; paths resolvidos por [[entities/pipeline-orchestrator-config]].

## O que faz
Executa, na ordem, [[entities/extracao]] → [[entities/remocao]] →
[[entities/geracao_fundo]] (ou fundo próprio) → [[entities/relighting]] ou [[entities/composicao]] →
[[entities/exportacao]]. Imprime progresso `[n/5]` por etapa e, ao final,
escreve o log JSON com metadados e contagem de erros.

## Inputs / Outputs
- **Inputs (argparse):**
  - `--video` (obrigatório) — vídeo de entrada.
  - `--prompt` (default `"cinematic lighting"`) — usado para relighting e, se não houver `--background`, também para gerar o fundo.
  - `--output` (opcional) — caminho do `.mp4` final; default `{paths.output_dir}/video_final.mp4`.
  - `--background` (opcional) — imagem de fundo própria; pula a geração por IA.
  - `--base` (opcional) — workspace override; ver [[entities/pipeline-orchestrator-config]].
  - `--modo` (`auto`|`relight`|`compose`, default `auto`) — seleção de agente 4; ver [[concepts/pipeline-orchestrator-mode-selection]].
- **Outputs:** `output/video_final.mp4`, `background/bg.png` e
  `pipeline_log.json` (lista `etapas`, `erros_total`, `tempo_total_s`, `device`, `modo`).

## Parâmetros-chave
| Flag | Default | Uso |
|---|---|---|
| `--steps` | 20 | inference steps SD/IC-Light |
| `--seed` | 12345 | reprodutibilidade |
| `--crf` | 18 | qualidade H.264 final |
| `--cfg-bg` | 7.0 | CFG da geração de fundo |
| `--cfg-relight` | 7.0 | CFG do IC-Light fbc |
| `--negative` | `""` | negative prompt para relighting |

## Fluxo de fundo
- `usar_fundo_proprio = args.background is not None`.
- **Fundo próprio:** abre a imagem, redimensiona para `width×height` do vídeo
  (`Image.LANCZOS`) e salva em `paths.bg_output` (`background/bg.png`).
- **Fundo por IA:** sobe ComfyUI, chama `gerar_fundo`, e em `finally` chama
  `comfy_proc.terminate()` para liberar a porta/VRAM.

## Seleção de modo (Agente 4)
Ver [[concepts/pipeline-orchestrator-mode-selection]] para o fluxo completo.
- `relight`: usa [[entities/relighting]] (IC-Light fbc, GPU, requer ≥5 GB VRAM).
- `compose`: usa [[entities/composicao]] (CPU, sem relighting).
- `auto` (default): decide via `dev["pode_relight"]` de `detectar_device()`.

## Gotchas
- Paths não são mais hardcoded — resolvidos por [[entities/pipeline-orchestrator-config]]. A variável de ambiente `LUMINA_BASE` ou `--base` substitui o workspace default.
- Após o relighting faz `del pipe` + `torch.cuda.empty_cache()` para liberar VRAM antes da exportação.
- Os `erros_total` somam apenas erros de remoção e relighting/composição (agentes que retornam `erros`); extração/exportação abortam por exceção via `check=True`.
- `--modo relight` sem GPU suficiente não aborta — faz fallback para `compose` com aviso no terminal; o log registra o modo final.
- **`app.py` (UI Gradio) "demora a abrir" = startup lento, não bug.** O import de `torch` + `gradio` + `diffusers` leva ~12.5s antes de a UI subir. Normal.

## Relacionados
[[entities/extracao]] · [[entities/remocao]] · [[entities/geracao_fundo]] ·
[[entities/relighting]] · [[entities/composicao]] · [[entities/exportacao]] ·
[[entities/pipeline-orchestrator-config]] · [[concepts/pipeline-orchestrator-mode-selection]] ·
[[concepts/pipeline-orchestrator-call-sequence]] · [[concepts/pipeline-orchestrator-log-structure]] ·
[[concepts/pipeline-orchestrator-background-branching]] · [[concepts/video-frame-pipeline]] ·
[[decisions/pipeline-orchestrator-lazy-imports]] · [[index]]
