# Log da Wiki — lumina-bg

Log cronológico **append-only**. Formato de cabeçalho: `## [YYYY-MM-DD] <type> | <title>`.
Convenções em [[CLAUDE]]. Nunca edite entradas passadas — apenas acrescente.

---

## [2026-06-13] wiki | Criação da LLM Wiki

Wiki inicializada em `wiki/` seguindo o padrão LLM Wiki: esquema em [[CLAUDE]],
catálogo em [[index]], páginas de componente para os 5 agentes + orquestrador,
páginas de conceito (IC-Light, rembg, SD 1.5, pipeline frame-a-frame, GPU/VRAM)
e duas decisões. Fonte do conhecimento: leitura de `README.md`, `pipeline.py`,
`agentes/*.py`, `plano_iclight_comfyui_colab.md`, `requirements.txt` e
`lumina_bg.ipynb`. Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] bug | Dois bugs no relighting (IC-Light fc)

Registrados em [[components/relighting]] e [[concepts/ic-light]] dois defeitos
verificados no código atual:
1. **Fundo descartado.** `aplicar_relighting` recebe `background_path`, abre `bg`
   e nunca o usa no denoising — só o foreground entra como condição concat. O
   resultado não compõe a pessoa no fundo.
2. **Carregamento de pesos errado.** `pipe.unet.load_state_dict(ic_weights,
   strict=False)`. IC-Light é distribuído como um **offset/delta** que deve ser
   **somado** aos pesos da UNet base do SD 1.5
   (`sd_merged = {k: origin[k] + offset[k]}`, com `strict=True`). Aplicar como
   state_dict direto sobrescreve com deltas, produzindo pesos inválidos.

## [2026-06-13] migration | IC-Light fc → fbc

Decisão registrada em [[decisions/migrate-fc-to-fbc]]. Migrar o relighting de
**fc** (foreground-conditioned, UNet de 8 canais = 4 noisy + 4 fg) para **fbc**
(foreground + background conditioned, UNet de 12 canais = 4 noisy + 4 fg + 4 bg).
O fbc consome o fundo gerado e produz a pessoa **composta diretamente no fundo**,
resolvendo o bug do bg descartado. O fix do offset-merge dos pesos
([[concepts/ic-light]]) vale para ambos. Página [[components/relighting]] marcada
como `status: in-migration`.

## [2026-06-13] decision | Compute split local vs Colab

Registrado em [[decisions/local-vs-colab]] e [[concepts/gpu-vram-local-vs-colab]].
Máquina local (Windows, GTX 1650 Ti 4GB, torch CPU-only, Python 3.13) roda os
passos leves — extração ffmpeg, rembg (CPU) e exportação ffmpeg, todos
verificados localmente nesta sessão. SD 1.5 e IC-Light exigem GPU e rodam no
Colab T4. Uma interface Gradio (GPU-aware, com preview de 1 frame antes do lote)
está sendo adicionada.

## [2026-06-13] wiki | Ingestão do modo Live (troca de fundo em tempo real)

Nova feature ingerida (implementada e testada nesta sessão): `live.py` +
`agentes/matting_live.py`. Webcam → matting → composição → câmera virtual, em
tempo real, para OBS/Meet/Zoom/streaming. Criadas [[components/live-mode]] e
[[concepts/realtime-matting]]; criado stub [[components/composicao]] (Agente 4b,
composição CPU sem relight, que não tinha página e é referenciado). [[index]]
atualizado (nota dos dois modos studio×live + entradas nas categorias).

Fatos verificados: matting via **MediaPipe Tasks `ImageSegmenter`** + **Selfie
Segmenter** (`selfie_segmenter.tflite`, float16, ~250KB, auto-baixado para
`models/`); a API legada `mp.solutions.selfie_segmentation` **não existe** no
build slim cp313 (mediapipe 0.10.35). Três gotchas: (1) `.copy()` obrigatório em
`confidence_masks[0].numpy_view()` ou segfault `0xC0000005`; (2) loader C++ quebra
em path com acento → usar `model_asset_buffer=` (bytes); (3) console cp1252 →
só ASCII. Saída via `pyvirtualcam` → **OBS Virtual Camera** (instalar OBS uma
vez). Perf medida (CPU/XNNPACK, torch 2.11.0+cpu): 640×360 ≈42fps, 960×540 ≈21fps
(default), 1280×720 ≈13fps. **Distinção-chave:** live faz matting + composição
(+ color-match leve), **não** relita com IC-Light — relight real por frame é
inviável a 30fps em 4GB VRAM; relight fica no modo offline ([[components/relighting]]).
Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] fact | Refino de borda no matting live (guided filter + componentes)

