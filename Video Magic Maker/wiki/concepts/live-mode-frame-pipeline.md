---
title: live-mode-frame-pipeline — fluxo de dados por frame no modo tempo real
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["live.py", "agentes/matting_live.py", "agentes/matting_rvm.py"]
tags: [concept, live, pipeline, dataflow, matting, compositing, virtualcam]
---
# live-mode-frame-pipeline — fluxo de dados por frame no modo tempo real

O pipeline em tempo real do [[entities/live-mode]] processa um frame BGR a ~30fps numa sequência fixa de estágios. O caminho exato depende do motor selecionado (MediaPipe vs RVM), mas os pontos de entrada e saída são idênticos.

## Diagrama de sequência — caminho MediaPipe

```
webcam (cv2.VideoCapture / CAP_DSHOW)
  │ BGR uint8 H×W×3
  ▼
[opcional] cv2.flip(frame, 1)          ← --mirror
  │
  ▼
LiveMatter.compor(frame, bg, ...)
  │
  ├─ 1. LiveMatter.mask(frame, suavizar)
  │     ├─ BGR→RGB, mp.Image(SRGB, rgb)
  │     ├─ ImageSegmenter.segment(mp_img)
  │     ├─ confidence_masks[0].numpy_view().copy()  → float32 H×W [0,1]
  │     └─ suavização temporal: m = suavizar*prev + (1-suavizar)*m
  │
  ├─ 2. refinar_borda(m, frame)         ← se refine=True (default)
  │     ├─ reduz frame+máscara a 0.5× (escala)
  │     ├─ ximgproc.guidedFilter(guia=frame_pequeno, src=mask_pequena, r=8, eps=1e-3)
  │     ├─ redimensiona resultado para resolução completa
  │     └─ fallback: cv2.bilateralFilter se opencv-contrib ausente
  │
  ├─ 3. Binarizar + limpar máscara
  │     ├─ alpha = (m > threshold).astype(float32)   [threshold=0.6]
  │     ├─ [opcional] MORPH_OPEN (abertura, default desligado)
  │     ├─ _maior_componente(alpha)                   ← limpar_ilhas=True
  │     ├─ cv2.erode(alpha, elipse, erode=2px)
  │     └─ cv2.GaussianBlur(alpha, feather=3px)
  │         → alpha H×W×1 float32 [0,1]
  │
  ├─ 4. [opcional] _color_match(pessoa, bg, alpha, forca)
  │
  └─ 5. Composição
        out = pessoa * alpha + bg * (1 - alpha)  → uint8 H×W×3 BGR
  │
  ▼
[opcional] cv2.putText overlay fps      ← somente --preview
  │
  ├─▶ pyvirtualcam.Camera.send(out)     ← câmera virtual (OBS)
  │   cam.sleep_until_next_frame()
  │
  └─▶ cv2.imshow(out)                   ← janela --preview (ESC sai)
```

## Diagrama de sequência — caminho RVM

```
frame BGR da webcam
  │
  ▼
RVMMatter.compor(frame, bg, color_match, feather)
  │
  ├─ 1. _infer(frame)
  │     ├─ BGR→RGB float32/255
  │     ├─ torch.from_numpy → [1,C,H,W]
  │     ├─ model(src, *rec, downsample_ratio=0.4) → fgr, pha, *rec
  │     ├─ fgr: [1,C,H,W] → HxWx3 RGB [0,1] → BGR float *255 (ascontiguousarray)
  │     └─ pha: [1,1,H,W] → HxW float .copy()
  │         → (fgr_bgr float, pha float H×W)
  │
  ├─ 2. [opcional] cv2.GaussianBlur(pha, feather=1px)
  │
  ├─ 3. [opcional] _color_match (importado de matting_live)
  │
  └─ 4. Composição usando foreground DESCONTAMINADO
        out = fgr * alpha + bg * (1 - alpha)   → clip → uint8
```

Diferença principal: o RVM pula todo o pós-processamento morfológico (passos 2–3 do caminho MediaPipe) porque o alpha matte já sai limpo. Também compõe usando o **foreground descontaminado** (`fgr`) em vez do frame cru — isso elimina a aura branca nas bordas do cabelo causada pela contaminação de cor do fundo antigo.

## Seleção da fonte de fundo

O argumento `bg` passado ao `compor()` varia conforme o modo:

| Flag em `live.py` | Cálculo do fundo |
|---|---|
| `--background <caminho>` | `carregar_fundo(caminho, w, h)` — carregado uma vez antes do loop, reutilizado a cada frame |
| `--blur N` | `fundo_desfocado(frame, N)` — calculado a cada frame a partir do frame atual |
| Fundo em vídeo (GUI) | `VideoFundo.proximo()` — um frame avançado por iteração do loop |

Ver [[entities/live-mode-background-helpers]] para a implementação dos helpers.

## Estado que persiste entre frames

| Objeto | O que armazena |
|---|---|
| `LiveMatter._prev_mask` | Máscara de confiança do frame anterior para suavização temporal |
| `RVMMatter.rec` | Quatro tensores de estado recorrente (estados ocultos GRU) — resetado se a resolução mudar |
| `RVMMatter._last_shape` | Shape do frame anterior para detectar mudança de resolução |
| `bg_img` (local em live.py) | Array do fundo estático pré-carregado (imutável, reutilizado) |

## Limpeza de recursos (bloco finally)

`live.py` envolve o loop em `try/except KeyboardInterrupt / finally`:

```python
finally:
    cap.release()
    matter.close()
    if cam is not None:
        cam.close()
    if a.preview:
        cv2.destroyAllWindows()
```

`matter.close()` chama `ImageSegmenter.close()` (MediaPipe) ou é no-op (RVM — o modelo torch não tem release explícito).

## Relacionados
[[entities/live-mode]] · [[entities/live-mode-cli]] · [[entities/live-mode-virtual-camera]] · [[entities/live-mode-background-helpers]] · [[concepts/realtime-matting]] · [[concepts/rvm-matting]] · [[concepts/live-mode-edge-refinement]] · [[index]]
