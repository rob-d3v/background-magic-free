"""
Agente 5 — Composição e Exportação
Compila todos os frames relitados em vídeo final com áudio original.
"""

import subprocess
import os
import time


def exportar_video(
    frames_dir: str,
    video_original: str,
    output_path: str,
    fps: float,
    crf: int = 18,
):
    """
    Monta vídeo final a partir dos frames relitados com áudio original.
    crf: qualidade H.264 (0=perfeito, 51=péssimo, 18=alta, 23=média)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    start = time.time()

    temp_video = output_path.replace(".mp4", "_noaudio.mp4")

    # Montar vídeo a partir dos frames
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", f"{frames_dir}/frame_%05d.png",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-preset", "slow",
        temp_video,
    ], check=True, capture_output=True)

    # Verificar se vídeo original tem áudio
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "json", video_original],
        capture_output=True, text=True,
    )
    has_audio = '"codec_type": "audio"' in probe.stdout

    if has_audio:
        # Adicionar áudio original
        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", video_original,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ], check=True, capture_output=True)
        os.remove(temp_video)
    else:
        os.rename(temp_video, output_path)

    elapsed = round(time.time() - start, 2)
    print(f"  Video final: {output_path} ({elapsed}s)")
    return {"output": output_path, "tempo_s": elapsed}
