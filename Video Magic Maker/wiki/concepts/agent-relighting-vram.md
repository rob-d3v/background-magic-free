---
title: "agent-relighting-vram — Modos de VRAM e GPU em carregar_iclight"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [concept, vram, gpu, low-vram, colab, ic-light, memory]
---
# agent-relighting-vram — Modos de VRAM e GPU em carregar_iclight

Documenta os três modos de execução do pipeline IC-Light fbc em relação a
hardware e gerenciamento de memória.

## Modos disponíveis

| Modo | Condição | Ativação |
|---|---|---|
| **CUDA normal** | GPU com VRAM suficiente (~8–12 GB) | `device="cuda"`, `low_vram=False` |
| **CUDA low-vram** | GPU pequena (~4–6 GB) | `device="cuda"`, `low_vram=True` |
| **CPU** | sem GPU | `device="cpu"` |

## Modo CUDA normal

```python
pipe = pipe.to("cuda")
```

Toda a pipeline (UNet, VAE, text_encoder) fica em VRAM. Mais rápido, mas exige
memória contínua suficiente para o modelo float16 inteiro. SD 1.5 fbc completo
ocupa aproximadamente:
- UNet (12ch): ~1.7 GB float16
- VAE: ~320 MB float16
- Text encoder: ~235 MB float16
- Total: ~2.3 GB base + overhead de ativações (~4–6 GB em uso)

## Modo low-vram

```python
pipe.enable_sequential_cpu_offload()
pipe.enable_attention_slicing()
pipe.enable_vae_slicing()
```

Três otimizações combinadas:
1. **sequential_cpu_offload**: move cada sub-módulo para GPU apenas quando está
   sendo executado, devolvendo para CPU logo após. Reduz pico de VRAM para ~2–3 GB,
   mas adiciona latência de transferência PCI-e a cada passo.
2. **attention_slicing**: processa a atenção na UNet em fatias menores, reduzindo
   o pico de memória das matrizes de atenção.
3. **vae_slicing**: decodifica o VAE em fatias — relevante para batches, mas
   mantido como precaução.

> O comentário no código cita "GPUs pequenas (ex: 4GB)". Com o fbc (12ch) e
> float16, 4 GB pode ser marginal mesmo com esses offloads. Testar em T4 (15 GB
> Colab) vs P100 (16 GB) vs GPUs locais 8 GB. (Inferido — não há benchmark no código.)

## Modo CPU

```python
pipe = pipe.to("cpu")
```

Fallback para desenvolvimento/debug. O dtype muda para `float32` (detectado por
`device == "cuda"` na construção). Extremamente lento para uso em produção.

## Interação com o gerador de ruído

```python
generator = torch.Generator(device="cpu").manual_seed(seed)
```

O gerador usa **sempre** `"cpu"` — mesmo em modo CUDA — para garantir
reproducibilidade entre dispositivos. Geradores CUDA podem produzir valores
diferentes conforme versão de driver/CUDA.

## Relação com Colab

O agente é descrito como etapa exclusiva do Colab (ver [[concepts/gpu-vram-local-vs-colab]]).
O `low_vram` foi adicionado como suporte a GPUs menores (Colab gratuito T4 = 15 GB
normalmente suficiente sem low_vram; RunPod/Lightning com 8 GB pode precisar).

## Configurações de scheduler não dependem de device

O `DPMSolverMultistepScheduler` opera em CPU por default e move tensores para o
device na chamada `set_timesteps(steps, device=fg_latent.device)`. Isso permite
que o scheduler funcione independentemente do modo de offload.

## Relacionados
[[concepts/agent-relighting-load-flow]] · [[concepts/agent-relighting-denoising-loop]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[entities/agent-relighting-module]] · [[index]]
