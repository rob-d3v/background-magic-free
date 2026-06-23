---
title: "Fonte: agentes/geracao_fundo.py"
type: source
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/geracao_fundo.py"]
tags: [source, stable-diffusion, comfyui, diffusers, background]
---
# Fonte: agentes/geracao_fundo.py

Módulo de ~182 linhas que implementa o Agente 3 — Geração de Fundo com SD 1.5.

## Estrutura

```
COMFYUI_URL = "http://127.0.0.1:8188"   # constante global

iniciar_comfyui(comfyui_dir)            # lança servidor, faz polling
gerar_fundo(prompt, width, height, ...) # ComfyUI backend
_SD_TXT2IMG = None                      # global lazy cache do pipeline diffusers
gerar_fundo_diffusers(prompt, ...)      # diffusers backend
```

## Dependências importadas

| Lib | Uso |
|---|---|
| `requests` | HTTP para ComfyUI API |
| `PIL.Image` | abrir bytes do `/view`, salvar output |
| `subprocess`, `time` | Popen + polling de startup |
| `uuid` | `client_id` único e seed aleatório |
| `io` | `BytesIO` para decodificar resposta de `/view` |
| `torch` (lazy) | apenas em `gerar_fundo_diffusers` |
| `diffusers.StableDiffusionPipeline` (lazy) | apenas em `gerar_fundo_diffusers` |

## Constantes / valores notáveis

- `COMFYUI_URL` = `"http://127.0.0.1:8188"` — não configurável por parâmetro.
- Checkpoint ComfyUI: `"v1-5-pruned-emaonly.safetensors"` — hardcoded no dict
  do workflow.
- `base_model` diffusers default: `"stablediffusionapi/realistic-vision-v51"`.
- Negative prompt default: `"person, human, people, ugly, blurry, low quality"`.
- Sampler ComfyUI: `euler_ancestral` + scheduler `karras`, `denoise=1.0`.

## Callers diretos

| Caller | Função chamada | Contexto |
|---|---|---|
| `lumina_bg.ipynb` (célula 7) | `iniciar_comfyui`, `gerar_fundo` | pipeline Colab completa |
| `pipeline.py` | `iniciar_comfyui`, `gerar_fundo` | CLI modo fundo-por-IA |
| `app.py` (`_obter_bg`) | `gerar_fundo_diffusers` | UI Gradio, modo "Gerar com IA" |

## Relacionados
[[entities/geracao_fundo]] · [[concepts/sd15-background-generation]] ·
[[concepts/agent-background-generation-comfyui-subprocess]] ·
[[decisions/agent-background-generation-two-backends]] · [[index]]
