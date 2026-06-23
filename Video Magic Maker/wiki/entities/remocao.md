---
title: remocao — Agente 2 (Remoção de Fundo)
type: entity
created: 2026-06-14
updated: 2026-06-14
sources: ["agentes/remocao.py"]
tags: [component, agent, rembg, segmentation]
status: stable
migrated-from: wiki/components/remocao.md
original-date: 2026-06-13
---
# remocao — Agente 2 (Remoção de Fundo)

`agentes/remocao.py` → `remover_fundo(frames_dir, output_dir, log_path=None)`.
Recorta a pessoa de cada frame com rembg, produzindo PNGs RGBA (fundo transparente).

## O que faz
- Cria uma sessão rembg `new_session("u2net_human_seg")` (modelo otimizado para
  pessoas) e processa cada frame com `remove(...)` + alpha matting.
- Suporta **resume automático**: `if os.path.exists(output_path): continue`.
- Captura exceção por frame, registra em `erros` e continua (não aborta o lote).

## Inputs / Outputs
- **Input:** PNGs em `frames/raw/` (saída de [[entities/extracao]]).
- **Output:** PNGs RGBA em `frames/nobg/` e um `dict`
  `{processados, erros, tempo_s}`. Erros também vão para `log_path`
  (`pipeline_log.json`, chave `remocao_fundo_erros`) quando há falhas.

## Parâmetros-chave (alpha matting)
| Param | Valor | Efeito |
|---|---|---|
| `alpha_matting` | `True` | bordas mais suaves (mais lento) |
| `alpha_matting_foreground_threshold` | 240 | limiar de foreground |
| `alpha_matting_background_threshold` | 10 | limiar de background |
| `alpha_matting_erode_size` | 10 | erosão da máscara |

## Gotchas
- **GPU é via `onnxruntime-gpu`**, não torch. Local (torch CPU-only) o rembg roda
  em **CPU** — funciona, mas é mais lento; verificado local nesta sessão.
  Ver [[concepts/gpu-vram-local-vs-colab]].
- A saída é **RGBA**; o relighting depois compõe o alpha sobre cinza neutro
  `(127,127,127)` para extrair o foreground RGB. Ver [[entities/relighting]].
- Detalhes do modelo e matting em [[concepts/rembg-background-removal]].

## Relacionados
[[entities/extracao]] · [[entities/relighting]] ·
[[concepts/rembg-background-removal]] · [[concepts/video-frame-pipeline]] · [[index]]

## Documentação aprofundada (Agente 2)

Páginas com análise exaustiva do subsistema:
- [[entities/agent-background-removal-remocao]] — fluxo interno passo-a-passo, I/O completo
- [[concepts/agent-background-removal-onnx-inference]] — providers ONNX, GPU/CPU, cache do modelo
- [[concepts/agent-background-removal-alpha-matting]] — algoritmo trimap, parâmetros, custo
- [[concepts/agent-background-removal-resume]] — mecanismo de idempotência por frame
- [[concepts/agent-background-removal-paths]] — workspace, estrutura de dirs, log.json
- [[decisions/agent-background-removal-model-choice]] — u2net_human_seg vs alternativas