Feature implementada e verificada nesta sessão em `agentes/matting_live.py`
`compor()`. Novo passo por frame, **depois** da confidence mask do MediaPipe e
**antes** do composite. Atualizadas [[components/live-mode]] (pipeline, params,
tabela de perf refine ON/OFF, gotchas) e [[concepts/realtime-matting]] (subseção
"Refino de borda" + tradeoff qualidade/fps).

Fatos verificados (contra o código):
1. `refinar_borda()` — **guided filter** (`cv2.ximgproc.guidedFilter`,
   opencv-contrib) com o frame BGR como guia, em **meia-res** (`escala=0.5`):
   cola a borda nos contornos reais e mata o "halo". Fallback p/
   `cv2.bilateralFilter` sem opencv-contrib.
2. `_maior_componente()` — limpeza por componentes conexos, mantém só área ≥ 10%
   da maior (remove ilhas flutuantes / falso positivo).
3. Depois: `erode` (default 1px, mata anel de halo) → `feather` gaussian (default
   **3px**, antes 5).
Novos params de `compor()`: `refine=True`, `erode=1`, `limpar_ilhas=True`,
`feather=3`. `live.py` ganhou `--fast` (= `refine=False`); UI Gradio (`app.py`)
ganhou checkbox "Borda alta qualidade".

Perf medida (CPU), refine ON / `--fast`: 640×360 ≈33/42 · 960×540 ≈15/21 ·
1280×720 ≈9/13 fps. Guided filter full-res a 720p ~80ms; a meia-res ~20ms — daí
`escala=0.5`. Motivação: usuário reportou borda crua + blob flutuante; guided
filter resolveu halo/alinhamento, componentes conexos removeram o blob. Nenhum
arquivo fora de `wiki/` foi modificado.

## [2026-06-13] fact | Mancha de fundo no ombro (threshold + abertura)

Segunda iteração de borda após o usuário apontar uma **mancha de fundo grudada no
ombro** (não era cabelo). O heatmap de confiança da máscara mostrou o corpo ~1.0 e
as bolhas no ombro/braço em cyan (~0.55) — fundo original marcado como pessoa e
*conectado* ao corpo, logo invisível para `_maior_componente`. Fix em `compor()`:
`threshold` 0.5 → **0.6** (corta a baixa confiança) + **abertura morfológica**
(`MORPH_OPEN`, novo param `abertura=3`) antes da limpeza de ilhas/erode/feather.
Atualizadas [[components/live-mode]] e [[concepts/realtime-matting]]. Custo desprezível
(720p ainda ~9fps). `--fast` também herda o fix (só pula o guided filter).

## [2026-06-13] fact | Abertura morfológica cortava o rosto — desligada

O usuário reportou que o fix anterior (threshold 0.6 + `abertura=3`) **cortou o
rosto**. Diagnóstico por varredura de parâmetros (threshold × abertura × erode) com
zoom no rosto e no ombro: a **abertura morfológica `MORPH_OPEN`** corta features
finas reais (queixo, nariz, mecha) além das protuberâncias. O `threshold` 0.6
**sozinho** já remove a mancha de baixa confiança (~0.55) do ombro. Mudança em
`compor()`: `abertura` default 3 → **0** (opt-in). Rosto preservado, ombro limpo,
~9.6fps @720p. Atualizadas [[components/live-mode]] e [[concepts/realtime-matting]].

## [2026-06-13] fact | Franja de fundo claro na borda do ombro — erode 1→2

