---
tags: [component, render, offline, matting, rvm, cpu, studio]
date: 2026-06-13
status: stable
source: agentes/render_video.py
---

# render-video — Render offline (RVM/MediaPipe), troca de fundo sem GPU

`agentes/render_video.py` — **render offline** que recorta a pessoa de cada frame
com o **motor de matting do live** (RVM ou MediaPipe — [[concepts/rvm-matting]] /
[[concepts/realtime-matting]]) e compõe sobre o novo fundo. **Não usa rembg**
([[components/remocao]]) e **não reilumina** (sem IC-Light) — troca o fundo com
recorte limpo. Tem **duas funções de entrada**:

| Função | Entrada | Saída | Áudio | Usado por |
|---|---|---|---|---|
| `render_matting(...)` | **diretório de frames** `*.png` | PNGs compostos num dir | — (áudio no `exportar_video` depois) | modo Studio (`app.py`) |
| `render_arquivo(...)` | **arquivo de vídeo** (lê direto, sem extrair frames) | um **mp4** | **remuxa o áudio original** | botão 🎬 do [[components/camera-app]] |

Ambas compartilham `_build_matter(engine, dr=None)` e `_VIDEO_EXT`.

> **Qualidade no offline: `fgr` descontaminado + `_dr_qualidade`.** O render herda
> as duas melhorias de qualidade do RVM ([[concepts/rvm-matting]]): (1) o `compor()`
> usa o **foreground descontaminado** `fgr` (não o frame cru) → mata a **aura branca
> do cabelo** na borda; (2) quando `engine=="rvm"`, ambas as funções passam um
> **`downsample_ratio` maior** via `_dr_qualidade(w,h) = clamp(720/max(w,h), 0.35,
> 0.7)` para `_build_matter(engine, dr=...)`, mirando a rede coarse em **~720px**
> (mais detalhe de cabelo) em vez dos ~512px do default 0.4 do live. Ex.: 720p → dr
> ≈ 0.56, 1080p → dr ≈ 0.375. Como o render é offline (sem pressão de fps), vale o
> custo. Verificado: render RVM com `fgr` + dr de qualidade funciona, áudio preservado.

É o caminho **"poderoso, sem GPU"** (`app.py` Studio e o app de câmera): borda
melhor que o [[components/composicao|compor]] (rembg) e dispensa a GPU/Colab do
relight IC-Light ([[components/relighting]]).

## `render_matting` — render a partir de um diretório de frames
`render_matting(frames_dir, background_path, output_dir, engine="rvm",
color_match=0.12, feather=2, progress_cb=None)`:
1. Lê os frames `*.png` de `frames_dir` em ordem (`sorted`).
2. **Fundo de imagem ou de vídeo.** Se `background_path` termina em extensão de
   vídeo (`_VIDEO_EXT = .mp4/.mov/.avi/.mkv/.webm`), abre um `VideoFundo`
   ([[components/live-mode]]) e **avança 1 frame de fundo por frame de saída**
   (loop se o vídeo de fundo for mais curto que o clipe). Caso contrário, faz
   **cover-crop** do fundo de imagem (`cobrir`, de `agentes/matting_live.py`) para
   o tamanho do 1º frame, fixo para todos os frames (como antes).
3. Constrói o motor via `_build_matter(engine, dr=_dr_qualidade(w,h))` quando
   `engine=="rvm"` (`RVMMatter` com ratio de qualidade; senão `LiveMatter`) e,
   **para cada frame em ordem**, chama `matter.compor(frame, bg, color_match,
   feather)` → grava o PNG resultante. O `compor` do RVM usa o foreground
   descontaminado `fgr` ([[concepts/rvm-matting]]).
4. `matter.close()` ao final; imprime `processados`/`tempo_s`/`fps`.

> **Coerência temporal — vantagem do offline.** O RVM é um matter de **vídeo** com
> **estado recorrente** entre frames ([[concepts/rvm-matting]]). Processar os
> frames **em ordem** dá menos tremor de borda — vantagem que o [[components/live-mode|live]]
> (frame-isolado) e o `compor` (rembg, por-frame) **não** têm.

