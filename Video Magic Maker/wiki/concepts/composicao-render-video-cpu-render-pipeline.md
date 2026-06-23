---
title: "Pipeline CPU de troca de fundo (composição e render)"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources:
  - agentes/composicao.py
  - agentes/render_video.py
  - agentes/matting_rvm.py
  - agentes/matting_live.py
tags:
  - pipeline
  - cpu
  - background-swap
  - composicao
  - render
---

# Pipeline CPU de troca de fundo (composição e render)

Dois caminhos independentes que trocam o fundo de um vídeo sem GPU e sem reiluminação por IA: o caminho leve (Pillow, composicao.py) e o caminho de qualidade (RVM + torch, render_video.py).

## Visão geral dos dois caminhos

```
[frames PNG RGBA]  ──► composicao.py (Pillow, CPU rápido)
                         └── alpha composite  ──► frames RGB

[frames PNG BGR]   ──► render_video.py  ──► RVMMatter (torch CPU)
                         └── RVM matte + compose ──► frames RGB

[arquivo .mp4]     ──► render_arquivo()
                         └── cv2.VideoCapture → RVMMatter → VideoWriter → FFmpeg mux ──► .mp4 c/ áudio
```

## Caminho leve: composicao.py

- **Entrada**: frames já recortados (PNG RGBA, fundo transparente) + imagem de fundo.
- **Operação**: resize+cover do fundo, alpha composite via PIL `paste`.
- **Ajustes**: brilho e cor por `ImageEnhance` (0 tokens de IA, determinístico).
- **Resume automático**: checa existência do arquivo de saída antes de processar.
- **Quando usar**: GPU indisponível, preview rápido, processamento em lote sem GPU.

## Caminho de qualidade: render_video.py

- **Entrada**: frames PNG BGR (não recortados) + fundo (imagem ou vídeo).
- **Operação**: RVMMatter processa em ordem → estado recorrente garante coerência temporal.
- **Downsample ratio**: calculado dinamicamente por `_dr_qualidade` para ~720px no lado longo, entre 0.35 e 0.70.
- **Fundo**: imagem estática (`cobrir`), fundo desfocado (`fundo_desfocado`) ou vídeo em loop (`VideoFundo`).
- **Resume parcial**: possível, mas reinicia estado RVM — para resultado limpo, apagar saída antes.
- **Audio mux**: FFmpeg `-map 1:a:0?` (áudio opcional, sem erro se ausente).

## Comparação dos caminhos

| Critério | composicao.py | render_video.py (RVM) |
|---|---|---|
| Dependências | Pillow | torch, opencv, RVM model |
| Entrada | RGBA (já recortado) | BGR bruto |
| Qualidade de borda | Depende do recorte anterior | Alta (alpha matte real, sem halo) |
| Coerência temporal | Nenhuma | Estado recorrente RVM |
| Velocidade | Muito rápida (CPU puro) | ~10 fps em CPU a 540p |
| Reiluminação | Nenhuma | Nenhuma |
| GPU | Não requer | Não requer (torch CPU) |

## Sequência de chamada (render_arquivo)

```
render_arquivo(input.mp4, output.mp4, engine="rvm", bg_mode="image", ...)
  ├── cv2.VideoCapture(input.mp4)  → fps, w, h, total
  ├── _build_matter("rvm", dr=_dr_qualidade(w,h))  → RVMMatter
  ├── cobrir(bg_image, w, h)  → fundo redimensionado
  ├── loop: cap.read() → matter.compor(frame, bg) → writer.write(out)
  ├── matter.close()
  ├── ffmpeg -map 0:v:0 -map 1:a:0? -c:v copy -c:a aac → output.mp4
  └── os.remove(tmp) ou os.replace(tmp, output) se ffmpeg falhar
```

## Relações

- [[composicao-render-video-composicao]] — caminho leve.
- [[composicao-render-video-render-video]] — caminho de qualidade.
- [[composicao-render-video-rvm-matter]] — motor RVM.
- [[composicao-render-video-matting-live]] — utilitários compartilhados (cobrir, VideoFundo, etc.).
