---
title: "Decision: Colab notebook as primary GPU distribution path"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb", "plano_iclight_comfyui_colab.md"]
tags: [decision, colab, deploy, gpu, distribution]
status: inferred
---

# Decision: Colab notebook as primary GPU distribution path

> Inferred from `lumina_bg.ipynb` header comment ("runs free on Google Colab"), the plan doc's explicit T4 target, and the absence of any Docker/cloud-run/self-host deployment path in the codebase.

## Context

The two GPU-critical pipeline stages — SD 1.5 background generation ([[entities/geracao_fundo]]) and IC-Light relighting ([[entities/relighting]]) — require a CUDA GPU with at least ~8–10 GB of VRAM. The target audience is individual creators who do not have access to such hardware locally. See [[concepts/gpu-vram-local-vs-colab]].

## Decision

Distribute `lumina_bg.ipynb` as the canonical entrypoint for GPU-required modes. Users open the notebook in Google Colab, select a free T4 GPU runtime, and run cells sequentially with no local installation.

## Alternatives considered (inferred)

| Option | Why not chosen |
|---|---|
| Docker image on cloud VPS | Cost for end users; operational complexity to maintain |
| Local GPU requirement | Excludes majority of target users |
| Hugging Face Spaces (Gradio) | Session timeouts; 1-frame-at-a-time GPU quota on free tier; not suited for multi-minute video jobs |
| pip-installable CLI | Still requires local GPU; does not solve distribution |

## Consequences

- **Free compute access:** Colab free tier provides T4 (~15GB VRAM) for sessions up to ~90 min, sufficient for ~1 min of video per session.
- **No server to maintain:** Google hosts the compute; no infra cost to the project.
- **Resume design required:** Colab free sessions disconnect unpredictably; the pipeline's frame-level skip-if-exists pattern ([[concepts/deploy-colab-resume-mechanism]]) was a direct consequence of this choice.
- **Model re-download cost:** SD 1.5 (~4GB) and IC-Light weights must be re-downloaded each Colab session; not cached to Drive. ~5 min overhead per run.
- **Self-clone bootstrap:** the notebook must clone the repo at runtime to access `agentes/`; see [[concepts/deploy-colab-module-bootstrap]].
- **No versioned releases:** users always get the latest `main` branch code; no pinned version for the `agentes/` modules.

## Status

Active as of the current codebase. No alternative deployment target is implemented.

## Related

[[entities/deploy-colab-notebook]] · [[entities/deploy-colab-drive-workspace]] · [[decisions/local-vs-colab]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
