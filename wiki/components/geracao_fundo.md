---
tags: [component, agent, stable-diffusion, comfyui]
date: 2026-06-13
status: stable
source: agentes/geracao_fundo.py
---

# geracao_fundo — Agente 3 (Geração de Fundo com SD 1.5)

`agentes/geracao_fundo.py` → `iniciar_comfyui()` + `gerar_fundo(...)`. Gera a
imagem de fundo via Stable Diffusion 1.5 usando a API do ComfyUI rodando em
background. Pulado quando o usuário fornece um fundo próprio (ver [[components/pipeline]]).

## O que faz
- `iniciar_comfyui(comfyui_dir)`: `Popen` de `python main.py --port 8188
  --cuda-device 0`, faz polling em `/system_stats` por até ~60s.
- `gerar_fundo(...)`: monta um workflow ComfyUI (grafo de nodes JSON), faz `POST
  /prompt`, faz polling em `/history/{id}` e baixa a imagem via `/view`.

## Inputs / Outputs
- **Inputs:** `prompt`, `width`, `height` (do vídeo), `output_path`,
  `negative_prompt`, `steps`, `cfg`, `seed`.
- **Output:** imagem salva em `output_path` (`background/bg.png`); retorna o path.

## Workflow (nodes)
`CheckpointLoaderSimple` (`v1-5-pruned-emaonly.safetensors`) → `EmptyLatentImage`
(`width×height`) → `KSampler` (`euler_ancestral` / `karras`, `denoise=1.0`) com
`CLIPTextEncode` positivo/negativo → `VAEDecode` → `SaveImage`.

## Parâmetros-chave
| Param | Default | Nota |
|---|---|---|
| `steps` | 25 | inference steps |
| `cfg` | 7.0 | CFG da geração (mais alto que o relighting) |
| `seed` | -1 | `-1` ⇒ seed aleatório (`uuid`); senão fixo |
| `negative_prompt` | `"person, human, people, ugly, blurry, low quality"` | evita pessoas no fundo |

## Gotchas
- **Requer GPU** (SD 1.5 no ComfyUI). Não roda na máquina local de 4GB / torch
  CPU-only — etapa exclusiva do Colab. Ver [[concepts/gpu-vram-local-vs-colab]].
- O ComfyUI é um **subprocesso**; o orquestrador chama `terminate()` em `finally`
  para liberar porta/VRAM. Se cair antes do `terminate`, a porta 8188 pode ficar presa.
- O polling de `/history` não tem timeout — se a geração travar, o loop espera
  indefinidamente.
- Gera **uma única imagem** reutilizada para todos os frames (fundo estático).
- Detalhes do modelo/workflow em [[concepts/sd15-background-generation]].

## Relacionados
[[components/pipeline]] · [[components/relighting]] ·
[[concepts/sd15-background-generation]] · [[concepts/ic-light]] · [[index]]
