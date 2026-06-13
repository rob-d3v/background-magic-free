"""
Agente 4 — Relighting com IC-Light (fbc — foreground + background conditioned)

Coloca a pessoa recortada DENTRO do fundo escolhido e reilumina para casar com
ele. Usa iclight_sd15_fbc: UNet de 12 canais (4 noisy + 4 fg + 4 bg). A saida
ja vem com a pessoa composta no ambiente — nao precisa de composicao extra.

Correcoes vs versao fc anterior (que tinha 2 bugs):
  1. O fundo agora E usado (condicao bg). Antes bg.png era carregado e ignorado.
  2. Pesos IC-Light sao OFFSET/DELTA: somados aos pesos base da UNet
     (sd_merged = base + offset, strict=True). Antes usava strict=False, que
     sobrescrevia a UNet com deltas crus -> relight quebrado.

Expoe:
  - carregar_iclight()      -> pipe pronto (UNet 12ch, scheduler DPM++ SDE Karras)
  - relight_frame()         -> reilumina UM frame (PIL) — usado no preview
  - aplicar_relighting()    -> batch com resume automatico
"""

import os
import time
import json

import torch
import numpy as np
from PIL import Image
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from safetensors.torch import load_file
from tqdm import tqdm

from huggingface_hub import hf_hub_download


FBC_REPO = "lllyasviel/ic-light"
FBC_FILE = "iclight_sd15_fbc.safetensors"
BASE_SD15 = "stablediffusionapi/realistic-vision-v51"


def _baixar_pesos_fbc(model_path: str | None) -> str:
    """Resolve o caminho dos pesos fbc: usa o local se existir, senao baixa do HF."""
    if model_path and os.path.exists(model_path):
        return model_path
    return hf_hub_download(repo_id=FBC_REPO, filename=FBC_FILE)


def carregar_iclight(
    model_path: str | None = None,
    base_model: str = BASE_SD15,
    device: str = "cuda",
    low_vram: bool = False,
):
    """
    Carrega pipeline IC-Light fbc (foreground + background conditioned).

    - Expande conv_in de 4 -> 12 canais (4 noisy + 4 fg + 4 bg), zero-init nos novos.
    - Carrega os pesos IC-Light como OFFSET somado a UNet base (strict=True).
    - Scheduler DPM++ 2M SDE Karras (recomendado pelo demo oficial).
    """
    print("  Carregando SD 1.5 base...")
    pipe = StableDiffusionPipeline.from_pretrained(
        base_model,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        safety_checker=None,
    )

    unet = pipe.unet
    with torch.no_grad():
        original_conv = unet.conv_in
        new_conv = torch.nn.Conv2d(
            12, original_conv.out_channels,
            original_conv.kernel_size,
            original_conv.stride,
            original_conv.padding,
        )
        new_conv.weight.zero_()
        new_conv.weight[:, :4, :, :].copy_(original_conv.weight)
        new_conv.bias.copy_(original_conv.bias)
        unet.conv_in = new_conv

    # IC-Light = offset/delta -> somar aos pesos base (strict=True)
    print("  Carregando pesos IC-Light fbc (offset-merge)...")
    weights_file = _baixar_pesos_fbc(model_path)
    offset = load_file(weights_file)
    origin = unet.state_dict()
    merged = {}
    for k in origin.keys():
        if k in offset:
            merged[k] = origin[k] + offset[k]
        else:
            merged[k] = origin[k]
    unet.load_state_dict(merged, strict=True)

    pipe.scheduler = DPMSolverMultistepScheduler(
        num_train_timesteps=1000,
        beta_start=0.00085,
        beta_end=0.012,
        algorithm_type="sde-dpmsolver++",
        use_karras_sigmas=True,
        steps_offset=1,
    )

    if device == "cuda":
        if low_vram:
            # GPUs pequenas (ex: 4GB): offload sequencial + slicing
            pipe.enable_sequential_cpu_offload()
            pipe.enable_attention_slicing()
            pipe.enable_vae_slicing()
        else:
            pipe = pipe.to("cuda")
    else:
        pipe = pipe.to("cpu")

    pipe.set_progress_bar_config(disable=True)
    print("  IC-Light fbc pronto")
    return pipe


# ─── Pre-processamento ────────────────────────────────────────────────────

