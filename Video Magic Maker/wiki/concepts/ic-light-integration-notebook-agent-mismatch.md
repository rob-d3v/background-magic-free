---
title: "ic-light-integration-notebook-agent-mismatch — Divergência fc/fbc entre notebook e agente"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb", "agentes/relighting.py"]
tags: [concept, ic-light, fc, fbc, colab, notebook, mismatch, bug]
---
# ic-light-integration-notebook-agent-mismatch — Divergência fc/fbc entre notebook e agente

> ⚠️ Contradiction: `lumina_bg.ipynb` (célula 4) baixa `iclight_sd15_fc.safetensors` (variante fc, 8 canais), mas `agentes/relighting.py` espera e usa `iclight_sd15_fbc.safetensors` (variante fbc, 12 canais). O notebook não foi atualizado após a migração fc→fbc.

## O problema

A migração de fc para fbc (documentada em [[decisions/migrate-fc-to-fbc]] e [[decisions/agent-relighting-fbc-completed]]) atualizou o agente Python, mas não a célula de download de modelos do notebook Colab.

### Notebook — célula 4 (estado atual, desatualizado)

```python
# IC-Light weights (foreground conditioned)
icl_dir = "/content/IC-Light/models"
icl_file = os.path.join(icl_dir, "iclight_sd15_fc.safetensors")   # <-- fc (8 canais)
hf_hub_download(
    repo_id="lllyasviel/ic-light",
    filename="iclight_sd15_fc.safetensors",                        # <-- fc
    local_dir=icl_dir,
)
```

### Agente Python — `agentes/relighting.py` (estado atual, correto)

```python
FBC_REPO = "lllyasviel/ic-light"
FBC_FILE = "iclight_sd15_fbc.safetensors"   # fbc (12 canais)
```

`_baixar_pesos_fbc` baixa `iclight_sd15_fbc.safetensors` diretamente do HF Hub para o cache padrão (`~/.cache/huggingface/`), ignorando o diretório `/content/IC-Light/models/` que a célula 4 popula.

## Consequência em tempo de execução

O agente `carregar_iclight()` não usa o arquivo baixado pela célula 4. Ele baixa o pesos correto (`fbc`) via `hf_hub_download` quando chamado na célula 7 ("Run pipeline"). A célula 4 baixa `fc` desnecessariamente — desperdiça tempo e espaço em disco no Colab (~400MB), sem impacto funcional.

**Não é um bug bloqueante**, mas representa:
- Download redundante (fc baixado mas nunca usado).
- Risco de confusão se alguém tentar usar o arquivo `fc` diretamente.

## Diferença de arquitetura de download (notebook vs agente)

O notebook tem duas formas de obter os pesos IC-Light:

| Abordagem | Onde | Arquivo alvo | Usado? |
|---|---|---|---|
| Célula 4: download explícito para `/content/IC-Light/models/` | notebook | `fc.safetensors` | Não (caminho não passado ao agente) |
| `_baixar_pesos_fbc(None)`: `hf_hub_download` para cache HF | `relighting.py` | `fbc.safetensors` | Sim |

## Outros pontos da célula 4 — repositório IC-Light clonado

A célula 3 também clona o repositório `lllyasviel/IC-Light` (GitHub) para `/content/IC-Light/` e instala seu `requirements.txt`. Isso foi provavelmente necessário para a versão fc anterior (que possivelmente usava scripts do repositório), mas a implementação fbc atual usa `diffusers` e não precisa do clone do repositório. O clone adiciona tempo de setup sem benefício funcional.

A célula 4 também baixa o SD 1.5 checkpoint para o diretório ComfyUI (`/content/ComfyUI/models/checkpoints/v1-5-pruned-emaonly.safetensors`), enquanto o agente usa `from_pretrained("stablediffusionapi/realistic-vision-v51")` (Realistic Vision v5.1, não o SD 1.5 original). São dois modelos base diferentes — o notebook e o agente não compartilham o SD 1.5.

## Correção recomendada no notebook (inferida)

Atualizar a célula 4 para:
1. Substituir `iclight_sd15_fc.safetensors` por `iclight_sd15_fbc.safetensors`.
2. Opcionalmente, remover o clone do repositório IC-Light (célula 3) e o download do SD 1.5 para o ComfyUI, pois o agente fbc não usa ComfyUI nem o repositório clonado.

## Relacionados

[[decisions/migrate-fc-to-fbc]] · [[decisions/agent-relighting-fbc-completed]] ·
[[concepts/ic-light]] · [[entities/agent-relighting-module]] ·
[[sources/lumina-bg-notebook]] · [[sources/agent-relighting-source]] · [[index]]
