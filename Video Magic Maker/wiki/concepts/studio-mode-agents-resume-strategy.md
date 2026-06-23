---
title: Studio Mode — Resume Strategy per Agent
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - "agentes/extracao.py"
  - "agentes/remocao.py"
  - "agentes/relighting.py"
  - "agentes/exportacao.py"
tags: [resume, idempotency, studio-mode, crash-recovery]
---
# Studio Mode — Resume Strategy per Agent

Crash-recovery behaviour varies across the five pipeline agents. Two support per-frame resume; three restart from scratch on re-run.

## Per-agent resume matrix

| Agent | Resume? | Mechanism | Rationale |
|---|---|---|---|
| 1 — extracao | No | `ffmpeg -y` overwrites all existing frames | Extraction is cheap (~1ms/frame); simpler to restart |
| 2 — remocao | Yes | `if os.path.exists(output_path): continue` | rembg is slow; saves hours on partial runs |
| 3 — geracao_fundo | N/A | Generates one image, always overwritten | Single image; negligible cost to regenerate |
| 4 — relighting | Yes | `if os.path.exists(output_path): continue` | ~1.5 s/frame on T4; resume is essential for long videos |
| 5 — exportacao | No | Two-pass ffmpeg always runs in full | Export is fast (seconds); no per-frame granularity possible |

## Agent 2 — remocao resume

```python
for frame_name in tqdm(frames, desc="Removendo fundo"):
    output_path = os.path.join(output_dir, frame_name)
    if os.path.exists(output_path):
        continue  # resume automático
    # ... process frame
```

The check is purely filesystem-based: if the output PNG exists it is assumed complete. There is no checksum or size validation. A frame that was written partially (e.g. power loss mid-write) will be treated as done. In practice this is acceptable because rembg writes atomically through the rembg library's own file handling.

## Agent 4 — relighting resume

```python
for i, frame_name in enumerate(tqdm(frames, desc="Relighting IC-Light fbc")):
    output_path = os.path.join(output_dir, frame_name)
    if os.path.exists(output_path):
        if progress_cb:
            progress_cb(i + 1, len(frames))
        continue
    # ... process frame
```

Same filesystem-existence check as remocao. The progress callback is invoked even for skipped (already-done) frames, so the Gradio progress bar advances correctly on resume. The output dimensions (`largura`, `altura`) are derived from the first frame regardless of resume state — always consistent.

## Agent 1 — no resume

The ffmpeg `-y` flag overwrites any existing `frame_%05d.png` files without prompting. If Agent 1 is re-run against the same output directory with a different input video, leftover frames from the previous run that extend beyond the new video's frame count will remain on disk and be counted in `total_frames`. The orchestrator is expected to clean or use a fresh workspace directory per job.

## Agent 5 — no resume and temp file hazard

Agent 5 always runs both ffmpeg passes. If the process is killed between pass 1 (video without audio, `_noaudio.mp4`) and pass 2 (mux), the `_noaudio.mp4` file is left on disk. On the next run, ffmpeg's `-y` flag overwrites it, so there is no corruption — but the partial file occupies disk space until the new run completes.

## Why not resume-all

Agents 1 and 5 use ffmpeg which processes the entire input in one subprocess call — there is no natural per-frame checkpoint hook. Adding resume to Agent 1 would require splitting ffmpeg into per-frame calls (expensive, high subprocess-overhead). Agents 1 and 5 are fast enough that the cost of restarting is acceptable.

## Related

[[entities/studio-mode-agents-pipeline]] · [[concepts/studio-mode-agents-data-flow]] · [[decisions/agent-frame-extraction-no-resume]] · [[index]]
