"""
Agente 2 — Remoção de Fundo
Processa cada frame com rembg usando GPU, produzindo PNGs com canal alpha.
"""

import os
import time
import json

from rembg import remove, new_session
from tqdm import tqdm


def remover_fundo(frames_dir: str, output_dir: str, log_path: str = None):
    """
    Remove o fundo de todos os frames usando rembg com GPU.
    Modelo: u2net_human_seg (otimizado para pessoas).
    Suporta resume automático — pula frames já processados.
    """
    os.makedirs(output_dir, exist_ok=True)

    session = new_session("u2net_human_seg")

    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith(".png")])
    erros = []

    start = time.time()

    for frame_name in tqdm(frames, desc="Removendo fundo"):
        input_path = os.path.join(frames_dir, frame_name)
        output_path = os.path.join(output_dir, frame_name)

        if os.path.exists(output_path):
            continue  # resume automático

        try:
            with open(input_path, "rb") as f:
                img_bytes = f.read()

            result = remove(
                img_bytes,
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10,
            )

            with open(output_path, "wb") as f:
                f.write(result)
        except Exception as e:
            erros.append({"frame": frame_name, "erro": str(e)})
            print(f"  ERRO em {frame_name}: {e}")

    elapsed = round(time.time() - start, 2)

    if log_path and erros:
        # Carregar log existente ou criar novo
        log_data = {}
        if os.path.exists(log_path):
            try:
                with open(log_path) as f:
                    log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = {}
        log_data["remocao_fundo_erros"] = erros
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)

    processados = len(frames) - len(erros)
    print(f"  {processados}/{len(frames)} frames processados ({elapsed}s)")
    return {"processados": processados, "erros": len(erros), "tempo_s": elapsed}
