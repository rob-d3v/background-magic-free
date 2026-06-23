---
title: Decisão: migrar IC-Light fc → fbc
type: decision
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [decision, ic-light, relighting, migration]
status: completed
migrated-from: wiki/decisions/migrate-fc-to-fbc.md
original-date: 2026-06-13
---
# Decisão: migrar IC-Light fc → fbc

## Contexto
O [[entities/relighting]] usa **IC-Light fc** (foreground-conditioned, UNet de 8
canais). O objetivo do produto é compor a pessoa **dentro** do fundo gerado, com
iluminação coerente. O fc, por design, só condiciona no foreground — não recebe o
fundo como entrada. Conceitos em [[concepts/ic-light]].

## Problema (bugs verificados no fc atual)
1. **Fundo descartado.** `aplicar_relighting` abre `background_path` e nunca o
   usa. O modelo fc não tem canais de bg, então mesmo se quiséssemos não daria
   para alimentar o fundo. Resultado: a pessoa é relitada "no vácuo", sem o
   ambiente — falha o objetivo central.
2. **Pesos carregados errado.** `load_state_dict(strict=False)` em vez do
   offset-merge (`{k: origin[k] + offset[k]}`, `strict=True`). Independente do
   modelo, isso já produz pesos inválidos. Ver [[concepts/ic-light]].

## Decisão
Migrar para **IC-Light fbc** (foreground + background conditioned, UNet de **12
canais** = 4 noisy + 4 fg + 4 bg, peso `iclight_sd15_fbc.safetensors`).

## Justificativa
- O fbc recebe **fg e bg** como condição e produz a pessoa **já composta no
  fundo** — elimina a etapa de composição manual que hoje está faltando.
- Usa o `background/bg.png` que [[entities/geracao_fundo]] já gera (ou o fundo
  próprio do usuário), encerrando o bug do bg descartado.
- Mantém o resto da pipeline igual (mesma SD 1.5 base, mesmo VAE, mesmo fluxo de
  diretórios em [[concepts/video-frame-pipeline]]).

## Implicações / trabalho
- `carregar_iclight`: expandir `conv_in` para **12 canais** (4 originais + 8
  zerados) e aplicar o **offset-merge** correto com `strict=True`.
- `aplicar_relighting`: codificar **bg** no latent e concatenar
  `cat([noisy, fg_latent, bg_latent], dim=1)`.
- Baixar `iclight_sd15_fbc.safetensors` (ajustar célula 4 do notebook).
- O fix do offset-merge se aplica a fc e fbc, então é pré-requisito comum.
- [[entities/relighting]] permanece `status: in-migration` até o fbc entrar.

## Status
**Concluído (2026-06-22).** `agentes/relighting.py` usa fbc com 12 canais e offset-merge correto (`strict=True`). Internos documentados em [[concepts/pipeline-orchestrator-iclight-fbc-internals]]. Registrado em [[log]] (2026-06-13, migration).

## Relacionados
[[entities/relighting]] · [[concepts/ic-light]] · [[entities/geracao_fundo]] ·
[[decisions/agent-relighting-fbc-completed]] · [[decisions/local-vs-colab]] · [[index]]
