---
title: "agent-relighting-channel-layout — Layout de 12 canais da UNet fbc"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [concept, ic-light, fbc, unet, channels, latent]
---
# agent-relighting-channel-layout — Layout de 12 canais da UNet fbc

Explica como o modelo IC-Light fbc expande a `conv_in` do SD 1.5 de 4 para 12
canais e como os latents são concatenados no loop de denoising.

## SD 1.5 base: 4 canais

A UNet original do SD 1.5 recebe `4 canais` na `conv_in`: o latent ruidoso `z_t`
(espaço do VAE, escala 1:8 da resolução pixel). Cada canal latente corresponde
aproximadamente a 64×64 píxeis de informação.

## fbc: expansão para 12 canais

O IC-Light fbc concatena **duas condições** no latent de entrada:

```
[z_t (4ch)] + [fg_latent (4ch)] + [bg_latent (4ch)] = 12 canais
```

| Slot | Canais | Conteúdo | Origem |
|---|---|---|---|
| noisy | 0–3 | latent ruidoso no passo t | `torch.randn` × `init_noise_sigma` |
| fg | 4–7 | foreground sobre cinza neutro (127) codificado no VAE | `_encode(pipe, fg_rgb)` |
| bg | 8–11 | fundo RGB codificado no VAE | `_encode(pipe, bg)` |

## Expansão de `conv_in` em `carregar_iclight`

```python
original_conv = unet.conv_in            # Conv2d(4, ...) original
new_conv = torch.nn.Conv2d(12, original_conv.out_channels, ...)
new_conv.weight.zero_()                 # zerando todos os 12 canais
new_conv.weight[:, :4, :, :].copy_(original_conv.weight)  # copia os 4 originais
new_conv.bias.copy_(original_conv.bias)
unet.conv_in = new_conv
```

- Os 4 primeiros pesos recebem os valores do SD 1.5 original (comportamento
  neutro no slot noisy).
- Os 8 canais novos (fg + bg) começam zerados — a UNet aprende a usá-los via o
  treinamento do IC-Light. O offset fbc depois ajusta esses pesos com os deltas
  corretos ao ser somado na etapa de [[concepts/agent-relighting-load-flow]].

## Concatenação no loop de denoising

```python
scaled = pipe.scheduler.scale_model_input(latents, t)
model_in = torch.cat([scaled, fg_latent, bg_latent], dim=1)   # shape: (1, 12, lh, lw)
noise_pred = pipe.unet(model_in, t, encoder_hidden_states=prompt_embeds).sample
```

O `fg_latent` e `bg_latent` são fixos (não variam com `t`) — agem como condição
estática que a UNet usa como referência de iluminação. Apenas `scaled` (o latent
ruidoso) muda a cada passo.

## Pré-condicionamento do foreground

Antes de codificar, o recorte RGBA é composto sobre cinza `(127,127,127)` por
`_fg_sobre_cinza`. Isso espelha o pré-processamento do demo oficial do IC-Light,
que usa cinza médio para não enviesar a iluminação estimada.

## Codificação VAE (determinística)

`_encode` usa `.latent_dist.mode()` (não `.sample()`), tornando a codificação
determinística — sem aleatoriedade na condição. Aplica o `scaling_factor` do VAE
(`≈ 0.18215` no SD 1.5):

```python
latent = pipe.vae.encode(t).latent_dist.mode()
return latent * pipe.vae.config.scaling_factor
```

## Múltiplo de 64

`_mult64` arredonda dimensões para múltiplo de 64 (não de 8 como na versão fc
anterior). Isso é mais conservador: garante compatibilidade tanto com o VAE
(múltiplo de 8) quanto com possíveis camadas de atenção na UNet (múltiplo de 64).

## Relacionados
[[concepts/agent-relighting-load-flow]] · [[concepts/agent-relighting-denoising-loop]] ·
[[entities/agent-relighting-module]] · [[concepts/ic-light]] · [[index]]
