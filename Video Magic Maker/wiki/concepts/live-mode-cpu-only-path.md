---
title: live-mode-cpu-only-path — execução CPU-only via XNNPACK (sem GPU)
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/matting_live.py", "live.py"]
tags: [concept, live, cpu, xnnpack, mediapipe, performance, gpu]
---
# live-mode-cpu-only-path — execução CPU-only via XNNPACK (sem GPU)

O modo ao vivo ([[entities/live-mode]]) roda o matting inteiramente em CPU. Esta página documenta por que isso é o caso, como funciona na prática e quais são as implicações de performance.

## Por que CPU-only

O motor padrão do live ([[entities/live-mode-livematter-class]], `LiveMatter`) usa o **MediaPipe Tasks `ImageSegmenter`**, que roda o modelo `selfie_segmenter.tflite` via **XNNPACK** — o backend de inferência otimizado para CPU do MediaPipe. Não há caminho de GPU no MediaPipe Tasks para este modelo neste ambiente.

O motor alternativo `RVMMatter` (`agentes/matting_rvm.py`) usa **PyTorch**. O `torch` instalado é `2.11.0+cpu` — a variante CPU-only. A GTX 1650 Ti presente na máquina local **não é utilizada** pelo matting em tempo real.

A razão arquitetural: o IC-Light (reiluminação) usa a GPU no modo offline, e os dois modos partilham a máquina. O live deliberadamente fica no CPU para não competir com o VRAM do modo studio. Ver [[concepts/gpu-vram-local-vs-colab]].

## XNNPACK: o que é

XNNPACK é uma biblioteca de kernels de álgebra linear otimizados para CPU (ARM NEON, x86 AVX/AVX2/AVX-512, WebAssembly SIMD). O MediaPipe usa XNNPACK automaticamente como delegate de aceleração quando disponível — nenhuma configuração explícita é necessária no código. O modelo float16 do Selfie Segmenter é convertido para float32 em CPU (XNNPACK não suporta float16 em todas as CPUs x86), com custo mínimo dado o tamanho pequeno do modelo (~250KB, resolução interna ~256²).

## Performance medida

Números medidos em CPU (máquina local) para o motor **MediaPipe**:

| Resolução | refine ON (guided filter) | `--fast` (refine OFF) |
|---|---|---|
| 640×360 | ~33fps | ~42fps |
| **960×540 (default)** | **~15fps** | **~21fps** |
| 1280×720 | ~9fps | ~13fps |

O **default 960×540** foi escolhido como equilíbrio entre fluidez e nitidez para uso em câmera virtual no Google Meet / Zoom. Ver [[decisions/live-mode-engine-selection]].

Para o motor **RVM** (torch CPU): ~9.6fps @540p. Mais lento porque torch+RVM é uma rede recorrente maior (~15MB) versus o Selfie Segmenter (~250KB).

## Implicação: sem CUDA, sem half-precision

Como `torch` é CPU-only (`2.11.0+cpu`), `RVMMatter` não pode chamar `.cuda()` nem usar autocast float16. O modelo torch roda em float32 em CPU. Isso é aceitável para o caso de uso (câmera virtual), mas significa que qualquer migração para GPU exigiria reinstalar `torch` com suporte CUDA.

## Guided filter em meia resolução

O passo mais caro do pipeline CPU é o guided filter de refino de borda. Full-res a 720p custa ~80ms/frame. A implementação roda o filtro em **escala=0.5** (metade das dimensões), reduzindo o custo para ~20ms — viabilizando o tempo real. A máscara de confiança já é espacialmente suave, então o downscaling introduz pouco erro perceptível. Ver [[concepts/live-mode-edge-refinement]].

## Resumo

| Componente | Execução | Aceleração |
|---|---|---|
| `selfie_segmenter.tflite` (MediaPipe) | CPU | XNNPACK automático |
| `torch` / RVM | CPU | nenhuma (torch+cpu) |
| OpenCV (`erode`, `GaussianBlur`, `connectedComponents`) | CPU | OpenCV interno (SSE/AVX) |
| `ximgproc.guidedFilter` | CPU | OpenCV contrib interno |
| `pyvirtualcam` | CPU | DirectShow / OBS driver |

## Relacionados

[[entities/live-mode]] · [[entities/live-mode-livematter-class]] · [[concepts/realtime-matting]] · [[concepts/live-mode-edge-refinement]] · [[decisions/live-mode-engine-selection]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
