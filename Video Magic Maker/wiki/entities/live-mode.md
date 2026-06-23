---
title: live-mode — Modo Live (troca de fundo em tempo real)
type: entity
created: 2026-06-14
updated: 2026-06-14
sources: ["live.py"]
tags: [component, live, realtime, matting, virtualcam, mediapipe]
status: stable
migrated-from: wiki/components/live-mode.md
original-date: 2026-06-13
---
# live-mode — Modo Live (troca de fundo em tempo real)

`live.py` (CLI) + `agentes/matting_live.py` (classe `LiveMatter` + helpers
`baixar_modelo`, `carregar_fundo`, `cobrir`, `fundo_desfocado`, `VideoFundo`).
Troca o fundo de uma webcam **em tempo real** e expõe o resultado como **câmera
virtual** para OBS / Google Meet / Zoom / streaming.

> **Fundo pode ser imagem OU vídeo.** Além de imagem fixa (cover-crop via `cobrir`)
> e desfoque da própria cena, o fundo pode ser um **vídeo em loop**. O helper
> `VideoFundo` (`agentes/matting_live.py`) abre um arquivo de vídeo
> (`cv2.VideoCapture`); `proximo()` devolve o próximo frame **cover-cropped**
> (`cobrir`) ao tamanho w×h e, ao chegar no fim, faz `cap.set(CAP_PROP_POS_FRAMES, 0)`
> e volta ao início (loop infinito); `.close()` libera o `VideoCapture`. Usado como
> **fundo animado** na GUI ([[entities/camera-app]]) e no render offline
> ([[entities/render-video]]).

> **Dois motores de recorte.** O matting tem dois backends selecionáveis: o
> **MediaPipe** ([[concepts/realtime-matting]], `LiveMatter`, rápido, default) e o
> **RVM** ([[concepts/rvm-matting]], `RVMMatter` em `agentes/matting_rvm.py`,
> alpha matte verdadeiro — mantém cabelo, sem bolhas no ombro, sem halo, ~9.6fps@540p).
> Escolha por `--engine {mediapipe,rvm}` no CLI (default `mediapipe`) ou pelo
> dropdown "Motor de recorte" na GUI ([[entities/camera-app]]). `RVMMatter.compor`
> é **drop-in** com `LiveMatter.compor` (ignora `refine/threshold/erode/abertura`),
> então o resto do pipeline não muda.

> **Distinção-chave vs modo studio (offline).** O live faz **matting +
> composição** (+ opcional color-match leve). **NÃO** reilumina com IC-Light
> ([[entities/relighting]]) — relight real por frame é inviável a 30fps em 4GB
> de VRAM. A qualidade de relight fica só no modo gravado/offline. É a arquitetura
> honesta de dois modos. Ver [[concepts/realtime-matting]].

## O que faz
Pipeline por frame (`LiveMatter.compor`):
1. **Webcam** via `cv2.VideoCapture` (`CAP_DSHOW` no Windows).
2. **Máscara** via [[concepts/realtime-matting|MediaPipe Tasks ImageSegmenter]]
   (Selfie Segmenter) → `LiveMatter.mask` (confidence mask + suavização temporal).
   No motor **RVM** ([[concepts/rvm-matting]]) este passo é um **alpha matte real**
   já limpo (estado recorrente entre frames) e os passos 3–4 abaixo **não rodam**.
3. **Refino de borda** (novo, opcional `refine=True`), aplicado **depois** da
   confidence mask e **antes** do composite:
   - `refinar_borda()` — **guided filter** (`cv2.ximgproc.guidedFilter`,
     opencv-contrib) usando o frame BGR como guia; **roda em meia resolução**
     (`escala=0.5`) para manter o tempo real. Cola a máscara nos contornos reais
     (cabelo, ombro) e elimina o "halo" (vazamento de fundo na borda). Sem
     opencv-contrib, cai num `cv2.bilateralFilter` edge-aware.
   - `_maior_componente()` — limpeza por **componentes conexos**: mantém só
     componentes com área ≥ 10% da maior, removendo ilhas flutuantes (falsos
     positivos do segmentador).
4. **Pós-processo da máscara:** binariza no `threshold` (default **0.6**) →
   `_maior_componente` → `erode` (default **2px**, mata o anel de halo residual e
   a franja de fundo claro) → `feather` (gaussian, default **3px**) → clip. O `threshold` 0.6
   descarta sozinho as **bolhas de baixa confiança** (~0.55) que o segmentador
   gruda no ombro/braço (fundo original marcado como pessoa, ligado ao corpo —
   componentes conexos não pegam). O corpo real fica ~1.0, então 0.6 não o afina.
   `abertura` (abertura morfológica) existe mas é **default 0 (off)**: ela corta
   protuberâncias finas, mas também come features reais do rosto (queixo, nariz,
   cabelo) — ver Gotchas.
5. **Composição** da pessoa sobre o fundo: imagem (cover-crop, `cobrir`), **vídeo
   em loop** (`VideoFundo.proximo()`, um frame por frame de saída) ou a própria cena
   desfocada (`fundo_desfocado`, `--blur`).
6. **Color-match leve** opcional (casa a cor da pessoa ao fundo; **sem IC-Light**).
7. **Câmera virtual:** `pyvirtualcam.Camera` (envia BGR) → **OBS Virtual Camera**.

## Inputs / Outputs
- **Inputs:** webcam (`--camera/-c`), imagem de fundo (`--background/-b`) **ou**
  `--blur N` (desfoca a própria cena). Modelo `selfie_segmenter.tflite`
  auto-baixado para `models/`.
