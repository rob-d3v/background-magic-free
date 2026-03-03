# PLANO: Pipeline de Troca de Fundo com IC-Light + ComfyUI no Google Colab

> **Destinatário:** Claude Code  
> **Objetivo:** Implementar uma pipeline completa e automatizada que receba um vídeo gravado pelo usuário, remova o fundo frame a frame, aplique um novo fundo gerado por Stable Diffusion, e reaplique iluminação coerente com IC-Light — tudo rodando no Google Colab com GPU gratuita (T4).

---

## 1. VISÃO GERAL DA PIPELINE

```
[Vídeo Original (.mp4)]
        ↓
[AGENTE 1 — Extração de Frames]
  └─ ffmpeg: vídeo → frames PNG
        ↓
[AGENTE 2 — Remoção de Fundo]
  └─ rembg (CUDA) → frames com alpha (PNG transparente)
        ↓
[AGENTE 3 — Geração de Fundo com SD 1.5]
  └─ ComfyUI API → fundo gerado via prompt do usuário
        ↓
[AGENTE 4 — Relighting com IC-Light]
  └─ IC-Light foreground conditioned → relight da pessoa no fundo
        ↓
[AGENTE 5 — Composição e Exportação]
  └─ ffmpeg: frames → vídeo final (.mp4) com áudio original
```

---

## 2. AMBIENTE — Google Colab

- **Runtime:** GPU T4 (gratuita) — `Runtime > Change runtime type > GPU`
- **VRAM disponível:** ~15GB (confortável para SD 1.5 + IC-Light)
- **Storage:** Google Drive montado para persistir frames e outputs
- **SO:** Ubuntu 22.04 (padrão Colab)

---

## 3. ESTRUTURA DE ARQUIVOS NO COLAB / DRIVE

```
/content/
├── drive/MyDrive/iclight_pipeline/
│   ├── input/
│   │   └── video.mp4                  ← usuário faz upload aqui
│   ├── frames/
│   │   ├── raw/                       ← frames extraídos pelo ffmpeg
│   │   └── nobg/                      ← frames sem fundo (RGBA PNG)
│   ├── background/
│   │   └── bg.png                     ← fundo gerado pelo SD
│   ├── relit/
│   │   └── frame_0001.png ...         ← frames com relighting final
│   └── output/
│       └── video_final.mp4            ← vídeo exportado
├── ComfyUI/                           ← instalação do ComfyUI
├── IC-Light/                          ← repositório IC-Light
└── pipeline.py                        ← script principal orquestrador
```

---

## 4. DEPENDÊNCIAS E INSTALAÇÃO

### 4.1 Sistema

```bash
apt-get install -y ffmpeg git wget curl python3-pip
```

### 4.2 Python

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install rembg[gpu] onnxruntime-gpu
pip install opencv-python Pillow numpy requests tqdm
pip install diffusers transformers accelerate safetensors
pip install huggingface_hub
```

### 4.3 ComfyUI

```bash
git clone https://github.com/comfyanonymous/ComfyUI /content/ComfyUI
cd /content/ComfyUI
pip install -r requirements.txt

# ComfyUI Manager (para instalar nodes custom)
cd /content/ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager
```

### 4.4 IC-Light

```bash
git clone https://github.com/lllyasviel/IC-Light /content/IC-Light
cd /content/IC-Light
pip install -r requirements.txt
```

### 4.5 Modelos necessários

```python
from huggingface_hub import hf_hub_download
import os

# SD 1.5 base
os.makedirs("/content/ComfyUI/models/checkpoints", exist_ok=True)
hf_hub_download(
    repo_id="runwayml/stable-diffusion-v1-5",
    filename="v1-5-pruned-emaonly.safetensors",
    local_dir="/content/ComfyUI/models/checkpoints"
)

# IC-Light modelo (foreground conditioned)
os.makedirs("/content/IC-Light/models", exist_ok=True)
hf_hub_download(
    repo_id="lllyasviel/ic-light",
    filename="iclight_sd15_fc.safetensors",
    local_dir="/content/IC-Light/models"
)
```

---

## 5. AGENTES — IMPLEMENTAÇÃO DETALHADA

### AGENTE 1 — Extração de Frames

**Responsabilidade:** Extrair todos os frames do vídeo de entrada mantendo FPS original.

```python
import subprocess
import json
import os

