"""
Agente 3 — Geração de Fundo com SD 1.5
Gera uma imagem de fundo via ComfyUI API rodando em background.
"""

import json
import uuid
import time
import subprocess
import io

import requests
from PIL import Image


COMFYUI_URL = "http://127.0.0.1:8188"


def iniciar_comfyui(comfyui_dir: str = "/content/ComfyUI"):
    """Inicia ComfyUI em background e aguarda ficar online."""
    process = subprocess.Popen(
        ["python", "main.py", "--port", "8188", "--cuda-device", "0"],
        cwd=comfyui_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(30):
        try:
            r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
            if r.status_code == 200:
                print("  ComfyUI online")
                return process
        except Exception:
            time.sleep(2)

    raise RuntimeError("ComfyUI nao subiu em 60s")


def gerar_fundo(
    prompt: str,
    width: int,
    height: int,
    output_path: str,
    negative_prompt: str = "person, human, people, ugly, blurry, low quality",
    steps: int = 25,
    cfg: float = 7.0,
    seed: int = -1,
):
    """Gera imagem de fundo via ComfyUI API com SD 1.5."""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    start = time.time()

    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed if seed != -1 else int(uuid.uuid4().int % 2**32),
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "bg_output"},
        },
    }

    client_id = str(uuid.uuid4())

    # Enviar workflow
    r = requests.post(
        f"{COMFYUI_URL}/prompt",
        json={"prompt": workflow, "client_id": client_id},
    )
    r.raise_for_status()
    prompt_id = r.json()["prompt_id"]

    # Aguardar conclusão
    while True:
        history = requests.get(f"{COMFYUI_URL}/history/{prompt_id}").json()
        if prompt_id in history:
            break
        time.sleep(1)

    # Baixar imagem gerada
    outputs = history[prompt_id]["outputs"]
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            img_info = node_output["images"][0]
            img_data = requests.get(
                f"{COMFYUI_URL}/view",
                params={
                    "filename": img_info["filename"],
                    "subfolder": img_info.get("subfolder", ""),
                },
            ).content
            img = Image.open(io.BytesIO(img_data))
            img.save(output_path)
            elapsed = round(time.time() - start, 2)
            print(f"  Fundo gerado: {output_path} ({elapsed}s)")
            return output_path

    raise RuntimeError("Falha ao gerar fundo — nenhuma imagem retornada pelo ComfyUI")
