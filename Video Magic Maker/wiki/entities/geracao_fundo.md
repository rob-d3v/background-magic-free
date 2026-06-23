---
title: geracao_fundo — Agente 3 (Geração de Fundo com SD 1.5)
type: entity
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/geracao_fundo.py"]
tags: [component, agent, stable-diffusion, comfyui, diffusers]
status: stable
migrated-from: wiki/components/geracao_fundo.md
original-date: 2026-06-13
---
# geracao_fundo — Agente 3 (Geração de Fundo com SD 1.5)

`agentes/geracao_fundo.py` expõe dois backends independentes para geração de
fundo com SD 1.5: `gerar_fundo()` via ComfyUI HTTP API (usado pelo Colab /
`pipeline.py`) e `gerar_fundo_diffusers()` via HuggingFace diffusers (usado
pela UI Gradio `app.py`). A etapa é pulada por inteiro quando o usuário fornece
um fundo próprio (ver [[entities/pipeline]]).

## Backend 1 — ComfyUI HTTP API

### Funções
- `iniciar_comfyui(comfyui_dir="/content/ComfyUI")` — lança `python main.py
  --port 8188 --cuda-device 0` como subprocesso (`Popen`, stdout/stderr
  descartados). Faz polling em `/system_stats` com up a 30 tentativas × 2s
  (=60s). Retorna o objeto `process`; o chamador deve chamar
  `process.terminate()` em `finally`.
- `gerar_fundo(prompt, width, height, output_path, ...)` — monta o workflow
  inline como dict JSON, `POST /prompt` com `client_id` UUID, faz polling em
  `GET /history/{prompt_id}` (sem timeout), baixa a imagem via `GET /view` e
  salva em `output_path`.

### Fluxo de dados (ComfyUI)
```
POST /prompt  {workflow JSON, client_id}
  → prompt_id

loop GET /history/{prompt_id}
  → quando aparece: outputs[node]["images"][0]

GET /view?filename=...&subfolder=...
  → bytes → PIL.Image → salvo em output_path
```

### Workflow (grafo de nodes)
`CheckpointLoaderSimple` (`v1-5-pruned-emaonly.safetensors`) → `EmptyLatentImage`
(`width×height`, `batch_size=1`) → `KSampler` (`euler_ancestral` / `karras`,
`denoise=1.0`) com `CLIPTextEncode` positivo/negativo → `VAEDecode` → `SaveImage`
(prefix `bg_output`).

## Backend 2 — diffusers (Gradio / `app.py`)

### Função
`gerar_fundo_diffusers(prompt, width, height, output_path=None, ...)` — carrega
`StableDiffusionPipeline.from_pretrained(base_model, torch_dtype=float16,
safety_checker=None).to("cuda")` **uma vez** num global `_SD_TXT2IMG` (lazy,
cached entre chamadas). Aceita um `base_model` configurável
(`stablediffusionapi/realistic-vision-v51` por padrão — variante realista de SD
1.5). Dimensões são arredondadas para múltiplos de 8 antes de passar ao pipeline.
Retorna `PIL.Image` (e salva em `output_path` se fornecido).

### Por que dois backends
Ver [[decisions/agent-background-generation-two-backends]].

## Parâmetros-chave (ambos)
| Param | Default | Nota |
|---|---|---|
| `steps` | 25 | inference steps |
| `cfg` | 7.0 | CFG da geração; alto vs relighting (~2.0) |
| `seed` | -1 | `-1` ⇒ aleatório (`uuid` no ComfyUI; `12345` fixo no diffusers); valor explícito ⇒ reprodutível |
| `negative_prompt` | `"person, human, people, ugly, blurry, low quality"` | impede pessoas no fundo |
| `base_model` (diffusers) | `stablediffusionapi/realistic-vision-v51` | substituível sem alterar o restante |

## Gotchas
- **Requer GPU CUDA** em ambos os caminhos. A UI Gradio verifica `DEV["cuda"]` e
  exibe erro se não houver GPU antes de chamar `gerar_fundo_diffusers`.
- O polling de `/history` (ComfyUI) **não tem timeout** — se a geração travar, o
  loop espera indefinidamente.
- A porta 8188 pode ficar presa se o ComfyUI não for terminado via `finally`.
- `_SD_TXT2IMG` (diffusers) permanece na VRAM entre chamadas (cache global) — bom
  para preview iterativo, mas ocupa ~3–4GB que não são liberados automaticamente.
- O seed `-1` tem comportamento diferente entre backends: ComfyUI usa `uuid4 %
  2**32`; diffusers usa `12345` hardcoded como fallback.
- Gera **uma única imagem estática** reutilizada em todos os frames do vídeo.
- Detalhes do modelo/workflow em [[concepts/sd15-background-generation]] e
  [[concepts/agent-background-generation-comfyui-subprocess]].

## Relacionados
[[entities/pipeline]] · [[entities/relighting]] ·
[[concepts/sd15-background-generation]] ·
[[concepts/agent-background-generation-comfyui-subprocess]] ·
[[decisions/agent-background-generation-two-backends]] ·
[[concepts/ic-light]] · [[index]]
