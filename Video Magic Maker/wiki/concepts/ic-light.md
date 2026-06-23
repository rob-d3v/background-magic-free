---
title: IC-Light — fc vs fbc, offset-merge e layouts de canais
type: concept
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [concept, ic-light, relighting, diffusion, fbc]
status: stable
migrated-from: wiki/concepts/ic-light.md
original-date: 2026-06-13
---
# IC-Light — fc vs fbc, offset-merge e layouts de canais

[IC-Light](https://github.com/lllyasviel/IC-Light) ("Imposing Consistent Light")
é um método de relighting sobre SD 1.5. Modifica a UNet base para aceitar canais
de condição extras concatenados no latent de entrada. Usado pelo
[[entities/relighting]].

## Duas variantes

| Variante | Sigla | Canais da UNet `conv_in` | Condição | Saída |
|---|---|---|---|---|
| Foreground-conditioned | **fc** | **8** = 4 noisy + 4 fg | só foreground | pessoa relitada (precisa compor o fundo depois) |
| Foreground + Background | **fbc** | **12** = 4 noisy + 4 fg + 4 bg | foreground **e** fundo | pessoa **já composta no fundo** |

- O código **atual usa fbc** (`iclight_sd15_fbc.safetensors`), monta `conv_in` de
  12 canais e concatena `fg_latent` **e** `bg_latent`. O fbc produz a composição
  diretamente. Ver [[decisions/agent-relighting-fbc-completed]] para detalhes da
  migração concluída.
- A variante fc (8 canais, só fg) era usada anteriormente e tinha dois bugs;
  está documentada em [[decisions/migrate-fc-to-fbc]] como histórico.

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

> **Bug corrigido** (2026-06-22): a versão fbc atual já aplica o offset-merge
> correto (`origin[k] + offset[k]`, `strict=True`). Ver
> [[decisions/agent-relighting-fbc-completed]] e [[concepts/agent-relighting-load-flow]].

## Layout dos canais de entrada
- Latent base SD 1.5: **4 canais** (VAE `scaling_factor`).
- Cada condição (fg, bg) é uma imagem RGB codificada pelo VAE → mais **4 canais**.
- fc: `cat([noisy(4), fg(4)])` = 8. fbc: `cat([noisy(4), fg(4), bg(4)])` = 12.
- Ao expandir `conv_in`, os 4 primeiros canais recebem os pesos originais; os
  canais extras começam zerados (como em `carregar_iclight`).

## Parâmetros de inferência
- CFG **baixo** (1.5–3.0; default 2.0). Ver [[entities/relighting]].
- Múltiplo de 8 nas dimensões (requisito do VAE/UNet).

## Relacionados
[[entities/relighting]] · [[entities/geracao_fundo]] ·
[[concepts/agent-relighting-load-flow]] · [[concepts/agent-relighting-channel-layout]] ·
[[decisions/migrate-fc-to-fbc]] · [[decisions/agent-relighting-fbc-completed]] ·
[[concepts/ic-light-integration-colab-setup]] ·
[[concepts/ic-light-integration-notebook-agent-mismatch]] ·
[[decisions/ic-light-integration-diffusers-vs-comfyui]] ·
[[concepts/sd15-background-generation]] · [[index]]