Inspeção com zoom (3×) no ombro direito mostrou uma **franja branca** seguindo o
contorno. Conferido contra o frame original: o fundo ali é um quarto claro/cheio
(closet, cama) — ou seja, a franja é **fundo claro vazando** pela rampa soft da
alpha, não um brilho real do ombro. Como `feather` (3) > `erode` (1), a rampa
estendia pra FORA, pegando o rolo claro. Fix: `erode` default 1 → **2** (rampa
fica dentro do corpo). Reduz a franja sem cortar rosto (erode é uniforme e leve,
≠ abertura morfológica). **Teto residual:** sobra uma franja fininha — limite do
MediaPipe (256²) em fundo claro de baixo contraste; o fix real é migrar pra
**RVM** (matting com alpha verdadeiro), registrado como próximo passo possível em
[[concepts/realtime-matting]].

## [2026-06-13] wiki | Ingestão do app de câmera GUI (camera_app.py + ajustes.py)

Dois arquivos novos (implementados e verificados nesta sessão): `camera_app.py`
(raiz) e `agentes/ajustes.py`. Criada [[components/camera-app]] (página de componente
combinada: GUI + ajustes, sem duplicação — a seção "Ajustes de imagem" é a canônica
de `ajustes.py`). [[index]] atualizado (entrada em Components, nota CLI×GUI nos dois
modos, e duas linhas em Sources). Linka para [[components/live-mode]] e
[[concepts/realtime-matting]].

Fatos verificados (contra o código):
- **GUI Tkinter + PIL ImageTk**, front-end recomendado do live acima do `live.py`
  CLI. Arquitetura de **duas threads**: worker (`_loop`, daemon) captura+processa a
  webcam e guarda o último frame BGR em `self._frame` sob `threading.Lock`; a main
  thread (`_tick`, `root.after(33,...)`) só exibe — **`ImageTk.PhotoImage` só pode
  ser criado na main thread** (Tkinter não é thread-safe). Estado setado por
  callbacks (main), lido pelo worker.
- Reúsa `LiveMatter`, `cobrir`, `fundo_desfocado` (`agentes/matting_live.py`) e
  `aplicar_ajustes` (`agentes/ajustes.py`). **`aplicar_ajustes` roda DEPOIS da
  composição** (no quadro final, como um app de câmera).
- Controles: dropdown de câmeras; fundo nenhum/desfocado/imagem (file picker);
  espelhar; borda alta qualidade (`refine`, = `--fast`); sliders zoom/enquadrar
  X/Y/brilho/contraste/saturação/nitidez + resetar; **gravar vídeo**
  (`VideoWriter` fourcc `mp4v`) e **tirar foto** (`imwrite`), ambos em
  `<workspace>/galeria/` com timestamp; **abrir galeria** (`os.startfile`); **câmera
  virtual** on/off (`pyvirtualcam`, BGR → OBS Virtual Camera).
- Captura/saída fixas `CAP_W=960, CAP_H=540, FPS=20`.
- `listar_cameras()` usa **pygrabber** (`FilterGraph().get_input_devices()`,
  DirectShow) p/ nomear câmeras SEM abri-las e **exclui a "OBS Virtual Camera"**
  (evita loop de feedback). Fallback: sonda índices 0..3 com cv2. Verificado:
  `[(0,'HD User Facing'),(1,'UGREEN Camera')]`.
- `agentes/ajustes.py` `aplicar_ajustes(img, zoom, pan_x, pan_y, brilho, contraste,
  saturacao, nitidez)` em BGR: zoom = center-crop+resize; pan = enquadramento com
  zoom; brilho/contraste via `cv2.convertScaleAbs`; saturação via canal S em HSV;
  nitidez via unsharp mask (`addWeighted` + GaussianBlur).
Gotchas: ImageTk só na main thread; pygrabber é Windows/DirectShow (fallback p/
índices em outros SO); excluir OBS Virtual Camera da entrada; câmera virtual exige
OBS Studio instalado uma vez. Rodar: `python camera_app.py`. Nenhum arquivo fora de
`wiki/` foi modificado.

## [2026-06-13] wiki | Ingestão do motor RVM (RobustVideoMatting) no live

