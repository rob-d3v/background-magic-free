---
tags: [component, agent, ic-light, relighting]
date: 2026-06-13
status: in-migration
source: agentes/relighting.py
---

# relighting — Agente 4 (Relighting com IC-Light)

`agentes/relighting.py` → `carregar_iclight(...)` + `aplicar_relighting(...)`.
Reilumina a pessoa para combinar com o ambiente. Etapa mais cara da pipeline
(~1.5s/frame na T4).

> **status: in-migration.** O código atual usa **IC-Light fc** e tem dois bugs
> conhecidos (ver Gotchas). Migração planejada para **fbc** em
> [[decisions/migrate-fc-to-fbc]]. Conceitos em [[concepts/ic-light]].

## O que faz (implementação atual — fc)
1. `carregar_iclight`: carrega SD 1.5, troca `unet.conv_in` por um `Conv2d` de
   **8 canais** de entrada (zera os pesos novos, copia os 4 originais para
   `[:, :4]`), e carrega os pesos IC-Light.
2. `aplicar_relighting`: por frame — compõe o RGBA sobre cinza neutro
   `(127,127,127)`, redimensiona para múltiplo de 8, codifica o foreground no
   latent (VAE) e roda o loop de denoising concatenando o `fg_latent` como
   condição (`torch.cat([latent_input, fg_latent], dim=1)`), com CFG manual.
   Suporta resume (`if os.path.exists(output_path): continue`).

## Inputs / Outputs
- **Inputs:** `frames_nobg_dir` (RGBA de [[components/remocao]]),
  `background_path` (`bg.png`), `prompt`, `steps`, `cfg`, `seed`, `log_path`.
- **Output:** PNGs relitados em `relit/`; `dict` `{processados, erros, tempo_s}`;
  erros em `pipeline_log.json` (chave `relighting_erros`).

## Parâmetros-chave
| Param | Default | Nota |
|---|---|---|
| `steps` | 25 | inference steps |
| `cfg` | 2.0 | IC-Light prefere CFG baixo (1.5–3.0) |
| `seed` | 42 | gerador CUDA |

## Gotchas (BUGS VERIFICADOS — corrigir na migração)
1. **`background_path` é aberto mas NUNCA usado.** `bg = Image.open(...)` é lido e
   descartado; o denoising só recebe o foreground. O fc não tem entrada de fundo
   → a pessoa não é composta no ambiente gerado. Isso é o motivo central da
   migração para **fbc** (12 canais, com 4 canais de bg). Ver
   [[decisions/migrate-fc-to-fbc]].
2. **Carregamento de pesos errado:** `pipe.unet.load_state_dict(ic_weights,
   strict=False)`. IC-Light é um **offset/delta** que deve ser **somado** à UNet
   base do SD 1.5: `sd_merged = {k: origin[k] + offset[k]}` com `strict=True`.
   Carregar como state_dict direto sobrescreve com deltas → pesos inválidos.
   Detalhe em [[concepts/ic-light]].

Outros: requer **GPU** (`torch.Generator("cuda")`, `.to("cuda")`) — etapa
exclusiva do Colab; ver [[concepts/gpu-vram-local-vs-colab]]. Embeds de prompt e
uncond são calculados uma vez fora do loop (otimização correta).

## Relacionados
[[components/pipeline]] · [[components/remocao]] · [[components/geracao_fundo]] ·
[[concepts/ic-light]] · [[decisions/migrate-fc-to-fbc]] · [[index]]
