"""
Agente 4 — Relighting com IC-Light
Aplica iluminação coerente em cada frame da pessoa, baseada no fundo gerado.
Usa IC-Light foreground-conditioned (iclight_sd15_fc).
"""

import os
import time
import json

import torch
import numpy as np
from PIL import Image
from diffusers import StableDiffusionPipeline
from safetensors.torch import load_file
from tqdm import tqdm


def carregar_iclight(
    iclight_dir: str = "/content/IC-Light",
    model_path: str = "/content/IC-Light/models/iclight_sd15_fc.safetensors",
):
    """
    Carrega pipeline IC-Light foreground-conditioned.
    Modifica o UNet do SD 1.5 para aceitar 8 canais (4 latent + 4 concat cond).
    """
    print("  Carregando SD 1.5 base...")
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
        safety_checker=None,
    )

    # Modificar input do UNet para 8 canais (IC-Light foreground conditioned)
    with torch.no_grad():
        original_conv = pipe.unet.conv_in
        new_conv = torch.nn.Conv2d(
            8, original_conv.out_channels,
            original_conv.kernel_size,
            original_conv.stride,
            original_conv.padding,
        )
        new_conv.weight.zero_()
        new_conv.weight[:, :4, :, :].copy_(original_conv.weight)
        new_conv.bias.copy_(original_conv.bias)
        pipe.unet.conv_in = new_conv

    # Carregar pesos IC-Light
    print("  Carregando pesos IC-Light...")
    ic_weights = load_file(model_path)
    pipe.unet.load_state_dict(ic_weights, strict=False)
    pipe = pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)

    print("  IC-Light pronto")
    return pipe


def _encode_image_to_latent(pipe, image, generator=None):
    """Codifica imagem PIL para latent space via VAE."""
    image_np = np.array(image).astype(np.float32) / 255.0
    image_tensor = torch.from_numpy(image_np).permute(2, 0, 1).unsqueeze(0)
    image_tensor = image_tensor.to(device=pipe.device, dtype=pipe.unet.dtype)
    image_tensor = image_tensor * 2.0 - 1.0
    latent = pipe.vae.encode(image_tensor).latent_dist.sample(generator)
    latent = latent * pipe.vae.config.scaling_factor
    return latent


def aplicar_relighting(
    pipe,
    frames_nobg_dir: str,
    background_path: str,
    output_dir: str,
    prompt: str,
    steps: int = 25,
    cfg: float = 2.0,
    seed: int = 42,
    log_path: str = None,
):
    """
    Aplica relighting IC-Light em todos os frames.
    Suporta resume automático — pula frames já processados.
    """
    os.makedirs(output_dir, exist_ok=True)

    bg = Image.open(background_path).convert("RGB")
    generator = torch.Generator("cuda").manual_seed(seed)

    frames = sorted([f for f in os.listdir(frames_nobg_dir) if f.endswith(".png")])
    erros = []

    start = time.time()

    # Encode prompt uma vez
    text_inputs = pipe.tokenizer(
        prompt, padding="max_length",
        max_length=pipe.tokenizer.model_max_length,
        return_tensors="pt",
    )
    prompt_embeds = pipe.text_encoder(text_inputs.input_ids.to(pipe.device))[0]

    # Negative prompt (vazio)
    uncond_inputs = pipe.tokenizer(
        "", padding="max_length",
        max_length=pipe.tokenizer.model_max_length,
        return_tensors="pt",
    )
    negative_embeds = pipe.text_encoder(uncond_inputs.input_ids.to(pipe.device))[0]

    for frame_name in tqdm(frames, desc="Relighting IC-Light"):
        output_path = os.path.join(output_dir, frame_name)
        if os.path.exists(output_path):
            continue

        try:
            fg = Image.open(os.path.join(frames_nobg_dir, frame_name)).convert("RGBA")

            # Extrair foreground em RGB (alpha sobre cinza neutro)
            fg_rgb = Image.new("RGB", fg.size, (127, 127, 127))
            fg_rgb.paste(fg, (0, 0), fg)

            # Resize para múltiplo de 8
            w, h = fg.size
            w8 = (w // 8) * 8
            h8 = (h // 8) * 8
            fg_rgb = fg_rgb.resize((w8, h8), Image.LANCZOS)

            # Encode foreground como condição concat
            fg_latent = _encode_image_to_latent(pipe, fg_rgb, generator)

            # Gerar noise
            latents = torch.randn_like(fg_latent)

            # Scheduler setup
            pipe.scheduler.set_timesteps(steps, device=pipe.device)
            timesteps = pipe.scheduler.timesteps
            latents = latents * pipe.scheduler.init_noise_sigma

            # Denoising loop com concat conditioning
            for t in timesteps:
                latent_input = pipe.scheduler.scale_model_input(latents, t)
                # Concatenar foreground latent como condição
                latent_input = torch.cat([latent_input, fg_latent], dim=1)

                with torch.no_grad():
                    # Classifier-free guidance
                    noise_cond = pipe.unet(
                        latent_input, t,
                        encoder_hidden_states=prompt_embeds,
                    ).sample
                    noise_uncond = pipe.unet(
                        latent_input, t,
                        encoder_hidden_states=negative_embeds,
                    ).sample
                    noise_pred = noise_uncond + cfg * (noise_cond - noise_uncond)

                latents = pipe.scheduler.step(noise_pred, t, latents).prev_sample

            # Decode
            with torch.no_grad():
                decoded = pipe.vae.decode(latents / pipe.vae.config.scaling_factor).sample
            decoded = (decoded / 2 + 0.5).clamp(0, 1)
            result_np = (decoded[0].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
            result_img = Image.fromarray(result_np)

            # Resize de volta ao tamanho original
            if result_img.size != (w, h):
                result_img = result_img.resize((w, h), Image.LANCZOS)

            result_img.save(output_path)

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
        log_data["relighting_erros"] = erros
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)

    processados = len(frames) - len(erros)
    print(f"  {processados}/{len(frames)} frames relitados ({elapsed}s)")
    return {"processados": processados, "erros": len(erros), "tempo_s": elapsed}
