---
title: Bifurcação de fundo — próprio vs gerado por IA
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["pipeline.py", "agentes/geracao_fundo.py"]
tags: [concept, orchestrator, pipeline, background, branching, comfyui, sd15]
status: stable
---
# Bifurcação de fundo — próprio vs gerado por IA

No passo 3 da pipeline (Agente 3), o orquestrador escolhe entre dois caminhos mutuamente exclusivos para produzir `background/bg.png`. A chave é o flag `--background` na CLI.

## Decisão

```python
usar_fundo_proprio = args.background is not None
```

A variável é avaliada antes do `pipeline_start` e controla o bloco `if/else` da Etapa 3.

## Caminho A — fundo próprio (`--background <arquivo>`)

```python
bg_img = Image.open(args.background).convert("RGB")
bg_img = bg_img.resize((meta["width"], meta["height"]), Image.LANCZOS)
bg_img.save(paths.bg_output)
pipeline_log["etapas"].append({"etapa": "fundo", "modo": "proprio"})
```

- A imagem é carregada, convertida para RGB (elimina alpha se presente), redimensionada para as dimensões exatas do vídeo usando `LANCZOS` e salva em `bg.png`.
- O redimensionamento usa as dimensões de `meta` capturadas no Agente 1 — garantindo que o fundo case pixel-a-pixel com os frames extraídos.
- Não depende de GPU. Roda em CPU.
- Não há verificação de formato — qualquer arquivo que o Pillow consiga abrir é aceito.

## Caminho B — fundo gerado por IA (sem `--background`)

```python
from agentes.geracao_fundo import iniciar_comfyui, gerar_fundo
comfy_proc = iniciar_comfyui()
try:
    gerar_fundo(prompt=args.prompt, width=meta["width"], height=meta["height"],
                output_path=paths.bg_output, steps=args.steps,
                cfg=args.cfg_bg, seed=args.seed)
    pipeline_log["etapas"].append({"etapa": "fundo", "modo": "ia"})
finally:
    comfy_proc.terminate()
```

- Sobe um servidor ComfyUI local na porta 8188 como subprocesso.
- Envia um workflow SD 1.5 (`v1-5-pruned-emaonly.safetensors`) via API HTTP.
- O `finally` garante que `comfy_proc.terminate()` sempre executa — mesmo se `gerar_fundo` lançar exceção. Sem isso, o processo ComfyUI ficaria preso na memória.
- **Requer GPU CUDA** e o ComfyUI instalado em `/content/ComfyUI` (path hardcoded no default de `iniciar_comfyui`).
- O `--prompt` é compartilhado com o relighting: usado tanto para descrever o ambiente do fundo quanto para instruir o IC-Light sobre a iluminação. Isso é intencional — o fundo e o relight devem descrever o mesmo cenário.

## Relação com o modo de execução (Agente 4)

O fundo (`bg.png`) é independente do modo relight/compose:

| Modo Agente 4 | Fundo próprio | Fundo por IA |
|---|---|---|
| `relight` | bg.png usado como condição de fundo para IC-Light fbc | bg.png usado como condição de fundo para IC-Light fbc |
| `compose` | bg.png usado como fundo para alpha composite Pillow | bg.png usado como fundo para alpha composite Pillow |

Em ambos os casos, `bg.png` é um arquivo PNG estático único reutilizado para todos os frames do vídeo.

## Implicações de qualidade

- **Fundo próprio + compose**: iluminação da pessoa permanece a do vídeo original; fundo pode ter luz incongruente. Mais rápido, sem GPU.
- **Fundo próprio + relight**: IC-Light reilumina a pessoa para casar com a luz do fundo fornecido. Requer GPU. Melhor integração visual.
- **Fundo IA + relight**: melhor qualidade geral — fundo e iluminação são coerentes com o `--prompt`. Requer GPU + ComfyUI.
- **Fundo IA + compose**: improvável em prática (`--modo compose` com fundo por IA), mas tecnicamente suportado.

## Gotchas

- `iniciar_comfyui` usa `comfyui_dir="/content/ComfyUI"` como default — é um path Colab hardcoded. Em ambiente local, é necessário passar `comfyui_dir` ou usar o backend diffusers (`gerar_fundo_diffusers`) via `app.py`.
- O polling de `/history` em `gerar_fundo` não tem timeout — se o ComfyUI travar silenciosamente, o orquestrador espera indefinidamente.
- O fundo gerado é uma imagem **estática** — o mesmo fundo é usado em todos os frames. Não há geração de fundo por frame.
- Se `args.seed == -1` (default da CLI não é -1; default é 12345), o ComfyUI usa um seed aleatório via `uuid4`. Reprodutibilidade requer seed explícito.

## Relacionados

[[entities/pipeline]] · [[entities/geracao_fundo]] ·
[[concepts/pipeline-orchestrator-mode-selection]] ·
[[concepts/pipeline-orchestrator-call-sequence]] ·
[[concepts/sd15-background-generation]] ·
[[concepts/agent-background-generation-comfyui-subprocess]] · [[index]]
