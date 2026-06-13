"""
Render offline de troca de fundo usando os motores de matting do modo live
(MediaPipe ou RVM), aplicado frame-a-frame num vídeo gravado.

Diferente do modo live: aqui **não há pressão de fps** — dá pra rodar o RVM em
qualidade total. O RVM é um modelo de matting de **vídeo** (mantém estado
recorrente entre frames), então processar os frames **em ordem** dá coerência
temporal (menos tremor de borda) que o live, frame-isolado, não tem.

É o caminho "poderoso, sem GPU": melhor que o `compor` (rembg) e não precisa da
GPU/Colab do relight IC-Light. Não reilumina — troca o fundo com recorte limpo.
"""

import os
import time

import cv2

import subprocess

from agentes.matting_live import cobrir, VideoFundo, fundo_desfocado

_VIDEO_EXT = (".mp4", ".mov", ".avi", ".mkv", ".webm")


def _build_matter(engine: str):
    if engine == "rvm":
        from agentes.matting_rvm import RVMMatter
        return RVMMatter()
    from agentes.matting_live import LiveMatter
    return LiveMatter()


def render_matting(
    frames_dir: str,
    background_path: str,
    output_dir: str,
    engine: str = "rvm",
    color_match: float = 0.12,
    feather: int = 2,
    progress_cb=None,
):
    """
    Recorta a pessoa de cada frame (motor `engine`) e compõe sobre o fundo.
    Processa os frames em ordem (coerência temporal no RVM). Resume automático:
    pula frames já existentes na saída — mas então o estado recorrente do RVM
    reinicia, então pra um render limpo apague a saída antes.
    """
    os.makedirs(output_dir, exist_ok=True)
    frames = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
    if not frames:
        raise ValueError(f"Sem frames em {frames_dir}")

    first = cv2.imread(os.path.join(frames_dir, frames[0]))
    h, w = first.shape[:2]

    # fundo: imagem fixa OU vídeo em loop (1 frame de fundo por frame de saída)
    bg_video = None
    if background_path.lower().endswith(_VIDEO_EXT):
        bg_video = VideoFundo(background_path, w, h)
        bg = None
    else:
        bg = cobrir(cv2.imread(background_path), w, h)

    matter = _build_matter(engine)
    start = time.time()
    feito = 0
    for i, fn in enumerate(frames):
        out_path = os.path.join(output_dir, fn)
        frame = cv2.imread(os.path.join(frames_dir, fn))
        fundo = bg_video.proximo() if bg_video is not None else bg
        out = matter.compor(frame, fundo, color_match=color_match, feather=feather)
        cv2.imwrite(out_path, out)
        feito += 1
        if progress_cb:
            progress_cb(i + 1, len(frames))
    matter.close()
    if bg_video is not None:
        bg_video.close()

    elapsed = round(time.time() - start, 2)
    fps = round(feito / elapsed, 1) if elapsed else 0
    print(f"  Render {engine}: {feito} frames em {elapsed}s ({fps} fps)")
    return {"processados": feito, "tempo_s": elapsed, "engine": engine}


def render_arquivo(
    input_path: str,
    output_path: str,
    engine: str = "rvm",
    bg_mode: str = "blur",
    bg_image_path: str = None,
    bg_video_path: str = None,
    blur: int = 45,
    color_match: float = 0.12,
    refine: bool = True,
    progress_cb=None,
):
    """
    Renderiza um **arquivo de vídeo** inteiro trocando o fundo, lendo direto do
    vídeo (sem extrair frames) e escrevendo um mp4 — depois remuxa o áudio
    original. Usado pelo botão "Renderizar vídeo" do app de câmera.

    bg_mode: none | blur | image (bg_image_path) | video (bg_video_path em loop).
    """
    import os
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Não consegui abrir o vídeo: {input_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

    matter = _build_matter(engine)
    bgv = VideoFundo(bg_video_path, w, h) if (bg_mode == "video" and bg_video_path) else None
    bgimg = None
    if bg_mode == "image" and bg_image_path and os.path.exists(bg_image_path):
        raw = cv2.imread(bg_image_path, cv2.IMREAD_COLOR)
        if raw is not None:
            bgimg = cobrir(raw, w, h)

    tmp = output_path[:-4] + "_noaudio.mp4" if output_path.endswith(".mp4") else output_path + ".tmp.mp4"
    writer = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if bg_mode == "none":
            out = frame
        else:
            if bgv is not None:
                bg = bgv.proximo()
            elif bgimg is not None:
                bg = bgimg
            else:
                bg = fundo_desfocado(frame, int(blur) | 1)
            out = matter.compor(frame, bg, color_match=color_match, refine=refine)
        writer.write(out)
        i += 1
        if progress_cb:
            progress_cb(i, total)
    cap.release()
    writer.release()
    matter.close()
    if bgv is not None:
        bgv.close()

    # remuxa o áudio original. `-map 1:a:0?` torna o áudio OPCIONAL: se o vídeo
    # tiver áudio ele entra; se não tiver, o ffmpeg só ignora (sem erro). Mais
    # robusto que sondar com ffprobe (a sonda por string falhava em alguns casos).
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp, "-i", input_path,
             "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy", "-c:a", "aac",
             "-shortest", output_path],
            check=True, capture_output=True)
        os.remove(tmp)
    except Exception:
        # se o mux falhar por qualquer motivo, ao menos entrega o vídeo sem áudio
        os.replace(tmp, output_path)

    return {"output": output_path, "frames": i, "engine": engine}
