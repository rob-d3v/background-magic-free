---
title: Matting em tempo real (MediaPipe Tasks + câmera virtual)
type: concept
created: 2026-06-14
updated: 2026-06-14
sources: ["agentes/matting_live.py"]
tags: [concept, realtime, matting, mediapipe, virtualcam, live]
status: stable
migrated-from: wiki/concepts/realtime-matting.md
original-date: 2026-06-13
---
# Matting em tempo real (MediaPipe Tasks + câmera virtual)

Conceito por trás do [[entities/live-mode]]: segmentar a pessoa de cada frame da
webcam rápido o suficiente para vídeo ao vivo e expor o resultado como câmera
virtual. Esta página é canônica para o **matting live com MediaPipe**; a remoção de
fundo offline (rembg) vive em [[concepts/rembg-background-removal]]. O live também
tem um motor alternativo de **alta qualidade**, **RVM** ([[concepts/rvm-matting]]),
com alpha matte verdadeiro — ver [Próximo passo](#próximo-passo-alpha-matte-real-rvm)
abaixo.

## Por que MediaPipe Tasks (e não rembg / IC-Light)
- **rembg (`u2net_human_seg`)** é preciso porém pesado — bom para o lote offline
  ([[entities/remocao]]), lento demais por frame ao vivo.
- **IC-Light** reilumina, mas relight real por frame é **inviável a 30fps em 4GB
  de VRAM** ([[concepts/gpu-vram-local-vs-colab]]). Por isso o live **não relita**
  — só matting + composição. Relight fica no modo offline ([[entities/relighting]]).
- **MediaPipe Tasks `ImageSegmenter`** (vision) com o modelo **Selfie Segmenter**
  é leve, roda em CPU via XNNPACK e entrega dezenas de fps.

## Modelo e API
- **Selfie Segmenter**: `selfie_segmenter.tflite`, **float16**, ~250KB,
  auto-baixado para `models/` do Google storage (`baixar_modelo`).
- API: **MediaPipe Tasks** `ImageSegmenter` (vision). A saída usada é
  `result.confidence_masks[0]`.
- **A API legada `mp.solutions.selfie_segmentation` NÃO existe** no build slim
  cp313 do mediapipe (**0.10.35**) — só a Tasks API está disponível. Gotcha-chave:
  qualquer tutorial baseado em `mp.solutions` não roda neste ambiente.

## Os três gotchas verificados
1. **Copiar a máscara na hora.** `confidence_masks[0].numpy_view()` é uma **view**
   para memória C++ liberada na próxima chamada do segmenter. Sem `.copy()`
   imediato → segfault (access violation `0xC0000005`). Com `.copy()` → ok.
2. **Path com acento quebra o loader.** O loader C++ falha em paths Windows com
   acento (ex.: "Repositórios"). Fix: ler o `.tflite` como **bytes** e passar
   `model_asset_buffer=` em vez de `model_asset_path=`.
3. **Console cp1252.** `print()` com não-ASCII (`→`) levanta
   `UnicodeEncodeError` no console Windows — usar só ASCII nos logs.

## Pós-processamento da máscara
Confidence mask → **refino de borda** (ver abaixo) → binariza → `erode` → `feather`
(gaussian) → **suavização temporal** entre frames (reduz tremor). Composição:
cover-crop da imagem de fundo (mesma lógica de [[entities/composicao]]) **ou** a
própria cena desfocada (`--blur`). Color-match opcional casa a cor da pessoa ao
fundo (leve, **sem** IC-Light).

## Refino de borda (guided filter + componentes conexos)
A confidence mask do Selfie Segmenter sai **suave e desalinhada** da silhueta real:
borda crua (cabelo/ombro borrados), um **"halo"** (anel de fundo que vaza na borda)
e, às vezes, **ilhas flutuantes** (blobs de falso positivo longe da pessoa). O passo
de refino (`refinar_borda` + `_maior_componente`, em `compor(refine=True)`) corrige
isso **antes** do composite:

1. **Guided filter** (`cv2.ximgproc.guidedFilter`, opencv-contrib) usando o frame
   BGR como guia. Ele "cola" a máscara nas bordas reais da imagem — fixa o cabelo
   e o ombro no contorno verdadeiro e some com o halo. Roda em **meia resolução**
   (`escala=0.5`): a máscara é suave, perde pouco ao escalar, e o custo cai de
   ~80ms (full-res 720p) para ~20ms. Sem opencv-contrib, há **fallback** para
   `cv2.bilateralFilter` (edge-aware, mais fraco, mas não quebra).
2. **Componentes conexos** (`_maior_componente`, `cv2.connectedComponentsWithStats`):
   mantém só componentes com área ≥ **10%** da maior, descartando as ilhas
   flutuantes sem perder partes legítimas grandes (mão erguida, objeto na mão).
3. **Threshold:** binariza em `threshold=0.6`. Isso **sozinho** remove as
   **bolhas de baixa confiança (~0.55)** que o segmentador gruda no ombro/braço —
   fundo original marcado como pessoa, *conectado* ao corpo, então os componentes
   conexos (passo 2) não pegam. No heatmap de confiança o corpo é ~1.0 e as bolhas
   são cyan (~0.55); 0.6 corta as bolhas sem afinar o corpo. Há um parâmetro
   `abertura` (abertura morfológica `MORPH_OPEN`) **desligado por default (0)**:
   ele cortaria protuberâncias finas, mas também come features reais do rosto
   (queixo, nariz, cabelo) — chega a "cortar o rosto" — então não compensa; o
   threshold já resolve a mancha do ombro.
4. Depois: `erode` (default 1px, mata o anel de halo residual) e `feather`
   (gaussian, default **3px** — reduzido de 5 ao ganhar o erode).

**Origem:** o usuário reportou, em iterações: (a) borda crua + halo, (b) um blob
flutuante, (c) uma mancha de fundo grudada no ombro e (d) que a correção de (c)
**cortou o rosto**. Guided filter alinhou a borda e matou o halo; componentes
conexos removeram o blob solto; `threshold` 0.6 removeu a mancha do ombro. A
abertura morfológica que havia sido adicionada junto era a causa de (d) — cortava
features finas do rosto —, então foi **desligada por default**; só o threshold
resolve a mancha sem tocar no rosto.

### Tradeoff qualidade × fps
O refino é o passo mais caro do pipeline live; por isso é **opt-out** via `--fast`
(`refine=False`) / checkbox "Borda alta qualidade" na UI Gradio. Custo medido
(CPU/XNNPACK) com refine **ON** (alta qualidade) vs **OFF** (`--fast`):

| Resolução | refine ON (fps) | `--fast` (fps) |
|---|---|---|
| 640×360 | ≈ 33 | ≈ 42 |
| 960×540 (default) | ≈ 15 | ≈ 21 |
| 1280×720 | ≈ 9 | ≈ 13 |

## Performance (medida, máquina local, CPU/XNNPACK)
Números na tabela **refine ON/OFF** acima. Resumo: os ~42/21/13 fps (640×360 /
960×540 / 1280×720) são o caminho `--fast` (sem guided filter); com refino ligado
caem para ~33/15/9 fps. A GTX 1650 Ti **não** é usada (torch CPU-only
`2.11.0+cpu`); 540p é o default pelo equilíbrio fluidez × nitidez. Ver
[[concepts/gpu-vram-local-vs-colab]].

## Próximo passo (alpha matte real): RVM — FEITO
A confidence mask 256² do Selfie Segmenter tem um **teto de qualidade de borda** em
fundo difícil/claro: mesmo com refino, o rosto/cabelo pode ser "comido" e sobra uma
franja fina. O fix de verdade era trocar por um modelo de **alpha matte real**.
**Feito nesta sessão:** o [[entities/live-mode|live]] ganhou um segundo motor,
**RVM (RobustVideoMatting)** — ver [[concepts/rvm-matting]]. RVM entrega alpha
verdadeiro (mantém cabelo, sem bolhas no ombro, sem halo) ao custo de ~9.6fps@540p
(vs ~15/21 do MediaPipe). É **selecionável** ("Motor de recorte" na GUI
[[entities/camera-app]]; flag `--engine {mediapipe,rvm}` no `live.py`), default
MediaPipe. O pós-processo desta página (guided filter / threshold / erode / abertura)
**não** se aplica ao RVM — o alpha já vem limpo.

## Câmera virtual (pyvirtualcam / OBS)
A saída vai para `pyvirtualcam.Camera` (frames **BGR**). No Windows o backend é a
**OBS Virtual Camera**: instalar o **OBS Studio uma vez** registra o dispositivo
(não precisa estar rodando). Em Meet/Zoom/OBS o usuário seleciona "OBS Virtual
Camera" como webcam.

## Relacionados
[[concepts/rvm-matting]] · [[entities/live-mode]] · [[entities/composicao]] ·
[[entities/relighting]] · [[concepts/rembg-background-removal]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[index]]
