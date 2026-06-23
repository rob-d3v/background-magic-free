---
title: "Decisão: u2net_human_seg + alpha matting como segmentador padrão"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/remocao.py", "requirements.txt"]
tags: [decision, rembg, u2net, alpha-matting, model-selection, inferred]
status: inferred
---
# Decisão: u2net_human_seg + alpha matting como segmentador padrão

**Status: inferred** — decisão inferida do código; não há ADR explícito no repositório.

O Agente 2 usa `u2net_human_seg` via rembg com `alpha_matting=True` como estratégia de remoção de fundo. Esta página justifica as escolhas implícitas.

## Contexto

A pipeline lumina-bg tem como caso de uso central **vídeo com pessoa em frente a um
fundo a ser substituído por IA (IC-Light)**. A segmentação precisa:
- Funcionar em CPU local para desenvolvimento (sem CUDA obrigatório).
- Produzir bordas suaves em cabelo e contornos de braços.
- Ser robusta a variações de iluminação e fundo.
- Ser resumível por frame (não é uma decisão do modelo em si, mas da arquitetura).

## Decisão 1: rembg/ONNX em vez de segmentador baseado em torch

**Escolha:** rembg (`onnxruntime-gpu`), não um modelo PyTorch (ex: Segment Anything, BiRefNet).

**Motivo inferido:**
- rembg roda em CPU automaticamente quando não há GPU CUDA — essencial para dev local
  com GTX 1650 Ti onde o torch não tem CUDA.
- API simples (`bytes → bytes`), sem necessidade de gerenciar tensors, device, dtypes.
- Os modelos torch (SAM, IC-Light, SD 1.5) já ocupam VRAM; ter o segmentador fora do
  ecossistema torch evita conflitos de memória.
- Custo de VRAM: o rembg/ONNX pode usar a GPU para inferência U²-Net sem afetar a
  VRAM reservada para IC-Light, pois termina antes do relighting começar.

## Decisão 2: `u2net_human_seg` em vez de `u2net` genérico

**Escolha:** variante `_human_seg`, não o modelo base.

**Motivo inferido:**
- O caso de uso é exclusivamente pessoas em vídeo — usar o modelo fine-tuned para
  pessoas produz máscaras de melhor qualidade em bordas de cabelo e silhuetas humanas.
- Não há necessidade de segmentar objetos genéricos nesta pipeline.

## Decisão 3: `alpha_matting=True` com os parâmetros atuais

**Escolha:** alpha matting habilitado com `foreground_threshold=240`, `background_threshold=10`, `erode_size=10`.

**Motivo inferido:**
- A qualidade das bordas importa para o resultado final: halos visíveis no vídeo
  composto são perceptíveis e degradam a qualidade do produto.
- Os parâmetros conservadores (`foreground_threshold=240`) reduzem falsos foregrounds.
- `erode_size=10` é um valor médio — suficiente para suavizar bordas de cabelo sem
  custo excessivo de processamento.

**Trade-off aceito:** alpha matting adiciona ~0.5–2s/frame em CPU. Com o gargalo
real sendo IC-Light (~1.5s/frame em T4), o custo extra do matting em GPU é aceitável.

## Alternativas não escolhidas (inferred)

| Alternativa | Por que não |
|---|---|
| `u2net` genérico | Qualidade inferior para pessoas |
| `isnet-general-use` | Não otimizado para pessoas |
| BiRefNet (torch) | Requer torch+GPU; sem fallback CPU |
| SAM (Segment Anything) | Requer prompt/ponto de referência; mais complexo de integrar por frame |
| `alpha_matting=False` | Bordas serrilhadas inaceitáveis para vídeo composto |

## Possíveis evoluções

- Substituir por modelo mais recente (ex: `birefnet-general`) quando houver GPU
  garantida em produção, para qualidade ainda maior.
- Expor `erode_size` e thresholds como parâmetros CLI para ajuste por vídeo.

## Relacionados

[[entities/agent-background-removal-remocao]] · [[concepts/agent-background-removal-alpha-matting]] ·
[[concepts/agent-background-removal-onnx-inference]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
