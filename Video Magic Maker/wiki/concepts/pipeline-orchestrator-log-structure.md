---
title: pipeline_log.json — estrutura e contrato
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["pipeline.py"]
tags: [concept, orchestrator, pipeline, logging, json]
status: stable
---
# pipeline_log.json — estrutura e contrato

`pipeline_log.json` é o único artefato de saída estruturado do orquestrador além do vídeo final. Escrito uma única vez ao final da execução bem-sucedida em `{base}/pipeline_log.json`.

## Estrutura completa

```json
{
  "etapas": [
    {"etapa": "extracao",       "fps": 29.97, "total_frames": 900,
                                "width": 1920, "height": 1080, "tempo_s": 3.12},

    {"etapa": "remocao_fundo",  "processados": 898, "erros": 2, "tempo_s": 270.1},

    {"etapa": "fundo",          "modo": "proprio"},
    // OU:
    {"etapa": "fundo",          "modo": "ia"},

    // Agente 4 — um dos dois:
    {"etapa": "relighting",     "processados": 896, "erros": 4,
                                "tempo_s": 1350.0, "largura": 1920, "altura": 1080},
    // OU:
    {"etapa": "composicao",     "processados": 898, "erros": 0, "tempo_s": 45.2},

    {"etapa": "exportacao",     "output": "<base>/output/video_final.mp4",
                                "tempo_s": 8.4}
  ],
  "erros_total": 6,
  "device": {
    "device": "cuda",
    "cuda": true,
    "gpu_name": "NVIDIA GeForce RTX 3080",
    "vram_gb": 10.0,
    "pode_relight": true
  },
  "modo": "relight",
  "tempo_total_s": 1680.5
}
```

## Campos de nível raiz

| Campo | Tipo | Descrição |
|---|---|---|
| `etapas` | list[dict] | lista ordenada, uma entrada por etapa executada |
| `erros_total` | int | soma de `erros` das etapas que retornam esse campo (remoção + relighting/composição) |
| `device` | dict | snapshot de `detectar_device()` capturado no início da execução |
| `modo` | str | modo final efetivo (`"relight"` ou `"compose"`) após qualquer fallback |
| `tempo_total_s` | float | elapsed desde antes da Etapa 1 até após a Etapa 5 |

## Observações sobre escrita

- O log é **construído em memória** durante a execução em `pipeline_log["etapas"]`.
- Escrito uma única vez em `json.dump(..., indent=2)` ao final — **não há escrita incremental**.
- Se a pipeline abortar em qualquer etapa (exceção não tratada), o log **não é escrito** — o arquivo anterior (de uma execução anterior) permanece inalterado ou o arquivo não existe.
- Os agentes de remoção e relighting escrevem **erros individuais de frame** no mesmo arquivo durante a execução (`remocao_fundo_erros`, `relighting_erros`) via merging de JSON — esses campos coexistem com a estrutura `etapas` final no mesmo arquivo.

## Campos de erros de frame (escritos durante execução)

Os agentes 2 e 4 (via `log_path`) escrevem erros de frames em formato diferente durante a execução, **antes** da escrita final do orquestrador:

```json
{
  "remocao_fundo_erros": [
    {"frame": "frame_00042.png", "erro": "...mensagem..."}
  ],
  "relighting_erros": [
    {"frame": "frame_00099.png", "erro": "...mensagem..."}
  ]
}
```

O orquestrador carrega o conteúdo existente do arquivo antes de escrever (`json.load` + merge), então esses campos são preservados no log final ao lado de `etapas`.

## Gotchas

- A ausência do arquivo pode indicar que a pipeline abortou antes de completar — não necessariamente que nunca rodou.
- `erros_total` conta apenas os agentes por-frame (2 e 4); os agentes 1, 3 e 5 abortam por exceção e nunca incrementam o contador.
- O `modo` em `pipeline_log` reflete o modo **final** (após fallback), não o argumento CLI `--modo`.
- `device` captura o estado da GPU no início — se a VRAM mudar durante a execução (outro processo), o log não reflete isso.

## Relacionados

[[entities/pipeline]] · [[entities/pipeline-orchestrator-config]] ·
[[concepts/pipeline-orchestrator-call-sequence]] · [[concepts/video-frame-pipeline]] · [[index]]
