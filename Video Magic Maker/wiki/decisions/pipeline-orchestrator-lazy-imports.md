---
title: "Decisão: imports de agentes dentro de main() (lazy, por etapa)"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["pipeline.py"]
tags: [decision, orchestrator, pipeline, imports, startup, gpu]
status: inferred
---
# Decisão: imports de agentes dentro de main() (lazy, por etapa)

> ⚠️ Esta decisão foi inferida a partir do código. Não há ADR ou comentário explícito justificando o padrão.

## Contexto

`pipeline.py` não importa os módulos de agente no topo do arquivo. Em vez disso, cada import ocorre imediatamente antes do uso, dentro de `main()`:

```python
# Agente 1
from agentes.extracao import extrair_frames
meta = extrair_frames(...)

# Agente 2
from agentes.remocao import remover_fundo
result_rembg = remover_fundo(...)

# Agente 3 (somente no caminho de fundo por IA)
from agentes.geracao_fundo import iniciar_comfyui, gerar_fundo
...

# Agente 4a
from agentes.relighting import carregar_iclight, aplicar_relighting
...
# OU
from agentes.composicao import compor_batch
...

# Agente 5
from agentes.exportacao import exportar_video
...
```

## Decisão

Importar agentes lazily, dentro da função `main()`, no ponto de uso — não no topo do módulo.

## Justificativas prováveis

**1. Custo de startup de GPU/ML pesado**
`agentes/relighting.py` importa `torch`, `diffusers`, `safetensors` e `numpy` no nível de módulo. Importar no topo carregaria esses pacotes mesmo em execuções que usam `--modo compose` (sem GPU). Com lazy import, uma execução `--modo compose` nunca toca `torch` ou `diffusers`.

**2. Caminho condicional real**
O Agente 3 (geração por IA) só é executado quando `--background` está ausente. O Agente 4 é sempre `relighting` OR `composicao`, nunca ambos. Um import no topo de `relighting` e `composicao` carregaria os dois módulos mesmo que apenas um seja usado — desperdiçando VRAM e tempo.

**3. Compatibilidade com ambientes sem dependências opcionais**
Em um ambiente sem `torch`/`diffusers` instalados (máquina local simples querendo apenas modo `compose`), um import no topo falharia imediatamente com `ImportError`. O lazy import permite que a pipeline rode até o ponto onde o módulo é necessário, que pode ser nunca para modo `compose`.

## Consequências

- **Positivo**: startup imediato do script; sem carregamento de GPU se não necessário; sem `ImportError` por dependências ausentes em caminhos não usados.
- **Negativo**: erros de import são detectados tarde (durante a execução, não no início); ferramentas de análise estática (linters, mypy) podem não detectar problemas de import facilmente.
- **Neutro**: o padrão é consistente para todos os 5 agentes, tornando o código previsível mesmo que seja diferente da convenção PEP 8 de imports no topo.

## Alternativas não escolhidas

- Import condicional no topo com `try/except ImportError` (mais verboso, mesma semântica).
- Verificação de disponibilidade de GPU antes de importar `torch` (mais complexo).
- Import sempre no topo + verificação de modo antes do uso (carrega módulos desnecessários).

## Relacionados

[[entities/pipeline]] · [[concepts/pipeline-orchestrator-mode-selection]] ·
[[concepts/pipeline-orchestrator-call-sequence]] · [[index]]
