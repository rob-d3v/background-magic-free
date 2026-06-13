---
tags: [concept, ic-light, relighting, diffusion]
date: 2026-06-13
status: in-migration
source: agentes/relighting.py
---

# IC-Light — fc vs fbc, offset-merge e layouts de canais

[IC-Light](https://github.com/lllyasviel/IC-Light) ("Imposing Consistent Light")
é um método de relighting sobre SD 1.5. Modifica a UNet base para aceitar canais
de condição extras concatenados no latent de entrada. Usado pelo
[[components/relighting]].

## Duas variantes

| Variante | Sigla | Canais da UNet `conv_in` | Condição | Saída |
|---|---|---|---|---|
| Foreground-conditioned | **fc** | **8** = 4 noisy + 4 fg | só foreground | pessoa relitada (precisa compor o fundo depois) |
| Foreground + Background | **fbc** | **12** = 4 noisy + 4 fg + 4 bg | foreground **e** fundo | pessoa **já composta no fundo** |

- O código atual usa **fc** (`iclight_sd15_fc.safetensors`), monta `conv_in` de 8
  canais e concatena só o `fg_latent`.
- A migração planejada é para **fbc** (`iclight_sd15_fbc.safetensors`): `conv_in`
  de 12 canais, concatenando `fg_latent` **e** `bg_latent`. O fbc consome o fundo
  gerado e produz a composição diretamente — eliminando a etapa (faltante) de
  composição manual. Ver [[decisions/migrate-fc-to-fbc]].

## Carregamento de pesos — offset/delta (ponto crítico)

IC-Light **não** é distribuído como uma UNet completa. É um **offset (delta)**
sobre os pesos da UNet base do SD 1.5. A forma correta de carregar é **somar** o
offset aos pesos originais:

```python
sd_origin = base_unet.state_dict()          # UNet do SD 1.5
sd_offset = load_file("iclight_sd15_fc.safetensors")
sd_merged = {k: sd_origin[k] + sd_offset[k] for k in sd_origin}
unet.load_state_dict(sd_merged, strict=True)
```

> **Bug atual:** [[components/relighting]] faz
> `pipe.unet.load_state_dict(ic_weights, strict=False)`, tratando o delta como um
> state_dict completo. Isso sobrescreve pesos com valores de offset (e ignora
> chaves ausentes via `strict=False`) → pesos inválidos. A correção do
> offset-merge vale para **fc e fbc**.

## Layout dos canais de entrada
- Latent base SD 1.5: **4 canais** (VAE `scaling_factor`).
- Cada condição (fg, bg) é uma imagem RGB codificada pelo VAE → mais **4 canais**.
- fc: `cat([noisy(4), fg(4)])` = 8. fbc: `cat([noisy(4), fg(4), bg(4)])` = 12.
- Ao expandir `conv_in`, os 4 primeiros canais recebem os pesos originais; os
  canais extras começam zerados (como em `carregar_iclight`).

## Parâmetros de inferência
- CFG **baixo** (1.5–3.0; default 2.0). Ver [[components/relighting]].
- Múltiplo de 8 nas dimensões (requisito do VAE/UNet).

## Relacionados
[[components/relighting]] · [[components/geracao_fundo]] ·
[[decisions/migrate-fc-to-fbc]] · [[concepts/sd15-background-generation]] · [[index]]