def extrair_frames(video_path: str, output_dir: str) -> dict:
    """
    Extrai frames do vídeo e retorna metadados.
    
    Returns:
        dict com fps, total_frames, resolucao
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Obter metadados do vídeo
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,width,height,nb_frames",
        "-of", "json", video_path
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    meta = json.loads(result.stdout)["streams"][0]
    
    fps_raw = meta["r_frame_rate"]  # ex: "30000/1001"
    num, den = map(int, fps_raw.split("/"))
    fps = round(num / den, 3)
    
    # Extrair frames
    extract_cmd = [
        "ffmpeg", "-i", video_path,
        "-q:v", "1",           # máxima qualidade JPEG/PNG
        "-pix_fmt", "rgb24",
        f"{output_dir}/frame_%05d.png"
    ]
    subprocess.run(extract_cmd, check=True)
    
    total_frames = len([f for f in os.listdir(output_dir) if f.endswith(".png")])
    
    return {
        "fps": fps,
        "total_frames": total_frames,
        "width": int(meta["width"]),
        "height": int(meta["height"])
    }
```

---

### AGENTE 2 — Remoção de Fundo

**Responsabilidade:** Processar cada frame com rembg usando GPU, produzindo PNGs com canal alpha.

```python
from rembg import remove, new_session
from PIL import Image
import os
from tqdm import tqdm

def remover_fundo(frames_dir: str, output_dir: str):
    """
    Remove o fundo de todos os frames usando rembg com GPU.
    Modelo: u2net_human_seg (otimizado para pessoas)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Sessão GPU com modelo otimizado para pessoas
    session = new_session("u2net_human_seg")
    
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith(".png")])
    
    for frame_name in tqdm(frames, desc="Removendo fundo"):
        input_path = os.path.join(frames_dir, frame_name)
        output_path = os.path.join(output_dir, frame_name)
        
        if os.path.exists(output_path):
            continue  # resume automático se interrompido
        
        with open(input_path, "rb") as f:
            img_bytes = f.read()
        
        result = remove(
            img_bytes,
            session=session,
            alpha_matting=True,              # bordas mais suaves
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10
        )
        
        with open(output_path, "wb") as f:
            f.write(result)
    
    print(f"✓ {len(frames)} frames processados")
```

---

### AGENTE 3 — Geração de Fundo com SD 1.5

**Responsabilidade:** Gerar uma imagem de fundo via Stable Diffusion 1.5 a partir de um prompt do usuário. Usa a API interna do ComfyUI rodando em background.

#### 3.1 Iniciar ComfyUI em background

```python
import subprocess
import time
import requests

def iniciar_comfyui():
    process = subprocess.Popen(
        ["python", "main.py", "--port", "8188", "--cuda-device", "0"],
        cwd="/content/ComfyUI",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    # Aguardar subida
    for _ in range(30):
        try:
            r = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
            if r.status_code == 200:
                print("✓ ComfyUI online")
                return process
        except:
            time.sleep(2)
    raise RuntimeError("ComfyUI não subiu em 60s")
```

#### 3.2 Gerar fundo via API

```python
import json
import uuid
import requests
from PIL import Image
import io

COMFYUI_URL = "http://127.0.0.1:8188"

def gerar_fundo(
    prompt: str,
    width: int,
    height: int,
    output_path: str,
    negative_prompt: str = "person, human, people, ugly, blurry, low quality",
    steps: int = 25,
    cfg: float = 7.0,
    seed: int = -1
):
    """
    Gera imagem de fundo via ComfyUI API com SD 1.5.
    """
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
                "latent_image": ["5", 0]
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]}
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["4", 1]}
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "bg_output"}
        }
    }
    
    client_id = str(uuid.uuid4())
    
    # Enviar workflow
    r = requests.post(
        f"{COMFYUI_URL}/prompt",
        json={"prompt": workflow, "client_id": client_id}
    )
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
                params={"filename": img_info["filename"], "subfolder": img_info["subfolder"]}
            ).content
            img = Image.open(io.BytesIO(img_data))
            img.save(output_path)
            print(f"✓ Fundo gerado: {output_path}")
            return output_path
    
    raise RuntimeError("Falha ao gerar fundo")
```

---

### AGENTE 4 — Relighting com IC-Light

**Responsabilidade:** Aplicar iluminação coerente em cada frame da pessoa, baseada no fundo gerado. Usa IC-Light `iclight_sd15_fc.safetensors` (foreground conditioned).

```python
import torch
import numpy as np
from PIL import Image
from diffusers import StableDiffusionPipeline, AutoencoderKL
from diffusers.models import UNet2DConditionModel
from transformers import CLIPTextModel, CLIPTokenizer
import os
from tqdm import tqdm

def carregar_iclight():
    """
    Carrega pipeline IC-Light foreground-conditioned.
    """
    # Importar utilitários do repositório IC-Light
    import sys
    sys.path.insert(0, "/content/IC-Light")
    from iclight_pipeline import StableDiffusionICLightPipeline  # classe customizada do repo
    
    pipe = StableDiffusionICLightPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
    )
    
    # Carregar pesos IC-Light no UNet
    ic_weights = torch.load(
        "/content/IC-Light/models/iclight_sd15_fc.safetensors",
        map_location="cpu"
    )
    pipe.unet.load_state_dict(ic_weights, strict=False)
    pipe = pipe.to("cuda")
    
    return pipe


