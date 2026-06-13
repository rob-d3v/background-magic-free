"""
Agente 4b — Composicao simples (fallback CPU, sem GPU)

Quando nao ha GPU para o IC-Light, ainda da pra colocar a pessoa no novo fundo:
compoe o recorte (RGBA) sobre a imagem de fundo via canal alpha. Nao reilumina
(a luz da pessoa continua a do video original), mas ja entrega o efeito de
"troca de ambiente". Roda em CPU, rapido.

Usado:
  - no modo local sem GPU (interface Gradio em modo leve)
  - como preview instantaneo antes do relight pesado
"""

import os
import time
import json

from PIL import Image, ImageEnhance
from tqdm import tqdm


def compor_frame(
    fg_rgba: Image.Image,
    bg_rgb: Image.Image,
    ajuste_brilho: float = 1.0,
    ajuste_cor: float = 1.0,
) -> Image.Image:
    """
    Compoe uma pessoa (RGBA) sobre o fundo (RGB). Redimensiona o fundo para o
    tamanho do frame. ajuste_brilho/ajuste_cor permitem casar levemente a pessoa
    ao fundo sem IA (1.0 = sem mudanca).
    """
    fg = fg_rgba.convert("RGBA")
    w, h = fg.size
    bg = bg_rgb.convert("RGB")

    # cobre w x h mantendo proporcao (resize + center crop)
    iw, ih = bg.size
    scale = max(w / iw, h / ih)
    nw, nh = int(round(iw * scale)), int(round(ih * scale))
    bg = bg.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    bg = bg.crop((left, top, left + w, top + h))

    person = fg
    if ajuste_brilho != 1.0:
        person = ImageEnhance.Brightness(person).enhance(ajuste_brilho)
    if ajuste_cor != 1.0:
        person = ImageEnhance.Color(person).enhance(ajuste_cor)

    base = bg.convert("RGBA")
    base.paste(person, (0, 0), person)
    return base.convert("RGB")


def compor_batch(
    frames_nobg_dir: str,
    background_path: str,
    output_dir: str,
    ajuste_brilho: float = 1.0,
    ajuste_cor: float = 1.0,
    log_path: str = None,
    progress_cb=None,
):
    """Compoe todos os frames sobre o fundo. Resume automatico."""
    os.makedirs(output_dir, exist_ok=True)
    bg = Image.open(background_path).convert("RGB")

    frames = sorted(f for f in os.listdir(frames_nobg_dir) if f.endswith(".png"))
    erros = []
    start = time.time()

    for i, frame_name in enumerate(tqdm(frames, desc="Compondo frames")):
        output_path = os.path.join(output_dir, frame_name)
        if os.path.exists(output_path):
            if progress_cb:
                progress_cb(i + 1, len(frames))
            continue
        try:
            fg = Image.open(os.path.join(frames_nobg_dir, frame_name)).convert("RGBA")
            out = compor_frame(fg, bg, ajuste_brilho, ajuste_cor)
            out.save(output_path)
        except Exception as e:
            erros.append({"frame": frame_name, "erro": str(e)})
            print(f"  ERRO em {frame_name}: {e}")
        if progress_cb:
            progress_cb(i + 1, len(frames))

    elapsed = round(time.time() - start, 2)

    if log_path and erros:
        log_data = {}
        if os.path.exists(log_path):
            try:
                with open(log_path) as f:
                    log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = {}
        log_data["composicao_erros"] = erros
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)

    processados = len(frames) - len(erros)
    print(f"  {processados}/{len(frames)} frames compostos ({elapsed}s)")
    return {"processados": processados, "erros": len(erros), "tempo_s": elapsed}
