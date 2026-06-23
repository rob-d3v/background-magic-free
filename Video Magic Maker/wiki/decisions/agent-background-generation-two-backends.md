---
title: "Decisão: dois backends de geração de fundo (ComfyUI vs diffusers)"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/geracao_fundo.py", "app.py"]
tags: [decision, stable-diffusion, comfyui, diffusers, gradio]
status: inferred
---
# Decisão: dois backends de geração de fundo (ComfyUI vs diffusers)

> ⚠️ Esta decisão é **inferida** do código — não há ADR explícito no repositório.

`agentes/geracao_fundo.py` implementa dois caminhos completamente independentes
para gerar a mesma imagem de fundo com SD 1.5: `gerar_fundo()` via ComfyUI e
`gerar_fundo_diffusers()` via HuggingFace diffusers.

## Contexto

A geração de fundo com SD 1.5 surgiu primeiro no contexto do notebook Colab
(`lumina_bg.ipynb`), onde o ComfyUI já estava instalado para o relighting. Ao
construir a interface Gradio (`app.py`), surgiu a necessidade de um caminho mais
direto — sem dependência de um servidor auxiliar rodando em background.

## Decisão

Manter dois backends:

| Backend | Caller | Onde roda | Dependência |
|---|---|---|---|
| `gerar_fundo()` | `pipeline.py`, notebook | Colab | ComfyUI servidor HTTP em background |
| `gerar_fundo_diffusers()` | `app.py` (Gradio) | Colab / GPU local | diffusers, torch |

## Justificativa (inferida)

1. **ComfyUI já presente no Colab** para o workflow de IC-Light. Reaproveitar o
   servidor evita instalar diffusers adicionalmente no ambiente de notebook.
2. **Gradio + diffusers = in-process.** Na UI Gradio, subir um subprocesso ComfyUI
   a cada clique no botão seria lento e gerenciaria mal o ciclo de vida. Com
   diffusers, o pipeline fica em memória (`_SD_TXT2IMG` global) e preview iterativo
   é instantâneo após o primeiro carregamento.
3. **Modelo diferente.** O path diffusers usa `realistic-vision-v51` (estilo
   fotorrealístico) enquanto o ComfyUI usa `v1-5-pruned-emaonly.safetensors`
   (SD 1.5 base). Isso sugere que a escolha do backend também permite trocar o
   checkpoint sem afetar o outro fluxo.
4. **Seed behavior diverge.** No ComfyUI, seed `-1` gera `uuid4 % 2**32`
   (verdadeiramente aleatório). No diffusers, seed `-1` cai em `12345` (fixo) —
   inconsistência que pode confundir quem espera aleatoriedade ao não especificar
   seed na UI.

## Consequências

- **Duplicação de parâmetros:** `steps`, `cfg`, `seed`, `negative_prompt` existem
  em ambos, mas o comportamento de seed difere (ver acima).
- **VRAM leak suave:** `_SD_TXT2IMG` não é liberado após uso; fica na VRAM até o
  processo Gradio terminar. No Colab, isso compete com IC-Light se ambos forem
  carregados na mesma sessão.
- **Checkpoint fixo no ComfyUI:** `v1-5-pruned-emaonly.safetensors` está hardcoded
  no workflow JSON. Trocar o modelo requer editar o código; no diffusers o
  `base_model` é parâmetro.

## Relacionados
[[entities/geracao_fundo]] · [[concepts/agent-background-generation-comfyui-subprocess]] ·
[[concepts/sd15-background-generation]] · [[decisions/local-vs-colab]] · [[index]]
