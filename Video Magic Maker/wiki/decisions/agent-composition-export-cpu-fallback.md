---
title: "Decisão: composição CPU como fallback do relighting GPU"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["pipeline.py", "agentes/composicao.py"]
tags: [decision, composicao, gpu, fallback, cpu, relighting]
status: stable
inferred: true
---
# Decisão: composição CPU como fallback do relighting GPU

## Contexto

O objetivo central do produto é trocar o fundo de vídeos **com reiluminação**
(IC-Light, [[entities/relighting]]). Porém o IC-Light requer GPU CUDA com ≥5GB
VRAM — indisponível em máquinas locais sem GPU ou no Colab gratuito sem
acelerador conectado.

## Decisão (inferred)

O [[entities/composicao]] (Agente 4b) foi adicionado como **fallback** que
executa o mesmo slot da pipeline sem GPU, entregando o efeito de "troca de
ambiente" sem reiluminação.

A seleção é automática em `pipeline.py`:

```python
if modo == "auto":
    modo = "relight" if dev["pode_relight"] else "compose"
```

O usuário pode forçar `--modo compose` ou `--modo relight` explicitamente.

## Justificativa

- **Utilidade imediata sem GPU.** O produto fica funcional em qualquer máquina,
  mesmo sem acelerador.
- **Preview rápido.** O docstring de `composicao.py` menciona explicitamente o
  uso "como preview instantâneo antes do relight pesado" — roda em segundos vs.
  minutos do IC-Light.
- **Mesma interface.** `compor_batch` retorna `{processados, erros, tempo_s}`,
  mesma forma que `aplicar_relighting`, e escreve no mesmo diretório `relit/`.
  O Agente 5 ([[entities/exportacao]]) consome sem distinção.
- **Zero dependência pesada.** Pillow já é dependência de toda a pipeline; não
  adiciona dependência nova.

## Trade-off

A composição CPU não é visualmente equivalente ao relighting:

| | Relighting (IC-Light) | Composição CPU |
|---|---|---|
| Iluminação da pessoa | Recalculada para o novo fundo | Original do vídeo gravado |
| Dependência | GPU CUDA ≥5GB | Qualquer CPU |
| Velocidade | ~1.5s/frame | <50ms/frame |
| Qualidade | Alta (iluminação coerente) | Média (sem coerência de luz) |

Ajustes manuais de brilho/cor (`ajuste_brilho`, `ajuste_cor`) permitem
aproximação grosseira, mas não substituem o relighting físico.

## Relacionados

[[entities/composicao]] · [[entities/relighting]] · [[entities/pipeline]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[decisions/migrate-fc-to-fbc]] · [[index]]
