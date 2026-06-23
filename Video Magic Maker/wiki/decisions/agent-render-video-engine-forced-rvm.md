---
title: "Decisão: render final sempre usa RVM (independente do motor do live)"
type: decision
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py", "agentes/render_video.py"]
tags: [decision, render, rvm, engine, quality, inferred]
status: inferred
---
# Decisão: render final sempre usa RVM (independente do motor do live)

> **Inferred** — não há registro explícito de deliberação; inferido do código e do
> comentário inline em `camera_app.py`.

## Contexto

O [[entities/camera-app]] permite ao usuário selecionar o motor de recorte ao vivo:
**MediaPipe** (rápido, ~15 fps) ou **RVM** (qualidade, ~9.6 fps). Esse motor é
armazenado em `self.engine` e usado no preview do modo vídeo.

Ao clicar **✅ Aplicar (renderizar tudo)**, `_aplicar_render` captura um snapshot
das configs para a thread de render:

```python
engine, bg_mode = "rvm", self.bg_mode    # render final SEMPRE no RVM (melhor qualidade)
```

O motor passado para `render_arquivo` é **sempre `"rvm"`**, independentemente de
`self.engine` (que pode ser `"mediapipe"`).

## Decisão

**Forçar `engine="rvm"` no render final**, ignorando a escolha do motor ao vivo.

## Justificativa

1. **Render é offline — sem pressão de fps.** O MediaPipe é necessário para o live
   por ser mais leve (~15+ fps), mas no render o tempo por frame não importa
   (usuário aceita esperar). O custo extra do RVM (~2.6 fps a 720p vs o MediaPipe
   mais rápido) é aceitável.

2. **RVM entrega alpha matte real.** O MediaPipe entrega uma confidence mask de
   baixa resolução (256²) que mesmo com guided filter/threshold/erode pode deixar
   borda cortada em fundo difícil. O RVM produz um alpha verdadeiro sem bolhas no
   ombro, sem halo e com cabelo preservado — exatamente o que importa num render
   permanente (arquivo salvo na galeria).

3. **Coerência temporal.** O RVM mantém estado recorrente entre frames
   ([[concepts/rvm-matting]]); processar os frames em ordem reduz o tremor de
   borda ao longo do vídeo. O render em ordem maximiza essa vantagem.

4. **Consistência para o usuário.** O preview ao vivo pode usar MediaPipe (pelo
   fps), mas o arquivo final sempre terá a melhor qualidade disponível. Isso evita
   a surpresa de renderizar com MediaPipe e obter resultado inferior ao preview
   com RVM.

## Trade-offs / consequências

- O render com RVM é mais lento (~2.6 fps @720p ≈ 12 min por minuto de vídeo
  @30fps). O usuário vê o progresso na status bar e o botão fica desabilitado.
- Se o torch/RVM não estiver instalado, o `_build_matter("rvm", ...)` vai
  lançar `ImportError` — o app mostra erro na UI. Não há fallback automático
  para MediaPipe no render.
- No modo Studio (`app.py`), `render_matting` também usa `engine="rvm"` por
  default — mesma lógica.

## Relacionados

[[entities/render-video]] · [[concepts/rvm-matting]] · [[entities/camera-app]] ·
[[concepts/agent-render-video-offline-pipeline]] · [[index]]
