---
title: "Agente 2 — remocao.py (rembg background removal)"
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/remocao.py", "pipeline.py", "config.py", "requirements.txt"]
tags: [agent, rembg, onnx, segmentation, alpha-matting, per-frame, resume]
---
# Agente 2 — remocao.py (rembg background removal)

`agentes/remocao.py` é o Agente 2 da pipeline lumina-bg: recorta a pessoa de cada frame via rembg/ONNX, produzindo PNGs RGBA prontos para relighting ou composição.

## Assinatura pública

```python
def remover_fundo(frames_dir: str, output_dir: str, log_path: str = None) -> dict:
```

Retorna `{"processados": int, "erros": int, "tempo_s": float}`.

## Posição na pipeline

O orquestrador (`pipeline.py`) chama o agente como passo 2/5:

```
[1] extracao → frames/raw/   (PNGs rgb24)
[2] remocao  → frames/nobg/  (PNGs RGBA)   ← este agente
[3] geracao_fundo / fundo próprio
[4] relighting (IC-Light) ou composicao
[5] exportacao → video_final.mp4
```

Chamada concreta no orquestrador:
```python
result_rembg = remover_fundo(paths.frames_raw, paths.frames_nobg, log_path=paths.log_path)
```

Onde `paths` é instância de `config.Paths` — ver [[concepts/agent-background-removal-paths]].

## Fluxo interno passo-a-passo

1. `os.makedirs(output_dir, exist_ok=True)` — cria `frames/nobg/` se não existe.
2. `new_session("u2net_human_seg")` — carrega o modelo ONNX em memória (download automático no primeiro uso; cache em `~/.u2net/`).
3. `sorted([...])` — lista todos os `.png` em `frames_dir`, ordenados lexicograficamente (`frame_00001.png` … `frame_NNNNN.png`).
4. Loop `tqdm` por frame:
   a. **Resume check**: `if os.path.exists(output_path): continue` — pula frames já prontos.
   b. Lê o arquivo inteiro como `bytes` com `open(..., "rb")`.
   c. Chama `remove(img_bytes, session=session, alpha_matting=True, ...)` — retorna `bytes` PNG RGBA.
   d. Escreve o resultado em `output_path` com `open(..., "wb")`.
   e. Qualquer exceção é capturada por frame: append em `erros`, print, continua.
5. Após o loop: se `log_path` e há erros, persiste `{"remocao_fundo_erros": [...]}` em `pipeline_log.json` (merge com conteúdo existente).
6. Retorna o dict de sumário.

## Parâmetros alpha matting

| Parâmetro | Valor | Descrição |
|---|---|---|
| `alpha_matting` | `True` | Liga pós-processamento de bordas |
| `alpha_matting_foreground_threshold` | 240 | Pixels acima → foreground definido (trimap) |
| `alpha_matting_background_threshold` | 10 | Pixels abaixo → background definido (trimap) |
| `alpha_matting_erode_size` | 10 | Erosão aplicada ao trimap antes do matting |

Ver [[concepts/agent-background-removal-alpha-matting]] para o algoritmo completo.

## Modelo ONNX

- ID: `"u2net_human_seg"` — variante do U²-Net treinada para pessoas.
- Backend: ONNX Runtime (`onnxruntime-gpu` em produção Colab; cai em CPU local).
- Cache: `~/.u2net/u2net_human_seg.onnx` (~176 MB); download único no primeiro uso.
- Ver [[concepts/agent-background-removal-onnx-inference]] para detalhes de providers.

## Resume automático

A linha `if os.path.exists(output_path): continue` torna a execução **idempotente**:
reexecutar o pipeline em Colab após desconexão continua de onde parou sem reprocessar
frames prontos. Ver [[concepts/agent-background-removal-resume]].

## Saída

- Arquivo: `frames/nobg/frame_NNNNN.png` — PNG RGBA, mesmo nome do frame de entrada.
- Canal alpha: 0 = transparente (fundo removido), 255 = opaco (pessoa).
- O consumidor downstream ([[entities/relighting]]) usa o canal alpha indiretamente:
  compõe o RGBA sobre cinza neutro `(127,127,127)` para obter foreground RGB antes
  do VAE.

## Tratamento de erros

- Exceções por frame: capturadas individualmente, não abortam o lote.
- Acumuladas em `erros = [{"frame": str, "erro": str}]`.
- Persistidas em `pipeline_log.json` chave `"remocao_fundo_erros"` se `log_path` fornecido.
- O orquestrador soma `result_rembg["erros"]` em `pipeline_log["erros_total"]`.

## Dependências diretas

- `rembg[gpu]>=2.0.50` (requirements.txt) → `remove`, `new_session`
- `onnxruntime-gpu>=1.16.0` — provider de inferência
- `tqdm>=4.66.0` — barra de progresso
- `os`, `time`, `json` — stdlib

## Relacionados

[[entities/remocao]] · [[concepts/agent-background-removal-alpha-matting]] ·
[[concepts/agent-background-removal-onnx-inference]] · [[concepts/agent-background-removal-resume]] ·
[[concepts/agent-background-removal-paths]] · [[decisions/agent-background-removal-model-choice]] ·
[[concepts/video-frame-pipeline]] · [[concepts/gpu-vram-local-vs-colab]] · [[index]]
