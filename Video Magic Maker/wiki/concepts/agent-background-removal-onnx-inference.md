---
title: "rembg/ONNX — inferência GPU e fallback CPU"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/remocao.py", "requirements.txt", "concepts/gpu-vram-local-vs-colab.md"]
tags: [concept, rembg, onnx, onnxruntime, gpu, inference, u2net]
---
# rembg/ONNX — inferência GPU e fallback CPU

`remocao.py` usa rembg sobre ONNX Runtime para executar o modelo U²-Net. A separação entre rembg e torch é o que permite ao agente 2 rodar em CPU local enquanto os demais agentes (IC-Light, SD 1.5) exigem CUDA.

## Cadeia de dependências

```
remocao.py
  └─ rembg (Python API)
       └─ onnxruntime-gpu  (execução do modelo .onnx)
            ├─ CUDAExecutionProvider   (GPU NVIDIA, se disponível)
            └─ CPUExecutionProvider   (fallback automático)
```

`rembg` **não usa torch para inferência** — o modelo é exportado como ONNX e executado
diretamente pelo ONNX Runtime. Por isso o agente funciona mesmo quando o torch instalado
é CPU-only (caso da máquina de dev local com GTX 1650 Ti / torch sem CUDA).

## Provider selection (ONNX Runtime)

O ONNX Runtime tenta providers em ordem de prioridade:

1. `CUDAExecutionProvider` — GPU NVIDIA; requer `onnxruntime-gpu` + driver CUDA.
2. `CPUExecutionProvider` — fallback universal.

`rembg` delega a seleção ao ONNX Runtime; não há código explícito de provider em
`remocao.py`. O provider ativo é transparente para o chamador — a API `remove()`
é a mesma em ambos os casos.

## Modelo: `u2net_human_seg`

- Arquitetura: U²-Net (encoder-decoder nested, skip connections em U duplo).
- Variante: `_human_seg` — fine-tuned para segmentação de silhueta humana vs.
  `u2net` genérico (objetos em geral). Produz máscaras mais nítidas em bordas
  de cabelo, ombros e mãos.
- Formato em disco: ONNX (`.onnx`), ~176 MB.
- Cache: `~/.u2net/u2net_human_seg.onnx` — baixado automaticamente pelo rembg
  no primeiro `new_session(...)`. Chamadas subsequentes reutilizam o arquivo local.

## Ciclo de vida da sessão

```python
session = new_session("u2net_human_seg")   # carrega uma vez, fora do loop
for frame_name in frames:
    result = remove(img_bytes, session=session, ...)  # reutiliza sessão
```

Criar a sessão fora do loop é crítico para performance: carrega o modelo ONNX
em memória (e na VRAM se GPU disponível) uma única vez, evitando o overhead de
carregamento a cada frame.

## Input/Output do modelo

| Etapa | Formato |
|---|---|
| Input para `remove()` | `bytes` (PNG raw — lido com `open(..., "rb").read()`) |
| Output de `remove()` | `bytes` (PNG RGBA — escrito com `open(..., "wb").write()`) |

rembg decodifica os bytes para imagem internamente, executa o modelo ONNX para
gerar a máscara de segmentação, aplica alpha matting (se habilitado), e serializa
o resultado de volta para PNG RGBA.

## Performance relativa

| Ambiente | Provider | Tempo estimado/frame |
|---|---|---|
| Colab T4 (15GB) | CUDAExecutionProvider | ~0.3s |
| Local GTX 1650 Ti (4GB, sem CUDA torch) | CPUExecutionProvider | ~1–3s |
| CPU puro (sem GPU) | CPUExecutionProvider | ~2–5s |

O gargalo da pipeline completa é IC-Light (~1.5s/frame em T4), não o rembg.

## Gotchas

- `onnxruntime-gpu` vs `onnxruntime`: o requirements.txt especifica `onnxruntime-gpu`
  para garantir que o provider CUDA esteja disponível em produção Colab. Instalar
  `onnxruntime` (sem `-gpu`) desabilita silenciosamente a GPU.
- Se a VRAM estiver cheia (ex: IC-Light ainda carregado), o ONNX Runtime pode cair
  para CPU mesmo com GPU disponível — mas o agente 2 roda antes do relighting, então
  não há conflito de memória no fluxo normal.
- O download do modelo na primeira execução (~176 MB) pode falhar em ambientes sem
  acesso à internet; nesse caso `new_session()` levanta exceção antes do loop.

## Relacionados

[[entities/agent-background-removal-remocao]] · [[concepts/agent-background-removal-alpha-matting]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[decisions/agent-background-removal-model-choice]] · [[index]]
