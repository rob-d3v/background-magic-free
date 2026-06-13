---
tags: [component, agent, composicao, cpu, fallback]
date: 2026-06-13
status: stable
source: agentes/composicao.py
---

# composicao — Agente 4b (Composição CPU, sem GPU)

`agentes/composicao.py` → `compor_frame(...)` + `compor_batch(...)`. Compõe o
recorte RGBA da pessoa sobre o novo fundo via canal alpha, **em CPU**. **Não
reilumina** — a luz da pessoa continua a do vídeo original. Entrega só o efeito de
"troca de ambiente".

## O que faz
- `compor_frame`: faz **cover-crop** do fundo (resize + center crop) para o tamanho
  do foreground e cola o RGBA via alpha (`base.paste(person, (0,0), person)`).
  Ajustes opcionais de brilho/cor (`ImageEnhance.Brightness`/`.Color`) casam
  levemente a pessoa ao fundo, sem IA.
- `compor_batch`: processa todos os frames com **resume automático**
  (`if os.path.exists(output_path): continue`), captura erro por frame em
  `composicao_erros` no `log_path`.

## Inputs / Outputs
- **Inputs:** `frames_nobg_dir` (RGBA de [[components/remocao]]),
  `background_path` (`bg.png`), `ajuste_brilho`, `ajuste_cor`, `log_path`.
- **Output:** PNGs RGB compostos em `output_dir`; `dict`
  `{processados, erros, tempo_s}`.

## Parâmetros-chave
| Param | Default | Nota |
|---|---|---|
| `ajuste_brilho` | 1.0 | 1.0 = sem mudança |
| `ajuste_cor` | 1.0 | 1.0 = sem mudança |

## Gotchas
- **Não há relighting** — usar quando não há GPU para o IC-Light
  ([[components/relighting]]) ou como **preview instantâneo** antes do lote pesado.
- Roda inteiramente em **CPU** (Pillow), independente de torch/CUDA. Ver
  [[concepts/gpu-vram-local-vs-colab]].
- Mesma lógica de composição cover-crop usada per-frame no [[components/live-mode|live mode]]
  (que faz a composição em tempo real, também sem relight).
- **Modo Studio.** No Gradio (`app.py`) este é o modo **"Compor (rapido, CPU)"**
  (`MODO_COMPOR`): rembg + composição. O modo **"Trocar fundo HD (RVM, CPU)"**
  ([[components/render-video]]) é o irmão de **maior qualidade de borda** — recorte
  RVM, sem rembg, também sem relight.

## Relacionados
[[components/remocao]] · [[components/relighting]] · [[components/live-mode]] ·
[[components/render-video]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