Novo motor de recorte de **alta qualidade** ingerido (implementado e verificado
nesta sessão): `agentes/matting_rvm.py`, classe `RVMMatter`. Alternativa ao
MediaPipe no modo live, selecionável. Criada [[concepts/rvm-matting]]; atualizadas
[[components/live-mode]] (motor selecionável + flag `--engine`), [[components/camera-app]]
(dropdown "Motor de recorte" thread-safe via `_paused`), [[concepts/realtime-matting]]
(o "próximo passo: alpha matte real" foi feito → linka pra RVM) e [[index]] (Concepts
+ descrições + Sources). É o fix de verdade pra borda do MediaPipe.

Fatos verificados (contra o código):
- **Alpha matte verdadeiro** (não confidence mask 256²): mantém cabelo/borda do
  rosto (não "come" o rosto), não cria bolhas de falso-positivo no ombro, sem franja
  de halo. Por isso **não** usa o pós-processo do MediaPipe (guided filter/threshold/
  erode/abertura) — o alpha já vem limpo; só `feather` opcional + `color_match`.
- Modelo **RobustVideoMatting mobilenetv3** via `torch.hub.load("PeterL1n/
  RobustVideoMatting", "mobilenetv3", trust_repo=True)`. Pesos `rvm_mobilenetv3.pth`
  (~15MB) baixados/cacheados pelo torch.hub na 1a carga (~12s). `trust_repo=True`
  obrigatório (senão trava pedindo confirmação interativa).
- **Estado recorrente** `rec=[None]*4` entre frames (coerência temporal, menos
  tremor); reseta `rec` se a resolução do frame mudar. `downsample_ratio=0.4`.
- Fluxo: BGR → RGB `/255` tensor `[1,C,H,W]` → `pha` (alpha) → `.numpy().copy()`
  (copy obrigatório: numpy compartilha memória do tensor liberada ao sair).
- **PERF (CPU, torch 2.12.0): ~9.6fps @960×540** (104ms/frame). Mais pesado que
  MediaPipe (~15 refine ON / ~21 fast no mesmo res).
- **DEPENDÊNCIA: torchvision** (RVM importa `torchvision.models.mobilenetv3`);
  instalá-la subiu torch 2.11→2.12 CPU.
- **Interface drop-in** com `LiveMatter.compor`: `RVMMatter.compor(..., **_ignored)`
  aceita e ignora `refine/threshold/erode/abertura`. Integração: `--engine
  {mediapipe,rvm}` no `live.py` (default mediapipe) e dropdown "Motor de recorte" no
  `camera_app.py` (troca thread-safe via `_paused`).
- **Motivação:** usuário testou o live na webcam real com fundo diferente e o
  rosto/cabelo ficava "comido" na borda — limite do MediaPipe (256² + hacks de
  morfologia agressivos). RVM resolve.
Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] wiki | Ingestão do render offline HD com RVM (modo Studio)

Nova feature ingerida (implementada e verificada nesta sessão): `agentes/render_video.py`
→ `render_matting(frames_dir, background_path, output_dir, engine="rvm",
color_match=0.12, feather=2, progress_cb=None)`. Criada [[components/render-video]];
atualizadas [[concepts/rvm-matting]] (RVM serve live **e** render offline — coerência
temporal brilha no offline; novo método `RVMMatter.reset()`), [[components/live-mode]],
[[components/composicao]] e [[components/exportacao]] (linkbacks), e [[index]]
(Components + Sources + nota dos **3 modos** do studio).

Fatos verificados (contra o código):
- Recorta a pessoa de cada frame com o motor de matting do live (RVM `RVMMatter` ou
  MediaPipe `LiveMatter`, via `_build_matter`) e compõe sobre o fundo (`cobrir` cv2).
  Processa os frames **em ordem** → coerência temporal do RVM (estado recorrente
  entre frames), vantagem que o live (frame-isolado) e o `compor`/rembg não têm.
  **NÃO usa rembg, NÃO reilumina.** É o caminho "poderoso sem GPU".
- **Resume** pula frames já existentes, mas isso reinicia o estado recorrente do RVM
  → pra render limpo apaga a saída antes (`app.py` faz `shutil.rmtree(frames_relit)`).
