# Índice da Wiki — lumina-bg

Catálogo de todas as páginas. Esquema e convenções em [[CLAUDE]]. Histórico em [[log]].

**lumina-bg**: pipeline Colab/GPU que troca o fundo de um vídeo de uma pessoa e
reilumina a pessoa para combinar com o novo ambiente. Fluxo: extração de frames
(ffmpeg) → remoção de fundo (rembg) → geração/upload de fundo (SD 1.5 / ComfyUI)
→ relighting (IC-Light) → exportação (ffmpeg, com áudio original).

**Dois modos:** **studio (offline)** — lote frame-a-frame; e **live** — troca de
fundo em tempo real (webcam → câmera virtual OBS) com matting + composição, **sem**
relight. O live tem CLI ([[components/live-mode]]) e uma **GUI desktop**
([[components/camera-app]], front-end recomendado). Ver também [[concepts/realtime-matting]].

O **studio (Gradio `app.py`)** tem **3 modos**: **HD** (`MODO_HD`) — recorte RVM
frame-a-frame, sem rembg, sem relight, melhor borda no-GPU ([[components/render-video]]);
**Compor** (`MODO_COMPOR`) — rembg + composição CPU ([[components/composicao]]); e
**Relight** (`MODO_RELIGHT`) — IC-Light com GPU ([[components/relighting]]). Default =
Relight se há GPU, senão HD.

---

## Architecture
- **Visão geral da pipeline** — orquestração dos 5 agentes, paths, resume, log → [[components/pipeline]]
- **Divisão de compute local vs Colab** — onde cada etapa roda e por quê → [[concepts/gpu-vram-local-vs-colab]] · [[decisions/local-vs-colab]]

## Components / Agents
- **pipeline** — orquestrador CLI; encadeia os 5 agentes, monta `pipeline_log.json` → [[components/pipeline]]
- **extracao** (Agente 1) — `ffmpeg`/`ffprobe`: vídeo → frames PNG + metadados (fps, dims) → [[components/extracao]]
- **remocao** (Agente 2) — rembg `u2net_human_seg`: frames → PNG RGBA sem fundo → [[components/remocao]]
- **geracao_fundo** (Agente 3) — ComfyUI + SD 1.5 via API: prompt → `bg.png` → [[components/geracao_fundo]]
- **relighting** (Agente 4) — IC-Light (fc atual, fbc planejado): reilumina a pessoa → [[components/relighting]]
- **exportacao** (Agente 5) — `ffmpeg`: frames relitados → `.mp4` com áudio original → [[components/exportacao]]
- **composicao** (Agente 4b) — Pillow/CPU: compõe RGBA sobre fundo, sem relight; fallback no-GPU e preview instantâneo → [[components/composicao]]
- **render-video** — render offline (RVM/MediaPipe), sem rembg e sem relight: `render_matting` (dir de frames → PNGs, modo HD do Gradio) e `render_arquivo` (arquivo de vídeo → mp4 **com áudio remuxado**, usado pelo botão 🎬 do app de câmera) → [[components/render-video]]
- **live-mode** — webcam → matting (MediaPipe ou RVM) → composição → câmera virtual OBS, em tempo real, sem relight; motor selecionável `--engine` → [[components/live-mode]]
- **camera-app** — GUI Tkinter do modo live (front-end recomendado): gravar/foto/galeria, zoom/enquadramento, brilho/contraste/saturação/nitidez, **stream pra câmera virtual** (start/PARAR), **🎬 renderizar arquivo de vídeo** (`render_arquivo`, com áudio), dropdown "Motor de recorte" (MediaPipe/RVM), fundo imagem/desfoque/**vídeo em loop** (`VideoFundo`); startup instantâneo (matter lazy no worker, janela topmost); inclui `agentes/ajustes.py` → [[components/camera-app]]

## Concepts
- **IC-Light** — fc vs fbc, offset-merge dos pesos, layouts de canais → [[concepts/ic-light]]
- **rembg / remoção de fundo** — `u2net_human_seg`, alpha matting, saída RGBA → [[concepts/rembg-background-removal]]
- **Geração de fundo com SD 1.5** — ComfyUI API, workflow KSampler, negative prompt → [[concepts/sd15-background-generation]]
- **Pipeline frame-a-frame e resume** — processamento por frame, skip de existentes, log de erros → [[concepts/video-frame-pipeline]]
- **GPU/VRAM, local vs Colab** — restrições de 4GB, torch CPU-only, split de compute → [[concepts/gpu-vram-local-vs-colab]]
- **Matting em tempo real** — MediaPipe Tasks ImageSegmenter / Selfie Segmenter, três gotchas, fps/res, câmera virtual pyvirtualcam/OBS → [[concepts/realtime-matting]]
- **RVM (RobustVideoMatting)** — motor de recorte alternativo do live; alpha matte real vs confidence mask, estado recorrente, torch.hub/torchvision, perf, quando usar vs MediaPipe → [[concepts/rvm-matting]]

## Decisions
- **Migrar IC-Light fc → fbc** — por que trocar o modelo de relighting → [[decisions/migrate-fc-to-fbc]]
- **Local vs Colab** — passos leves local, compute pesado no Colab T4 → [[decisions/local-vs-colab]]

## Sources
- `plano_iclight_comfyui_colab.md` (raiz do repo) — plano original da pipeline; base de [[components/pipeline]] e dos agentes.
- `README.md` (raiz do repo, pt-BR) — guia de uso voltado ao usuário final.
- `lumina_bg.ipynb` (raiz do repo) — notebook Colab de 9 células que executa a pipeline.
- `camera_app.py` (raiz do repo) — GUI Tkinter do modo live; base de [[components/camera-app]].
- `agentes/ajustes.py` — ajustes de imagem BGR (zoom/pan/brilho/contraste/saturação/nitidez); documentado em [[components/camera-app]].
- `agentes/matting_rvm.py` — motor de recorte RVM (RobustVideoMatting) do live e do render offline; base de [[concepts/rvm-matting]].
- `agentes/render_video.py` — render offline HD (RVM) frame-a-frame do modo studio; base de [[components/render-video]].
- `app.py` — UI Gradio do modo studio (3 modos: HD/Compor/Relight); referenciado em [[components/render-video]].
