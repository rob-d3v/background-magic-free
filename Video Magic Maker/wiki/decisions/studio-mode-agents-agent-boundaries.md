---
title: Decision — Five separate agent modules (studio pipeline boundaries)
type: decision
created: 2026-06-22
updated: 2026-06-22
sources:
  - "agentes/extracao.py"
  - "agentes/remocao.py"
  - "agentes/geracao_fundo.py"
  - "agentes/relighting.py"
  - "agentes/exportacao.py"
tags: [architecture, decision, studio-mode, modularity]
status: inferred
---
# Decision — Five separate agent modules (studio pipeline boundaries)

> ⚠️ This decision is **inferred** from code structure. No explicit ADR was found in the repository.

The studio pipeline is divided into five independent Python modules rather than a single script. Each module exposes one or two public functions and communicates with the next only via filesystem paths and a small in-memory return dict.

## What was decided

Each pipeline step lives in its own file (`extracao.py`, `remocao.py`, `geracao_fundo.py`, `relighting.py`, `exportacao.py`) with no cross-imports between agent modules. The orchestrator (`pipeline.py` or `app.py`) is the only code that calls more than one agent.

## Why (inferred)

**Independent restartability.** Agents 2 and 4 implement per-frame resume without needing to know about any other agent. If they were fused into a single module the resume logic would need to span multiple concerns.

**Heterogeneous runtimes.** Agents 1 and 5 require only `ffmpeg`/`ffprobe` (CPU, no Python ML deps). Agents 2, 3, and 4 require GPU and heavy model weights. Separating them allows the orchestrator to conditionally skip or swap any single agent — for example, Agent 3 is skipped entirely when the user provides their own background image, and Agent 4 is skipped when `pode_relight=False` (no GPU or insufficient VRAM).

**Dual-backend agent 3.** [[entities/geracao_fundo]] exposes two backends in one file (`gerar_fundo` via ComfyUI and `gerar_fundo_diffusers` via diffusers). Keeping this in a single module lets the orchestrators choose the appropriate backend without importing from two different locations.

**Testability and preview.** `relight_frame` (single-frame variant in Agent 4) is called directly by the Gradio UI for the preview feature without running the full batch. This is only clean because the agent module is self-contained.

**Disk as the interface contract.** Using `frames/raw/`, `frames/nobg/`, and `relit/` as the canonical data exchange between agents means any agent can be re-run independently without replaying the whole pipeline — a practical necessity on Colab where GPU sessions time out mid-run.

## Trade-offs

The strict filesystem-as-interface means the pipeline cannot easily stream frames in memory from one agent to the next. Every frame is written and read from disk between steps. For a 1080p video at 30fps this is acceptable; for real-time use the live-mode pipeline (`agentes/matting_live.py`, `agentes/matting_rvm.py`) uses a different, memory-based architecture.

## Related

[[entities/studio-mode-agents-pipeline]] · [[concepts/studio-mode-agents-data-flow]] · [[entities/pipeline]] · [[index]]