## `render_arquivo` — render direto de um arquivo de vídeo (com áudio)
`render_arquivo(input_path, output_path, engine="rvm", bg_mode="blur",
bg_image_path=None, bg_video_path=None, blur=45, color_match=0.12, refine=True,
progress_cb=None)`. Renderiza um **arquivo de vídeo inteiro** trocando o fundo,
**sem extrair frames em disco** — chamado pelo botão **✅ Aplicar (renderizar
tudo)** do **modo vídeo** do [[components/camera-app]].

1. Abre o vídeo com **`cv2.VideoCapture`** e lê `fps`/`w`/`h`/`total` (`fps` cai pra
   `24.0` se o container não reporta).
2. Constrói o matter via `_build_matter(engine, dr=_dr_qualidade(w,h))` quando
   `engine=="rvm"` (ratio de qualidade mirando ~720px — [[concepts/rvm-matting]]).
   Pré-resolve o fundo conforme `bg_mode`: `video` → `VideoFundo(bg_video_path, w, h)` em loop; `image` → lê a
   **imagem original** do `bg_image_path` com `cv2.imread` e faz `cobrir(raw, w, h)`
   no tamanho **do vídeo**; senão (`blur`) → `fundo_desfocado(frame, blur|1)` por
   frame; `none` → passa o frame cru (sem matting).
3. **Para cada frame** (`cap.read()` em loop): compõe `matter.compor(frame, bg,
   color_match, refine=refine)` e escreve num **mp4 temporário** (`VideoWriter`,
   fourcc **`mp4v`**, `<output>_noaudio.mp4`). `progress_cb(i, total)` por frame.
4. **Remux robusto do áudio original** (passo que o `render_matting` não tem):
   **sempre** roda `ffmpeg -y -i <tmp> -i <input> -map 0:v:0 -map 1:a:0? -c:v copy
   -c:a aac -shortest <output>`. O **`?`** em `-map 1:a:0?` torna o áudio
   **opcional**: se o input tem áudio, entra; se não tem, o ffmpeg **ignora sem
   erro**. Em sucesso, remove o temporário. **Fallback:** se o mux falhar por
   qualquer motivo (`try/except`), `os.replace(tmp, output_path)` entrega ao menos o
   vídeo **sem áudio**.

> **Bug corrigido (áudio).** Antes o áudio era sondado com `ffprobe` + match de
> string (`'"codec_type": "audio"'`) e às vezes falhava → render saía **mudo**
> mesmo com áudio no input. O `-map 1:a:0?` elimina a sonda: o ffmpeg decide sozinho
> se há áudio. Verificado: clipe **com** áudio → render mantém o áudio.

> **Bug corrigido (param de fundo).** O parâmetro era `bg_image_bgr` (imagem já no
> tamanho da câmera, repassada pelo app) e degradava ao reescalar. Agora é
> **`bg_image_path`**: `render_arquivo` lê a imagem **original** (`cv2.imread`) e faz
> `cobrir` no tamanho do **vídeo de entrada** — sem perda por dupla reescala.

> **Diferenças vs `render_matting`:** (a) entrada é **arquivo**, não diretório de
> frames; (b) **escreve mp4** direto (não PNGs); (c) **carrega o áudio** original
> (mux robusto `-map 1:a:0?`); (d) tem o modo de fundo **`blur`** (`fundo_desfocado`
> por frame) e **`none`** (passthrough sem matting), além de imagem/vídeo; (e) usa
> `refine` (repassa ao `compor`) em vez de `feather`. Verificado end-to-end.

## Inputs / Outputs (`render_matting`)
- **Inputs:** `frames_dir` (frames crus, ex. `frames_raw/`), `background_path`
  (imagem `bg.png` **ou** vídeo `.mp4/.mov/.avi/.mkv/.webm` → fundo animado em loop),
  `output_dir`, `engine` (`"rvm"` | `"mediapipe"`), `color_match`, `feather`,
  `progress_cb`.
- **Output:** PNGs RGB compostos em `output_dir`; `dict`
  `{processados, tempo_s, engine}`.

