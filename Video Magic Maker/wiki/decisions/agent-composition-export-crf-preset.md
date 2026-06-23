---
title: "Decisão: CRF 18 e preset slow para encoding H.264 de saída"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/exportacao.py", "pipeline.py"]
tags: [decision, exportacao, h264, crf, quality, ffmpeg]
status: stable
inferred: true
---
# Decisão: CRF 18 e preset slow para encoding H.264 de saída

## Contexto

O [[entities/exportacao]] encoda os frames compostos/relitados com `libx264`.
Dois parâmetros dominam o trade-off qualidade/velocidade/tamanho de arquivo:
`crf` (qualidade) e `preset` (velocidade de encoding).

## Decisão

- **CRF padrão: 18** (configurável via `--crf` no CLI).
- **Preset: slow** (hardcoded, não exposto como parâmetro CLI).

## Justificativa (inferred)

### CRF 18

O docstring do `pipeline.py` documenta: `crf: qualidade H.264 (0=perfeito,
51=péssimo, 18=alta, 23=média)`. CRF 18 é próximo de lossless perceptual
("visually lossless" segundo documentação do x264). Para vídeos de demonstração
de produto (onde a qualidade visual importa) é escolha apropriada.

O CRF é **configurável** pelo usuário via `--crf`, permitindo trocar por 23
(menor) em casos onde tamanho de arquivo importa mais.

### Preset slow

`-preset slow` melhora a eficiência de compressão (menor arquivo para mesmo CRF)
em troca de mais tempo de CPU no encoding. Como o export é a última etapa da
pipeline e raramente é o gargalo (IC-Light ~1.5s/frame vs. export ~2ms/frame
estimado), o custo extra de CPU no preset slow é desprezível em termos relativos.

O preset **não é exposto** como parâmetro CLI — simplifica a interface e evita
configuração desnecessária para o caso de uso principal.

## Implicação: `-pix_fmt yuv420p`

Também hardcoded junto com CRF/preset. Garante compatibilidade com players que
não suportam yuv444p. Detalhe técnico em
[[concepts/agent-composition-export-ffmpeg-reassembly]].

## Relacionados

[[entities/exportacao]] · [[entities/pipeline]] ·
[[concepts/agent-composition-export-ffmpeg-reassembly]] · [[index]]