- **Output:** stream BGR na câmera virtual **OBS Virtual Camera**; opcional janela
  de `--preview`. Em Meet/Zoom/OBS o usuário seleciona "OBS Virtual Camera".

## Parâmetros-chave
| Flag | Default | Nota |
|---|---|---|
| `--background` / `-b` | — | imagem de fundo (cover-crop) |
| `--blur N` | — | desfoca a própria cena em vez de trocar |
| `--camera` / `-c` | — | índice da webcam de entrada |
| `--width` | 960 | largura de captura/saída |
| `--height` | 540 | altura — **540p é o default** (fluidez × nitidez) |
| `--fps` | — | fps alvo |
| `--mirror` | — | espelha horizontalmente |
| `--feather` | — | suaviza a borda da máscara (gaussian) |
| `--suavizar` | — | suavização temporal entre frames |
| `--color-match` | — | casa cor da pessoa ao fundo (leve, sem relight) |
| `--fast` | off | **pula o guided filter** (`refine=False`) → mais fps, borda mais crua |
| `--engine` | `mediapipe` | motor de recorte: `mediapipe` (rápido) ou `rvm` (alpha real, [[concepts/rvm-matting]]) |
| `--preview` | — | abre janela de pré-visualização |
| `--no-virtualcam` | — | desliga a saída para câmera virtual |

### Parâmetros de `compor()` (refino de borda)
| Param | Default | Nota |
|---|---|---|
| `refine` | `True` | guided filter (meia-res) cola a borda nos contornos reais |
| `threshold` | `0.6` | corte da máscara — descarta bolhas de baixa confiança no ombro/braço |
| `abertura` | `0` | abertura morfológica (opt-in) — corta protuberâncias **e** features finas do rosto |
| `limpar_ilhas` | `True` | `_maior_componente`: descarta componentes < 10% da maior área |
| `erode` | `2` | encolhe a máscara N px antes do feather; `erode ≥ feather` empurra a rampa pra dentro do corpo e mata a franja de fundo claro vazando na borda |
| `feather` | `3` | raio do gaussian na borda (px) — **default mudou de 5 → 3** |

`--fast` (CLI) e o checkbox **"Borda alta qualidade"** da UI Gradio (`app.py`)
controlam o mesmo `refine`: marcado = alta qualidade (guided filter ON);
`--fast` = `refine=False`.

### Performance medida (máquina local)
Matting roda em **CPU** via XNNPACK (torch é CPU-only `2.11.0+cpu`; a GTX 1650 Ti
não é usada para o matting). Duas colunas: **refine ON** (borda alta qualidade,
guided filter) vs **refine OFF** (`--fast`):

| Resolução | refine ON (fps) | `--fast` (fps) |
|---|---|---|
| 640×360 | ≈ 33 | ≈ 42 |
| 960×540 (default) | ≈ 15 | ≈ 21 |
| 1280×720 | ≈ 9 | ≈ 13 |

O guided filter **full-res** a 720p custa ~80ms/frame; rodando em **meia-res**
(`escala=0.5`) cai p/ ~20ms — é o que mantém o tempo real com `refine` ligado.

## Gotchas
1. **`.copy()` obrigatório na máscara.** `confidence_masks[0].numpy_view()`
   retorna uma view para memória C++ liberada na chamada seguinte — sem `.copy()`
   imediato o processo dá segfault (access violation `0xC0000005`). Verificado.
2. **Path com acentos quebra o loader.** O loader C++ do MediaPipe falha em paths
   Windows com acento (ex.: "Repositórios"). Fix: carregar o modelo como bytes e
   passar `model_asset_buffer=` em vez de `model_asset_path=`. Verificado.
3. **Console cp1252.** Caracteres não-ASCII (`→`) em `print()` levantam
   `UnicodeEncodeError` no console Windows — usar só ASCII.
4. **Sem `mp.solutions.selfie_segmentation`.** A API legada não existe no build
   slim cp313 do mediapipe (0.10.35); só a **Tasks API** está disponível. Detalhe
   em [[concepts/realtime-matting]].
5. **Câmera virtual = OBS.** O backend no Windows é a **OBS Virtual Camera**: o
   usuário precisa instalar o OBS Studio **uma vez** (registra o dispositivo); não
   precisa estar rodando.
6. **Guided filter exige opencv-contrib.** `cv2.ximgproc.guidedFilter` só existe
   no pacote `opencv-contrib-python` (não no `opencv-python` base). Sem ele,
   `refinar_borda` cai num `cv2.bilateralFilter` (refino mais fraco) — não quebra,
   mas a borda fica menos colada.
7. **Sempre rode o guided filter em meia-res.** Full-res a 720p custa ~80ms/frame
   e derruba o tempo real; `escala=0.5` (~20ms) é obrigatório. A máscara é suave,
   então perde pouco ao escalar.

> **Front-end recomendado:** além do `live.py` (CLI), o live tem uma **GUI desktop**
> em [[entities/camera-app]] (Tkinter) com gravar/foto/galeria, zoom/enquadramento,
> ajustes de imagem e câmera virtual.

> **O mesmo RVM também roda offline.** No modo Studio há o **render offline HD**
> ([[entities/render-video]]) que usa o mesmo `RVMMatter` frame-a-frame num vídeo
> gravado — sem pressão de fps e com coerência temporal (frames em ordem).

## Relacionados
[[entities/camera-app]] · [[concepts/realtime-matting]] · [[concepts/rvm-matting]] ·
[[entities/render-video]] · [[concepts/gpu-vram-local-vs-colab]] ·
[[entities/relighting]] · [[entities/composicao]] · [[entities/remocao]] · [[index]]
