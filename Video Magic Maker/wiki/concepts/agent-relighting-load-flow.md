---
title: "agent-relighting-load-flow — Sequência de carregamento do pipeline IC-Light fbc"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [concept, ic-light, fbc, loading, offset-merge, unet]
---
# agent-relighting-load-flow — Sequência de carregamento do pipeline IC-Light fbc

Descreve passo a passo o que `carregar_iclight()` faz ao construir o pipeline
IC-Light fbc a partir do SD 1.5 base.

## Sequência completa

```
1. from_pretrained(BASE_SD15)
       ↓ pipe com UNet 4-ch, VAE, tokenizer, text_encoder
2. Expandir conv_in: 4ch → 12ch (zero-init + cópia dos 4 originais)
       ↓ UNet agora aceita 12 canais, mas pesos novos zerados
3. _baixar_pesos_fbc()  →  offset dict (safetensors)
       ↓ tensor dict com chaves iguais ao state_dict da UNet
4. offset-merge: merged[k] = origin[k] + offset[k]
       ↓ UNet com pesos SD15 + deltas IC-Light
5. unet.load_state_dict(merged, strict=True)
       ↓ todas as chaves devem bater — erro explícito se não baterem
6. Configurar DPMSolverMultistepScheduler (SDE Karras)
7. Mover para device (cuda/cpu) ou ativar low-vram offloads
8. set_progress_bar_config(disable=True)
```

## Etapa 1: SD 1.5 base

`StableDiffusionPipeline.from_pretrained` com:
- `torch_dtype=torch.float16` em CUDA (reduz ~50% de VRAM) / `float32` em CPU.
- `safety_checker=None` — desabilitado para performance; o conteúdo é sempre a
  pessoa do usuário (imagem própria, sem geração livre).

## Etapa 2: expansão de conv_in (12 canais)

Ver [[concepts/agent-relighting-channel-layout]] para o layout completo.  
O ponto crítico é que isso ocorre **antes** do offset-merge, pois o offset do
fbc já inclui deltas para os 12 canais de `conv_in`.

## Etapa 3: resolução do arquivo de pesos

`_baixar_pesos_fbc(model_path)`:
- Se `model_path` é fornecido e o arquivo existe no disco → usa diretamente.
- Caso contrário → `hf_hub_download(repo_id="lllyasviel/ic-light", filename="iclight_sd15_fbc.safetensors")`.
  O HF Hub mantém cache em `~/.cache/huggingface/` — segunda chamada é instantânea.

## Etapa 4–5: offset-merge (ponto crítico de correção de bug)

```python
origin = unet.state_dict()
offset = load_file(weights_file)
merged = {}
for k in origin.keys():
    if k in offset:
        merged[k] = origin[k] + offset[k]
    else:
        merged[k] = origin[k]
unet.load_state_dict(merged, strict=True)
```

**Por que isso importa:** IC-Light é distribuído como um *delta* treinado sobre o
SD 1.5, não como uma UNet completa. Carregar com `load_state_dict(offset, strict=False)`
(o bug da versão fc anterior) sobrescrevia os pesos com os deltas crus —
equivalente a usar uma UNet inicializada aleatoriamente com valores próximos de
zero. O resultado visível era relighting não-funcional.

`strict=True` garante que nenhuma chave está faltando ou sobrando — falha
explicitamente se o offset não for compatível com a UNet expandida.

## Etapa 6: scheduler DPM++ 2M SDE Karras

```python
DPMSolverMultistepScheduler(
    num_train_timesteps=1000,
    beta_start=0.00085,
    beta_end=0.012,
    algorithm_type="sde-dpmsolver++",
    use_karras_sigmas=True,
    steps_offset=1,
)
```

Configuração do demo oficial lllyasviel/IC-Light. O `sde-dpmsolver++` tem melhor
qualidade que o DDIM para poucos passos (20 por default). `use_karras_sigmas=True`
aplica o schedule de sigmas de Karras, que concentra steps nas regiões de
transição mais importantes.

## Etapa 7: gerenciamento de device/VRAM

Ver [[concepts/agent-relighting-vram]] para os três modos (cuda, low_vram, cpu).

## Relacionados
[[concepts/agent-relighting-channel-layout]] · [[concepts/agent-relighting-vram]] ·
[[concepts/agent-relighting-denoising-loop]] · [[entities/agent-relighting-module]] ·
[[concepts/ic-light]] · [[index]]
