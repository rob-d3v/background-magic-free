---
tags: [component, orchestrator, pipeline]
date: 2026-06-13
status: stable
source: pipeline.py
---

# pipeline — Orquestrador

`pipeline.py`. Script CLI que encadeia os 5 agentes em ordem e monta o
`pipeline_log.json` final. É o ponto de entrada da pipeline no Colab.

## O que faz
Executa, na ordem, [[components/extracao]] → [[components/remocao]] →
[[components/geracao_fundo]] (ou fundo próprio) → [[components/relighting]] →
[[components/exportacao]]. Imprime progresso `[n/5]` por etapa e, ao final,
escreve o log JSON com metadados e contagem de erros.

## Inputs / Outputs
- **Inputs (argparse):**
  - `--video` (obrigatório) — vídeo de entrada.
  - `--prompt` (obrigatório) — usado para relighting e, se não houver
    `--background`, também para gerar o fundo.
  - `--output` (obrigatório) — caminho do `.mp4` final.
  - `--background` (opcional) — imagem de fundo própria; pula a geração por IA.
- **Outputs:** `output/video_final.mp4`, `background/bg.png` e
  `pipeline_log.json` (lista `etapas`, `erros_total`, `tempo_total_s`).

## Parâmetros-chave
| Flag | Default | Uso |
|---|---|---|
| `--steps` | 25 | inference steps SD/IC-Light |
| `--seed` | 42 | reprodutibilidade |
| `--crf` | 18 | qualidade H.264 final |
| `--cfg-bg` | 7.0 | CFG da geração de fundo |
| `--cfg-relight` | 2.0 | CFG do IC-Light (prefere baixo) |

## Fluxo de fundo
- `usar_fundo_proprio = args.background is not None`.
- **Fundo próprio:** abre a imagem, redimensiona para `width×height` do vídeo
  (`Image.LANCZOS`) e salva em `BG_OUTPUT` (`background/bg.png`).
- **Fundo por IA:** sobe ComfyUI, chama `gerar_fundo`, e em `finally` chama
  `comfy_proc.terminate()` para liberar a porta/VRAM.

## Gotchas
- **Paths hardcoded para Colab.** `BASE_DIR = "/content/drive/MyDrive/iclight_pipeline"`
  e derivados. Para rodar local isso precisa ser parametrizado (tarefa aberta —
  ver [[concepts/gpu-vram-local-vs-colab]]).
- Após o relighting faz `del pipe` + `torch.cuda.empty_cache()` para liberar VRAM
  antes da exportação.
- Os `erros_total` somam apenas erros de remoção e relighting (agentes que
  retornam `erros`); extração/exportação abortam por exceção via `check=True`.
- **`app.py` (UI Gradio) "demora a abrir" = startup lento, não bug.** Medido
  nesta sessão: o import de `torch` + `gradio` + `diffusers` no topo do `app.py`
  leva **~12.5s** antes de a UI subir. Não há travamento — o app sobe e **binda a
  porta normalmente** depois desse import. A demora é só o custo de import.

## Relacionados
[[components/extracao]] · [[components/remocao]] · [[components/geracao_fundo]] ·
[[components/relighting]] · [[components/exportacao]] ·
[[concepts/video-frame-pipeline]] · [[index]]
