---
tags: [decision, infra, gpu, colab]
date: 2026-06-13
status: stable
---

# Decisão: compute split local vs Colab

## Contexto
O desenvolvimento acontece numa máquina local modesta, mas a pipeline tem etapas
que exigem GPU robusta. Restrições detalhadas em [[concepts/gpu-vram-local-vs-colab]].

- **Local:** Windows 11, GTX 1650 Ti **4GB VRAM**, **torch CPU-only**, Python 3.13.
- **Colab:** GPU **T4 ~15GB**, gratuito, Drive montado.

## Problema
SD 1.5 ([[components/geracao_fundo]]) e IC-Light ([[components/relighting]])
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
- **De-hardcodar paths.** [[components/pipeline]] fixa `/content/drive/...`; rodar
  local exige parametrizar `BASE_DIR` (tarefa aberta).
- **Interface Gradio GPU-aware** (em construção): detecta GPU e oferece **preview
  de 1 frame** antes do lote, para validar prompt/fundo/luz barato. Funciona como
  ponte entre dev local (preview leve) e execução Colab (lote pesado).

## Status
**Estável** como estratégia. Registrado em [[log]] (2026-06-13, decision).

## Relacionados
[[concepts/gpu-vram-local-vs-colab]] · [[components/pipeline]] ·
[[decisions/migrate-fc-to-fbc]] · [[index]]