def _resize_center_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    """Redimensiona cobrindo w x h e corta o centro (resize_and_center_crop)."""
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(round(iw * scale)), int(round(ih * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _mult64(x: int) -> int:
    return max(64, (x // 64) * 64)


def _fg_sobre_cinza(fg_rgba: Image.Image) -> Image.Image:
    """Compoe o recorte (RGBA) sobre cinza neutro 127, como no demo oficial."""
    base = Image.new("RGB", fg_rgba.size, (127, 127, 127))
    base.paste(fg_rgba, (0, 0), fg_rgba)
    return base


def _encode(pipe, img_rgb: Image.Image) -> torch.Tensor:
    """VAE-encode deterministico (.mode()) de uma imagem PIL RGB."""
    arr = np.array(img_rgb).astype(np.float32) / 255.0
    t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    t = t.to(device=pipe.vae.device, dtype=pipe.vae.dtype)
    t = t * 2.0 - 1.0
    latent = pipe.vae.encode(t).latent_dist.mode()
    return latent * pipe.vae.config.scaling_factor


# ─── Relight de um frame (usado no preview e no batch) ─────────────────────

def relight_frame(
    pipe,
    fg_rgba: Image.Image,
    bg_rgb: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    steps: int = 20,
    cfg: float = 7.0,
    seed: int = 12345,
    largura: int | None = None,
    altura: int | None = None,
) -> Image.Image:
    """
    Reilumina UM frame: pessoa (fg_rgba, com alpha) dentro do fundo (bg_rgb).
    Retorna PIL RGB com a pessoa composta e reiluminada no ambiente.
    """
    device = pipe.vae.device if hasattr(pipe, "vae") else "cuda"

    # Dimensoes alvo (multiplo de 64)
    if largura is None or altura is None:
        w0, h0 = fg_rgba.size
        largura = _mult64(w0)
        altura = _mult64(h0)
    else:
        largura, altura = _mult64(largura), _mult64(altura)

    fg = _fg_sobre_cinza(fg_rgba)
    fg = _resize_center_crop(fg, largura, altura)
    bg = _resize_center_crop(bg_rgb.convert("RGB"), largura, altura)

    generator = torch.Generator(device="cpu").manual_seed(seed)

    with torch.no_grad():
        fg_latent = _encode(pipe, fg)
        bg_latent = _encode(pipe, bg)

        # Embeddings de texto (cond e uncond)
        def _embed(text):
            ids = pipe.tokenizer(
                text, padding="max_length",
                max_length=pipe.tokenizer.model_max_length,
                truncation=True, return_tensors="pt",
            ).input_ids.to(pipe.text_encoder.device)
            return pipe.text_encoder(ids)[0]

        prompt_embeds = _embed(prompt)
        negative_embeds = _embed(negative_prompt)

        # Latent inicial
        lh, lw = altura // 8, largura // 8
        latents = torch.randn(
            (1, 4, lh, lw), generator=generator, dtype=fg_latent.dtype
        ).to(fg_latent.device)

        pipe.scheduler.set_timesteps(steps, device=fg_latent.device)
        latents = latents * pipe.scheduler.init_noise_sigma

        for t in pipe.scheduler.timesteps:
            scaled = pipe.scheduler.scale_model_input(latents, t)
            # 12 canais: noisy + fg + bg
            model_in = torch.cat([scaled, fg_latent, bg_latent], dim=1)

            noise_cond = pipe.unet(model_in, t, encoder_hidden_states=prompt_embeds).sample
            noise_uncond = pipe.unet(model_in, t, encoder_hidden_states=negative_embeds).sample
            noise_pred = noise_uncond + cfg * (noise_cond - noise_uncond)

            latents = pipe.scheduler.step(noise_pred, t, latents).prev_sample

        decoded = pipe.vae.decode(latents / pipe.vae.config.scaling_factor).sample

    decoded = (decoded / 2 + 0.5).clamp(0, 1)
    out = (decoded[0].permute(1, 2, 0).float().cpu().numpy() * 255).astype(np.uint8)
    return Image.fromarray(out)


# ─── Batch ─────────────────────────────────────────────────────────────────

def aplicar_relighting(
    pipe,
    frames_nobg_dir: str,
    background_path: str,
    output_dir: str,
    prompt: str,
    negative_prompt: str = "",
    steps: int = 20,
    cfg: float = 7.0,
    seed: int = 12345,
    largura: int | None = None,
    altura: int | None = None,
    log_path: str = None,
    progress_cb=None,
):
    """
    Aplica relighting fbc em todos os frames. Resume automatico (pula prontos).
    A resolucao de saida (largura/altura) e fixa para todos os frames para o
    video ficar consistente; se None, deriva do primeiro frame.
    """
    os.makedirs(output_dir, exist_ok=True)
    bg = Image.open(background_path).convert("RGB")

    frames = sorted(f for f in os.listdir(frames_nobg_dir) if f.endswith(".png"))
    if not frames:
        return {"processados": 0, "erros": 0, "tempo_s": 0.0}

    # Fixar dimensoes a partir do primeiro frame (multiplo de 64)
    if largura is None or altura is None:
        w0, h0 = Image.open(os.path.join(frames_nobg_dir, frames[0])).size
        largura, altura = _mult64(w0), _mult64(h0)

    erros = []
    start = time.time()

    for i, frame_name in enumerate(tqdm(frames, desc="Relighting IC-Light fbc")):
        output_path = os.path.join(output_dir, frame_name)
        if os.path.exists(output_path):
            if progress_cb:
                progress_cb(i + 1, len(frames))
            continue
        try:
            fg = Image.open(os.path.join(frames_nobg_dir, frame_name)).convert("RGBA")
            out = relight_frame(
                pipe, fg, bg, prompt,
                negative_prompt=negative_prompt,
                steps=steps, cfg=cfg, seed=seed,
                largura=largura, altura=altura,
            )
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
        log_data["relighting_erros"] = erros
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)

    processados = len(frames) - len(erros)
    print(f"  {processados}/{len(frames)} frames relitados ({elapsed}s)")
    return {
        "processados": processados, "erros": len(erros),
        "tempo_s": elapsed, "largura": largura, "altura": altura,
    }