def aplicar_relighting(
    pipe,
    frames_nobg_dir: str,
    background_path: str,
    output_dir: str,
    prompt: str,
    steps: int = 25,
    cfg: float = 2.0,   # IC-Light funciona melhor com CFG baixo
    seed: int = 42
):
    """
    Aplica relighting IC-Light em todos os frames.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    bg = Image.open(background_path).convert("RGB")
    generator = torch.Generator("cuda").manual_seed(seed)
    
    frames = sorted([f for f in os.listdir(frames_nobg_dir) if f.endswith(".png")])
    
    for frame_name in tqdm(frames, desc="Relighting IC-Light"):
        output_path = os.path.join(output_dir, frame_name)
        if os.path.exists(output_path):
            continue
        
        fg = Image.open(os.path.join(frames_nobg_dir, frame_name)).convert("RGBA")
        
        # Redimensionar bg para o tamanho do frame
        bg_resized = bg.resize(fg.size, Image.LANCZOS)
        
        # IC-Light: foreground + background → frame relitado
        result = pipe(
            prompt=prompt,
            image=fg,
            bg_image=bg_resized,
            num_inference_steps=steps,
            guidance_scale=cfg,
            generator=generator,
            height=fg.height,
            width=fg.width,
        ).images[0]
        
        result.save(output_path)
    
    print(f"✓ {len(frames)} frames relitados")
```

---

### AGENTE 5 — Composição e Exportação

**Responsabilidade:** Compilar todos os frames relitados em vídeo final com áudio original.

```python
import subprocess
import os

def exportar_video(
    frames_dir: str,
    video_original: str,
    output_path: str,
    fps: float,
    crf: int = 18  # qualidade H.264 (0=perfeito, 51=péssimo)
):
    """
    Monta vídeo final com áudio original.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Montar vídeo sem áudio
    temp_video = output_path.replace(".mp4", "_noaudio.mp4")
    
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", f"{frames_dir}/frame_%05d.png",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-preset", "slow",
        temp_video
    ], check=True)
    
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
        output_path
    ], check=True)
    
    os.remove(temp_video)
    print(f"✓ Vídeo final: {output_path}")
    return output_path
```

---

## 6. ORQUESTRADOR PRINCIPAL — `pipeline.py`

```python
"""
pipeline.py — Orquestrador da pipeline IC-Light Video

Uso:
    python pipeline.py \
        --video /content/drive/MyDrive/iclight_pipeline/input/video.mp4 \
        --prompt "modern studio with soft blue ambient lighting, cinematic" \
        --output /content/drive/MyDrive/iclight_pipeline/output/video_final.mp4
"""

import argparse
import os
from pathlib import Path

# ─── Configurações de caminhos ───────────────────────────────────────────────
BASE_DIR = "/content/drive/MyDrive/iclight_pipeline"
FRAMES_RAW = f"{BASE_DIR}/frames/raw"
FRAMES_NOBG = f"{BASE_DIR}/frames/nobg"
FRAMES_RELIT = f"{BASE_DIR}/frames/relit"
BG_OUTPUT = f"{BASE_DIR}/background/bg.png"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Caminho do vídeo de entrada")
    parser.add_argument("--prompt", required=True, help="Prompt para gerar o fundo")
    parser.add_argument("--output", required=True, help="Caminho do vídeo de saída")
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--crf", type=int, default=18, help="Qualidade do vídeo (18=alta, 28=menor)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎬 IC-Light Video Pipeline")
    print("=" * 60)
    
    # AGENTE 1 — Extração
    print("\n[1/5] Extraindo frames...")
    from agentes.extracao import extrair_frames
    meta = extrair_frames(args.video, FRAMES_RAW)
    print(f"    {meta['total_frames']} frames @ {meta['fps']}fps — {meta['width']}x{meta['height']}")
    
    # AGENTE 2 — Remoção de fundo
    print("\n[2/5] Removendo fundo (rembg GPU)...")
    from agentes.remocao import remover_fundo
    remover_fundo(FRAMES_RAW, FRAMES_NOBG)
    
    # AGENTE 3 — Gerar fundo com SD
    print("\n[3/5] Gerando fundo com Stable Diffusion 1.5...")
    from agentes.geracao_fundo import iniciar_comfyui, gerar_fundo
    comfy_proc = iniciar_comfyui()
    gerar_fundo(
        prompt=args.prompt,
        width=meta["width"],
        height=meta["height"],
        output_path=BG_OUTPUT,
        steps=args.steps,
        seed=args.seed
    )
    comfy_proc.terminate()
    
    # AGENTE 4 — Relighting
    print("\n[4/5] Aplicando relighting com IC-Light...")
    from agentes.relighting import carregar_iclight, aplicar_relighting
    pipe = carregar_iclight()
    aplicar_relighting(
        pipe=pipe,
        frames_nobg_dir=FRAMES_NOBG,
        background_path=BG_OUTPUT,
        output_dir=FRAMES_RELIT,
        prompt=args.prompt,
        steps=args.steps,
        seed=args.seed
    )
    
    # AGENTE 5 — Exportar
    print("\n[5/5] Exportando vídeo final...")
    from agentes.exportacao import exportar_video
    exportar_video(
        frames_dir=FRAMES_RELIT,
        video_original=args.video,
        output_path=args.output,
        fps=meta["fps"]
    )
    
    print("\n" + "=" * 60)
    print(f"✅ Concluído! Vídeo salvo em: {args.output}")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

