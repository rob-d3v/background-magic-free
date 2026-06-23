---
title: ComfyUI subprocess launch pattern (Agente 3)
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/geracao_fundo.py", "lumina_bg.ipynb"]
tags: [concept, comfyui, subprocess, stable-diffusion, background]
---
# ComfyUI subprocess launch pattern (Agente 3)

`iniciar_comfyui()` lança o servidor ComfyUI como subprocesso do Python do
chamador, aguarda ele ficar online via polling HTTP, e devolve o handle do
processo para que o chamador chame `terminate()` quando terminar.

## Por que subprocesso

ComfyUI é um servidor web autônomo (FastAPI + asyncio) que não expõe uma API
Python importável. A única forma de consumi-lo programaticamente é subir o
servidor e usar sua HTTP API (`/prompt`, `/history`, `/view`). O subprocesso é
isolado no GPU/VRAM e pode ser terminado de forma limpa com `process.terminate()`.

## Sequência de inicialização

```
Popen(["python", "main.py", "--port", "8188", "--cuda-device", "0"],
      cwd=comfyui_dir, stdout=DEVNULL, stderr=DEVNULL)

for _ in range(30):          # até 60s (30 × 2s sleep)
    GET /system_stats → 200 OK → retorna process
    sleep 2

raise RuntimeError se não subiu
```

- `stdout`/`stderr` são descartados — falhas de boot do ComfyUI ficam silenciosas.
- O `cuda-device 0` assume uma única GPU; ambientes multi-GPU precisariam de
  ajuste.

## Ciclo de vida esperado (Colab)

```python
comfy_proc = iniciar_comfyui()
try:
    gerar_fundo(...)     # usa a API HTTP
finally:
    comfy_proc.terminate()   # libera porta 8188 e VRAM
```

No notebook `lumina_bg.ipynb` (célula 7 / etapa 3) esse padrão é seguido
corretamente. Se o `finally` não executar (kernel interrompido, exceção não
capturada), a porta 8188 fica ocupada até o runtime reiniciar.

## Detecção de prontidão

O polling é feito em `GET /system_stats` (endpoint nativo do ComfyUI que retorna
informações de CPU/RAM/GPU). Uma resposta `200 OK` indica que o servidor está
aceitando conexões. O timeout total de 60s é suficiente para o Colab T4, onde o
ComfyUI sobe em ~10–20s.

## API HTTP utilizada

| Endpoint | Método | Uso |
|---|---|---|
| `/system_stats` | GET | polling de prontidão |
| `/prompt` | POST | envia workflow JSON + `client_id` → retorna `prompt_id` |
| `/history/{prompt_id}` | GET | polling de conclusão → retorna outputs |
| `/view` | GET | download da imagem gerada (`filename`, `subfolder`) |

## Gotchas

- **Polling sem timeout em `/history`** — se o job travar na GPU, o loop `while
  True` fica indefinidamente. Adicionar um `max_wait` seria melhoria simples.
- **stdout/stderr descartados** — erros internos do ComfyUI (OOM, checkpoint não
  encontrado) não aparecem no log da pipeline. Redirecionar para arquivo facilitaria
  debug.
- **Única instância** — a porta 8188 é fixa; não há suporte a múltiplos workers
  simultâneos. O chamador deve garantir que apenas um subprocesso ComfyUI rode por
  vez.
- **Checkpoint path implícito** — `v1-5-pruned-emaonly.safetensors` deve estar em
  `{comfyui_dir}/models/checkpoints/`. O notebook baixa via `hf_hub_download`
  antes de iniciar o ComfyUI. Se o arquivo não existir, o ComfyUI sobe mas o job
  falha silenciosamente (ver gotcha de stderr descartado).

## Relacionados
[[entities/geracao_fundo]] · [[concepts/sd15-background-generation]] ·
[[decisions/agent-background-generation-two-backends]] · [[index]]
