"""
app.py — Interface Gradio do lumina-bg

Fluxo guiado:
  1. Enviar video  -> extrai frames
  2. Escolher 1 frame  -> recorta a pessoa (preview)
  3. Definir o fundo  (enviar imagem ou gerar com IA)
  4. Ajustar iluminacao / modo  (compor rapido  ou  reiluminar IC-Light)
  5. Pre-visualizar NESSE frame  -> iterar ate ficar bom
  6. Aplicar a todos os frames  -> video final

GPU-aware: sem GPU, so o modo "compor" fica disponivel (roda em CPU). O relight
IC-Light precisa de GPU (Colab T4). A ideia do preview de 1 frame e justamente
acertar o look num frame so antes de gastar tempo processando o video inteiro.

Rodar:
    python app.py                 # local (http://127.0.0.1:7860)
    # no Colab: app.launch(share=True) ja e chamado automaticamente
"""

import os
import sys
import subprocess

import numpy as np
import gradio as gr
from PIL import Image

from config import Paths, detectar_device
from agentes.extracao import extrair_frames
from agentes.exportacao import exportar_video

# ─── Estado global do app (single-user) ───────────────────────────────────
PATHS = Paths().criar_dirs()
DEV = detectar_device()
ESTADO = {"meta": None, "n_frames": 0}

_REMBG_SESSION = None
_RELIGHT_PIPE = None
_LIVE_MATTER = None      # LiveMatter (lazy) para o preview de recorte na UI
_OFFLINE_MATTER = None   # matter (RVM) para preview do render offline
_LIVE_PROC = None        # subprocesso do live.py (camera virtual)
LIVE_BG_PATH = os.path.join(PATHS.background_dir, "live_bg.png")

MODO_HD = "Trocar fundo HD (RVM, CPU)"
MODO_COMPOR = "Compor (rapido, CPU)"
MODO_RELIGHT = "Reiluminar (IC-Light, GPU)"


def _offline_matter():
    global _OFFLINE_MATTER
    if _OFFLINE_MATTER is None:
        from agentes.matting_rvm import RVMMatter
        _OFFLINE_MATTER = RVMMatter()
    _OFFLINE_MATTER.reset()
    return _OFFLINE_MATTER


def _frame_path(idx: int) -> str:
    return os.path.join(PATHS.frames_raw, f"frame_{idx + 1:05d}.png")


def _nobg_path(idx: int) -> str:
    return os.path.join(PATHS.frames_nobg, f"frame_{idx + 1:05d}.png")


def _rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        from rembg import new_session
        _REMBG_SESSION = new_session("u2net_human_seg")
    return _REMBG_SESSION


def _remover_fundo_um(idx: int) -> Image.Image:
    """Recorta a pessoa de um frame (com cache em disco)."""
    out_path = _nobg_path(idx)
    if os.path.exists(out_path):
        return Image.open(out_path).convert("RGBA")
    from rembg import remove
    img = Image.open(_frame_path(idx))
    res = remove(
        img, session=_rembg_session(), alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10, alpha_matting_erode_size=10,
    ).convert("RGBA")
    os.makedirs(PATHS.frames_nobg, exist_ok=True)
    res.save(out_path)
    return res


def _relight_pipe():
    global _RELIGHT_PIPE
    if _RELIGHT_PIPE is None:
        from agentes.relighting import carregar_iclight
        low_vram = (DEV["vram_gb"] or 99) < 8.0
        _RELIGHT_PIPE = carregar_iclight(device="cuda", low_vram=low_vram)
    return _RELIGHT_PIPE


# ─── Callbacks ─────────────────────────────────────────────────────────────

def cb_preparar(video_path):
    if not video_path:
        raise gr.Error("Envie um video primeiro.")
    meta = extrair_frames(video_path, PATHS.frames_raw)
    ESTADO["meta"] = meta
    ESTADO["n_frames"] = meta["total_frames"]
    # frame do meio como inicial (costuma ter a pessoa bem posicionada)
    meio = meta["total_frames"] // 2
    info = (f"{meta['total_frames']} frames @ {meta['fps']}fps — "
            f"{meta['width']}x{meta['height']}")
    return (
        gr.update(maximum=meta["total_frames"] - 1, value=meio, visible=True, interactive=True),
        Image.open(_frame_path(meio)),
        info,
        gr.update(interactive=True),  # botao recortar
        gr.update(interactive=True),  # botao preview
        gr.update(interactive=True),  # botao aplicar
    )


def cb_mostrar_frame(idx):
    idx = int(idx)
    if not os.path.exists(_frame_path(idx)):
        return None
    return Image.open(_frame_path(idx))


