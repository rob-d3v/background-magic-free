---
title: "Decisão: dois caminhos CPU sem reiluminação"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/composicao.py
  - agentes/render_video.py
tags:
  - decisão
  - arquitetura
  - cpu
  - tradeoff
---

# Decisão: dois caminhos CPU sem reiluminação

> Inferred from source code comments and structure.

O sistema mantém dois caminhos distintos para troca de fundo sem GPU, em vez de um único caminho unificado.

## Contexto

O caminho "premium" do produto é o IC-Light (relight com difusão), que requer GPU (Colab ou hardware dedicado). Para usuários sem GPU, era necessário um fallback útil.

## Decisão

Dois caminhos foram criados, cada um otimizado para um ponto diferente no tradeoff velocidade/qualidade:

1. **composicao.py** (Pillow, sem torch): para quem já tem frames recortados (RGBA). Sem dependências pesadas, muito rápido, serve como preview instantâneo antes de disparar o relight.

2. **render_video.py + RVM** (torch CPU): para recorte de alta qualidade sem GPU. RVM produz alpha matte real (sem halo, sem "comer" o rosto) com coerência temporal. Mais pesado (~10 fps), mas "o caminho poderoso sem GPU".

## Rationale

- O caminho leve não pode substituir o RVM porque depende de frames já recortados por outro agente.
- O RVM não pode substituir o caminho leve para preview porque leva mais tempo para inicializar (torch.hub) e processar.
- Nenhum dos dois reilumina — isso é explicitamente aceito como tradeoff: "não reilumina, mas já entrega o efeito de troca de ambiente".

## Consequências

- O código de `render_video.py` usa `_build_matter(engine)` para selecionar entre RVM e MediaPipe em runtime — a decisão de qual motor usar fica no chamador (interface Gradio ou API).
- O resumo parcial do RVM tem uma limitação de coerência (ver [[composicao-render-video-rvm-temporal-coherence]]) que é documentada no código mas não bloqueada — o usuário decide.

## Relações

- [[composicao-render-video-cpu-render-pipeline]] — visão geral dos dois caminhos.
- [[composicao-render-video-composicao]] — caminho leve.
- [[composicao-render-video-render-video]] — caminho de qualidade.
