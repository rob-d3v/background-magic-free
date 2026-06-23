---
title: "agent-relighting-fbc-completed — Migração fc→fbc concluída"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [decision, ic-light, fbc, migration, completed]
---
# agent-relighting-fbc-completed — Migração fc→fbc concluída (status: done)

A migração de IC-Light fc para fbc, planejada em [[decisions/migrate-fc-to-fbc]],
foi **concluída** na versão atual de `agentes/relighting.py`.

## O que mudou (fc → fbc implementado)

| Aspecto | fc (versão anterior, com bugs) | fbc (implementação atual) |
|---|---|---|
| Modelo | `iclight_sd15_fc.safetensors` | `iclight_sd15_fbc.safetensors` |
| `conv_in` canais | 8 (4 noisy + 4 fg) | **12** (4 noisy + 4 fg + 4 bg) |
| Background no loop | aberto e descartado | codificado no VAE e concatenado |
| Concatenação | `cat([scaled, fg_latent])` | `cat([scaled, fg_latent, bg_latent])` |
| Offset-merge | `load_state_dict(offset, strict=False)` (BUG) | `origin[k] + offset[k]`, `strict=True` (CORRETO) |
| Scheduler | não explicitado | DPM++ 2M SDE Karras explicitamente configurado |
| Múltiplo de dimensão | 8 | 64 (mais conservador) |
| CFG default | 2.0 | 7.0 |
| Seed generator | `torch.Generator("cuda")` | `torch.Generator("cpu")` (reproduzível) |

## Bugs corrigidos confirmados

1. **Background descartado** — `bg_latent` agora é codificado com `_encode(pipe, bg)`
   e concatenado em cada passo de denoising. O fundo gera iluminação coerente na
   composição.
2. **Offset-merge errado** — substituído pelo loop `origin[k] + offset[k]` com
   `strict=True`. Pesos da UNet são agora a soma correta dos pesos base SD 1.5 +
   deltas IC-Light fbc.

## Trabalho pendente identificado (inferido)

- O CFG default subiu de 2.0 para 7.0. O demo oficial lllyasviel/IC-Light usa
  valores baixos (1.5–5.0). CFG alto pode introduzir over-saturation em relighting.
  Recomenda-se teste comparativo e possível redução para 3.0–5.0.
- Não há testes automatizados para `relight_frame` / `aplicar_relighting`.
- O `_mult64` usa `max(64, ...)` — imagens menores que 64px são promovidas para
  64px, o que pode causar upscaling inesperado em casos extremos.

## Relacionados
[[decisions/migrate-fc-to-fbc]] · [[entities/agent-relighting-module]] ·
[[concepts/agent-relighting-load-flow]] · [[concepts/agent-relighting-channel-layout]] ·
[[concepts/ic-light]] · [[index]]