def cb_recortar(idx):
    idx = int(idx)
    if ESTADO["meta"] is None:
        raise gr.Error("Prepare o video primeiro (passo 1).")
    return _remover_fundo_um(idx)


def _obter_bg(bg_modo, bg_upload, bg_prompt, steps, cfg, seed):
    """Resolve a imagem de fundo (PIL) conforme o modo escolhido."""
    meta = ESTADO["meta"]
    w, h = meta["width"], meta["height"]
    if bg_modo == "Enviar imagem":
        if bg_upload is None:
            raise gr.Error("Envie uma imagem de fundo ou escolha 'Gerar com IA'.")
        bg = Image.open(bg_upload).convert("RGB") if isinstance(bg_upload, str) else bg_upload.convert("RGB")
        bg.save(PATHS.bg_output)
        return bg
    else:
        if not DEV["cuda"]:
            raise gr.Error("Gerar fundo com IA precisa de GPU. Sem GPU, envie uma imagem.")
        from agentes.geracao_fundo import gerar_fundo_diffusers
        return gerar_fundo_diffusers(
            prompt=bg_prompt, width=w, height=h, output_path=PATHS.bg_output,
            steps=int(steps), cfg=float(cfg), seed=int(seed),
        )


def cb_preview(idx, modo, bg_modo, bg_upload, bg_prompt, prompt, negative, steps, cfg, seed):
    idx = int(idx)
    if ESTADO["meta"] is None:
        raise gr.Error("Prepare o video primeiro (passo 1).")

    if modo == MODO_HD:
        # recorte HD com RVM direto no frame cru (sem rembg)
        import cv2
        import numpy as np
        from agentes.matting_live import cobrir
        bg_pil = _obter_bg(bg_modo, bg_upload, bg_prompt, steps, cfg, seed)
        frame = cv2.imread(_frame_path(idx))
        bg = cobrir(cv2.cvtColor(np.array(bg_pil), cv2.COLOR_RGB2BGR),
                    frame.shape[1], frame.shape[0])
        out = _offline_matter().compor(frame, bg, color_match=0.12, feather=2)
        return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))

    fg = _remover_fundo_um(idx)
    bg = _obter_bg(bg_modo, bg_upload, bg_prompt, steps, cfg, seed)

    if modo == "Reiluminar (IC-Light, GPU)":
        if not DEV["pode_relight"]:
            raise gr.Error(
                "Relight precisa de GPU (>=5GB). Sem isso, use o modo 'Compor'. "
                "Para relight, rode no Google Colab (T4)."
            )
        from agentes.relighting import relight_frame
        pipe = _relight_pipe()
        out = relight_frame(
            pipe, fg, bg, prompt, negative_prompt=negative,
            steps=int(steps), cfg=float(cfg), seed=int(seed),
        )
    else:
        from agentes.composicao import compor_frame
        out = compor_frame(fg, bg)
    return out


