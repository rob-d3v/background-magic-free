---
title: Decisão: compute split local vs Colab
type: decision
created: 2026-06-14
updated: 2026-06-14
sources: []
tags: [decision, infra, gpu, colab]
status: stable
migrated-from: wiki/decisions/local-vs-colab.md
original-date: 2026-06-13
---
# Decisão: compute split local vs Colab

## Contexto
O desenvolvimento acontece numa máquina local modesta, mas a pipeline tem etapas
que exigem GPU robusta. Restrições detalhadas em [[concepts/gpu-vram-local-vs-colab]].

- **Local:** Windows 11, GTX 1650 Ti **4GB VRAM**, **torch CPU-only**, Python 3.13.
- **Colab:** GPU **T4 ~15GB**, gratuito, Drive montado.

## Problema
SD 1.5 ([[entities/geracao_fundo]]) e IC-Light ([[entities/relighting]])
exigem GPU + VRAM além dos 4GB locais, e o torch local é CPU-only — qualquer
`.to("cuda")` falha. Mas iterar tudo no Colab é lento e sujeito a desconexões.

## Decisão
**Dividir o compute:** etapas leves rodam **local**; etapas pesadas (difusão)
rodam no **Colab T4**.

| Etapa | Onde | Verificado local? |
|---|---|---|
| extração (ffmpeg) | local + Colab | ✅ |
| rembg (ONNX, cai em CPU) | local + Colab | ✅ (CPU) |
| SD 1.5 fundo | **Colab** | n/a (GPU) |
| IC-Light relighting | **Colab** | n/a (GPU) |
| exportação (ffmpeg) | local + Colab | ✅ |

## Justificativa
- rembg usa ONNX Runtime, independente do torch → roda em CPU local sem mudar
  código. ffmpeg é CPU. Logo, dá para desenvolver/depurar os estágios leves
  localmente, rápido, sem queimar tempo de Colab.
- SD/IC-Light não têm caminho local viável com 4GB + torch CPU-only → ficam no Colab.
- Resume frame-a-frame ([[concepts/video-frame-pipeline]]) absorve as
  desconexões do Colab free.

## Consequências / trabalho
- **De-hardcodar paths — concluído.** [[entities/pipeline-orchestrator-config]] resolve workspace dinamicamente. Ver [[decisions/pipeline-orchestrator-paths-refactor]].
- **`--modo compose` — novo.** Permite executar a pipeline completa local sem GPU, trocando o fundo via alpha composite (sem IC-Light). Ver [[concepts/pipeline-orchestrator-mode-selection]].
- **Interface Gradio GPU-aware** (em construção): detecta GPU e oferece **preview
  de 1 frame** antes do lote, para validar prompt/fundo/luz barato. Funciona como
  ponte entre dev local (preview leve) e execução Colab (lote pesado).

## Status
**Estável** como estratégia. Paths de-hardcodados; modo compose para fluxo local completo. Registrado em [[log]] (2026-06-13, decision).

## Relacionados
[[concepts/gpu-vram-local-vs-colab]] · [[entities/pipeline]] ·
[[decisions/migrate-fc-to-fbc]] · [[index]]
