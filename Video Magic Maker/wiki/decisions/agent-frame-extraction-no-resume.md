---
title: Sem resume granular na extração de frames
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/extracao.py"]
tags: [decision, resume, ffmpeg, extraction, idempotency]
status: inferred
---
# Sem resume granular na extração de frames

> **Decisão inferida** — não há documento explícito de decisão; conclusão derivada da leitura do código.

O [[entities/extracao]] usa `-y` no ffmpeg, o que significa que **reexecutar a extração sempre reprocessa todos os frames**, sem detectar ou pular frames já existentes.

## Contexto

Os agentes de remoção de fundo e relighting implementam resume granular por frame:

```python
# em remocao.py e relighting.py
if os.path.exists(output_path):
    continue   # pula frame já processado
```

Isso é crítico para eles porque cada frame pode levar 0.3–1.5s e uma execução interrompida no Colab pode ter processado centenas de frames. A extração, por outro lado, leva ~1ms/frame via ffmpeg nativo — um vídeo de 1.800 frames (1 minuto a 30fps) é extraído em ~2-3 segundos total.

## Decisão

Não implementar resume granular na extração. O flag `-y` foi mantido e o agente sempre sobrescreve.

## Justificativa (inferida)

1. **Custo irrelevante:** ~2-3s para reextrair 1 minuto de vídeo é desprezível comparado ao gargalo real (IC-Light ~45 minutos para o mesmo vídeo).
2. **Simplicidade:** verificar existência de N PNGs e comparar com o vídeo de origem exigiria lógica extra de validação (timestamp? hash? contagem?).
3. **Correção garantida:** sobrescrever garante que o `output_dir` está sempre consistente com o vídeo de entrada atual. Resume parcial introduziria risco de mistura de frames de vídeos diferentes se o diretório não for limpo entre execuções.

## Trade-off

- **Pro:** código simples, sem risco de frames residuais de execuções anteriores.
- **Contra:** se o usuário reexecutar só para testar um frame diferente, toda a extração repete (custo baixo, mas não zero em vídeos muito longos — acima de ~30 minutos).

## Comparação com outros agentes

| Agente | Resume granular? | Razão |
|---|---|---|
| extração | Não | Custo baixo (~1ms/frame) |
| remoção fundo | Sim | Custo médio (~0.3s/frame) |
| relighting | Sim | Custo alto (~1.5s/frame) |
| exportação | Não | Opera o vídeo inteiro de uma vez |

## Relacionados

[[entities/extracao]] · [[concepts/video-frame-pipeline]] · [[concepts/agent-frame-extraction-output-dir-conventions]] · [[index]]
