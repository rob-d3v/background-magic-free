---
title: "ic-light-integration-colab-setup — IC-Light no Colab: setup, deps e divisão de responsabilidades"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb", "agentes/relighting.py"]
tags: [concept, ic-light, colab, setup, gpu, t4, notebook]
---
# ic-light-integration-colab-setup — IC-Light no Colab: setup, deps e divisão de responsabilidades

Descreve como o Colab prepara o ambiente para o IC-Light e como as células do notebook se relacionam (ou não) com o que `agentes/relighting.py` realmente executa.

## Contexto: por que só roda no Colab

IC-Light usa SD 1.5 com a UNet expandida para 12 canais (fbc) em `torch.float16 + CUDA`. Isso requer:
- GPU CUDA com ≥5 GB VRAM.
- A máquina de dev local tem GTX 1650 Ti (4 GB) e torch CPU-only.

Logo, todo o relighting é Colab-only. Ver [[concepts/gpu-vram-local-vs-colab]] e [[decisions/local-vs-colab]].

## Células do notebook relevantes para IC-Light

### Célula 3 — Clone do repositório IC-Light

```bash
git clone --depth 1 https://github.com/lllyasviel/IC-Light /content/IC-Light
pip install -q -r /content/IC-Light/requirements.txt
```

Clona o repositório original e instala suas dependências. Na implementação fbc atual, **este clone não é usado** por `agentes/relighting.py` — o agente usa `diffusers` diretamente, sem os scripts do repositório IC-Light. O clone é um resquício da versão fc anterior. Ver [[concepts/ic-light-integration-notebook-agent-mismatch]].

### Célula 4 — Download de pesos (desatualizada)

Baixa `iclight_sd15_fc.safetensors` para `/content/IC-Light/models/`. O agente usa `iclight_sd15_fbc.safetensors` via HF Hub cache — ignorando este diretório.

Baixa também `v1-5-pruned-emaonly.safetensors` para `/content/ComfyUI/models/checkpoints/`. O agente usa `stablediffusionapi/realistic-vision-v51` via `from_pretrained` — não usa este checkpoint.

### Célula 2 — Dependências que o IC-Light precisa

```bash
pip install diffusers transformers accelerate safetensors
pip install rembg[gpu] onnxruntime-gpu
pip install torch torchvision torchaudio --index-url .../cu118
```

Estas são as dependências que `agentes/relighting.py` de fato usa: `torch`, `diffusers`, `safetensors`, `huggingface_hub`. O `rembg[gpu]` é para o [[entities/remocao]], não para o relighting.

### Célula 7 — Execução (onde o IC-Light realmente roda)

```python
from agentes.relighting import carregar_iclight, aplicar_relighting
pipe = carregar_iclight()     # baixa fbc do HF Hub se necessário
result_relight = aplicar_relighting(pipe, ...)
del pipe
torch.cuda.empty_cache()
```

O IC-Light fbc é carregado aqui. O `carregar_iclight()` sem `model_path` aciona `_baixar_pesos_fbc(None)`, que baixa `iclight_sd15_fbc.safetensors` do HF Hub para `~/.cache/huggingface/`. A GPU T4 do Colab (≥15 GB) roda no modo normal (não `low_vram`).

Após o relighting, o pipeline é destruído e a VRAM liberada antes da exportação.

## Fluxo de dados IC-Light no Colab

```
Drive: /content/drive/MyDrive/iclight_pipeline/
  frames/nobg/   ← RGBA PNGs sem fundo (Agente 2: rembg)
  background/    ← bg.png (Agente 3: SD 1.5 ou fundo próprio)
       ↓
  agentes/relighting.py  ← carregar_iclight() → pipe (GPU T4)
       ↓
  relit/         ← PNGs RGB: pessoa composta+relitada no fundo
       ↓
  output/        ← video_final.mp4 (Agente 5: ffmpeg)
```

Todos os diretórios ficam no Drive para sobreviver a desconexões do Colab free. O resume em `aplicar_relighting` pula frames já presentes em `relit/`.

## VRAM no T4

O T4 tem ~15 GB VRAM. O pipeline SD 1.5 fbc em fp16 usa ~4–6 GB em pico — confortável sem `low_vram`. Após `del pipe + cuda.empty_cache()`, a VRAM é liberada para o ffmpeg (que não usa GPU, mas evita pressão de memória).

## Desconexões do Colab

O Colab free desconecta após ~30–90 min de ociosidade ou ~12h de uso. O resume frame-a-frame de `aplicar_relighting` (teste `os.path.exists(output_path)`) significa que re-executar a célula 7 retoma do último frame concluído. Frames parcialmente escritos não ocorrem porque o `out.save(output_path)` é atômico no nível do arquivo.

## Relacionados

[[concepts/ic-light-integration-notebook-agent-mismatch]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[concepts/agent-relighting-vram]] ·
[[decisions/local-vs-colab]] · [[entities/relighting]] ·
[[sources/lumina-bg-notebook]] · [[index]]
