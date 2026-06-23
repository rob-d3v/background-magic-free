---
title: "agent-relighting-source — Sumário de agentes/relighting.py"
type: source
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [source, relighting, ic-light, fbc]
---
# agent-relighting-source — Sumário de agentes/relighting.py

Arquivo-fonte: `agentes/relighting.py` (307 linhas, sem dependências internas ao
projeto além de imports stdlib/pip).

## Propósito declarado (docstring do módulo)

> "Coloca a pessoa recortada DENTRO do fundo escolhido e reilumina para casar com
> ele. Usa iclight_sd15_fbc: UNet de 12 canais (4 noisy + 4 fg + 4 bg). A saída
> já vem com a pessoa composta no ambiente — não precisa de composição extra."

## Estrutura do arquivo

| Seção | Linhas | Conteúdo |
|---|---|---|
| Cabeçalho e imports | 1–30 | docstring, imports |
| Constantes | 34–37 | `FBC_REPO`, `FBC_FILE`, `BASE_SD15` |
| `_baixar_pesos_fbc` | 39–43 | helper de resolução do arquivo de pesos |
| `carregar_iclight` | 46–115 | carregamento completo do pipeline |
| Pré-processamento | 118–149 | `_resize_center_crop`, `_mult64`, `_fg_sobre_cinza`, `_encode` |
| `relight_frame` | 154–226 | inferência de um frame |
| `aplicar_relighting` | 231–306 | batch com resume |

## Nota de correção no cabeçalho

O módulo documenta explicitamente os dois bugs corrigidos em relação à versão fc
anterior:
1. O fundo agora é usado (condição bg).
2. Pesos IC-Light são OFFSET/DELTA somados (não carregados direto).

Isso confirma que as correções listadas em [[decisions/agent-relighting-fbc-completed]]
estão intencionalmente implementadas.

## Relacionados
[[entities/agent-relighting-module]] · [[concepts/agent-relighting-load-flow]] ·
[[concepts/agent-relighting-denoising-loop]] · [[concepts/agent-relighting-channel-layout]] ·
[[concepts/agent-relighting-vram]] · [[index]]
