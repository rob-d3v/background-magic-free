---
title: Detecção de FPS — resolução de fração NTSC e outros formatos
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/extracao.py"]
tags: [concept, fps, ffprobe, ntsc, fraction, frame-rate]
---
# Detecção de FPS — resolução de fração NTSC e outros formatos

O [[entities/extracao]] precisa do FPS real do vídeo para que a [[entities/exportacao]] reconstitua o timing original. O valor é lido do campo `r_frame_rate` do ffprobe e requer uma etapa de conversão não trivial.

## Por que ffprobe retorna uma fração?

O padrão MPEG/H.264 armazena frame rate como uma fração `num/den` para evitar imprecisão de ponto flutuante. Os casos mais comuns:

| Conteúdo | `r_frame_rate` | FPS calculado |
|---|---|---|
| Cinema digital (DCI) | `24/1` | 24.0 |
| PAL (Europa/Brasil analógico) | `25/1` | 25.0 |
| NTSC (EUA/Japão analógico) | `30000/1001` | 29.97 |
| NTSC alto (webcam/streaming) | `60000/1001` | 59.94 |
| Câmera moderna comum | `30/1` | 30.0 |

O denominador `1001` é o marcador histórico do NTSC drop-frame, onde 30000/1001 ≈ 29.97002997... O arredondamento a 3 casas dá `29.97`.

## Código de resolução

```python
fps_raw = meta["r_frame_rate"]       # ex: "30000/1001"
num, den = map(int, fps_raw.split("/"))
fps = round(num / den, 3)            # ex: 29.97
```

1. `fps_raw.split("/")` divide em `["30000", "1001"]`.
2. `map(int, ...)` converte para inteiros.
3. Divisão de ponto flutuante em Python 3 — `num / den` já é `float`.
4. `round(..., 3)` limita a 3 casas decimais, suficiente para qualquer frame rate prático (erro máximo de 0.0005 fps).

## Onde o fps é consumido

O valor `fps` retornado por `extrair_frames()` é repassado diretamente a `exportar_video()` como argumento `fps=meta["fps"]`. Lá ele é usado no flag `-r {fps}` do ffmpeg para definir o frame rate do vídeo de saída. Sem essa precisão, o vídeo exportado teria timing ligeiramente errado (áudio dessincronizado em vídeos longos).

## Gotchas

- `r_frame_rate` pode diferir de `avg_frame_rate` em vídeos com frame rate variável (VFR). O agente usa sempre `r_frame_rate` (frame rate declarado pelo codec), que é a referência para reprodução.
- Se o campo vier ausente (container corrompido), o `json.loads` vai lançar `KeyError` — não há tratamento explícito de fallback.

## Relacionados

[[entities/extracao]] · [[entities/exportacao]] · [[sources/agent-frame-extraction-config-py]] · [[index]]