def cb_aplicar(idx, modo, bg_modo, bg_upload, bg_prompt, prompt, negative,
               steps, cfg, seed, crf, progress=gr.Progress()):
    if ESTADO["meta"] is None:
        raise gr.Error("Prepare o video primeiro (passo 1).")
    meta = ESTADO["meta"]

    def _cb(done, tot):
        progress(0.4 + 0.5 * done / max(tot, 1), desc=f"Processando frame {done}/{tot}")

    # ── Modo HD (RVM): recorta direto do frame cru, sem rembg ──
    if modo == MODO_HD:
        progress(0.1, desc="Preparando fundo...")
        _obter_bg(bg_modo, bg_upload, bg_prompt, steps, cfg, seed)
        # apaga saida antiga p/ render limpo (estado recorrente do RVM)
        import shutil
        if os.path.isdir(PATHS.frames_relit):
            shutil.rmtree(PATHS.frames_relit, ignore_errors=True)
        progress(0.2, desc="Recortando e compondo (RVM)...")
        from agentes.render_video import render_matting
        render_matting(PATHS.frames_raw, PATHS.bg_output, PATHS.frames_relit,
                       engine="rvm", progress_cb=_cb)
        progress(0.92, desc="Montando video final...")
        out_path = os.path.join(PATHS.output_dir, "video_final.mp4")
        exportar_video(PATHS.frames_relit, ESTADO.get("video_path"), out_path,
                       fps=meta["fps"], crf=int(crf))
        progress(1.0, desc="Pronto!")
        return out_path, out_path

    # 1) remover fundo de todos
    from agentes.remocao import remover_fundo
    progress(0.0, desc="Recortando pessoa de todos os frames...")
    remover_fundo(PATHS.frames_raw, PATHS.frames_nobg, log_path=PATHS.log_path)

    # 2) fundo (reusa o mesmo do preview)
    progress(0.4, desc="Preparando fundo...")
    _obter_bg(bg_modo, bg_upload, bg_prompt, steps, cfg, seed)

    # 3) relight ou compose
    total = meta["total_frames"]

    if modo == "Reiluminar (IC-Light, GPU)":
        if not DEV["pode_relight"]:
            raise gr.Error("Relight precisa de GPU. Use 'Compor' ou rode no Colab.")
        from agentes.relighting import aplicar_relighting
        aplicar_relighting(
            _relight_pipe(), PATHS.frames_nobg, PATHS.bg_output, PATHS.frames_relit,
            prompt, negative_prompt=negative, steps=int(steps), cfg=float(cfg),
            seed=int(seed), log_path=PATHS.log_path, progress_cb=_cb,
        )
    else:
        from agentes.composicao import compor_batch
        compor_batch(
            PATHS.frames_nobg, PATHS.bg_output, PATHS.frames_relit,
            log_path=PATHS.log_path, progress_cb=_cb,
        )

    # 4) exportar
    progress(0.92, desc="Montando video final...")
    out_path = os.path.join(PATHS.output_dir, "video_final.mp4")
    # achar o video original (ultimo enviado fica em frames? nao — usar input dir)
    video_orig = ESTADO.get("video_path")
    exportar_video(
        PATHS.frames_relit, video_orig, out_path,
        fps=meta["fps"], crf=int(crf),
    )
    progress(1.0, desc="Pronto!")
    return out_path, out_path


def cb_guardar_video(video_path):
    """Guarda o caminho do video original para o export usar o audio."""
    ESTADO["video_path"] = video_path
    return gr.update()


# ─── Modo AO VIVO (OBS / Meet / stream) ────────────────────────────────────

def _live_matter():
    global _LIVE_MATTER
    if _LIVE_MATTER is None:
        from agentes.matting_live import LiveMatter
        _LIVE_MATTER = LiveMatter()
    return _LIVE_MATTER


def cb_live_preview(snapshot, bg_modo, bg_img, blur, feather, color_match, alta_qual):
    """Recorta a pessoa de um snapshot da webcam e compoe — valida o look na UI."""
    if snapshot is None:
        raise gr.Error("Tire um snapshot na webcam primeiro.")
    import cv2
    from agentes.matting_live import cobrir, fundo_desfocado
    frame = cv2.cvtColor(np.asarray(snapshot), cv2.COLOR_RGB2BGR)
    h, w = frame.shape[:2]
    if bg_modo == "Desfocar fundo":
        bg = fundo_desfocado(frame, int(blur) | 1)
    else:
        if bg_img is None:
            raise gr.Error("Envie uma imagem de fundo ou escolha 'Desfocar fundo'.")
        bg = cobrir(cv2.cvtColor(np.asarray(bg_img), cv2.COLOR_RGB2BGR), w, h)
    out = _live_matter().compor(
        frame, bg, feather=int(feather), color_match=float(color_match),
        refine=bool(alta_qual),
    )
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def _live_cmd(bg_modo, bg_img, blur, res, feather, color_match, mirror, preview, alta_qual):
    w, h = {"640x360": (640, 360), "960x540": (960, 540), "1280x720": (1280, 720)}[res.split()[0]]
    args = [sys.executable, "live.py", "--width", str(w), "--height", str(h),
            "--feather", str(int(feather)), "--color-match", str(float(color_match))]
    if not alta_qual:
        args += ["--fast"]
    if bg_modo == "Desfocar fundo":
        args += ["--blur", str(int(blur) | 1)]
    else:
        if bg_img is None:
            raise gr.Error("Envie uma imagem de fundo ou escolha 'Desfocar fundo'.")
        Image.fromarray(np.asarray(bg_img)).convert("RGB").save(LIVE_BG_PATH)
        args += ["--background", LIVE_BG_PATH]
    if mirror:
        args += ["--mirror"]
    if preview:
        args += ["--preview"]
    return args


