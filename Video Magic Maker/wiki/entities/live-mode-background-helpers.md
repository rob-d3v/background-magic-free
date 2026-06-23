---
title: live-mode-background-helpers — VideoFundo, carregar_fundo, cobrir, fundo_desfocado
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/matting_live.py"]
tags: [entity, live, background, videofundo, helpers, matting-live]
---
# live-mode-background-helpers — VideoFundo, carregar_fundo, cobrir, fundo_desfocado

`agentes/matting_live.py` exporta quatro helpers de gestão de fundo usados por [[entities/live-mode]] e [[entities/camera-app]]. Juntos, normalizam qualquer fonte de fundo (imagem estática, vídeo animado, desfoque gaussiano) para um array BGR `uint8` com exatamente as dimensões do frame.

## cobrir(bg_bgr, w, h) — resize cover-crop

`cobrir` redimensiona uma imagem de fundo para preencher um canvas `w×h` mantendo a proporção, depois realiza center-crop para as dimensões exatas.

Algoritmo:
1. `scale = max(w / iw, h / ih)` — a menor escala que faz ambas as dimensões atingirem o alvo.
2. Redimensiona com `cv2.INTER_LANCZOS4` (alta qualidade).
3. Recorta `r[y:y+h, x:x+w]` centrado.

Usado por `carregar_fundo`, `VideoFundo.proximo` e a GUI ([[entities/camera-app]]).

## carregar_fundo(path, w, h) — carregar imagem estática de fundo

Carrega uma imagem de fundo do disco com `cv2.imread` (BGR), valida existência e leiturabilidade, depois chama `cobrir` para ajustar ao tamanho do frame.

Chamado **uma vez antes do loop** em `live.py` (não por frame) — o resultado é cacheado em `bg_img`.

## fundo_desfocado(frame_bgr, intensidade) — desfoque estilo Meet

Retorna o frame de entrada borrado com kernel gaussiano de tamanho `max(3, intensidade | 1)`. O `| 1` garante que o tamanho do kernel seja ímpar (requisito do OpenCV). Chamado **por frame** no loop quando `--blur N` está ativo.

É o modo de fundo mais leve: sem carregamento de modelo, sem I/O de disco — apenas um desfoque gaussiano sobre o frame atual.

## VideoFundo — fundo de vídeo animado (loop)

`VideoFundo(path, w, h)` abre um arquivo de vídeo com `cv2.VideoCapture` e transmite seus frames como fundo, em loop infinito.

### proximo() — próximo frame de fundo

```python
def proximo(self) -> np.ndarray:
    ok, f = self.cap.read()
    if not ok:                   # fim do vídeo → rebobina
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, f = self.cap.read()
    return cobrir(f, self.w, self.h)
```

Cada chamada avança um frame. Quando o vídeo termina, `CAP_PROP_POS_FRAMES` é definido como 0 para rebobinar. O frame é cover-cropped para as dimensões alvo antes de retornar.

### Contextos de uso

- **Modo live** ([[entities/live-mode]], [[entities/live-mode-cli]]): fundo virtual animado (a GUI [[entities/camera-app]] expõe isso como opção de "fundo em vídeo").
- **Render offline** ([[entities/render-video]]): fundo animado sincronizado por frame no pipeline de render em lote.

### close()

Chama `self.cap.release()` para liberar o handle do `VideoCapture`.

## Relacionados
[[entities/live-mode]] · [[entities/live-mode-cli]] · [[entities/camera-app]] · [[entities/render-video]] · [[concepts/live-mode-frame-pipeline]] · [[index]]
