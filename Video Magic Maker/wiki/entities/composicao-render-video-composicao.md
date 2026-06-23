---
title: "Agente Composicao (CPU fallback)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/composicao.py
tags:
  - composicao
  - cpu
  - fallback
  - background-swap
---

# Agente Composicao (CPU fallback)

Composição RGBA-over-RGB sem GPU: cola o recorte da pessoa sobre um novo fundo via canal alpha, com ajuste leve de brilho/cor.

## Papel no sistema

Identificado como "Agente 4b" no código fonte. É o caminho leve ativado quando não há GPU disponível para o IC-Light (relight pesado). Também serve como preview instantâneo antes de disparar o render de qualidade. Usa apenas Pillow (PIL) — zero dependência de torch, ONNX ou mediapipe.

Não reilumina: a luz da pessoa continua sendo a do vídeo original. O efeito entregue é "troca de ambiente", não "integração de iluminação".

## Funções

### `compor_frame(fg_rgba, bg_rgb, ajuste_brilho, ajuste_cor)`

Compõe um único frame. Lógica:

1. Redimensiona o fundo com `scale = max(w/iw, h/ih)` (cover, mantém proporção).
2. Center-crop para o tamanho exato do foreground.
3. Aplica `ImageEnhance.Brightness` e `ImageEnhance.Color` se diferentes de 1.0.
4. `base.paste(person, (0,0), person)` — composição pelo canal alpha da pessoa.
5. Retorna RGB (sem alpha).

### `compor_batch(frames_nobg_dir, background_path, output_dir, ...)`

Processa todos os `.png` de um diretório. Features:

- **Resume automático**: pula frames cujo arquivo de saída já existe (`os.path.exists(output_path)`).
- Progresso via callback `progress_cb(i+1, total)` ou tqdm.
- Erros por frame são coletados e opcionalmente gravados em `log_path` (JSON, chave `composicao_erros`).
- Retorna `{"processados", "erros", "tempo_s"}`.

## Relações

- Consome frames produzidos por um agente de matting anterior (rembg/[[composicao-render-video-rvm-matter]] etc.) — esperados como PNG RGBA.
- Alternativa leve ao [[composicao-render-video-render-video]], que usa RVM com coerência temporal.
- Acionado pelo modo Gradio "leve" (sem GPU).
