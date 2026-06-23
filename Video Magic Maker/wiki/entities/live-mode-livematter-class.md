---
title: live-mode-livematter-class — LiveMatter, segmentador MediaPipe em tempo real
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/matting_live.py"]
tags: [entity, live, mediapipe, segmenter, class, matting, cpu]
---
# live-mode-livematter-class — LiveMatter, segmentador MediaPipe em tempo real

`LiveMatter` (em `agentes/matting_live.py`) é a classe central do [[entities/live-mode]]: encapsula o `ImageSegmenter` do MediaPipe Tasks e expõe dois métodos públicos — `mask()` para obter a confidence mask por frame, e `compor()` para o pipeline completo de matting + composição.

## Ciclo de vida

```python
matter = LiveMatter()          # __init__: baixa modelo, cria ImageSegmenter
out = matter.compor(frame, bg) # chamado a cada frame no loop
matter.close()                 # libera o ImageSegmenter C++
```

Suporta uso como context manager (`with LiveMatter() as m:`).

## __init__ — inicialização

1. Chama `baixar_modelo()`: baixa `selfie_segmenter.tflite` (~250KB) do Google Storage para `models/` se ainda não existir.
2. Lê o arquivo `.tflite` como **bytes** (`model_asset_buffer=`) em vez de passar o caminho — workaround para o loader C++ do MediaPipe que falha em paths Windows com acentos (ex.: "Repositórios").
3. Cria um `ImageSegmenter` com `RunningMode.IMAGE` (síncrono, não streaming), `output_confidence_masks=True`, `output_category_mask=False`.
4. Inicializa `self._prev_mask = None` para a suavização temporal.

## mask(frame_bgr, suavizar) — confidence mask por frame

Converte BGR → RGB, cria `mp.Image(SRGB, rgb)`, chama `seg.segment()` e extrai `confidence_masks[0].numpy_view()`.

**Gotcha crítico:** `numpy_view()` retorna uma view para memória C++ liberada na próxima chamada do segmenter. O código faz `.copy()` imediato — sem isso o processo dá segfault (`0xC0000005`).

Aplica suavização temporal (EMA):
```python
m = suavizar * self._prev_mask + (1.0 - suavizar) * m   # default 0.55
```
Maior `suavizar` = movimento mais suave de borda, com mais lag de resposta.

Retorna `float32` H×W com valores no intervalo [0, 1].

## compor(frame_bgr, bg_bgr, ...) — pipeline completo

Orquestra seis estágios sobre a máscara retornada por `mask()`:

| Estágio | Implementação | Default |
|---|---|---|
| 1. Confidence mask + EMA | `self.mask(suavizar)` | suavizar=0.55 |
| 2. Guided filter (refino de borda) | `refinar_borda(m, frame)` | refine=True |
| 3. Binarizar no threshold | `m > threshold` | threshold=0.6 |
| 4. Abertura morfológica | `MORPH_OPEN(abertura)` | abertura=0 (off) |
| 5. Limpeza de ilhas | `_maior_componente(alpha)` | limpar_ilhas=True |
| 6. Erosão + feather | `erode=2px`, `feather=3px` | — |

Ver [[concepts/live-mode-edge-refinement]] para o raciocínio por trás de cada estágio.

Composição final:
```python
out = pessoa * alpha + bg_bgr * (1 - alpha)   # float32 → uint8
```

O `color_match` opcional puxa a média de cor da pessoa em direção à média do fundo (sem reiluminação IC-Light).

## Modelo: Selfie Segmenter float16

- URL: `https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite`
- Tamanho: ~250KB
- Resolução interna: ~256² (saída upsampled para a resolução do frame)
- Backend de execução: XNNPACK (CPU) — ver [[concepts/live-mode-cpu-only-path]]
- A API legada `mp.solutions.selfie_segmentation` **não existe** no build slim cp313 do mediapipe (0.10.35); apenas a Tasks API funciona.

## Relacionados

[[entities/live-mode]] · [[entities/live-mode-cli]] · [[concepts/realtime-matting]] · [[concepts/live-mode-edge-refinement]] · [[concepts/live-mode-frame-pipeline]] · [[concepts/live-mode-cpu-only-path]] · [[index]]