def cb_live_iniciar(bg_modo, bg_img, blur, res, feather, color_match, mirror, preview, alta_qual):
    global _LIVE_PROC
    if _LIVE_PROC is not None and _LIVE_PROC.poll() is None:
        return "Camera virtual ja esta rodando. Pare antes de reiniciar."
    args = _live_cmd(bg_modo, bg_img, blur, res, feather, color_match, mirror, preview, alta_qual)
    _LIVE_PROC = subprocess.Popen(args, cwd=os.path.dirname(os.path.abspath(__file__)))
    cmd = " ".join(f'"{a}"' if " " in a else a for a in args)
    return (f"**Camera virtual iniciada** (PID {_LIVE_PROC.pid}).\n\n"
            f"Selecione **OBS Virtual Camera** no Meet/Zoom/OBS.\n\n"
            f"Comando equivalente:\n```\n{cmd}\n```")


def cb_live_parar():
    global _LIVE_PROC
    if _LIVE_PROC is None or _LIVE_PROC.poll() is not None:
        return "Nenhuma camera virtual rodando."
    _LIVE_PROC.terminate()
    try:
        _LIVE_PROC.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _LIVE_PROC.kill()
    _LIVE_PROC = None
    return "Camera virtual parada."


# ─── UI ─────────────────────────────────────────────────────────────────────

def _banner_device():
    if DEV["pode_relight"]:
        return f"GPU detectada: **{DEV['gpu_name']}** ({DEV['vram_gb']}GB) — relight IC-Light disponivel."
    elif DEV["cuda"]:
        return (f"GPU **{DEV['gpu_name']}** ({DEV['vram_gb']}GB) — pouca VRAM p/ relight. "
                "Modo **Compor** disponivel. Para relight, use o Colab (T4).")
    else:
        return ("Sem GPU CUDA — modo **Compor** (CPU) disponivel. "
                "Para reiluminar (IC-Light), rode no Google Colab com GPU T4.")


MODOS = [MODO_HD, MODO_COMPOR, MODO_RELIGHT]
MODO_DEFAULT = MODO_RELIGHT if DEV["pode_relight"] else MODO_HD

LIVE_RES = ["640x360 (alta ~33 / fast ~42 fps)",
            "960x540 (alta ~15 / fast ~21 fps)",
            "1280x720 (alta ~9 / fast ~13 fps)"]

