---
title: "ic-light-integration-diffusers-vs-comfyui — IC-Light via diffusers vs ComfyUI"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/relighting.py", "lumina_bg.ipynb"]
tags: [decision, ic-light, diffusers, comfyui, architecture, inferred]
status: inferred
---
# ic-light-integration-diffusers-vs-comfyui — IC-Light via diffusers vs ComfyUI

> Inferido: não há documento explícito de decisão. A conclusão é derivada da comparação entre o notebook e o código do agente.

## Duas abordagens presentes no repositório

O `lumina_bg.ipynb` configura tanto **ComfyUI** quanto o **repositório lllyasviel/IC-Light**, mas `agentes/relighting.py` usa **nenhum deles** — implementa o pipeline diretamente com `diffusers`.

| Aspecto | ComfyUI + repo IC-Light (notebook) | diffusers direto (agente fbc) |
|---|---|---|
| Setup | Clone 2 repos + requirements | `pip install diffusers safetensors` |
| Controle do loop | Opaco (nodes ComfyUI) | Total (código Python explícito) |
| UNet customizada | Via nós ComfyUI específicos | `Conv2d` manual + offset-merge |
| Scheduler | Configurado via workflow JSON | `DPMSolverMultistepScheduler` explícito |
| Integração com a pipeline Python | Subprocesso ou API REST | Import direto |
| Reproducibilidade por frame | Depende do workflow | `torch.Generator("cpu").manual_seed(seed)` |
| Resume granular | Não (ComfyUI não expõe) | Sim (`os.path.exists` por frame) |

## Por que diffusers foi escolhido (inferido)

1. **Resume frame-a-frame**: o relighting de vídeos precisa pausar e retomar entre frames (desconexões do Colab). Com diffusers, `aplicar_relighting` testa `os.path.exists(output_path)` antes de cada frame. Com ComfyUI, seria necessário um mecanismo externo de controle de estado.

2. **Transparência do offset-merge**: o bug histórico (carregar offset como UNet completa) só foi diagnosticável porque o loop é explícito em Python. Via ComfyUI, o nó de carregamento obscureceria esse comportamento.

3. **Integração nativa com a pipeline**: `relight_frame` é chamado diretamente pela UI Gradio para preview de 1 frame. Com ComfyUI, isso exigiria uma chamada HTTP à API do ComfyUI (subprocesso).

4. **Sem dependência de servidor**: ComfyUI precisa de um processo servidor rodando. O agente diffusers é uma função Python síncrona.

5. **CFG e scheduler explícitos**: o demo oficial lllyasviel/IC-Light usa DPM++ 2M SDE Karras. Com diffusers, isso é configurado em 6 linhas de código; com ComfyUI, depende de nós específicos que podem mudar entre versões.

## Estado atual do ComfyUI no projeto

`agentes/geracao_fundo.py` (Agente 3) usa ComfyUI via subprocesso para geração de fundo com SD 1.5. A célula 3 do notebook clona ComfyUI para esse propósito. O IC-Light (Agente 4) **não usa ComfyUI** — a presença dos dois no mesmo Colab é independente.

Ver [[entities/geracao_fundo]] para o uso de ComfyUI no Agente 3.

## Relacionados

[[entities/relighting]] · [[entities/geracao_fundo]] ·
[[concepts/ic-light-integration-notebook-agent-mismatch]] ·
[[concepts/ic-light]] · [[concepts/agent-relighting-load-flow]] ·
[[decisions/migrate-fc-to-fbc]] · [[index]]
