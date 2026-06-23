---
title: Geração de fundo com Stable Diffusion 1.5 (via ComfyUI)
type: concept
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/geracao_fundo.py"]
tags: [concept, stable-diffusion, comfyui, diffusers, background]
status: stable
migrated-from: wiki/concepts/sd15-background-generation.md
original-date: 2026-06-13
---
# Geração de fundo com Stable Diffusion 1.5 (via ComfyUI)

O fundo novo é gerado por **Stable Diffusion 1.5** rodando dentro do **ComfyUI**,
acionado por API. Usado pelo [[entities/geracao_fundo]]. Alternativa: o usuário
faz upload de um fundo próprio e esta etapa é pulada (ver [[entities/pipeline]]).

## Por que ComfyUI
ComfyUI expõe uma API HTTP (`/prompt`, `/history`, `/view`) e descreve a geração
como um **grafo de nodes** em JSON. Isso evita escrever o loop de difusão à mão e
reaproveita o ecossistema de checkpoints. O servidor sobe como subprocesso na
porta 8188.

## Workflow (grafo de nodes)
```
CheckpointLoaderSimple (v1-5-pruned-emaonly.safetensors)
   ├─ model ─┐
   ├─ clip ──┼─> CLIPTextEncode (positivo)  ─┐
   │         └─> CLIPTextEncode (negativo)  ─┤
   └─ vae ───────────────────────────┐      │
EmptyLatentImage (width×height) ──────┼──> KSampler ──> VAEDecode ──> SaveImage
                                      └──────┘
```
- **KSampler:** `euler_ancestral` + scheduler `karras`, `denoise=1.0`.
- **Negative prompt** padrão: `"person, human, people, ugly, blurry, low quality"`
  — impede que apareçam pessoas no fundo (a pessoa vem do foreground).

## Parâmetros
| Param | Default | Nota |
|---|---|---|
| `steps` | 25 | inference steps |
| `cfg` | 7.0 | CFG da geração (alto vs. o relighting, que usa ~2.0) |
| `seed` | -1 | `-1` ⇒ aleatório; valor fixo ⇒ reprodutível |

## Dimensões
O fundo é gerado em `width×height` do **vídeo** (vindos de [[entities/extracao]]),
para alinhar com os frames. SD 1.5 foi treinado em ~512px; resoluções muito
diferentes podem degradar a qualidade.

## Relação com o relighting
O fundo (`background/bg.png`) é a entrada de fundo do IC-Light. No **fc** atual
ele é (incorretamente) descartado; no **fbc** planejado ele entra como condição.
Ver [[concepts/ic-light]] e [[decisions/migrate-fc-to-fbc]].

## Backend alternativo: diffusers (Gradio)

Na UI Gradio (`app.py`), o mesmo resultado é obtido via
`gerar_fundo_diffusers()` com `StableDiffusionPipeline` do HuggingFace diffusers
— sem precisar do ComfyUI. O modelo padrão é `realistic-vision-v51` (variante
fotorrealística de SD 1.5), diferente do `v1-5-pruned-emaonly` do ComfyUI.
Ver [[decisions/agent-background-generation-two-backends]] para a justificativa.

## Gotchas
- Requer **GPU** em ambos os backends → etapa exclusiva do Colab (exceto se GPU
  local com VRAM suficiente). Ver [[concepts/gpu-vram-local-vs-colab]].
- Gera **uma imagem estática** reutilizada em todos os frames.
- Seed `-1` tem comportamento divergente: ComfyUI → aleatório real; diffusers →
  `12345` fixo.

## Relacionados
[[entities/geracao_fundo]] · [[concepts/agent-background-generation-comfyui-subprocess]] ·
[[decisions/agent-background-generation-two-backends]] ·
[[concepts/ic-light]] · [[entities/relighting]] · [[index]]
