"""
Agente 1 — Extração de Frames
Extrai todos os frames do vídeo de entrada mantendo FPS original.
"""

import subprocess
import json
import os
import time


def extrair_frames(video_path: str, output_dir: str) -> dict:
    """
    Extrai frames do vídeo e retorna metadados.

    Returns:
        dict com fps, total_frames, width, height
    """
    os.makedirs(output_dir, exist_ok=True)

    start = time.time()

    # Obter metadados do vídeo
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,width,height,nb_frames",
        "-of", "json", video_path
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    meta = json.loads(result.stdout)["streams"][0]

    fps_raw = meta["r_frame_rate"]  # ex: "30000/1001"
    num, den = map(int, fps_raw.split("/"))
    fps = round(num / den, 3)

    # Extrair frames
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-q:v", "1",
        "-pix_fmt", "rgb24",
        f"{output_dir}/frame_%05d.png"
    ]
    subprocess.run(extract_cmd, check=True, capture_output=True)

    total_frames = len([f for f in os.listdir(output_dir) if f.endswith(".png")])
    elapsed = round(time.time() - start, 2)

    return {
        "fps": fps,
        "total_frames": total_frames,
        "width": int(meta["width"]),
        "height": int(meta["height"]),
        "tempo_s": elapsed,
    }
