---
title: "Paths e workspace — contexto do Agente 2"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["config.py", "pipeline.py", "agentes/remocao.py"]
tags: [concept, paths, workspace, config, colab, local]
---
# Paths e workspace — contexto do Agente 2

O Agente 2 recebe seus diretórios de entrada e saída via parâmetros, resolvidos por `config.Paths` no orquestrador. Esta página documenta como os paths são construídos e onde os arquivos do agente 2 vivem em disco.

## Paths relevantes para o Agente 2

| Variável | Path padrão (local) | Path padrão (Colab) |
|---|---|---|
| `frames_dir` (input) | `workspace/frames/raw/` | `/content/drive/MyDrive/iclight_pipeline/frames/raw/` |
| `output_dir` (saída) | `workspace/frames/nobg/` | `/content/drive/MyDrive/iclight_pipeline/frames/nobg/` |
| `log_path` | `workspace/pipeline_log.json` | `/content/drive/MyDrive/iclight_pipeline/pipeline_log.json` |

## Como os paths são resolvidos (`config.py`)

`config.Paths` segue esta prioridade:

1. Argumento `--base` na CLI → `os.path.abspath(base)`
2. Env var `LUMINA_BASE` → `os.path.abspath(LUMINA_BASE)`
3. Colab com Google Drive montado → `/content/drive/MyDrive/iclight_pipeline`
4. Fallback local → `./workspace`

O agente 2 recebe os paths já resolvidos — não tem acesso a `config.py` diretamente.

## Estrutura de arquivos gerados

```
<base>/
├── frames/
│   ├── raw/          ← input do Agente 2 (PNGs rgb24 do ffmpeg)
│   │   ├── frame_00001.png
│   │   └── frame_NNNNN.png
│   └── nobg/         ← output do Agente 2 (PNGs RGBA)
│       ├── frame_00001.png  (mesmo nome, canal alpha adicionado)
│       └── frame_NNNNN.png
└── pipeline_log.json ← erros do Agente 2 em "remocao_fundo_erros"
```

## Convenção de nomes de frame

O ffmpeg gera `frame_%05d.png` — cinco dígitos com zero à esquerda.
O Agente 2 lê via `sorted(os.listdir(...))`, que ordena lexicograficamente.
Com 5 dígitos, a ordenação léxica coincide com a cronológica até 99.999 frames
(~55 minutos a 30fps) — suficiente para qualquer caso de uso atual.

## `pipeline_log.json` — estrutura de erros

Quando há erros, o agente 2 escreve ou atualiza a chave `"remocao_fundo_erros"`:

```json
{
  "remocao_fundo_erros": [
    {"frame": "frame_00023.png", "erro": "...mensagem da exceção..."}
  ]
}
```

O arquivo pode já existir com outras chaves (escrito pelo orquestrador ou outros
agentes); `remocao.py` faz merge correto: carrega o JSON existente, adiciona a chave
e reescreve.

## Relacionados

[[entities/agent-background-removal-remocao]] · [[concepts/agent-background-removal-resume]] ·
[[concepts/video-frame-pipeline]] · [[index]]
