---
title: composicao — Agente 4b (Composição CPU, sem GPU)
type: entity
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/composicao.py", "pipeline.py"]
tags: [component, agent, composicao, cpu, fallback, pillow]
status: stable
migrated-from: wiki/components/composicao.md
original-date: 2026-06-13
---
# composicao — Agente 4b (Composição CPU, sem GPU)

`agentes/composicao.py` expõe dois callables: `compor_frame` (por frame) e
`compor_batch` (lote completo com resume). Compõe o recorte RGBA da pessoa sobre
o novo fundo via canal alpha em **CPU puro** (Pillow). Não reilumina — a luz da
pessoa permanece a do vídeo original.

## Papel na pipeline

O agente ocupa o slot 4 da [[entities/pipeline]] como **fallback do
[[entities/relighting]]**: quando não há GPU CUDA disponível (ou o usuário força
`--modo compose`), `compor_batch` substitui `aplicar_relighting` e escreve os
mesmos PNGs RGB em `relit/`. O [[entities/exportacao]] consome esses PNGs da
mesma forma independente de qual agente os gerou.

```
frames/nobg/  (RGBA, [[entities/remocao]])
background/bg.png
    ↓ compor_batch
relit/         (RGB compostos, prontos para exportacao)
```

## `compor_frame` — composição de um frame

```python
def compor_frame(
    fg_rgba: Image.Image,
    bg_rgb: Image.Image,
    ajuste_brilho: float = 1.0,
    ajuste_cor: float = 1.0,
) -> Image.Image:
```

### Algoritmo passo a passo

1. **Normalização de modo:** converte `fg_rgba → RGBA`, `bg_rgb → RGB`.
2. **Cover-crop do fundo** (ver [[concepts/agent-composition-export-cover-crop]]):
   - Lê dimensão alvo `(w, h)` do foreground.
   - Calcula `scale = max(w/iw, h/ih)` — escala que garante cobertura total.
   - Redimensiona o fundo com `Image.LANCZOS`.
   - Central-crop: `left = (nw−w)//2`, `top = (nh−h)//2`.
3. **Ajustes opcionais de pessoa** (só aplicados se valor ≠ 1.0):
   - `ImageEnhance.Brightness(person).enhance(ajuste_brilho)`
   - `ImageEnhance.Color(person).enhance(ajuste_cor)`
   Esses ajustes permitem "casar" levemente a tonalidade da pessoa ao fundo sem IA.
4. **Alpha composite:** converte fundo para RGBA → `base.paste(person, (0,0), person)`.
   O terceiro argumento de `paste` é a máscara; usar o próprio `person` (RGBA)
   como máscara aplica o canal A de `person` como transparência.
5. **Retorno:** converte resultado para `RGB` (descarta o canal alpha).

### Inputs / Outputs de `compor_frame`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `fg_rgba` | `Image.Image` | Frame recortado (RGBA) vindo de `frames/nobg/` |
| `bg_rgb` | `Image.Image` | Imagem de fundo (RGB), pode ter qualquer resolução |
| `ajuste_brilho` | float | Multiplicador de brilho na pessoa. 1.0 = sem mudança |
| `ajuste_cor` | float | Multiplicador de saturação na pessoa. 1.0 = sem mudança |
| **retorno** | `Image.Image` | Frame composto, modo RGB |

## `compor_batch` — lote com resume

```python
def compor_batch(
    frames_nobg_dir: str,
    background_path: str,
    output_dir: str,
    ajuste_brilho: float = 1.0,
    ajuste_cor: float = 1.0,
    log_path: str = None,
    progress_cb=None,
) -> dict:
```

### Comportamento

- Ordena os frames por nome (`sorted`) para processamento determinístico.
- **Resume automático:** `if os.path.exists(output_path): continue` — frames já
  compostos são pulados. Ver [[concepts/video-frame-pipeline]] para implicações.
- Erro por frame é capturado em `try/except` e acumulado em `erros: list[dict]`.
- Se `log_path` é fornecido e há erros, persiste `composicao_erros` no JSON
  (merge com conteúdo preexistente do log).
- `progress_cb(i+1, len(frames))` chamado após cada frame (inclusive os pulados).
- Retorna `{processados, erros, tempo_s}` — mesmo shape que [[entities/relighting]]
  para uniformidade no `pipeline_log.json`.

### Gotcha de resume e RVM

O mecanismo de resume é seguro para este agente porque a composição é
**stateless por frame** — cada frame é independente. Isso contrasta com o
[[entities/render-video]] (modo RVM offline), onde o estado recorrente do RVM
deve processar frames em sequência sem pular — lá o resume pode introduzir
artefatos de borda temporal.

## Parâmetros-chave resumidos

| Param | Default | Nota |
|---|---|---|
| `ajuste_brilho` | 1.0 | 1.0 = sem mudança |
| `ajuste_cor` | 1.0 | 1.0 = sem mudança |
| `log_path` | None | Se None, erros são só impressos, não persistidos |
| `progress_cb` | None | Callback `(atual, total)` para UI (Gradio) |

## Modo no Gradio

No `app.py` este agente é o motor do modo **"Compor (rápido, CPU)"**
(`MODO_COMPOR`): rembg + composição. O modo **"Trocar fundo HD (RVM, CPU)"**
([[entities/render-video]]) oferece melhor qualidade de borda usando RVM, mas
sem reiluminação. Ambos são alternativas sem GPU ao [[entities/relighting]].

## Relacionados

[[entities/remocao]] · [[entities/relighting]] · [[entities/exportacao]] ·
[[entities/live-mode]] · [[entities/render-video]] ·
[[concepts/agent-composition-export-cover-crop]] ·
[[concepts/agent-composition-export-alpha-composite]] ·
[[concepts/video-frame-pipeline]] · [[concepts/gpu-vram-local-vs-colab]] ·
[[decisions/agent-composition-export-cpu-fallback]] · [[index]]
