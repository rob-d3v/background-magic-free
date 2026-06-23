---
title: "agent-relighting-denoising-loop — Loop de denoising em relight_frame"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [concept, ic-light, fbc, denoising, cfg, diffusion, inference]
---
# agent-relighting-denoising-loop — Loop de denoising em relight_frame

Descreve o fluxo completo de inferência dentro de `relight_frame()`, desde o
pré-processamento de imagens até o pixel final de saída.

## Fluxo completo

```
fg_rgba (RGBA PIL)        bg_rgb (RGB PIL)
      ↓                         ↓
_fg_sobre_cinza()         resize_center_crop()
_resize_center_crop()           ↓
      ↓                    _encode(pipe, bg)
_encode(pipe, fg)               ↓
      ↓                   bg_latent (1,4,lh,lw)
fg_latent (1,4,lh,lw)          ↓
              ↓           ↓
         torch.randn → latents (1,4,lh,lw)  ← semente determinística
                    × init_noise_sigma
                         ↓
              ┌── for t in scheduler.timesteps ──┐
              │  scaled = scale_model_input(latents, t)                │
              │  model_in = cat([scaled, fg_latent, bg_latent], dim=1) │  12ch
              │  noise_cond   = unet(model_in, t, cond_embeds).sample  │
              │  noise_uncond = unet(model_in, t, uncond_embeds).sample│
              │  noise_pred = uncond + cfg × (cond − uncond)           │  CFG
              │  latents = scheduler.step(noise_pred, t, latents)      │
              └───────────────────────────────────────────────────────┘
                         ↓
              vae.decode(latents / scaling_factor).sample
                         ↓
              (decoded/2 + 0.5).clamp(0,1) → uint8 → PIL.Image RGB
```

## Pré-processamento

**Foreground:**
1. `_fg_sobre_cinza(fg_rgba)` — compõe o recorte RGBA sobre `(127,127,127)`.
   Remove transparência preservando as bordas suavizadas da pessoa; o cinza médio
   não enviesa estimativa de iluminação.
2. `_resize_center_crop(fg, largura, altura)` — cobre as dimensões alvo e corta
   o centro.

**Background:**
1. `.convert("RGB")` — garante 3 canais (descarta alfa se houver).
2. `_resize_center_crop(bg, largura, altura)` — mesma resolução do foreground.

Ambos ficam com exatamente `largura × altura` píxeis, ambos são múltiplos de 64
(ver `_mult64` em [[concepts/agent-relighting-channel-layout]]).

## Codificação VAE e escalonamento

`_encode` faz a codificação determinística (`.mode()`) e aplica `scaling_factor`
(`≈ 0.18215` no SD 1.5) para trazer os latents para a escala usada no treinamento.
Isso é necessário porque o VAE treina com os latents não escalados, mas o UNet/
scheduler trabalham com os escalados.

## Embeddings de texto

A função interna `_embed(text)` tokeniza e codifica o texto com o `text_encoder`
do pipeline. Ambos os embeddings (condicional e incondicional) são calculados
**antes** do loop — não dentro — para não recomputar a cada passo (otimização
correta, igual à versão anterior).

## Latent inicial

```python
latents = torch.randn((1, 4, lh, lw), generator=generator, dtype=fg_latent.dtype)
         .to(fg_latent.device)
latents = latents * pipe.scheduler.init_noise_sigma
```

`generator` usa `device="cpu"` mesmo em CUDA para reproducibilidade cross-device
(gerador CUDA pode variar com driver). `init_noise_sigma` escala o ruído inicial
para o schedule DPM++ SDE.

## Loop de denoising

A cada passo `t`:
1. `scale_model_input` normaliza `latents` para a escala que o scheduler espera.
2. `torch.cat([scaled, fg_latent, bg_latent], dim=1)` monta o tensor de 12 canais.
3. A UNet roda **duas vezes** (classifier-free guidance): uma com `prompt_embeds`,
   uma com `negative_embeds`.
4. CFG clássico: `noise_pred = uncond + cfg × (cond − uncond)`.
5. `scheduler.step` atualiza `latents` para o passo anterior.

Nota: o `fg_latent` e `bg_latent` são constantes — injetados em cada passo sem
recodificar. Isso é correto para IC-Light fbc, que usa fg/bg como condição estática.

## Decodificação e normalização de saída

```python
decoded = pipe.vae.decode(latents / pipe.vae.config.scaling_factor).sample
decoded = (decoded / 2 + 0.5).clamp(0, 1)
out = (decoded[0].permute(1, 2, 0).float().cpu().numpy() * 255).astype(np.uint8)
return Image.fromarray(out)
```

O VAE decodifica em `[-1, 1]`; a divisão por 2 + 0.5 traz para `[0, 1]`. `clamp`
previne artefatos de overflow.

## Parâmetros e seus efeitos

| Param | Default | Recomendação IC-Light |
|---|---|---|
| `steps` | 20 | 20–28 com DPM++ SDE Karras |
| `cfg` | 7.0 | — |
| `seed` | 12345 | qualquer inteiro; fixar para reproducibilidade por frame |

> ⚠️ O CFG default do código (`7.0`) é maior que o default da versão fc anterior
> (`2.0`). O demo oficial do IC-Light fbc usa valores entre 2 e 5. CFG alto pode
> introduzir over-saturation; considerar reduzir para 2.0–5.0 se artefatos
> aparecerem. (Inferido da documentação do demo, não do código.)

## Relacionados
[[concepts/agent-relighting-channel-layout]] · [[concepts/agent-relighting-load-flow]] ·
[[entities/agent-relighting-module]] · [[concepts/ic-light]] · [[index]]