## Parâmetros-chave
| Param | Default | Nota |
|---|---|---|
| `engine` | `"rvm"` | motor de matting; `"rvm"` (alpha real) ou `"mediapipe"` |
| `color_match` | `0.12` | casa levemente a cor da pessoa ao fundo (sem relight) |
| `feather` | `2` | suaviza a borda da máscara (px) |
| `progress_cb` | `None` | `cb(done, total)` por frame — usado pela barra do Studio |

## Performance (medida, CPU)
- **RVM @720p ≈ 2.6 fps** (incl. `imread`/`imwrite`). Mais lento que o live
  (RVM ~9.6fps @540p, [[concepts/rvm-matting]]) por causa da resolução maior + IO,
  mas é **offline** — sem pressão de fps.
- Ex.: 1 min @30fps = **1800 frames ≈ 12 min**.
- **Qualidade:** recorte limpo (rosto/cabelo intactos, sem blob no ombro, sem
  halo) — mesma qualidade do RVM live, verificado num frame renderizado.

## Gotchas
- **Resume reinicia o estado recorrente do RVM.** O loop pula frames já existentes
  na saída — mas isso **zera** a coerência temporal do RVM no ponto retomado. Para
  um **render limpo, apague a saída antes**: o `app.py` faz
  `shutil.rmtree(PATHS.frames_relit)` antes de chamar `render_matting`.
- **Não passa por rembg.** O modo HD recorta direto do **frame cru** e **pula** o
  passo `remover_fundo` ([[components/remocao]]).
- **Não reilumina.** A luz da pessoa continua a do vídeo original (como o
  [[components/composicao|compor]] e o [[components/live-mode|live]]); relight real
  só no modo IC-Light ([[components/relighting]]).
- **Fundo de vídeo em loop.** Se `background_path` for um vídeo (`_VIDEO_EXT`), o
  `VideoFundo` avança 1 frame por frame de saída e **dá loop** quando o vídeo de
  fundo é mais curto que o clipe — então o clipe inteiro sempre tem fundo, mas o
  fundo se repete. Fundo de imagem continua fixo.

## Integração no Studio (`app.py`)
O modo Studio (Gradio) tem **3 modos** — constantes em `app.py`:
- `MODO_HD = "Trocar fundo HD (RVM, CPU)"` — usa este render.
- `MODO_COMPOR = "Compor (rapido, CPU)"` — rembg + [[components/composicao]].
- `MODO_RELIGHT = "Reiluminar (IC-Light, GPU)"` — [[components/relighting]].

Default = `MODO_RELIGHT` se há GPU (`DEV["pode_relight"]`), senão `MODO_HD`.

No modo HD:
- **Preview** (`cb_preview`): recorta o **frame cru** com `_offline_matter()` — um
  `RVMMatter` cacheado, com **`.reset()`** antes (zera o estado recorrente para um
  preview de 1 frame; método novo em `agentes/matting_rvm.py`).
- **Aplicar** (`cb_aplicar`): `shutil.rmtree(frames_relit)` → `render_matting(
  frames_raw, bg_output, frames_relit, engine="rvm", ...)` → `exportar_video`
  ([[components/exportacao]], com o áudio original). **Pula** o `remover_fundo`.

## Integração no app de câmera (`camera_app.py`)
No **modo vídeo** do [[components/camera-app]] (estado `source=="video"`), o vídeo
carregado substitui a câmera na tela principal e o usuário ajusta fundo/motor/
ajustes vendo o frame escolhido ao vivo; ao clicar **✅ Aplicar (renderizar tudo)**
(`_aplicar_render`), chama `render_arquivo(...)` numa thread, passando um
**snapshot** das configs atuais do app (engine, bg_mode, **bg_image_path**/
bg_video_path, blur, refine). Durante o render o app **solta a webcam** (flag
`_rendering`) pra não disputar CPU com o RVM. É a forma de aplicar o mesmo recorte/
fundo do live a um vídeo gravado **com áudio**, sem passar pelo Studio.

## Relacionados
[[concepts/rvm-matting]] · [[components/camera-app]] · [[components/live-mode]] ·
[[components/composicao]] · [[components/exportacao]] · [[components/remocao]] ·
[[components/relighting]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
