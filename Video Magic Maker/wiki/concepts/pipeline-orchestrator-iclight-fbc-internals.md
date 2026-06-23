---
title: IC-Light fbc — internos do UNet 12 canais e offset-merge
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [concept, ic-light, fbc, unet, offset-merge, relighting, diffusion]
status: stable
---
# IC-Light fbc — internos do UNet 12 canais e offset-merge

Documenta como o [[entities/relighting]] carrega e opera o IC-Light fbc depois da migração fbc concluída. Contexto da migração: [[decisions/migrate-fc-to-fbc]].

## Por que 12 canais de entrada

O IC-Light **fbc** (foreground + background conditioned) tem UNet com `conv_in` de **12 canais**:

```
4 canais — latent noisy (z_t, o que o denoiser prevê)
4 canais — fg latent    (pessoa sobre cinza neutro, VAE-encoded)
4 canais — bg latent    (fundo, VAE-encoded)
```

A versão **fc** (foreground-conditioned) anterior usava 8 canais (4 noisy + 4 fg) e descartava o fundo — o bug central que motivou a migração.

## `carregar_iclight` — sequência de carga

1. **Carrega SD 1.5 base** (`stablediffusionapi/realistic-vision-v51`, fp16 em CUDA).
2. **Expande `conv_in`**: cria um `Conv2d(12 → out_channels)`, zera todos os pesos, copia os 4 canais originais para `[:, :4, :, :]`, copia o bias. Os 8 canais novos começam com peso zero — o modelo inicialmente os ignora e aprende a usá-los via fine-tuning (IC-Light).
3. **Offset-merge**: carrega `iclight_sd15_fbc.safetensors` como `offset`. Para cada key da UNet base: `merged[k] = origin[k] + offset[k]` (para keys presentes no offset); keys ausentes ficam com o valor base. Carrega com `strict=True` — garante que nenhuma key é perdida ou sobrescrita incorretamente.
4. **Scheduler**: substitui pelo `DPMSolverMultistepScheduler` com `algorithm_type="sde-dpmsolver++"` e `use_karras_sigmas=True` — o scheduler recomendado pelo demo oficial.
5. **VRAM management**: se `low_vram=True` (< 8 GB), ativa `enable_sequential_cpu_offload` + `enable_attention_slicing` + `enable_vae_slicing`; caso contrário, `.to("cuda")` direto.

## Por que offset-merge (não load_state_dict direto)

Os pesos `iclight_sd15_fbc.safetensors` são **deltas/offsets** em relação à UNet base do SD 1.5, não uma UNet completa. Carregar diretamente com `load_state_dict` sobrescreveria a UNet base com os deltas crus — produzindo pesos inválidos. O merge correto é:

```python
merged[k] = origin[k] + offset[k]   # soma, não substituição
unet.load_state_dict(merged, strict=True)
```

A versão fc anterior usava `load_state_dict(ic_weights, strict=False)` — esse era o segundo bug documentado em [[decisions/migrate-fc-to-fbc]].

## `relight_frame` — denoising de um frame

Fluxo de um frame:

1. **Pré-proc foreground**: compõe a RGBA sobre cinza neutro `(127,127,127)` → `_fg_sobre_cinza`. Isso é o padrão do demo oficial: o cinza neutro sinaliza "fundo desconhecido" para o modelo.
2. **Resize**: ambos fg e bg são `_resize_center_crop` para o tamanho alvo (múltiplo de 64).
3. **VAE-encode** fg e bg: `pipe.vae.encode(t).latent_dist.mode()` (deterministico) × `scaling_factor`.
4. **Text embeds**: `pipe.tokenizer` + `pipe.text_encoder` para prompt e negative prompt — calculados uma vez por frame.
5. **Loop de denoising**: para cada timestep `t`:
   - `model_in = torch.cat([scaled_noisy, fg_latent, bg_latent], dim=1)` — 12 canais.
   - Predição condicional e incondicional com o mesmo `model_in`.
   - CFG manual: `noise_pred = noise_uncond + cfg * (noise_cond - noise_uncond)`.
   - `scheduler.step(noise_pred, t, latents)`.
6. **VAE-decode**: `pipe.vae.decode(latents / scaling_factor)` → denormaliza → `PIL.Image` RGB.

A saída já é a pessoa composta e relitada no fundo — não precisa de composição adicional.

## `aplicar_relighting` — detalhes do batch

- **Dimensões fixas**: derivadas do primeiro frame (múltiplo de 64); todos os frames são processados no mesmo tamanho para consistência temporal.
- **Resume**: `if os.path.exists(output_path): continue` — idempotente.
- **`progress_cb`**: callback opcional `(i, total)` para UIs (Gradio).
- **`low_vram`**: determinado pelo orquestrador com `(vram_gb or 99) < 8.0`.
- Erros por frame não abortam o batch; são persistidos em `pipeline_log.json` (`relighting_erros`).

## Pesos e download

```python
FBC_REPO = "lllyasviel/ic-light"
FBC_FILE = "iclight_sd15_fbc.safetensors"
BASE_SD15 = "stablediffusionapi/realistic-vision-v51"
```

`_baixar_pesos_fbc(model_path)`: usa path local se existir, senão baixa do HuggingFace Hub via `hf_hub_download`. O SD 1.5 base é baixado pelo `from_pretrained` do diffusers (cache HF padrão).

## Relacionados

[[entities/relighting]] · [[decisions/migrate-fc-to-fbc]] · [[concepts/ic-light]] · [[concepts/video-frame-pipeline]] · [[entities/pipeline]] · [[index]]
