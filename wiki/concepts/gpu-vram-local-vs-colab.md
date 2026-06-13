---
tags: [concept, gpu, vram, colab, infra]
date: 2026-06-13
status: stable
---

# GPU/VRAM — restrições e split local vs Colab

A pipeline mistura etapas leves (CPU/IO) e etapas pesadas (difusão em GPU). O
ambiente de dev local não suporta as etapas pesadas, então o compute é
**dividido**. A decisão está em [[decisions/local-vs-colab]].

## Máquina de dev local
- **SO:** Windows 11.
- **GPU:** GTX 1650 Ti, **4GB VRAM** — insuficiente para SD 1.5 + IC-Light em fp16
  com folga.
- **torch:** build **CPU-only** (sem CUDA) — qualquer código que faça `.to("cuda")`
  ou `torch.Generator("cuda")` falha localmente.
- **Python:** 3.13.

## Colab (alvo de produção)
- **GPU T4, ~15GB VRAM** — confortável para SD 1.5 + IC-Light.
- Drive montado para persistir frames/outputs e permitir resume.
- Desconecta após ~30–90 min no plano free → o resume frame-a-frame
  ([[concepts/video-frame-pipeline]]) é o que torna isso tolerável.

## O que roda onde

| Etapa | GPU? | Local (4GB / torch CPU) | Colab T4 |
|---|---|---|---|
| [[components/extracao]] (ffmpeg) | não | ✅ verificado | ✅ |
| [[components/remocao]] (rembg/ONNX) | opcional | ✅ verificado (CPU, mais lento) | ✅ (GPU) |
| [[components/geracao_fundo]] (SD 1.5) | **sim** | ❌ | ✅ |
| [[components/relighting]] (IC-Light) | **sim** | ❌ | ✅ |
| [[components/exportacao]] (ffmpeg) | não | ✅ verificado | ✅ |

> Verificado **localmente nesta sessão**: extração ffmpeg, rembg em CPU e
> exportação ffmpeg funcionam. SD e IC-Light foram confirmados como
> GPU-obrigatórios.

## Por que rembg roda local mas IC-Light não
rembg usa **ONNX Runtime**, independente do torch; cai em CPU automaticamente. SD
1.5 e IC-Light usam **torch + CUDA** e fp16 — exigem GPU e mais VRAM que os 4GB
locais. Ver [[concepts/rembg-background-removal]] e [[concepts/ic-light]].

## Interface Gradio (em construção)
Uma UI Gradio **GPU-aware** está sendo adicionada: detecta se há GPU disponível e
oferece um **preview de 1 frame** antes de rodar o lote completo — para validar
prompt/fundo/iluminação sem pagar o custo de todos os frames.

## Gotchas
- Paths em [[components/pipeline]] são hardcoded para `/content/drive/...` (Colab);
  rodar local exige parametrizá-los (tarefa aberta).
- Após o relighting o orquestrador faz `del pipe` + `torch.cuda.empty_cache()`
  para liberar VRAM antes da exportação.

## Relacionados
[[decisions/local-vs-colab]] · [[concepts/video-frame-pipeline]] ·
[[components/relighting]] · [[components/geracao_fundo]] · [[index]]