- **Studio (`app.py`) virou 3 modos:** `MODO_HD="Trocar fundo HD (RVM, CPU)"`,
  `MODO_COMPOR="Compor (rapido, CPU)"`, `MODO_RELIGHT="Reiluminar (IC-Light, GPU)"`.
  Default = Relight se há GPU (`DEV["pode_relight"]`), senão HD. No HD: `cb_preview`
  recorta o frame cru com `_offline_matter()` (RVMMatter cacheado, `.reset()` antes —
  novo método em `matting_rvm.py` que zera `rec`/`_last_shape`); `cb_aplicar` faz
  `rmtree(frames_relit)` → `render_matting(frames_raw, bg_output, frames_relit,
  engine="rvm", ...)` → `exportar_video` (áudio original). O HD **pula** `remover_fundo`.
- **PERF (CPU):** RVM @720p ≈ **2.6fps** (incl. imread/imwrite) — mais lento que o
  live (540p ~9.6fps) por res maior + IO, mas offline (sem pressão de fps). Ex.:
  1 min @30fps = 1800 frames ≈ 12 min. **Qualidade:** recorte limpo (rosto/cabelo
  intactos, sem blob no ombro, sem halo), verificado num frame renderizado.
Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] fact | Fundo de vídeo em loop (live + render offline)

Pequena feature ingerida (implementada e verificada end-to-end nesta sessão): o
fundo pode ser um **vídeo em loop**, tanto no modo live (GUI) quanto no render
offline. Atualizadas [[components/live-mode]] (helper `VideoFundo` na lista de
helpers de `matting_live.py`; fundo pode ser imagem OU vídeo, com o passo de
composição citando `VideoFundo.proximo()`), [[components/camera-app]] (opção de
fundo "Vídeo" + `VideoFundo` no pipeline do worker), [[components/render-video]]
(fundo de vídeo em loop no offline) e [[index]] (entradas de camera-app e
render-video).

Fatos verificados (contra o código):
- Nova classe **`VideoFundo`** em `agentes/matting_live.py`: abre um arquivo de
  vídeo (`cv2.VideoCapture`); `proximo()` devolve o próximo frame **cover-cropped**
  (`cobrir`) ao tamanho w×h; ao chegar no fim faz `cap.set(CAP_PROP_POS_FRAMES, 0)`
  e volta ao início (**loop**); `.close()` libera. Usada como fundo animado.
- **`camera_app.py`:** o radio de fundo ganhou a opção **"Vídeo"** + botão
  "Escolher vídeo de fundo..." (`_pick_bg_video`, `filedialog` mp4/mov/avi/mkv/webm).
  Quando `bg_mode=="video"` o worker chama `self.bg_video.proximo()` a cada frame
  (fallback p/ desfoque se falhar); o `VideoFundo` é fechado no `fechar()`.
- **`agentes/render_video.py`:** `render_matting` detecta se `background_path`
  termina em extensão de vídeo (`_VIDEO_EXT = .mp4/.mov/.avi/.mkv/.webm`) → usa
  `VideoFundo` e avança 1 frame de fundo por frame de saída (loop se o vídeo de
  fundo for mais curto que o clipe). Caso contrário, fundo de imagem fixa como antes.
- Verificado: `VideoFundo` devolve frames e o render compõe a pessoa sobre os
  frames do vídeo de fundo.
Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] fact | `app.py` não tinha bug — só startup lento (~12.5s de import)

Registrado em [[components/pipeline]] (gotcha). O relato de que o `app.py` (UI
Gradio do studio) "demorou / não abriu" **não era um bug**: medido nesta sessão, o
import de `torch` + `gradio` + `diffusers` no topo do arquivo leva **~12.5s** antes
de a UI subir. Não há travamento — após esse import o app sobe e **binda a porta
normalmente**. A demora é só o custo de import. Nenhum arquivo fora de `wiki/` foi
modificado.

## [2026-06-13] fact | App de câmera: render de arquivo (com áudio), toggle de stream e startup instantâneo

Três mudanças verificadas nesta sessão em `camera_app.py` e `agentes/render_video.py`.
Atualizadas [[components/camera-app]] e [[components/render-video]] (+ [[index]]).

