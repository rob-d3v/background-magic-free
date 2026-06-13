"""
config.py — Configuracao central de paths e deteccao de ambiente.

Resolve onde a pipeline guarda os arquivos de trabalho (workspace) e detecta
se ha GPU CUDA disponivel. Funciona em 3 ambientes:

  - Local (Windows/Linux): workspace em ./workspace (ou env LUMINA_BASE)
  - Google Colab: workspace em /content/drive/MyDrive/iclight_pipeline
  - Custom: via env var LUMINA_BASE ou argumento --base

Antes os paths eram hardcoded para /content/drive/... (so Colab). Agora sao
resolvidos dinamicamente para rodar local e no Colab.
"""

import os


def _em_colab() -> bool:
    """Detecta se estamos rodando no Google Colab."""
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def resolver_base(base: str | None = None) -> str:
    """
    Resolve o diretorio base do workspace.

    Prioridade:
      1. argumento `base` explicito
      2. env var LUMINA_BASE
      3. /content/drive/MyDrive/iclight_pipeline  (se Colab com Drive montado)
      4. ./workspace  (local)
    """
    if base:
        return os.path.abspath(base)

    env_base = os.environ.get("LUMINA_BASE")
    if env_base:
        return os.path.abspath(env_base)

    if _em_colab():
        drive_base = "/content/drive/MyDrive/iclight_pipeline"
        if os.path.isdir("/content/drive/MyDrive"):
            return drive_base

    return os.path.abspath("./workspace")


class Paths:
    """Container de paths derivados do diretorio base."""

    def __init__(self, base: str | None = None):
        self.base = resolver_base(base)
        self.input = f"{self.base}/input"
        self.frames_raw = f"{self.base}/frames/raw"
        self.frames_nobg = f"{self.base}/frames/nobg"
        self.frames_relit = f"{self.base}/relit"
        self.background_dir = f"{self.base}/background"
        self.bg_output = f"{self.background_dir}/bg.png"
        self.preview_dir = f"{self.base}/preview"
        self.output_dir = f"{self.base}/output"
        self.log_path = f"{self.base}/pipeline_log.json"

    def criar_dirs(self):
        for d in (
            self.input, self.frames_raw, self.frames_nobg, self.frames_relit,
            self.background_dir, self.preview_dir, self.output_dir,
        ):
            os.makedirs(d, exist_ok=True)
        return self


def detectar_device() -> dict:
    """
    Detecta capacidade de compute.

    Returns dict:
      device: "cuda" | "cpu"
      cuda: bool
      gpu_name: str | None
      vram_gb: float | None
      pode_relight: bool  (True se ha GPU CUDA com VRAM suficiente)
    """
    info = {
        "device": "cpu",
        "cuda": False,
        "gpu_name": None,
        "vram_gb": None,
        "pode_relight": False,
    }
    try:
        import torch
        if torch.cuda.is_available():
            info["device"] = "cuda"
            info["cuda"] = True
            info["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            vram = round(props.total_memory / (1024 ** 3), 1)
            info["vram_gb"] = vram
            # IC-Light SD1.5 fp16 precisa ~6GB confortavel; 4GB e arriscado mas
            # tentavel com offload. Marcamos pode_relight com folga >= 5GB.
            info["pode_relight"] = vram >= 5.0
    except Exception:
        pass
    return info
