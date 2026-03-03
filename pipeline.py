"""
pipeline.py — Orquestrador da pipeline IC-Light Video

Uso:
    python pipeline.py \
        --video /content/drive/MyDrive/iclight_pipeline/input/video.mp4 \
        --prompt "modern studio with soft blue ambient lighting, cinematic" \
        --output /content/drive/MyDrive/iclight_pipeline/output/video_final.mp4
"""

import argparse
import json
import os
import time
from pathlib import Path

# Caminhos base
BASE_DIR = "/content/drive/MyDrive/iclight_pipeline"
FRAMES_RAW = f"{BASE_DIR}/frames/raw"
FRAMES_NOBG = f"{BASE_DIR}/frames/nobg"
FRAMES_RELIT = f"{BASE_DIR}/relit"
BG_OUTPUT = f"{BASE_DIR}/background/bg.png"
LOG_PATH = f"{BASE_DIR}/pipeline_log.json"


def main():
    parser = argparse.ArgumentParser(description="IC-Light Video Pipeline")
    parser.add_argument("--video", required=True, help="Caminho do video de entrada")
    parser.add_argument("--prompt", required=True, help="Prompt para gerar o fundo")
    parser.add_argument("--output", required=True, help="Caminho do video de saida")
    parser.add_argument("--steps", type=int, default=25, help="Inference steps SD/IC-Light")
    parser.add_argument("--seed", type=int, default=42, help="Seed para reproducibilidade")
    parser.add_argument("--crf", type=int, default=18, help="Qualidade H.264 (18=alta, 28=menor)")
    parser.add_argument("--cfg-bg", type=float, default=7.0, help="CFG scale para geracao de fundo")
    parser.add_argument("--cfg-relight", type=float, default=2.0, help="CFG scale para IC-Light")
    args = parser.parse_args()

    pipeline_log = {"etapas": [], "erros_total": 0}
    pipeline_start = time.time()

    print("=" * 60)
    print("  IC-Light Video Pipeline — lumina-bg")
    print("=" * 60)

    # ─── AGENTE 1 — Extração de Frames ───────────────────────────
    print("\n[1/5] Extraindo frames...")
    from agentes.extracao import extrair_frames

    meta = extrair_frames(args.video, FRAMES_RAW)
    print(f"    {meta['total_frames']} frames @ {meta['fps']}fps — {meta['width']}x{meta['height']}")
    pipeline_log["etapas"].append({"etapa": "extracao", **meta})

    # ─── AGENTE 2 — Remoção de Fundo ─────────────────────────────
    print("\n[2/5] Removendo fundo (rembg GPU)...")
    from agentes.remocao import remover_fundo

    result_rembg = remover_fundo(FRAMES_RAW, FRAMES_NOBG, log_path=LOG_PATH)
    pipeline_log["etapas"].append({"etapa": "remocao_fundo", **result_rembg})
    pipeline_log["erros_total"] += result_rembg["erros"]

    # ─── AGENTE 3 — Geração de Fundo com SD 1.5 ──────────────────
    print("\n[3/5] Gerando fundo com Stable Diffusion 1.5...")
    from agentes.geracao_fundo import iniciar_comfyui, gerar_fundo

    comfy_proc = iniciar_comfyui()
    try:
        gerar_fundo(
            prompt=args.prompt,
            width=meta["width"],
            height=meta["height"],
            output_path=BG_OUTPUT,
            steps=args.steps,
            cfg=args.cfg_bg,
            seed=args.seed,
        )
        pipeline_log["etapas"].append({"etapa": "geracao_fundo", "status": "ok"})
    finally:
        comfy_proc.terminate()

    # ─── AGENTE 4 — Relighting com IC-Light ───────────────────────
    print("\n[4/5] Aplicando relighting com IC-Light...")
    from agentes.relighting import carregar_iclight, aplicar_relighting

    pipe = carregar_iclight()
    result_relight = aplicar_relighting(
        pipe=pipe,
        frames_nobg_dir=FRAMES_NOBG,
        background_path=BG_OUTPUT,
        output_dir=FRAMES_RELIT,
        prompt=args.prompt,
        steps=args.steps,
        cfg=args.cfg_relight,
        seed=args.seed,
        log_path=LOG_PATH,
    )
    pipeline_log["etapas"].append({"etapa": "relighting", **result_relight})
    pipeline_log["erros_total"] += result_relight["erros"]

    # Liberar VRAM
    del pipe
    import torch
    torch.cuda.empty_cache()

    # ─── AGENTE 5 — Exportação ────────────────────────────────────
    print("\n[5/5] Exportando video final...")
    from agentes.exportacao import exportar_video

    result_export = exportar_video(
        frames_dir=FRAMES_RELIT,
        video_original=args.video,
        output_path=args.output,
        fps=meta["fps"],
        crf=args.crf,
    )
    pipeline_log["etapas"].append({"etapa": "exportacao", **result_export})

    # ─── Relatório final ──────────────────────────────────────────
    pipeline_log["tempo_total_s"] = round(time.time() - pipeline_start, 2)

    with open(LOG_PATH, "w") as f:
        json.dump(pipeline_log, f, indent=2)

    print("\n" + "=" * 60)
    print(f"  Concluido! Video salvo em: {args.output}")
    print(f"  Tempo total: {pipeline_log['tempo_total_s']}s")
    if pipeline_log["erros_total"] > 0:
        print(f"  AVISO: {pipeline_log['erros_total']} frame(s) com erro — ver {LOG_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
