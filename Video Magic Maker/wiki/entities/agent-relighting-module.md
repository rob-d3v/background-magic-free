---
title: "agent-relighting-module — agentes/relighting.py (IC-Light fbc)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py"]
tags: [entity, agent, ic-light, relighting, fbc, sd15, diffusion]
---
# agent-relighting-module — agentes/relighting.py (IC-Light fbc)

Módulo Python que implementa o Agente 4 (Relighting). Expõe três funções públicas
para carregar o pipeline IC-Light fbc e processar frames individuais ou em lote.

## Constantes globais

```python
FBC_REPO = "lllyasviel/ic-light"
FBC_FILE = "iclight_sd15_fbc.safetensors"
BASE_SD15 = "stablediffusionapi/realistic-vision-v51"
```

- `FBC_REPO` / `FBC_FILE`: localização do peso offset no Hugging Face Hub.
- `BASE_SD15`: modelo base SD 1.5 (Realistic Vision v5.1) usado antes de aplicar
  o offset fbc. Qualquer SD 1.5 compatível pode ser substituído aqui.

## Dependências externas

| Pacote | Uso |
|---|---|
| `torch` | tensores, gerador, `no_grad` |
| `diffusers` | `StableDiffusionPipeline`, `DPMSolverMultistepScheduler` |
| `safetensors.torch.load_file` | carrega o offset fbc sem pickles |
| `huggingface_hub.hf_hub_download` | baixa o peso se não existir localmente |
| `PIL` | leitura/escrita de frames PNG |
| `numpy` | conversão PIL ↔ tensor |
| `tqdm` | barra de progresso no batch |

## API pública

### `carregar_iclight(model_path, base_model, device, low_vram) → pipe`

Constrói e retorna o pipeline SD 1.5 modificado para IC-Light fbc. Ver detalhes
de implementação em [[concepts/agent-relighting-load-flow]].

**Parâmetros:**

| Param | Default | Tipo |
|---|---|---|
| `model_path` | `None` | `str \| None` — caminho local do `.safetensors`; baixa do HF se ausente |
| `base_model` | `BASE_SD15` | `str` — repo HF do SD 1.5 base |
| `device` | `"cuda"` | `"cuda"` ou `"cpu"` |
| `low_vram` | `False` | `bool` — ativa offload sequencial + attention/VAE slicing |

**Retorno:** instância de `StableDiffusionPipeline` com UNet de 12 canais e
scheduler DPM++ 2M SDE Karras configurado. Ver [[concepts/agent-relighting-vram]].

---

### `relight_frame(pipe, fg_rgba, bg_rgb, prompt, ...) → PIL.Image`

Reilumina um único frame. Usado tanto no preview interativo quanto internamente
por `aplicar_relighting`. Ver fluxo completo em [[concepts/agent-relighting-denoising-loop]].

**Parâmetros:**

| Param | Default | Significado |
|---|---|---|
| `fg_rgba` | — | foreground com canal alpha (recorte da pessoa) |
| `bg_rgb` | — | fundo RGB |
| `prompt` | — | prompt de texto para guiar o relighting |
| `negative_prompt` | `""` | prompt negativo |
| `steps` | `20` | passos de denoising |
| `cfg` | `7.0` | escala CFG |
| `seed` | `12345` | semente do gerador de ruído |
| `largura` / `altura` | `None` | resolução alvo; derivada do frame se `None`, arredondada para múltiplo de 64 |

**Retorno:** `PIL.Image` RGB com a pessoa composta e reiluminada no fundo.

---

### `aplicar_relighting(pipe, frames_nobg_dir, background_path, output_dir, prompt, ...) → dict`

Processa todos os frames `.png` de `frames_nobg_dir` em sequência. Suporta resume
automático (pula frames já presentes em `output_dir`). Dimensões são fixadas pelo
primeiro frame para consistência temporal do vídeo.

**Retorno:**
```python
{
    "processados": int,   # frames concluídos com sucesso
    "erros": int,         # falhas
    "tempo_s": float,     # tempo total
    "largura": int,       # resolução usada
    "altura": int,
}
```

Erros por frame são persistidos em `log_path` (JSON, chave `relighting_erros`).

## Funções auxiliares internas

| Função | Propósito |
|---|---|
| `_baixar_pesos_fbc(model_path)` | resolve caminho local ou baixa do HF |
| `_resize_center_crop(img, w, h)` | cobre w×h e corta o centro (resize + crop) |
| `_mult64(x)` | arredonda para baixo para múltiplo de 64 (mín 64) |
| `_fg_sobre_cinza(fg_rgba)` | compõe RGBA sobre fundo cinza 127 (pré-condicionamento) |
| `_encode(pipe, img_rgb)` | VAE-encode determinístico (`.mode()`), retorna latent escalado |

## Relacionados
[[concepts/agent-relighting-load-flow]] · [[concepts/agent-relighting-denoising-loop]] ·
[[concepts/agent-relighting-vram]] · [[concepts/agent-relighting-channel-layout]] ·
[[decisions/agent-relighting-fbc-completed]] · [[entities/relighting]] · [[concepts/ic-light]] ·
[[index]]