1. **Renderizar arquivo de vídeo no app GUI.** Nova função `render_arquivo(
   input_path, output_path, engine="rvm", bg_mode, bg_image_bgr=None,
   bg_video_path=None, blur=45, color_match=0.12, refine=True, progress_cb=None)`
   em `agentes/render_video.py`, **ao lado** do `render_matting` (que opera em dir de
   frames). Lê o vídeo direto com `cv2.VideoCapture` (sem extrair frames), recorta +
   compõe cada frame com o motor escolhido (RVM/MediaPipe) sobre o fundo (`none`
   passthrough / `blur` `fundo_desfocado` / `image` `cobrir` / `video` `VideoFundo`
   em loop), escreve um mp4 temporário (`VideoWriter` `mp4v`, `<out>_noaudio.mp4`) e
   **remuxa o áudio original**: `ffprobe` detecta se há áudio → `ffmpeg -c:v copy
   -c:a aac -map 0:v:0 -map 1:a:0 -shortest`; se não há áudio, só `os.replace`.
   `camera_app.py` ganhou o botão **🎬 Renderizar vídeo...** (`_render_video`): file
   dialog → **snapshot** das configs atuais (engine/bg_mode/bg_img/bg_video_path/
   blur/refine) → roda `render_arquivo` numa **thread daemon** (não congela a UI),
   progresso na status bar (via `root.after(0,...)`), `messagebox` no fim; salva em
   `<base>/galeria/render_<timestamp>.mp4`. Verificado end-to-end (61 frames → mp4
   válido; áudio remuxado quando o input tem áudio).
2. **Toggle de stream claro.** O botão da câmera virtual agora rotula **"🔴 Iniciar
   câmera virtual (stream)"** ↔ **"■ PARAR stream (câmera virtual)"** (antes "Câmera
   virtual"/"Parar virtual", pouco óbvio).
3. **Startup instantâneo + janela pra frente.** O `LiveMatter` agora é criado
   **dentro do worker** (`self.matter = None` no `__init__`, instanciado no topo de
   `_loop`), não mais no `__init__` (que bloqueava ~1.8s no init do MediaPipe). Além
   disso o `__init__` faz `lift()` + `attributes("-topmost", True)` (solto após 900ms
   via `root.after`) + `focus_force()` + `minsize(900,560)` pra a janela **vir pra
   frente** (antes podia abrir atrás de outras). Status inicial "Carregando
   recorte...". Contexto: usuário reportou "não abre" — na verdade abria, mas lento e
   às vezes atrás de outras janelas. Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] fact | App de câmera: cache automático de preferências

Feature verificada nesta sessão em `camera_app.py`. Atualizada
[[components/camera-app]] (nova seção "Cache de preferências"). Toda configuração
do app agora **persiste num JSON** e é **restaurada ao reabrir**.

Fatos verificados (contra o código):
- **Arquivo:** `<workspace base>/camera_app_config.json`
  (`self._cfg_path = os.path.join(self.paths.base, "camera_app_config.json")`).
- **Métodos novos:** `_load_config()` (lê o JSON, `{}` se não existir),
  `_save_config()` (grava o dict atual), `_restaurar_fundo()` (recarrega
  imagem/vídeo de fundo dos caminhos salvos; se o arquivo sumiu, cai pro modo
  "blur").
- **Chaves:** `camera`, `engine`, `bg_mode`, `blur`, `bg_image_path`,
  `bg_video_path`, `mirror`, `refine`, `zoom`, `pan_x`, `pan_y`, `brilho`,
  `contraste`, `saturacao`, `nitidez`.
- **`__init__`:** carrega o cfg **ANTES** de setar os atributos (cada atributo =
  `c.get(chave, default)`); **valida a câmera salva** contra as presentes
  (`salvo_cam if salvo_cam in cam_ids else cams[0]`); `_build_ui` inicializa os
  widgets já com os valores salvos; depois chama `_restaurar_fundo()`.
- **Quando salva:** mudanças discretas (`_on_cam`, `_on_engine`, `_on_bg`,
  `_pick_bg`, `_pick_bg_video`, `_reset`), checkboxes (espelhar/borda), sliders ao
  soltar o botão (`<ButtonRelease-1>` em `_slider`) e no `fechar()` (estado final
  ao sair).
