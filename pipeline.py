"""
pipeline.py — Orquestrador da pipeline lumina-bg (IC-Light Video)

Roda local e no Colab. Paths resolvidos por config.py (nao mais hardcoded).
Device (GPU/CPU) detectado automaticamente; sem GPU usa modo "compose" (sem
relight). Com GPU usa IC-Light fbc (pessoa composta no fundo + reiluminada).

Exemplos:
    # fundo gerado por IA (precisa GPU)
    python pipeline.py --video meu.mp4 --prompt "modern studio, blue ambient light"

    # fundo proprio
    python pipeline.py --video meu.mp4 --background fundo.png --prompt "soft light"

    # forcar so composicao (sem relight, roda em CPU)
    python pipeline.py --video meu.mp4 --background fundo.png --modo compose
"""

import argparse
import json
import os
import time

from PIL import Image

from config import Paths, detectar_device


def main():
    parser = argparse.ArgumentParser(description="lumina-bg — IC-Light Video Pipeline")
    parser.add_argument("--video", required=True, help="Caminho do video de entrada")
    parser.add_argument("--prompt", default="cinematic lighting", help="Prompt p/ relight e geracao de fundo")
    parser.add_argument("--output", default=None, help="Caminho do video final (default: <base>/output/video_final.mp4)")
    parser.add_argument("--background", default=None, help="Imagem de fundo propria (pula geracao por IA)")
    parser.add_argument("--base", default=None, help="Diretorio de trabalho (default: ./workspace ou Drive no Colab)")
    parser.add_argument("--modo", choices=["auto", "relight", "compose"], default="auto",
                        help="relight=IC-Light (GPU); compose=so alpha (CPU); auto=decide por GPU")
    parser.add_argument("--steps", type=int, default=20, help="Inference steps SD/IC-Light")
    parser.add_argument("--seed", type=int, default=12345, help="Seed para reproducibilidade")
    parser.add_argument("--crf", type=int, default=18, help="Qualidade H.264 (18=alta, 28=menor)")
    parser.add_argument("--cfg-bg", type=float, default=7.0, help="CFG scale p/ geracao de fundo")
    parser.add_argument("--cfg-relight", type=float, default=7.0, help="CFG scale p/ IC-Light fbc")
    parser.add_argument("--negative", default="", help="Negative prompt p/ relight")
    args = parser.parse_args()

    paths = Paths(args.base).criar_dirs()
    output = args.output or f"{paths.output_dir}/video_final.mp4"
    dev = detectar_device()

    # Decidir modo
    modo = args.modo
    if modo == "auto":
        modo = "relight" if dev["pode_relight"] else "compose"

    usar_fundo_proprio = args.background is not None

    pipeline_log = {"etapas": [], "erros_total": 0, "device": dev, "modo": modo}
    pipeline_start = time.time()

    print("=" * 60)
    print("  lumina-bg — IC-Light Video Pipeline")
    print(f"  Device: {dev['device']} ({dev['gpu_name'] or 'sem GPU'}, "
          f"{dev['vram_gb'] or '?'}GB)  |  Modo: {modo}")
    print(f"  Fundo: {'proprio' if usar_fundo_proprio else 'gerado por IA'}")
    print(f"  Workspace: {paths.base}")
    print("=" * 60)

    if modo == "relight" and not dev["pode_relight"]:
        print("  AVISO: modo relight pedido mas sem GPU suficiente. "
              "Caindo para 'compose'.")
        modo = "compose"

    # ─── AGENTE 1 — Extracao ──────────────────────────────────────
    print("\n[1/5] Extraindo frames...")
    from agentes.extracao import extrair_frames
    meta = extrair_frames(args.video, paths.frames_raw)
    print(f"    {meta['total_frames']} frames @ {meta['fps']}fps — {meta['width']}x{meta['height']}")
    pipeline_log["etapas"].append({"etapa": "extracao", **meta})

    # ─── AGENTE 2 — Remocao de fundo ──────────────────────────────
    print("\n[2/5] Removendo fundo (rembg)...")
    from agentes.remocao import remover_fundo
    result_rembg = remover_fundo(paths.frames_raw, paths.frames_nobg, log_path=paths.log_path)
    pipeline_log["etapas"].append({"etapa": "remocao_fundo", **result_rembg})
    pipeline_log["erros_total"] += result_rembg["erros"]

    # ─── AGENTE 3 — Fundo ─────────────────────────────────────────
    if usar_fundo_proprio:
        print(f"\n[3/5] Usando fundo proprio: {args.background}")
        bg_img = Image.open(args.background).convert("RGB")
        bg_img = bg_img.resize((meta["width"], meta["height"]), Image.LANCZOS)
        bg_img.save(paths.bg_output)
        pipeline_log["etapas"].append({"etapa": "fundo", "modo": "proprio"})
    else:
        print("\n[3/5] Gerando fundo com Stable Diffusion 1.5...")
        from agentes.geracao_fundo import iniciar_comfyui, gerar_fundo
        comfy_proc = iniciar_comfyui()
        try:
            gerar_fundo(
                prompt=args.prompt, width=meta["width"], height=meta["height"],
                output_path=paths.bg_output, steps=args.steps, cfg=args.cfg_bg, seed=args.seed,
            )
            pipeline_log["etapas"].append({"etapa": "fundo", "modo": "ia"})
        finally:
            comfy_proc.terminate()

    # ─── AGENTE 4 — Relight (fbc) ou Compose ──────────────────────
    if modo == "relight":
        print("\n[4/5] Relighting com IC-Light fbc...")
        from agentes.relighting import carregar_iclight, aplicar_relighting
        low_vram = (dev["vram_gb"] or 99) < 8.0
        pipe = carregar_iclight(device="cuda", low_vram=low_vram)
        result = aplicar_relighting(
            pipe=pipe, frames_nobg_dir=paths.frames_nobg, background_path=paths.bg_output,
            output_dir=paths.frames_relit, prompt=args.prompt, negative_prompt=args.negative,
            steps=args.steps, cfg=args.cfg_relight, seed=args.seed, log_path=paths.log_path,
        )
        del pipe
        import torch
        torch.cuda.empty_cache()
        pipeline_log["etapas"].append({"etapa": "relighting", **result})
        pipeline_log["erros_total"] += result["erros"]
    else:
        print("\n[4/5] Compondo pessoa no fundo (modo compose, CPU)...")
        from agentes.composicao import compor_batch
        result = compor_batch(
            frames_nobg_dir=paths.frames_nobg, background_path=paths.bg_output,
            output_dir=paths.frames_relit, log_path=paths.log_path,
        )
        pipeline_log["etapas"].append({"etapa": "composicao", **result})
        pipeline_log["erros_total"] += result["erros"]

    # ─── AGENTE 5 — Exportacao ────────────────────────────────────
    print("\n[5/5] Exportando video final...")
    from agentes.exportacao import exportar_video
    result_export = exportar_video(
        frames_dir=paths.frames_relit, video_original=args.video,
        output_path=output, fps=meta["fps"], crf=args.crf,
    )
    pipeline_log["etapas"].append({"etapa": "exportacao", **result_export})

    pipeline_log["tempo_total_s"] = round(time.time() - pipeline_start, 2)
    with open(paths.log_path, "w") as f:
        json.dump(pipeline_log, f, indent=2)

    print("\n" + "=" * 60)
    print(f"  Concluido! Video salvo em: {output}")
    print(f"  Tempo total: {pipeline_log['tempo_total_s']}s")
    if pipeline_log["erros_total"] > 0:
        print(f"  AVISO: {pipeline_log['erros_total']} frame(s) com erro — ver {paths.log_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
