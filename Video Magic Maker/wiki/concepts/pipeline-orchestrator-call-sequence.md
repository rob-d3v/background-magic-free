---
title: Pipeline Orchestrator — sequência completa de chamadas
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["pipeline.py", "config.py"]
tags: [concept, orchestrator, pipeline, call-sequence, data-flow]
status: stable
---
# Pipeline Orchestrator — sequência completa de chamadas

Visão end-to-end de tudo que `pipeline.py` faz desde a invocação CLI até a escrita do log final. Complementa [[entities/pipeline]] (o que o orquestrador faz) e [[concepts/pipeline-orchestrator-mode-selection]] (a lógica de modo).

## Diagrama de sequência

```
CLI: python pipeline.py --video <v> [--background <b>] [--modo <m>] ...
│
├─ 1. argparse.parse_args()
│     → args.video, args.prompt, args.background, args.modo, args.steps, ...
│
├─ 2. Paths(args.base).criar_dirs()   → paths (workspace criado em disco)
│     output = args.output or "{paths.output_dir}/video_final.mp4"
│
├─ 3. detectar_device()               → dev {"device", "cuda", "gpu_name", "vram_gb", "pode_relight"}
│
├─ 4. Resolução de modo
│     if modo == "auto":
│         modo = "relight" if dev["pode_relight"] else "compose"
│     (+ fallback silencioso se relight pedido mas sem GPU)
│
├─ 5. usar_fundo_proprio = (args.background is not None)
│
├─ 6. pipeline_log = {"etapas": [], "erros_total": 0, "device": dev, "modo": modo}
│     pipeline_start = time.time()
│
│ ══ AGENTE 1 — Extração ══════════════════════════════════════════════════
├─ 7. import agentes.extracao.extrair_frames  (lazy, aqui)
│     meta = extrair_frames(args.video, paths.frames_raw)
│     → dict {fps, total_frames, width, height, tempo_s}
│     pipeline_log["etapas"].append({"etapa": "extracao", **meta})
│
│ ══ AGENTE 2 — Remoção de fundo ══════════════════════════════════════════
├─ 8. import agentes.remocao.remover_fundo  (lazy)
│     result_rembg = remover_fundo(paths.frames_raw, paths.frames_nobg, paths.log_path)
│     → dict {processados, erros, tempo_s}
│     pipeline_log["etapas"].append({"etapa": "remocao_fundo", **result_rembg})
│     pipeline_log["erros_total"] += result_rembg["erros"]
│
│ ══ AGENTE 3 — Fundo ═════════════════════════════════════════════════════
├─ 9a. se usar_fundo_proprio:
│       Image.open(args.background).resize(width×height, LANCZOS).save(paths.bg_output)
│       pipeline_log["etapas"].append({"etapa": "fundo", "modo": "proprio"})
│
├─ 9b. senão (fundo por IA):
│       import agentes.geracao_fundo.{iniciar_comfyui, gerar_fundo}  (lazy)
│       comfy_proc = iniciar_comfyui()
│       try:
│           gerar_fundo(prompt, width, height, paths.bg_output, steps, cfg_bg, seed)
│           pipeline_log["etapas"].append({"etapa": "fundo", "modo": "ia"})
│       finally:
│           comfy_proc.terminate()   ← sempre executa, libera porta/VRAM
│
│ ══ AGENTE 4 — Relight / Compose ═════════════════════════════════════════
├─ 10a. se modo == "relight":
│        import agentes.relighting.{carregar_iclight, aplicar_relighting}  (lazy)
│        low_vram = (dev["vram_gb"] or 99) < 8.0
│        pipe = carregar_iclight(device="cuda", low_vram=low_vram)
│        result = aplicar_relighting(pipe, paths.frames_nobg, paths.bg_output,
│                                    paths.frames_relit, prompt, negative, steps,
│                                    cfg_relight, seed, paths.log_path)
│        del pipe; torch.cuda.empty_cache()    ← libera VRAM antes da exportação
│        pipeline_log["etapas"].append({"etapa": "relighting", **result})
│        pipeline_log["erros_total"] += result["erros"]
│
├─ 10b. se modo == "compose":
│        import agentes.composicao.compor_batch  (lazy)
│        result = compor_batch(paths.frames_nobg, paths.bg_output,
│                              paths.frames_relit, paths.log_path)
│        pipeline_log["etapas"].append({"etapa": "composicao", **result})
│        pipeline_log["erros_total"] += result["erros"]
│
│ ══ AGENTE 5 — Exportação ════════════════════════════════════════════════
├─ 11. import agentes.exportacao.exportar_video  (lazy)
│      result_export = exportar_video(paths.frames_relit, args.video,
│                                     output, fps=meta["fps"], crf=args.crf)
│      pipeline_log["etapas"].append({"etapa": "exportacao", **result_export})
│
│ ══ Finalização ══════════════════════════════════════════════════════════
└─ 12. pipeline_log["tempo_total_s"] = round(time.time() - pipeline_start, 2)
       json.dump(pipeline_log, open(paths.log_path, "w"), indent=2)
       print summary (output path, tempo_total, aviso de erros se > 0)
```

## Fluxo de diretórios

```
{base}/frames/raw/      ← Agente 1 escreve (ffmpeg)
{base}/frames/nobg/     ← Agente 2 escreve (rembg RGBA PNGs)
{base}/background/bg.png ← Agente 3 escreve (fundo próprio ou SD 1.5)
{base}/relit/           ← Agente 4 escreve (IC-Light ou Pillow composite)
{base}/output/video_final.mp4 ← Agente 5 escreve (ffmpeg H.264 + áudio)
{base}/pipeline_log.json ← sobrescrito no final (não append)
```

## O que passa entre etapas

| De → Para | Dados transferidos | Mecanismo |
|---|---|---|
| Agente 1 → orquestrador | `meta` dict com fps, dimensões | retorno de função |
| Agente 1 → Agente 2 | PNGs em `frames/raw/` | sistema de arquivos |
| Agente 2 → Agente 4 | PNGs RGBA em `frames/nobg/` | sistema de arquivos |
| Agente 3 → Agente 4 | `bg.png` único | sistema de arquivos |
| Agente 4 → Agente 5 | PNGs compostos em `relit/` | sistema de arquivos |
| Agente 1 → Agente 5 | `meta["fps"]` | retorno em memória (via orquestrador) |

Nenhum agente conhece outro diretamente — o orquestrador distribui os caminhos e passa os metadados necessários.

## Tratamento de erros por estágio

| Agente | Comportamento em erro |
|---|---|
| Extração (1) | `check=True` no subprocess → aborta toda a pipeline imediatamente |
| Remoção (2) | try/except por frame → registra em `erros`, continua o lote |
| Fundo IA (3) | `finally: comfy_proc.terminate()` → garante limpeza; exceção propaga |
| Fundo próprio (3) | Pillow I/O → exceção propaga se arquivo inválido |
| Relighting/Compose (4) | try/except por frame → registra em `erros`, continua o lote |
| Exportação (5) | `check=True` no subprocess → aborta se ffmpeg falha |

Só os agentes por-frame (2 e 4) têm recuperação granular. Os agentes por-vídeo (1, 3, 5) falham com exceção não tratada.

## Relacionados

[[entities/pipeline]] · [[entities/pipeline-orchestrator-config]] ·
[[concepts/pipeline-orchestrator-mode-selection]] · [[concepts/video-frame-pipeline]] ·
[[concepts/pipeline-orchestrator-log-structure]] ·
[[decisions/pipeline-orchestrator-lazy-imports]] · [[index]]