with gr.Blocks(title="lumina-bg") as demo:
    gr.Markdown("# lumina-bg — troque o fundo do seu video")
    gr.Markdown(_banner_device())

    with gr.Tabs():
        # ════════════ ABA STUDIO (gravar video, offline) ════════════
        with gr.Tab("🎬 Studio — gravar video"):
            with gr.Row():
                # ── Coluna esquerda: configuracao ──
                with gr.Column(scale=1):
                    gr.Markdown("### 1. Enviar video")
                    video_in = gr.Video(label="Seu video")
                    btn_preparar = gr.Button("1. Preparar video", variant="primary")
                    info_video = gr.Markdown("")

                    gr.Markdown("### 2. Escolher um frame")
                    frame_slider = gr.Slider(0, 1, step=1, value=0, label="Frame",
                                             visible=False, interactive=False)
                    btn_recortar = gr.Button("Recortar pessoa (preview)", interactive=False)

                    gr.Markdown("### 3. Fundo")
                    bg_modo = gr.Radio(["Enviar imagem", "Gerar com IA"],
                                       value="Enviar imagem", label="Origem do fundo")
                    bg_upload = gr.Image(label="Imagem de fundo", type="pil")
                    bg_prompt = gr.Textbox(
                        label="Prompt do fundo (se 'Gerar com IA')",
                        placeholder="modern studio, soft blue ambient light, cinematic",
                    )

                    gr.Markdown("### 4. Iluminacao / modo")
                    modo = gr.Radio(MODOS, value=MODO_DEFAULT, label="Modo")
                    prompt = gr.Textbox(
                        label="Descricao da luz (relight)",
                        value="soft cinematic studio lighting",
                    )
                    negative = gr.Textbox(label="Negative prompt", value="")
                    with gr.Row():
                        steps = gr.Slider(10, 40, value=20, step=1, label="Steps")
                        cfg = gr.Slider(1.0, 12.0, value=7.0, step=0.5, label="CFG")
                    with gr.Row():
                        seed = gr.Number(value=12345, label="Seed", precision=0)
                        crf = gr.Slider(14, 28, value=18, step=1, label="Qualidade (CRF)")

                # ── Coluna direita: preview e resultado ──
                with gr.Column(scale=1):
                    gr.Markdown("### Preview")
                    frame_preview = gr.Image(label="Frame selecionado / recorte", type="pil")
                    btn_preview = gr.Button("5. Pre-visualizar neste frame",
                                            variant="primary", interactive=False)
                    resultado_preview = gr.Image(label="Resultado no frame", type="pil")

                    gr.Markdown("### 6. Aplicar a todos e exportar")
                    btn_aplicar = gr.Button("Aplicar a todos os frames", variant="stop",
                                            interactive=False)
                    video_out = gr.Video(label="Video final")
                    file_out = gr.File(label="Baixar")

        # ════════════ ABA LIVE (OBS / Meet / stream) ════════════
        with gr.Tab("🔴 Live — OBS / Meet / stream"):
            gr.Markdown(
                "Troca o fundo da **webcam em tempo real** e publica numa "
                "**camera virtual**. Selecione **OBS Virtual Camera** no Meet/Zoom/OBS.\n\n"
                "> Pre-requisito (Windows): ter o **OBS Studio** instalado uma vez "
                "(registra a camera virtual). Nao precisa estar aberto.\n\n"
                "> Live faz recorte + composicao (sem relight IC-Light). Para "
                "reiluminar de verdade, use a aba **Studio** (video gravado)."
            )
            with gr.Row():
                with gr.Column(scale=1):
                    live_bg_modo = gr.Radio(
                        ["Imagem de fundo", "Desfocar fundo"],
                        value="Imagem de fundo", label="Fundo",
                    )
                    live_bg = gr.Image(label="Imagem de fundo", type="numpy")
                    live_blur = gr.Slider(5, 75, value=45, step=2,
                                          label="Intensidade do desfoque")
                    live_res = gr.Radio(LIVE_RES, value=LIVE_RES[1], label="Resolucao / FPS")
                    with gr.Row():
                        live_feather = gr.Slider(0, 15, value=3, step=1, label="Suavizar borda (px)")
                        live_cmatch = gr.Slider(0.0, 1.0, value=0.12, step=0.02, label="Casar cor")
                    live_alta = gr.Checkbox(
                        value=True,
                        label="Borda alta qualidade (refino guided filter — borda limpa, menos fps)",
                    )
                    with gr.Row():
                        live_mirror = gr.Checkbox(value=True, label="Espelhar (selfie)")
                        live_prev = gr.Checkbox(value=True, label="Janela de preview")
                with gr.Column(scale=1):
                    gr.Markdown("### Testar recorte (snapshot da webcam)")
                    live_snap = gr.Image(label="Webcam", sources=["webcam"], type="numpy")
                    btn_live_test = gr.Button("Testar recorte neste snapshot", variant="primary")
                    live_result = gr.Image(label="Resultado", type="numpy")
                    gr.Markdown("### Camera virtual")
                    with gr.Row():
                        btn_live_start = gr.Button("▶ Iniciar camera virtual", variant="primary")
                        btn_live_stop = gr.Button("■ Parar", variant="stop")
                    live_status = gr.Markdown("")

    # ── Ligações: Studio ──
    video_in.change(cb_guardar_video, inputs=video_in, outputs=[])
    btn_preparar.click(
        cb_preparar, inputs=video_in,
        outputs=[frame_slider, frame_preview, info_video,
                 btn_recortar, btn_preview, btn_aplicar],
    )
    frame_slider.change(cb_mostrar_frame, inputs=frame_slider, outputs=frame_preview)
    btn_recortar.click(cb_recortar, inputs=frame_slider, outputs=frame_preview)

    preview_inputs = [frame_slider, modo, bg_modo, bg_upload, bg_prompt,
                      prompt, negative, steps, cfg, seed]
    btn_preview.click(cb_preview, inputs=preview_inputs, outputs=resultado_preview)

    btn_aplicar.click(
        cb_aplicar,
        inputs=[frame_slider, modo, bg_modo, bg_upload, bg_prompt, prompt,
                negative, steps, cfg, seed, crf],
        outputs=[video_out, file_out],
    )

    # ── Ligações: Live ──
    btn_live_test.click(
        cb_live_preview,
        inputs=[live_snap, live_bg_modo, live_bg, live_blur, live_feather, live_cmatch, live_alta],
        outputs=live_result,
    )
    btn_live_start.click(
        cb_live_iniciar,
        inputs=[live_bg_modo, live_bg, live_blur, live_res, live_feather,
                live_cmatch, live_mirror, live_prev, live_alta],
        outputs=live_status,
    )
    btn_live_stop.click(cb_live_parar, inputs=[], outputs=live_status)


if __name__ == "__main__":
    # No Colab, share=True gera link publico automaticamente
    em_colab = False
    try:
        import google.colab  # noqa: F401
        em_colab = True
    except ImportError:
        pass
    demo.launch(share=em_colab, theme=gr.themes.Soft(primary_hue="indigo"))