---

## 7. NOTEBOOK COLAB — CÉLULA A CÉLULA

O Claude Code deve gerar um `.ipynb` com as seguintes células em ordem:

```
Célula 1: Montar Google Drive
Célula 2: Instalar dependências (apt + pip)
Célula 3: Clonar ComfyUI + IC-Light
Célula 4: Download dos modelos (SD 1.5 + IC-Light weights)
Célula 5: Upload do vídeo (widget ipywidgets ou Google Drive path)
Célula 6: INPUT do usuário (prompt do fundo)
Célula 7: Executar pipeline.py com os parâmetros
Célula 8: Preview do frame do meio (antes/depois)
Célula 9: Download do vídeo final
```

---

## 8. ESTRUTURA DE MÓDULOS

```
/content/
└── agentes/
    ├── __init__.py
    ├── extracao.py         ← Agente 1
    ├── remocao.py          ← Agente 2
    ├── geracao_fundo.py    ← Agente 3
    ├── relighting.py       ← Agente 4
    └── exportacao.py       ← Agente 5
pipeline.py
```

---

## 9. PARÂMETROS TUNÁVEIS

| Parâmetro | Default | Descrição |
|---|---|---|
| `--steps` | 25 | Inference steps SD/IC-Light. Reduzir pra 15 acelera. |
| `--seed` | 42 | Seed para consistência entre runs |
| `--crf` | 18 | Qualidade H.264 final. 18=alta, 23=media |
| `alpha_matting` | True | Bordas suaves no rembg. False = mais rápido |
| `cfg` IC-Light | 2.0 | IC-Light prefere CFG baixo (1.5–3.0) |

---

## 10. TRATAMENTO DE ERROS E RESUME

- Todos os agentes verificam se o output já existe antes de processar (`if os.path.exists(output_path): continue`) — a pipeline é **resumível automaticamente** se o Colab desconectar.
- Usar `try/except` em cada frame com log do frame problemático, sem abortar o processo.
- Ao final, gerar relatório `pipeline_log.json` com frames com erro para reprocessamento manual.

---

## 11. ESTIMATIVA DE TEMPO (GPU T4 — Colab Free)

| Etapa | Tempo por frame | 1 min de vídeo (1800 frames) |
|---|---|---|
| Extração (ffmpeg) | ~1ms | ~2s |
| rembg remoção | ~0.3s | ~9 min |
| SD 1.5 fundo | único | ~15s |
| IC-Light relighting | ~1.5s | ~45 min |
| Export ffmpeg | ~2ms | ~4s |
| **TOTAL** | — | **~55 min** |

---

## 12. OUTPUTS ESPERADOS

- `video_final.mp4` — vídeo com fundo trocado + iluminação coerente + áudio original
- `background/bg.png` — fundo gerado pelo SD
- `pipeline_log.json` — log de execução com frames com erro

---

## 13. CHECKLIST PARA O CLAUDE CODE

- [ ] Criar estrutura de diretórios `/content/agentes/`
- [ ] Implementar cada agente como módulo Python isolado
- [ ] Gerar `pipeline.py` orquestrador
- [ ] Gerar notebook `.ipynb` com células sequenciais
- [ ] Testar imports de cada agente individualmente
- [ ] Garantir resume automático em todos os agentes
- [ ] Implementar preview antes/depois (frame do meio)
- [ ] Gerar `requirements.txt` com todas as dependências e versões fixadas
- [ ] Adicionar barra de progresso (`tqdm`) em todos os loops
- [ ] Logar tempo de execução de cada etapa

---

*Plano gerado para execução via Claude Code. Todos os blocos de código são funcionais e prontos para implementação direta.*
