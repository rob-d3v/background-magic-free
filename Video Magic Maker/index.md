# Video Magic Maker — brain index

_123 pages · regenerated 2026-06-23._ Read this first; then open the page.

## Overview

- [[wiki/overview/background-magic-free|background-magic-free (lumina-bg) — Overview]] — background-magic-free (internal name lumina-bg) is a free, no-green-screen tool that swaps the background of a person video and optionally relights the person t…
- [[wiki/overview/background-magic-free-quickref|background-magic-free — Quickref (operating contract)]] — Read this first.

## Entities

- [[wiki/entities/agent-background-removal-remocao|Agente 2 — remocao.py (rembg background removal)]] — agentes/remocao.py é o Agente 2 da pipeline lumina-bg: recorta a pessoa de cada frame via rembg/ONNX, produzindo PNGs RGBA prontos para relighting ou composição…
- [[wiki/entities/composicao-render-video-composicao|Agente Composicao (CPU fallback)]] — Composição RGBA-over-RGB sem GPU: cola o recorte da pessoa sobre um novo fundo via canal alpha, com ajuste leve de brilho/cor.
- [[wiki/entities/composicao-render-video-render-video|Agente Render Video (RVM offline)]] — Render offline de troca de fundo usando RVM ou MediaPipe, aplicado frame-a-frame sem pressão de tempo real — caminho "poderoso sem GPU".
- [[wiki/entities/deploy-colab-drive-workspace|Deploy: Google Drive workspace (iclight_pipeline/)]] — The Google Drive directory tree mounted at /content/drive/MyDrive/iclightpipeline/ serves as the persistent workspace for the Colab pipeline; it survives runtim…
- [[wiki/entities/deploy-colab-notebook|Deploy: lumina_bg.ipynb — Colab GPU notebook]] — The primary user-facing distribution artifact for GPU-required pipeline modes; a self-contained 9-cell Jupyter notebook designed to run on Google Colab with a f…
- [[wiki/entities/gradio-app-live-tab|Gradio App — Live Tab]] — The Live tab (🔴 Live — OBS / Meet / stream) enables real-time webcam background replacement via [[gradio-app-app-py]], publishing to an OBS Virtual Camera that …
- [[wiki/entities/gradio-app-studio-tab|Gradio App — Studio Tab]] — The Studio tab (🎬 Studio — gravar video) is the offline video background-replacement workflow inside [[gradio-app-app-py]], structured as a six-step guided flow…
- [[wiki/entities/gradio-app-app-py|Gradio App — app.py (lumina-bg Web UI)]] — app.py is the Gradio 4.x web UI entry point for lumina-bg, exposing a guided two-tab interface (Studio and Live) served at http://127.0.0.1:7860 locally or via …
- [[wiki/entities/image-adjustments-agent-ajustes-module|Image Adjustments Module (agentes/ajustes.py)]] — Single-function OpenCV module that applies zoom/pan, brightness, contrast, saturation, and sharpness to a composed BGR frame as the final post-processing step.
- [[wiki/entities/composicao-render-video-matting-live|LiveMatter — Matting em tempo real (MediaPipe)]] — Segmentador de pessoa em tempo real usando MediaPipe Tasks ImageSegmenter, rodando a ~30 fps em CPU; também fornece utilitários de fundo compartilhados pelo pip…
- [[wiki/entities/composicao-render-video-rvm-matter|RVMMatter — Matting com RobustVideoMatting]] — Motor de matting de vídeo de alta qualidade (RVM) que mantém estado recorrente entre frames, eliminando tremor de borda e halo causados por abordagens frame-iso…
- [[wiki/entities/studio-mode-agents-pipeline|Studio Mode — Five-Agent Pipeline]] — The studio-mode pipeline processes an input video through five sequential agents — frame extraction, background removal, background generation, relighting, and …
- [[wiki/entities/agent-relighting-module|agent-relighting-module — agentes/relighting.py (IC-Light fbc)]] — Módulo Python que implementa o Agente 4 (Relighting).
- [[wiki/entities/camera-app|camera-app — App de câmera ao vivo (GUI Tkinter)]] — cameraapp.py (raiz do repo) — front-end desktop (GUI Tkinter + PIL ImageTk)
- [[wiki/entities/camera-app-gui-config-persistence|camera-app-gui — Config persistence (camera_app_config.json)]] — Every user preference set in [[entities/camera-app]] is persisted to a JSON file and
- [[wiki/entities/composicao|composicao — Agente 4b (Composição CPU, sem GPU)]] — agentes/composicao.py expõe dois callables: comporframe (por frame) e
- [[wiki/entities/gradio-app-config-device-detection|config.py — Paths and Device Detection]] — config.py provides two facilities used at startup by [[gradio-app-app-py]]: a dynamic workspace path resolver (Paths) and a GPU capability probe (detectardevice…
- [[wiki/entities/pipeline-orchestrator-config|config.py — Paths e detecção de device]] — config.py centraliza duas responsabilidades anteriormente espalhadas em pipeline.py: resolução dinâmica do workspace (substitui paths hardcoded Colab) e detecçã…
- [[wiki/entities/exportacao|exportacao — Agente 5 (Exportação de Vídeo Final)]] — agentes/exportacao.py → exportarvideo(...).
- [[wiki/entities/extracao|extracao — Agente 1 (Extração de Frames)]] — agentes/extracao.py expõe uma única função pública — extrairframes(videopath, outputdir) — que converte o vídeo de entrada em frames PNG numerados e devolve met…
- [[wiki/entities/geracao_fundo|geracao_fundo — Agente 3 (Geração de Fundo com SD 1.5)]] — agentes/geracaofundo.py expõe dois backends independentes para geração de
- [[wiki/entities/live-mode|live-mode — Modo Live (troca de fundo em tempo real)]] — live.py (CLI) + agentes/mattinglive.py (classe LiveMatter + helpers
- [[wiki/entities/live-mode-background-helpers|live-mode-background-helpers — VideoFundo, carregar_fundo, cobrir, fundo_desfocado]] — agentes/mattinglive.py exporta quatro helpers de gestão de fundo usados por [[entities/live-mode]] e [[entities/camera-app]].
- [[wiki/entities/live-mode-cli|live-mode-cli — live.py, ponto de entrada CLI do modo ao vivo]] — live.py é o ponto de entrada de linha de comando que conecta captura de webcam, seleção de motor, carregamento de fundo, composição e saída para câmera virtual …
- [[wiki/entities/live-mode-livematter-class|live-mode-livematter-class — LiveMatter, segmentador MediaPipe em tempo real]] — LiveMatter (em agentes/mattinglive.py) é a classe central do [[entities/live-mode]]: encapsula o ImageSegmenter do MediaPipe Tasks e expõe dois métodos públicos…
- [[wiki/entities/live-mode-virtual-camera|live-mode-virtual-camera — saída pyvirtualcam / OBS Virtual Camera]] — A câmera virtual é o estágio de saída do [[entities/live-mode]]: uma instância de pyvirtualcam.Camera que expõe o stream BGR composto como dispositivo de webcam…
- [[wiki/entities/pipeline|pipeline — Orquestrador]] — pipeline.py.
- [[wiki/entities/relighting|relighting — Agente 4 (Relighting com IC-Light fbc)]] — agentes/relighting.py → carregariclight(...) + relightframe(...) + aplicarrelighting(...).
- [[wiki/entities/remocao|remocao — Agente 2 (Remoção de Fundo)]] — agentes/remocao.py → removerfundo(framesdir, outputdir, logpath=None).
- [[wiki/entities/render-video|render-video — Render offline (RVM/MediaPipe), troca de fundo sem GPU]] — agentes/rendervideo.py — render offline que recorta a pessoa de cada frame

## Concepts

- [[wiki/concepts/agent-composition-export-alpha-composite|Alpha composite CPU: como compor_frame cola a pessoa no fundo]] — O [[entities/composicao]] usa a operação de alpha compositing do Pillow para
- [[wiki/concepts/agent-background-removal-alpha-matting|Alpha matting — suavização de bordas no rembg]] — Alpha matting é o pós-processamento que suaviza as bordas da máscara gerada pelo U²-Net, produzindo transições naturais em regiões de cabelo, contornos difusos …
- [[wiki/concepts/pipeline-orchestrator-background-branching|Bifurcação de fundo — próprio vs gerado por IA]] — No passo 3 da pipeline (Agente 3), o orquestrador escolhe entre dois caminhos mutuamente exclusivos para produzir background/bg.png.
- [[wiki/concepts/composicao-render-video-rvm-temporal-coherence|Coerência temporal via estado recorrente RVM]] — O RobustVideoMatting mantém 4 tensores de estado entre frames, o que produz bordas temporalmente estáveis — menos tremor — diferente de processar cada frame iso…
- [[wiki/concepts/deploy-colab-module-bootstrap|Colab deploy: agentes/ module bootstrap via self-clone]] — Cell 7 of [[entities/deploy-colab-notebook]] makes the agentes/ Python package available inside Colab at runtime by cloning the project's own GitHub repository.
- [[wiki/concepts/deploy-colab-cell-data-flow|Colab deploy: cell-by-cell data flow]] — How data enters, transforms, and exits through the 9 notebook cells of [[entities/deploy-colab-notebook]], from raw video to final download.
- [[wiki/concepts/deploy-colab-resume-mechanism|Colab deploy: frame-level resume mechanism]] — The notebook pipeline is designed to survive Colab free-tier disconnections (which occur after ~30–90 min) by writing all intermediate outputs to Google Drive a…
- [[wiki/concepts/agent-background-generation-comfyui-subprocess|ComfyUI subprocess launch pattern (Agente 3)]] — iniciarcomfyui() lança o servidor ComfyUI como subprocesso do Python do
- [[wiki/concepts/agent-frame-extraction-output-dir-conventions|Convenções de diretório e nomenclatura de frames]] — O [[entities/extracao]] grava PNGs num diretório que ele recebe como argumento.
- [[wiki/concepts/agent-composition-export-cover-crop|Cover-crop de fundo: algoritmo de preenchimento sem distorção]] — O [[entities/composicao]] (Agente 4b) e o [[entities/live-mode]] (modo câmera ao
- [[wiki/concepts/composicao-render-video-dr-qualidade|Cálculo dinâmico de downsample_ratio (RVM offline)]] — No modo offline, o downsampleratio do RVM é calculado para manter ~720px no lado mais longo do frame — mais detalhe que o default 0.4 de tempo real (~512px), cu…
- [[wiki/concepts/agent-frame-extraction-fps-detection|Detecção de FPS — resolução de fração NTSC e outros formatos]] — O [[entities/extracao]] precisa do FPS real do vídeo para que a [[entities/exportacao]] reconstitua o timing original.
- [[wiki/concepts/image-adjustments-agent-dirty-flag-cache|Dirty-flag cache for video-edit adjustments]] — In video-edit mode, cameraapp.py uses two boolean dirty flags to avoid re-running the expensive matting+composition step when only cheap image adjustments have …
- [[wiki/concepts/agent-render-video-offline-pipeline|Fluxo de dados — render offline (render_arquivo e render_matting)]] — Esta página descreve o fluxo de dados e sequência de chamadas do caminho
- [[wiki/concepts/gpu-vram-local-vs-colab|GPU/VRAM — restrições e split local vs Colab]] — A pipeline mistura etapas leves (CPU/IO) e etapas pesadas (difusão em GPU).
- [[wiki/concepts/sd15-background-generation|Geração de fundo com Stable Diffusion 1.5 (via ComfyUI)]] — O fundo novo é gerado por Stable Diffusion 1.5 rodando dentro do ComfyUI,
- [[wiki/concepts/gradio-app-background-resolution|Gradio App — Background Resolution Flow (_obter_bg)]] — obterbg is the internal helper in [[gradio-app-app-py]] that resolves the background PIL image for both preview and render, abstracting over "upload" vs "genera…
- [[wiki/concepts/gradio-app-gpu-gating|Gradio App — GPU Gating and Degraded-Mode Behaviour]] — app.py uses detectardevice() from [[gradio-app-config-device-detection]] at startup to build a DEV dict that gates which features are available, and displays a …
- [[wiki/concepts/gradio-app-guided-flow|Gradio App — Guided Studio Flow (call sequence)]] — The Studio tab in [[gradio-app-app-py]] implements a linear six-step guided flow where each step unlocks the next via button interactivity gating and shared in-…
- [[wiki/concepts/gradio-app-live-subprocess-pattern|Gradio App — Live Subprocess Pattern]] — The Live tab in [[gradio-app-app-py]] uses a subprocess pattern rather than running the camera loop inside the Gradio event loop, because live.py is a blocking …
- [[wiki/concepts/gradio-app-processing-modes|Gradio App — Three Processing Modes]] — app.py offers three processing modes selectable by the user, gated by GPU availability.
- [[wiki/concepts/pipeline-orchestrator-iclight-fbc-internals|IC-Light fbc — internos do UNet 12 canais e offset-merge]] — Documenta como o [[entities/relighting]] carrega e opera o IC-Light fbc depois da migração fbc concluída.
- [[wiki/concepts/ic-light|IC-Light — fc vs fbc, offset-merge e layouts de canais]] — [IC-Light](https://github.com/lllyasviel/IC-Light) ("Imposing Consistent Light")
- [[wiki/concepts/image-adjustments-agent-transform-internals|Image adjustment transform internals]] — Detailed mechanics of each transform stage inside aplicarajustes, including parameter ranges, OpenCV calls used, and edge-case behaviour.
- [[wiki/concepts/image-adjustments-agent-render-video-gap|Image adjustments absent from offline video render]] — The offline batch render path (agentes/rendervideo.py) does not call aplicarajustes, meaning zoom/pan/brightness/contrast/saturation/sharpness settings are sile…
- [[wiki/concepts/realtime-matting|Matting em tempo real (MediaPipe Tasks + câmera virtual)]] — Conceito por trás do [[entities/live-mode]]: segmentar a pessoa de cada frame da
- [[wiki/concepts/agent-background-removal-paths|Paths e workspace — contexto do Agente 2]] — O Agente 2 recebe seus diretórios de entrada e saída via parâmetros, resolvidos por config.Paths no orquestrador.
- [[wiki/concepts/composicao-render-video-cpu-render-pipeline|Pipeline CPU de troca de fundo (composição e render)]] — Dois caminhos independentes que trocam o fundo de um vídeo sem GPU e sem reiluminação por IA: o caminho leve (Pillow, composicao.py) e o caminho de qualidade (R…
- [[wiki/concepts/pipeline-orchestrator-call-sequence|Pipeline Orchestrator — sequência completa de chamadas]] — Visão end-to-end de tudo que pipeline.py faz desde a invocação CLI até a escrita do log final.
- [[wiki/concepts/video-frame-pipeline|Pipeline frame-a-frame e mecanismo de resume]] — A pipeline processa vídeo como uma sequência de frames PNG que fluem por
- [[wiki/concepts/image-adjustments-agent-post-composition-placement|Post-composition placement of image adjustments]] — Image adjustments (zoom, brightness, contrast, saturation, sharpness) are applied after full frame composition so that they affect the final output exactly as a…
- [[wiki/concepts/rvm-matting|RVM — RobustVideoMatting (matting de alta qualidade)]] — RVM (RobustVideoMatting) é o motor de recorte de alta qualidade,
- [[wiki/concepts/agent-background-removal-resume|Resume automático por frame — Agente 2]] — O Agente 2 suporta resume granular por frame: ao reexecutar a pipeline após uma interrupção (desconexão do Colab, crash), frames já processados são pulados e o …
- [[wiki/concepts/pipeline-orchestrator-mode-selection|Seleção de modo — auto / relight / compose]] — O [[entities/pipeline]] escolhe entre dois caminhos de processamento no passo 4 da pipeline: relight (IC-Light fbc, GPU) ou compose (alpha composite, CPU).
- [[wiki/concepts/studio-mode-agents-data-flow|Studio Mode — Inter-Agent Data Flow]] — End-to-end data flow through the five studio-pipeline agents, covering what each agent consumes, what it produces, and which values are passed in memory vs on-d…
- [[wiki/concepts/studio-mode-agents-resume-strategy|Studio Mode — Resume Strategy per Agent]] — Crash-recovery behaviour varies across the five pipeline agents.
- [[wiki/concepts/agent-relighting-channel-layout|agent-relighting-channel-layout — Layout de 12 canais da UNet fbc]] — Explica como o modelo IC-Light fbc expande a convin do SD 1.5 de 4 para 12
- [[wiki/concepts/agent-relighting-denoising-loop|agent-relighting-denoising-loop — Loop de denoising em relight_frame]] — Descreve o fluxo completo de inferência dentro de relightframe(), desde o
- [[wiki/concepts/agent-relighting-load-flow|agent-relighting-load-flow — Sequência de carregamento do pipeline IC-Light fbc]] — Descreve passo a passo o que carregariclight() faz ao construir o pipeline
- [[wiki/concepts/agent-relighting-vram|agent-relighting-vram — Modos de VRAM e GPU em carregar_iclight]] — Documenta os três modos de execução do pipeline IC-Light fbc em relação a
- [[wiki/concepts/camera-app-gui-camera-listing|camera-app-gui — Camera detection and listing (listar_cameras)]] — listarcameras() (module-level function in cameraapp.py) enumerates available
- [[wiki/concepts/camera-app-gui-dark-theme|camera-app-gui — Dark theme and scrollable control panel]] — CameraApp.setupstyle and buildui implement a modern dark visual design
- [[wiki/concepts/camera-app-gui-dual-thread-frame-pipeline|camera-app-gui — Dual-thread frame pipeline]] — cameraapp.py splits all work across two threads to keep Tkinter responsive while
- [[wiki/concepts/camera-app-gui-gallery-recording|camera-app-gui — Gallery, recording, and photo capture]] — CameraApp writes all generated media — video recordings, photos, and offline
- [[wiki/concepts/camera-app-gui-video-edit-mode|camera-app-gui — Video edit mode (source="video")]] — The camera app embeds a non-destructive video editor into its main window.
- [[wiki/concepts/agent-composition-export-ffmpeg-reassembly|ffmpeg reassembly: dois passes para vídeo final com áudio original]] — O [[entities/exportacao]] (Agente 5) e a variante renderarquivo em
- [[wiki/concepts/ic-light-integration-colab-setup|ic-light-integration-colab-setup — IC-Light no Colab: setup, deps e divisão de responsabilidades]] — Descreve como o Colab prepara o ambiente para o IC-Light e como as células do notebook se relacionam (ou não) com o que agentes/relighting.py realmente executa.
- [[wiki/concepts/ic-light-integration-notebook-agent-mismatch|ic-light-integration-notebook-agent-mismatch — Divergência fc/fbc entre notebook e agente]] — A migração de fc para fbc (documentada em [[decisions/migrate-fc-to-fbc]] e [[decisions/agent-relighting-fbc-completed]]) atualizou o agente Python, mas não a c…
- [[wiki/concepts/live-mode-cpu-only-path|live-mode-cpu-only-path — execução CPU-only via XNNPACK (sem GPU)]] — O modo ao vivo ([[entities/live-mode]]) roda o matting inteiramente em CPU.
- [[wiki/concepts/live-mode-edge-refinement|live-mode-edge-refinement — pipeline de refino de borda (guided filter + morfologia)]] — O Selfie Segmenter do MediaPipe produz uma confidence mask suave e desalinhada em resolução interna de ~256².
- [[wiki/concepts/live-mode-frame-pipeline|live-mode-frame-pipeline — fluxo de dados por frame no modo tempo real]] — O pipeline em tempo real do [[entities/live-mode]] processa um frame BGR a ~30fps numa sequência fixa de estágios.
- [[wiki/concepts/pipeline-orchestrator-log-structure|pipeline_log.json — estrutura e contrato]] — pipelinelog.json é o único artefato de saída estruturado do orquestrador além do vídeo final.
- [[wiki/concepts/rembg-background-removal|rembg — Remoção de fundo]] — [rembg](https://github.com/danielgatis/rembg) é a biblioteca que recorta a pessoa
- [[wiki/concepts/agent-background-removal-onnx-inference|rembg/ONNX — inferência GPU e fallback CPU]] — remocao.py usa rembg sobre ONNX Runtime para executar o modelo U²-Net.

## Decisions

- [[wiki/decisions/studio-mode-agents-agent-boundaries|Decision — Five separate agent modules (studio pipeline boundaries)]] — The studio pipeline is divided into five independent Python modules rather than a single script.
- [[wiki/decisions/gradio-app-preview-before-render|Decision — Single-Frame Preview Before Full Render]] — The Studio tab requires the user to preview the result on a single frame before committing to a full-video render.
- [[wiki/decisions/gradio-app-single-user-global-state|Decision — Single-User Global State in app.py]] — app.py uses module-level global variables for all session state and model handles rather than Gradio's gr.State or a session-scoped object.
- [[wiki/decisions/deploy-colab-primary-gpu-path|Decision: Colab notebook as primary GPU distribution path]] — The two GPU-critical pipeline stages — SD 1.5 background generation ([[entities/geracaofundo]]) and IC-Light relighting ([[entities/relighting]]) — require a CU…
- [[wiki/decisions/camera-app-gui-lazy-matter-init|Decision: lazy LiveMatter init in worker thread (camera-app-gui)]] — LiveMatter.init (MediaPipe Tasks ImageSegmenter) takes approximately 1.8 s
- [[wiki/decisions/camera-app-gui-render-always-rvm|Decision: render always uses RVM engine (camera-app-gui)]] — cameraapp.py allows the user to choose between two matting engines for the live
- [[wiki/decisions/agent-composition-export-crf-preset|Decisão: CRF 18 e preset slow para encoding H.264 de saída]] — O [[entities/exportacao]] encoda os frames compostos/relitados com libx264.
- [[wiki/decisions/composicao-render-video-ffmpeg-audio-mux|Decisão: FFmpeg com -map 1:a:0? para áudio opcional]] — O remux do áudio original após o render usa -map 1:a:0?
- [[wiki/decisions/agent-composition-export-cpu-fallback|Decisão: composição CPU como fallback do relighting GPU]] — O objetivo central do produto é trocar o fundo de vídeos com reiluminação
- [[wiki/decisions/local-vs-colab|Decisão: compute split local vs Colab]] — O desenvolvimento acontece numa máquina local modesta, mas a pipeline tem etapas
- [[wiki/decisions/pipeline-orchestrator-paths-refactor|Decisão: de-hardcodar paths → config.py (Paths + resolver_base)]] — O pipeline.py original fixava todos os caminhos para o Google Colab:
- [[wiki/decisions/agent-composition-export-ffprobe-audio-detection|Decisão: detecção de áudio por substring ffprobe vs. -map opcional]] — O [[entities/exportacao]] precisa saber se o vídeo original tem áudio antes de
- [[wiki/decisions/agent-background-generation-two-backends|Decisão: dois backends de geração de fundo (ComfyUI vs diffusers)]] — agentes/geracaofundo.py implementa dois caminhos completamente independentes
- [[wiki/decisions/composicao-render-video-dois-caminhos-cpu|Decisão: dois caminhos CPU sem reiluminação]] — O sistema mantém dois caminhos distintos para troca de fundo sem GPU, em vez de um único caminho unificado.
- [[wiki/decisions/pipeline-orchestrator-lazy-imports|Decisão: imports de agentes dentro de main() (lazy, por etapa)]] — pipeline.py não importa os módulos de agente no topo do arquivo.
- [[wiki/decisions/migrate-fc-to-fbc|Decisão: migrar IC-Light fc → fbc]] — O [[entities/relighting]] usa IC-Light fc (foreground-conditioned, UNet de 8
- [[wiki/decisions/agent-render-video-engine-forced-rvm|Decisão: render final sempre usa RVM (independente do motor do live)]] — O [[entities/camera-app]] permite ao usuário selecionar o motor de recorte ao vivo:
- [[wiki/decisions/agent-background-removal-model-choice|Decisão: u2net_human_seg + alpha matting como segmentador padrão]] — Status: inferred — decisão inferida do código; não há ADR explícito no repositório.
- [[wiki/decisions/image-adjustments-agent-fixed-transform-order|Fixed transform order: spatial → tone → color → sharpness]] — The four transform stages inside aplicarajustes follow a fixed order (zoom/pan → brightness/contrast → saturation → sharpness) that is non-configurable by the c…
- [[wiki/decisions/image-adjustments-agent-stateless-pure-function|Image adjustments implemented as a stateless pure function]] — aplicarajustes was designed as a single stateless function rather than a class with instance state, keeping it side-effect-free and trivially testable.
- [[wiki/decisions/agent-frame-extraction-no-resume|Sem resume granular na extração de frames]] — O [[entities/extracao]] usa -y no ffmpeg, o que significa que reexecutar a extração sempre reprocessa todos os frames, sem detectar ou pular frames já existente…
- [[wiki/decisions/agent-relighting-fbc-completed|agent-relighting-fbc-completed — Migração fc→fbc concluída]] — A migração de IC-Light fc para fbc, planejada em [[decisions/migrate-fc-to-fbc]],
- [[wiki/decisions/ic-light-integration-diffusers-vs-comfyui|ic-light-integration-diffusers-vs-comfyui — IC-Light via diffusers vs ComfyUI]] — O luminabg.ipynb configura tanto ComfyUI quanto o repositório lllyasviel/IC-Light, mas agentes/relighting.py usa nenhum deles — implementa o pipeline diretament…
- [[wiki/decisions/live-mode-engine-selection|live-mode-engine-selection — MediaPipe vs RVM para matting em tempo real]] — Decisão (inferida): oferecer dois motores de matting selecionáveis com diferentes tradeoffs de fps/qualidade em vez de se comprometer com um único, com o MediaP…

## Sources

- [[wiki/sources/agent-background-generation-geracao-fundo-py|Fonte: agentes/geracao_fundo.py]] — Módulo de ~182 linhas que implementa o Agente 3 — Geração de Fundo com SD 1.5.
- [[wiki/sources/agent-render-video-source|Fonte: agentes/render_video.py]] — agentes/rendervideo.py — ~175 linhas.
- [[wiki/sources/readme|Source — README.md (user guide, pt-BR)]] — End-user usage guide for lumina-bg / background-magic-free (pt-BR), at the repo root.
- [[wiki/sources/gradio-app-source-app-py|Source — app.py]] — app.py is the Gradio web UI entry point for the lumina-bg project (background-magic-free repo).
- [[wiki/sources/gradio-app-source-config-py|Source — config.py]] — config.py provides centralized workspace path resolution and GPU capability detection for lumina-bg, consumed by app.py at startup.
- [[wiki/sources/lumina-bg-notebook|Source — lumina_bg.ipynb (Colab notebook)]] — The 9-step Colab notebook that runs the full Studio (batch, GPU) pipeline end-to-end.
- [[wiki/sources/plano-iclight-comfyui-colab|Source — plano_iclight_comfyui_colab.md (design plan)]] — The original design plan (pt-BR) for the Colab pipeline, addressed to Claude Code as the implementer.
- [[wiki/sources/image-adjustments-agent-ajustes-py|Source: agentes/ajustes.py]] — Reference summary of agentes/ajustes.py — the Image Adjustments module.
- [[wiki/sources/camera-app-gui-ajustes|Source: agentes/ajustes.py — image adjustment pipeline]] — agentes/ajustes.py — single public function aplicarajustes that applies
- [[wiki/sources/agent-background-removal-remocao-py|Source: agentes/remocao.py]] — Implementação do Agente 2 — Remoção de Fundo.
- [[wiki/sources/pipeline-orchestrator-config-py|Source: config.py — configuração central de paths e device]] — config.py é o módulo de configuração central da pipeline.
- [[wiki/sources/agent-relighting-source|agent-relighting-source — Sumário de agentes/relighting.py]] — Arquivo-fonte: agentes/relighting.py (307 linhas, sem dependências internas ao
- [[wiki/sources/agent-frame-extraction-config-py|config.py — resolução de paths e detecção de device]] — config.py é o módulo central de configuração da pipeline lumina-bg.
