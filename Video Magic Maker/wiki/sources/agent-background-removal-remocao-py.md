---
title: "Source: agentes/remocao.py"
type: source
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/remocao.py"]
tags: [source, rembg, segmentation, agent-2]
---
# Source: agentes/remocao.py

Implementação do Agente 2 — Remoção de Fundo. 73 linhas. Sem dependências de projeto além do `rembg`.

## Sumário do arquivo

- **Docstring de módulo**: descreve o agente como processador por frame com GPU via rembg, produzindo PNGs com canal alpha.
- **Imports**: `os`, `time`, `json` (stdlib); `rembg.remove`, `rembg.new_session`; `tqdm.tqdm`.
- **Função única**: `remover_fundo(frames_dir, output_dir, log_path=None)`.

## Pontos arquiteturais notáveis

1. **Sessão rembg fora do loop**: `new_session("u2net_human_seg")` é chamado uma vez
   antes do `for` — carrega o modelo ONNX em memória uma única vez.

2. **Resume por existência de arquivo**: `if os.path.exists(output_path): continue` —
   não há hash, timestamp ou manifest; a presença do arquivo é a prova de conclusão.

3. **I/O em bytes**: lê e escreve `bytes` brutos (não PIL Image) — rembg aceita e
   retorna PNG serializado diretamente, evitando decode/encode intermediário.

4. **Alpha matting habilitado** com três parâmetros explícitos no `remove()`:
   `alpha_matting_foreground_threshold=240`, `alpha_matting_background_threshold=10`,
   `alpha_matting_erode_size=10`.

5. **Tratamento de erro por frame**: `try/except Exception` → `erros.append(...)` →
   `print(...)` → continua o loop. Não usa `logging`, apenas `print` e JSON.

6. **Persistência de erros**: merge com `pipeline_log.json` existente — carrega
   JSON, adiciona chave `"remocao_fundo_erros"`, reescreve. Proteção contra JSON
   corrompido: `except (json.JSONDecodeError, ValueError): log_data = {}`.

7. **Retorno**: dict com três chaves — `processados`, `erros`, `tempo_s`.

## Ausências relevantes

- Sem configuração de providers ONNX (delegado ao rembg/onnxruntime).
- Sem logging estruturado (só print + JSON).
- Sem parâmetros de alpha matting expostos como argumentos — hardcoded.
- Sem timeout por frame.
- Sem validação do PNG de saída após escrita.

## Relacionados

[[entities/agent-background-removal-remocao]] · [[concepts/agent-background-removal-onnx-inference]] ·
[[concepts/agent-background-removal-alpha-matting]] · [[index]]
