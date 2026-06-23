---
title: Convenções de diretório e nomenclatura de frames
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/extracao.py", "config.py", "app.py", "pipeline.py"]
tags: [concept, paths, frames, workspace, naming, conventions]
---
# Convenções de diretório e nomenclatura de frames

O [[entities/extracao]] grava PNGs num diretório que ele recebe como argumento. A estrutura completa do workspace é definida por `config.py` e usada de forma consistente por todos os agentes.

## Árvore de workspace

```
<base>/
  input/                   # vídeo original (copiado pela UI, não usado pela extração)
  frames/
    raw/                   ← output_dir da extração (frames_raw)
      frame_00001.png
      frame_00002.png
      …
      frame_NNNNN.png
    nobg/                  ← saída da remoção de fundo (RGBA)
      frame_00001.png
      …
  background/
    bg.png                 ← fundo único (gerado ou carregado)
    live_bg.png            ← fundo para modo live (app.py)
  relit/                   ← saída do relighting / composição
    frame_00001.png
    …
  preview/                 ← diretório reservado (não usado ativamente)
  output/
    video_final.mp4        ← vídeo final exportado
  pipeline_log.json        ← log JSON da pipeline
```

## Resolução do `<base>`

`config.py` → `resolver_base()` usa a seguinte prioridade:

| Prioridade | Fonte | Valor |
|---|---|---|
| 1 | argumento `base` explícito | qualquer caminho absoluto |
| 2 | env var `LUMINA_BASE` | qualquer caminho absoluto |
| 3 | Google Colab com Drive montado | `/content/drive/MyDrive/iclight_pipeline` |
| 4 | fallback local | `./workspace` (relativo ao cwd) |

No Colab o workspace fica no Drive para sobreviver a reconexões. Localmente fica em `./workspace` no diretório do projeto.

## Nomenclatura dos frames

Todos os agentes seguem o padrão `frame_%05d.png`:

- Índice base-1: o primeiro frame é `frame_00001.png`, não `frame_00000.png`.
- 5 dígitos zero-padded: suporta até 99.999 frames (~55 minutos a 30fps).
- Extensão `.png`: lossless, RGB 8-bit (via `-pix_fmt rgb24` no ffmpeg).

O padrão é gerado diretamente pelo formato de template do ffmpeg (`%05d`) e consumido por listagem de diretório nos outros agentes. A consistência do nome é a **chave de idempotência** do resume nos agentes downstream (ver [[concepts/video-frame-pipeline]]).

## Acesso ao frame por índice (app.py)

A UI Gradio usa índice base-0 (slider de 0 a N-1) e converte internamente:

```python
def _frame_path(idx: int) -> str:
    return os.path.join(PATHS.frames_raw, f"frame_{idx + 1:05d}.png")
```

Portanto slider em posição `0` → `frame_00001.png`, posição `N-1` → `frame_NNNNN.png`.

## Criação dos diretórios

`config.py` → `Paths.criar_dirs()` cria todos os subdiretórios de uma vez com `os.makedirs(d, exist_ok=True)`:

```python
for d in (
    self.input, self.frames_raw, self.frames_nobg, self.frames_relit,
    self.background_dir, self.preview_dir, self.output_dir,
):
    os.makedirs(d, exist_ok=True)
```

O `extrair_frames()` em si também chama `os.makedirs(output_dir, exist_ok=True)` no início — garantia extra para uso isolado fora do contexto do orquestrador.

## Gotchas

- Se o `frames_raw` não for limpo entre extrações de vídeos diferentes, a contagem de `total_frames` vai incluir frames residuais do vídeo anterior.
- No modo HD do `app.py`, o `render_matting()` limpa `frames_relit` com `shutil.rmtree` antes de processar, para garantir render limpo (estado recorrente do RVM). Isso não se aplica ao `frames_raw`.

## Relacionados

[[entities/extracao]] · [[entities/pipeline]] · [[sources/agent-frame-extraction-config-py]] · [[concepts/video-frame-pipeline]] · [[index]]
