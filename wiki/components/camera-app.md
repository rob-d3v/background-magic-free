---
tags: [component, live, realtime, gui, tkinter, virtualcam, ajustes, render]
date: 2026-06-13
status: stable
source: camera_app.py
---

# camera-app — App de câmera ao vivo (GUI Tkinter)

`camera_app.py` (raiz do repo) — front-end **desktop (GUI Tkinter + PIL ImageTk)**
do [[components/live-mode|modo live]]. É o **front-end recomendado do live**, acima
do `live.py` (CLI): troca o fundo da webcam em tempo real ([[concepts/realtime-matting|matting MediaPipe]])
e adiciona os controles de um app de câmera de verdade (gravar, foto, galeria,
zoom/enquadramento, brilho/contraste/saturação/nitidez, câmera virtual).

Reúsa toda a engine do live — `LiveMatter` (matting), `cobrir` / `fundo_desfocado`
de `agentes/matting_live.py` — e os ajustes de imagem de `agentes/ajustes.py`
(documentados na seção [Ajustes de imagem](#ajustes-de-imagem-agentesajustespy)
abaixo). **Não** reilumina com IC-Light (igual ao live; relight por frame é inviável
a 30fps em 4GB — ver [[components/relighting]]).

Rodar: `python camera_app.py`.

## O que faz
**Arquitetura de duas threads** (Tkinter não é thread-safe):
- **Worker thread** (`_loop`, daemon): captura a webcam (`cv2.VideoCapture`,
  `CAP_DSHOW` no Windows), faz matting + composição (`LiveMatter.compor`), aplica
  `aplicar_ajustes`, grava/foto/câmera virtual, e guarda o **último frame BGR**
  processado em `self._frame` sob um `threading.Lock`. **O `LiveMatter` é criado
  DENTRO do worker** (`self.matter = None` no `__init__`, instanciado no topo de
  `_loop`), não mais no `__init__` — assim a **janela abre instantânea** em vez de
  travar ~1.8s no init do MediaPipe (ver [Startup](#startup-janela-instant%C3%A2nea)).
- **Main thread (Tk)** (`_tick`, agendada por `root.after(33, ...)` ≈ 30fps de
  display): só **lê** o frame, **reescala** o frame PIL para o tamanho atual do
  widget de vídeo (proporção mantida — ver [UI](#ui-tema-escuro-painel-rol%C3%A1vel-v%C3%ADdeo-responsivo))
  e o exibe. **`ImageTk.PhotoImage` só pode ser criado
  na main thread** — daí a separação. O estado (zoom, fundo, mirror, etc.) é
  **setado pelos callbacks** dos widgets (main thread) e **lido pelo worker**;
  a sincronização por lock cobre só o frame (o resto são reads/writes atômicos de
  atributos simples).

Pipeline por frame no worker:
1. captura → `cv2.resize` p/ `CAP_W×CAP_H` → `cv2.flip` se `mirror`;
2. fundo: `none` (passa direto) | `blur` (`fundo_desfocado(frame, blur)`) |
   `image` (`self.bg_img`, já em cover via `cobrir`) | `video`
   (`self.bg_video.proximo()` a cada frame — `VideoFundo` em loop, ver
   [[components/live-mode]]; **fallback p/ desfoque** se o frame de vídeo falhar);
3. `matter.compor(frame, bg, color_match=0.12, refine=self.refine)` — `matter` é
   `LiveMatter` ou `RVMMatter` ([[concepts/rvm-matting]]) conforme o "Motor de
   recorte"; a assinatura é a mesma (o RVM ignora `refine`);
4. **`aplicar_ajustes(...)` DEPOIS da composição** (afeta o quadro final, como um
   app de câmera) — ver abaixo;
5. grava (`VideoWriter`), tira foto (`imwrite`), envia p/ câmera virtual.

**Controles da UI:**
- **Câmera** — dropdown (`Combobox`) com as câmeras do PC; trocar de câmera reabre
  o `VideoCapture` no worker (`req_cam != cur_cam`).
- **Motor de recorte** — dropdown (`Combobox`): "MediaPipe (rápido)" ou "RVM
  (qualidade — mantém cabelo)". Troca o backend de matting ([[concepts/rvm-matting|RVM]]
  vs [[concepts/realtime-matting|MediaPipe]]). A troca é **thread-safe**: `_on_engine`
  seta `_paused=True`, instancia o novo matter (RVM baixa o modelo na 1a vez — ver
  Gotchas), troca `self.matter` e religa `_paused=False`; o worker pula frames
  enquanto `_paused`. Em erro, volta o dropdown pro motor atual e mostra `messagebox`.
- **Fundo** — radio Nenhum / Desfocado / Imagem / **Vídeo** + botão "Escolher
  imagem de fundo..." (`filedialog`) + botão **"Escolher vídeo de fundo..."**
  (`_pick_bg_video`, `filedialog` mp4/mov/avi/mkv/webm → abre um `VideoFundo`) +
  slider **Desfoque** (5–75, forçado ímpar via `| 1`). No modo "Vídeo" o worker
  chama `self.bg_video.proximo()` por frame (fundo animado em loop), com fallback
  p/ desfoque se falhar; o `VideoFundo` é fechado no `fechar()`.
- **Espelhar (selfie)** e **Borda alta qualidade** (`refine` on/off — mesmo flag
  que `--fast` no CLI, ver [[components/live-mode]]).
- **Ajustes:** sliders Zoom / Enquadrar X / Enquadrar Y / Brilho / Contraste /
  Saturação / Nitidez + **Resetar ajustes**.
- **Ações:** **● Gravar** (toggle `VideoWriter`), **📷 Foto** (`req_photo`),
  **🔴 Iniciar câmera virtual (stream)** ↔ **■ PARAR stream (câmera virtual)**
  (toggle `req_virtual` — rótulo explícito; antes era "Câmera virtual"/"Parar
  virtual", pouco óbvio), **📁 Galeria** (`os.startfile`) e **🎬 Renderizar
  vídeo...** (`_render_video`, ver [Renderizar vídeo](#renderizar-v%C3%ADdeo-render_video)).
- **Status bar:** fps medido + resolução + indicadores REC / virtual; também
  mostra o progresso do render.

## Inputs / Outputs
- **Inputs:** webcam selecionada no dropdown; opcionalmente uma imagem de fundo
  (file picker). Modelo de matting auto-baixado via `LiveMatter` (ver
  [[components/live-mode]]).
- **Outputs:**
  - **Vídeo** (`video_<timestamp>.mp4`, `cv2.VideoWriter` fourcc **`mp4v`**) e
    **foto** (`foto_<timestamp>.png`, `cv2.imwrite`), ambos em
    **`<workspace>/galeria/`** (`Paths().base + "/galeria"`).
  - **Câmera virtual** opcional: `pyvirtualcam.Camera(..., fmt=PixelFormat.BGR)` →
    **OBS Virtual Camera** (a mesma do `live.py`).
  - **Render de arquivo** (botão 🎬): `render_<timestamp>.mp4` na mesma galeria —
    aplica o fundo/efeitos atuais a um vídeo escolhido (ver abaixo).

## Renderizar vídeo (`_render_video`)
Botão **🎬 Renderizar vídeo...** — aplica o **fundo e o motor atuais** a um
**arquivo de vídeo** inteiro (não só ao stream da webcam) e salva o resultado na
galeria. Fluxo:
1. `filedialog` escolhe o vídeo de entrada (mp4/mov/avi/mkv/webm). Se o fundo está
   em "Nenhum", um `messagebox` confirma (renderiza sem trocar o fundo).
2. **Snapshot das configs atuais** — `engine`, `bg_mode`, `bg_img` (`.copy()`),
   `bg_video_path`, `blur`, `refine` — capturado **antes** de disparar a thread,
   pra o worker do live continuar usando os valores originais sem corrida.
3. Roda `render_arquivo(...)` ([[components/render-video]]) numa **thread daemon
   separada** (não congela a UI). O botão vira "🎬 Renderizando..." e fica
   `disabled`; o progresso aparece na status bar (via `progress_cb` → `root.after(0,
   ...)`, porque só a main thread mexe em widgets).
4. No fim, reabilita o botão e mostra `messagebox` (sucesso ou erro). Saída em
   `<workspace>/galeria/render_<timestamp>.mp4`.

> O `render_arquivo` **remuxa o áudio original** do vídeo de entrada (o stream live
> e a gravação `● Gravar` são mudos). Verificado end-to-end (61 frames → mp4 válido;
> áudio remuxado quando o input tem áudio). Detalhes em [[components/render-video]].

## Cache de preferências
Toda configuração do app **persiste num JSON** e é **restaurada ao reabrir** — não
é preciso reconfigurar câmera/fundo/ajustes a cada sessão.

- **Arquivo:** `<workspace base>/camera_app_config.json`
  (`self._cfg_path = os.path.join(self.paths.base, "camera_app_config.json")`).
- **Métodos:**
  - `_load_config()` — lê o JSON; retorna `{}` se não existir.
  - `_save_config()` — grava o dict atual no arquivo.
  - `_restaurar_fundo()` — recarrega a **imagem/vídeo de fundo** a partir dos
    caminhos salvos; se o arquivo sumiu, cai pro modo **"blur"** (desfoque).
- **Chaves salvas:** `camera` (índice), `engine` (`mediapipe`/`rvm`), `bg_mode`,
  `blur`, `bg_image_path`, `bg_video_path`, `mirror`, `refine`, `zoom`, `pan_x`,
  `pan_y`, `brilho`, `contraste`, `saturacao`, `nitidez`.
- **Carregamento no `__init__`:** o cfg é lido **ANTES** de setar os atributos
  (cada atributo = `c.get(chave, default)`). A **câmera salva é validada** contra
  as câmeras presentes (`salvo_cam if salvo_cam in cam_ids else cams[0]` — se a
  câmera sumiu, usa a primeira). O `_build_ui` já **inicializa os widgets com os
  valores salvos** (combobox de câmera/motor, radio de fundo, todos os sliders,
  checkboxes); depois chama `_restaurar_fundo()`.
- **Quando salva:**
  - **mudanças discretas** — `_on_cam`, `_on_engine`, `_on_bg`, `_pick_bg`,
    `_pick_bg_video`, `_reset`;
  - **checkboxes** — espelhar / borda alta qualidade;
  - **sliders** — ao **soltar o botão** (`<ButtonRelease-1>` em `_slider`), não a
    cada movimento;
  - **`fechar()`** — garante o estado final ao sair.
- **Robustez:** leitura e escrita em `try/except` — um JSON corrompido ou disco
  cheio **não quebra o app** (só ignora e segue com os defaults).

## Startup (janela instantânea)
A janela abre **na hora** e **vem pra frente**, sem o atraso antigo:
- **Matter lazy no worker.** `self.matter = None` no `__init__`; o `LiveMatter` é
  criado no **início de `_loop`** (worker thread). O init do MediaPipe (~1.8s) não
  bloqueia mais a UI. Status inicial: "Carregando recorte...".
- **Janela topmost + foco.** O `__init__` faz `update_idletasks()` + `minsize(900,
  560)` + `lift()` + `attributes("-topmost", True)` (solto após 900ms via
  `root.after`) + `focus_force()` — a janela **vem pra frente** em vez de abrir
  atrás de outras.
- **Contexto:** o usuário reportou que o app "não abria". Na verdade ele abria, mas
  **lento** (init do MediaPipe) e às vezes **atrás de outras janelas** — os dois
  pontos acima resolvem.

## UI (tema escuro, painel rolável, vídeo responsivo)
A UI passou por um **redesign** que resolveu responsividade ruim (botões sumiam em
janela curta) e visual datado. Pontos verificados:

- **Tema escuro moderno (`_setup_style`).** Novo método chamado no início de
  `_build_ui`; usa o ttk `Style` com o theme **`clam`** como base. Paleta em
  `self.COL`: `bg` #16161f, `panel` #20202e, `card` #2c2c40, `accent` **#7c6cf0**
  (roxo), `rec` **#e0556b** (vermelho), `txt` #e6e6f0, `mute`. Estilos custom:
  **`Accent.TButton`** (roxo, ações primárias), **`Rec.TButton`** (vermelho,
  gravar), `Muted.TLabel`, `Status.TLabel`, `TLabelframe` e combobox/scrollbar/
  checkbutton/radiobutton escuros. A **listbox do dropdown** (combobox) é colorida
  via `option_add` (que o ttk `Style` não alcança).
- **Painel de controles rolável.** Os controles vivem num `tk.Canvas` + `ttk.Scrollbar`
  vertical + frame interno; um bind `<Configure>` ajusta o `scrollregion`, e a roda
  do mouse rola via `bind_all("<MouseWheel>")`. **Corrige o bug "os botões somem"**:
  antes os controles eram um **grid fixo** (contador `r`) que **clipava** quando a
  janela era curta; agora rolam.
- **Seções em `ttk.Labelframe`.** Os controles foram agrupados em quatro grupos
  rotulados: **"CÂMERA & MOTOR"**, **"FUNDO"**, **"AJUSTES DE IMAGEM"**, **"GRAVAR &
  STREAM"**. O layout interno migrou de grid (com contador `r`) para **`pack`**
  dentro de cada seção.
- **Vídeo responsivo.** O `tk.Label` do vídeo fica num frame que **expande**
  (`grid` + `columnconfigure(0, weight=1)`); o `_tick` agora **reescala** o frame
  PIL para caber em `video.winfo_width()/winfo_height()` mantendo a proporção. Antes
  era fixo **960×540**, deixando espaço morto ao redor.
- **Geometria.** Janela inicia em `geometry("1180x720")` com `minsize(760, 520)`
  (antes `minsize(900, 560)`, ver [Startup](#startup-janela-instant%C3%A2nea)). O
  helper `_slider` foi reescrito **pack-based** (sem o param `row`); o `tk.Scale` é
  estilizado com as cores da paleta.

## Parâmetros-chave
- **`CAP_W=960, CAP_H=540, FPS=20`** — captura e saída fixas (sem flags de CLI; é
  GUI). 540p é o mesmo default do live (fluidez × nitidez).
- **`listar_cameras()`** — usa **pygrabber** (`FilterGraph().get_input_devices()`,
  DirectShow) para **nomear** as câmeras **sem abri-las**, e **exclui a "OBS Virtual
  Camera"** da lista (senão vira loop de feedback). Fallback: sonda índices 0..3 com
  `cv2.VideoCapture`. Verificado na máquina: `[(0,'HD User Facing'),(1,'UGREEN Camera')]`.
- **`refine`** (checkbox "Borda alta qualidade", default ligado) — repassado a
  `compor(refine=...)`; mesma semântica de `--fast` no CLI ([[components/live-mode]]).
- **`color_match=0.12`** fixo no `compor` (color-match leve, sem relight).

### Ajustes de imagem (`agentes/ajustes.py`)
`aplicar_ajustes(img, zoom, pan_x, pan_y, brilho, contraste, saturacao, nitidez)`
opera sobre frames **BGR** e é aplicado **depois** da composição (página canônica
deste módulo é esta seção; não duplicar em outro lugar):

| Param | Faixa | Como |
|---|---|---|
| `zoom` | 1.0–4.0 | **center-crop** (`w/zoom × h/zoom`) + `resize` ao tamanho original |
| `pan_x` / `pan_y` | -1..1 | **enquadramento**: desloca o recorte (só tem efeito com `zoom>1`) |
| `brilho` | -100..100 | `beta` em `cv2.convertScaleAbs` (soma no pixel) |
| `contraste` | 0.5–2.0 | `alpha` em `cv2.convertScaleAbs` (ganho multiplicativo) |
| `saturacao` | 0–2.0 | escala o canal **S** em HSV (clip 0–255) |
| `nitidez` | 0–2.0 | **unsharp mask**: `addWeighted(img, 1+n, GaussianBlur, -n)` |

Cada etapa é pulada quando está no valor neutro (zoom≤1, contraste=1 e brilho=0,
saturacao=1, nitidez=0), então o custo é só dos ajustes ativos.

## Gotchas
1. **`ImageTk.PhotoImage` só na main thread.** Tkinter não é thread-safe; criar o
   `PhotoImage` no worker corrompe/trava. Por isso o worker só produz BGR e a main
   thread (`_tick`/`root.after`) faz a conversão e o `configure(image=...)`. Guardar
   uma referência (`self.video.image = img`) é obrigatório ou o GC come a imagem.
2. **`listar_cameras` é Windows/DirectShow.** `pygrabber` usa DirectShow; em outro
   SO cai no fallback de sondar índices (que **abre** as câmeras, mais lento e sem
   nomes amigáveis).
3. **Excluir a OBS Virtual Camera da entrada.** Se ela aparecer no dropdown e for
   selecionada enquanto a saída virtual está ligada, vira **loop de feedback**. Por
   isso `listar_cameras` a filtra.
4. **Câmera virtual exige OBS Studio instalado uma vez** (registra a OBS Virtual
   Camera) — mesma dependência do `live.py`; não precisa estar rodando. Se falhar, o
   app mostra erro e desliga `req_virtual`.
5. **Ajustes depois da composição.** `aplicar_ajustes` roda no **quadro final**
   (pessoa + fundo já compostos), de propósito — zoom/brilho afetam a cena inteira,
   como um app de câmera. Não confundir com ajuste só na pessoa.
6. **Trocar para RVM congela ~12s na 1a vez.** A primeira seleção do motor RVM baixa
   `rvm_mobilenetv3.pth` (~15MB) via torch.hub; a UI mostra "Carregando motor (RVM
   baixa o modelo na 1a vez)..." e o worker fica `_paused`. Exige **torchvision**
   instalado ([[concepts/rvm-matting]]); se faltar/erro, o app volta pro MediaPipe.
7. **O render usa um snapshot, não o estado vivo.** `_render_video` captura as
   configs (engine/fundo/blur/refine) **antes** de disparar a thread, e o
   `render_arquivo` constrói seu **próprio** matter — não compartilha `self.matter`
   com o worker do live. Mexer nos controles durante o render não afeta o render em
   curso, e vice-versa. `progress_cb`/`messagebox` precisam de `root.after(0, ...)`
   (só a main thread mexe em widgets Tk).

## Relacionados
[[components/live-mode]] · [[concepts/realtime-matting]] · [[concepts/rvm-matting]] ·
[[components/render-video]] · [[components/relighting]] · [[components/composicao]] · [[index]]