- **Robustez:** leitura/escrita em `try/except` — JSON corrompido ou disco cheio
  não quebra o app (só ignora). Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] fact | Render de vídeo: preview de 1 frame, solta a webcam, áudio robusto

Três correções verificadas nesta sessão no render de vídeo do app de câmera
(`camera_app.py` + `agentes/render_video.py`). Atualizadas [[components/camera-app]]
(seção "Renderizar vídeo" reescrita + gotchas 7/8) e [[components/render-video]]
(`render_arquivo`: assinatura, mux robusto, novos bugs corrigidos + integração).

Fatos verificados (contra o código):
1. **Preview de 1 frame antes de renderizar.** `_render_video` não renderiza direto:
   abre o vídeo, pega o **frame do meio** (`CAP_PROP_POS_FRAMES = total//2`, fallback
   frame 0) e abre um `tk.Toplevel` (`_abrir_preview_render`) com esse frame já
   composto (fundo+ajustes atuais). Botões "↻ Atualizar preview" (recompõe com as
   configs **vivas**), "🎬 Renderizar vídeo todo" (`Accent.TButton`) e "Cancelar". O
   render real só dispara no `_executar_render`. Helpers novos: `_bg_for_frame(frame)`
   (fundo BGR no tamanho do frame: vídeo→1º frame, imagem→`cv2.imread`, senão
   desfoque), `_compose_one(frame)` (fundo + `compor` + `aplicar_ajustes`; reseta o
   estado do RVM), `_fit(img,maxw,maxh)` (escala pra caber, nunca amplia).
2. **Solta a webcam durante o render.** Nova flag `self._rendering`; quando `True` o
   worker (`_loop`) **libera o `cap`** (`cap.release()`, `cap=None`, frame `None`) e
   fica ocioso — a webcam/CPU não competem com o RVM do render (pesado).
   `_executar_render` seta `_rendering=True` antes e `_rendering=False` no `fim()`; o
   worker reabre a câmera sozinho depois.
3. **Áudio corrigido (bug).** `render_arquivo` antes sondava o áudio com `ffprobe` +
   match de string (`'"codec_type": "audio"'`) e às vezes falhava → saída **muda**.
   Agora **sempre** roda `ffmpeg ... -map 0:v:0 -map 1:a:0?` — o `?` torna o áudio
   **opcional** (entra se existir, ignorado sem erro se não). Verificado: clipe com
   áudio → render mantém o áudio. Fallback: mux falhou → `os.replace` entrega o vídeo
   sem áudio. Também: param `bg_image_bgr` → **`bg_image_path`** (`render_arquivo` lê
   a imagem **original** com `cv2.imread` e faz `cobrir` no tamanho **do vídeo** —
   antes recebia a imagem já no tamanho da câmera, o que degradava).
Nenhum arquivo fora de `wiki/` foi modificado.

## [2026-06-13] fact | App de câmera: redesign da UI (tema escuro, painel rolável, vídeo responsivo)

Redesign da UI verificado nesta sessão em `camera_app.py` (resolveu responsividade
ruim — botões sumiam em janela curta — e visual datado). Atualizada
[[components/camera-app]] (nova seção "UI" + `_tick` agora reescala o vídeo).

Fatos verificados (contra o código):
- **Tema escuro (`_setup_style`)**, novo método chamado no início de `_build_ui`:
  ttk `Style` theme **`clam`**; paleta `self.COL` (bg #16161f, panel #20202e, card
  #2c2c40, accent #7c6cf0, rec #e0556b, txt #e6e6f0, mute). Estilos custom
  `Accent.TButton` (roxo, primárias), `Rec.TButton` (vermelho, gravar),
  `Muted.TLabel`, `Status.TLabel`, `TLabelframe`, combobox/scrollbar/checkbutton/
  radiobutton escuros; listbox do combobox colorida via `option_add`.
- **Painel de controles rolável** — `tk.Canvas` + `ttk.Scrollbar` vertical + frame
  interno; bind `<Configure>` ajusta `scrollregion`; roda via `bind_all("<MouseWheel>")`.
  Corrige o bug "botões somem" (antes era grid fixo com contador `r` que clipava).
- **Controles agrupados em `ttk.Labelframe`:** "CÂMERA & MOTOR", "FUNDO", "AJUSTES
  DE IMAGEM", "GRAVAR & STREAM". Layout interno migrou de grid (contador `r`) para
  `pack`.
- **Vídeo responsivo** — `tk.Label` num frame que expande (`grid` +
  `columnconfigure(0, weight=1)`); `_tick` reescala o frame PIL para
  `video.winfo_width()/height()` mantendo proporção (antes fixo 960×540, com espaço
  morto).
- **Geometria** `geometry("1180x720")` inicial, `minsize(760, 520)` (antes
  `minsize(900, 560)`). `_slider` reescrito pack-based (sem o param `row`);
  `tk.Scale` estilizado com a paleta.
- Verificado: import OK; o app constrói a UI e roda sem erro Tk. Nenhum arquivo fora
  de `wiki/` foi modificado.

## [2026-06-13] fact | Render de vídeo virou MODO VÍDEO embutido (sem modal)

O render de vídeo do `camera_app.py` deixou de usar um **modal/Toplevel** e virou
um **MODO VÍDEO embutido na tela principal**. Reescrita a seção de render em
[[components/camera-app]] ("Modo vídeo (editar e renderizar arquivo na tela
principal)", substituindo a antiga "Renderizar vídeo (`_render_video`)" / preview em
Toplevel) e atualizados os gotchas 7/8; ajustados os linkbacks em
[[components/render-video]] (botão e seção de integração).

Fatos verificados (contra o código):
- Novo estado **`self.source`** = `"camera"` | `"video"`. No modo vídeo o arquivo
  carregado **substitui a câmera** na área de preview e a **webcam é solta** — o
  worker `_loop`, com `source=="video"`, faz `cap.release()` (`cap=None`,
  `cur_cam=None`) e passa a ler o `self._vcap` do arquivo; não filma mais.
- **`_carregar_video()`** (botão "🎬 Carregar vídeo (editar)..."): file dialog → lê
  `total` de frames (aborta se `<=0`), seta `source="video"`, `_video_pos=total//2`,
  `_dirty_base=True`; mostra a **barra de vídeo** (`video_bar`, antes `pack_forget`),
  configura o `frame_slider` (range `0..total-1`) e o botão vira "🔁 Trocar vídeo...".
- **Barra de vídeo** (só no modo vídeo): slider de frame (`_video_scrub` →
  `self._video_pos`), botão "✅ Aplicar (renderizar tudo)" (`_aplicar_render`,
  `Accent.TButton`) e "📷 Voltar à câmera" (`_voltar_camera`: volta `source="camera"`,
  solta `_vcap`, `cur_cam=None` p/ reabrir a webcam, esconde a barra).
- **Preview ao vivo no worker** via dois flags: **`_dirty_base`** (refazer o
  recorte — frame/fundo/motor/blur/refine/mirror/pick bg) e **`_dirty_adj`** (só
  reaplicar ajustes). `_compose_base(frame)` faz matte+fundo SEM ajustes (cacheado em
  `_video_base`, reseta o RVM; `bg_mode=="none"` → frame cru); `aplicar_ajustes` por
  cima a cada `_dirty_adj`. Seek (`CAP_PROP_POS_FRAMES`) + `read` quando `_video_pos`
  muda. Assim todo controle atualiza o preview do frame ao vivo sem recortar à toa.
  Callbacks: ajustes (`_set`)/`_reset` → `_dirty_adj`; fundo/motor/blur/refine/mirror/
  pick bg → `_dirty_base`. Status bar: "MODO VÍDEO — <arquivo>  frame X/Y".
- **`_aplicar_render()`**: snapshot das configs, `_rendering=True` (solta a webcam),
  roda `render_arquivo(self.video_path, ...)` em thread daemon, salva em
  `galeria/render_<ts>.mp4`, `messagebox` no `fim()`.
- **Removidos:** `_abrir_preview_render` (Toplevel), `_render_video`,
  `_executar_render`, `_compose_one`, `_fit` — não há mais modal.
- **Motivação:** o modal não deixava trocar o frame nem ver os ajustes aplicados, e
  a câmera continuava filmando atrás; agora tudo é na tela principal, câmera parada.
Nenhum arquivo fora de `wiki/` foi modificado.
