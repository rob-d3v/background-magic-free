---
title: Fluxo de dados — render offline (render_arquivo e render_matting)
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/render_video.py", "agentes/matting_rvm.py", "agentes/matting_live.py"]
tags: [concept, render, offline, pipeline, dataflow, rvm, mediapipe, ffmpeg, audio]
---
# Fluxo de dados — render offline (render_arquivo e render_matting)

Esta página descreve o **fluxo de dados e sequência de chamadas** do caminho
CPU-only de render offline implementado em `agentes/render_video.py`
([[entities/render-video]]). O caminho tem **duas funções de entrada** com fluxos
distintos.

## `render_arquivo` — fluxo completo (arquivo de vídeo → mp4 com áudio)

Usado pelo botão **✅ Aplicar (renderizar tudo)** do [[entities/camera-app]].

```
camera_app._aplicar_render()
  │  snapshot: engine="rvm", bg_mode, bg_image_path, bg_video_path, blur, refine
  │  thread daemon:
  └─► render_arquivo(input_path, output_path, engine, bg_mode, ...)
        │
        ├─ cv2.VideoCapture(input_path)
        │    lê fps / w / h / total
        │
        ├─ _build_matter(engine, dr=_dr_qualidade(w,h))
        │    engine=="rvm"  →  RVMMatter(downsample_ratio=_dr_qualidade(w,h))
        │    engine!="rvm"  →  LiveMatter()
        │
        ├─ resolve fundo (uma vez, antes do loop)
        │    bg_mode=="video"  →  VideoFundo(bg_video_path, w, h)   [loop]
        │    bg_mode=="image"  →  cv2.imread(bg_image_path) + cobrir(raw, w, h)
        │    bg_mode=="blur"   →  fundo_desfocado(frame, blur) por frame (no loop)
        │    bg_mode=="none"   →  frame passado direto (sem matting)
        │
        ├─ tmp = output_path[:-4] + "_noaudio.mp4"
        ├─ cv2.VideoWriter(tmp, mp4v, fps, (w,h))
        │
        └─ LOOP: cap.read()
              frame → matter.compor(frame, bg, color_match, refine)
              │         RVMMatter: usa fgr descontaminado + alpha matte
              │         LiveMatter: confidence mask → guided filter → composite
              writer.write(out)
              progress_cb(i, total)
           cap.release() / writer.release() / matter.close()
           bgv.close() se VideoFundo
        │
        └─ REMUX DE ÁUDIO (ffmpeg subprocess)
              ffmpeg -y -i tmp -i input_path
                     -map 0:v:0 -map 1:a:0?   ← áudio opcional
                     -c:v copy -c:a aac -shortest output_path
              sucesso → os.remove(tmp)
              falha   → os.replace(tmp, output_path)  [entrega vídeo mudo]
```

### Pontos-chave do fluxo

- **`_dr_qualidade(w,h)`** calcula `clamp(720/max(w,h), 0.35, 0.7)`: mira a rede
  coarse do RVM em ~720px (mais detalhe de cabelo). É passado apenas quando
  `engine=="rvm"`; `LiveMatter` não tem `downsample_ratio`.

- **O fundo de imagem é lido do path original** (não do BGR já escalonado do
  camera_app): `cv2.imread(bg_image_path)` + `cobrir(raw, w, h)` — escala ao
  tamanho exato do vídeo de entrada, sem perda por dupla reescala (bug anterior
  que degradava fundos em vídeos de resolução diferente da câmera).

- **O `VideoFundo` é instanciado uma vez** antes do loop e avança 1 frame por
  frame de saída (`bgv.proximo()`), dando loop automático quando o vídeo de
  fundo é mais curto que o clipe.

- **A thread do worker do camera_app solta a câmera** (`_rendering=True`) durante
  o render para não disputar CPU com o RVM. Ver [[entities/camera-app]].

- **O ffmpeg remux usa `-map 1:a:0?`** (ponto de interrogação = áudio opcional):
  se o input tem áudio, entra; se não tem, o ffmpeg ignora sem erro. Isso elimina
  a necessidade de sondar com `ffprobe` (a sonda anterior falhava por match de
  string).

- **Fallback robusto:** se o `subprocess.run(ffmpeg, check=True)` lançar exceção
  (ffmpeg ausente, disco cheio, formato incompatível), `os.replace(tmp, output_path)`
  entrega o vídeo sem áudio — sem quebrar o app.

## `render_matting` — fluxo de diretório de frames

Usado pelo modo Studio (`app.py`, modo HD). Não remuxo de áudio — o
`exportar_video` do Studio faz isso separadamente.

```
app.py cb_aplicar (modo MODO_HD)
  │  shutil.rmtree(frames_relit)   ← render limpo (reseta estado RVM)
  └─► render_matting(frames_dir, background_path, output_dir, engine="rvm", ...)
        │
        ├─ sorted(*.png)  →  lista de frames em ordem (coerência temporal do RVM)
        │
        ├─ cv2.imread(frames[0])  →  detecta w, h
        │
        ├─ fundo:
        │    background_path em _VIDEO_EXT  →  VideoFundo(background_path, w, h)
        │    caso contrário                 →  cobrir(cv2.imread(bg_path), w, h)
        │
        ├─ _build_matter(engine, dr=_dr_qualidade(w,h))
        │
        └─ LOOP: frames em ordem
              cv2.imread(frame)
              fundo = bg_video.proximo() ou bg (fixo)
              out = matter.compor(frame, fundo, color_match, feather)
              cv2.imwrite(output_dir/fn, out)
              progress_cb(i+1, len(frames))
           matter.close() / bg_video.close()
        │
        └─ retorna {"processados", "tempo_s", "engine"}
```

### Coerência temporal do RVM

O RVM mantém estado recorrente `rec=[None]*4` entre frames. Processar os frames
**em ordem** (via `sorted`) faz o estado temporal acumular — cada frame informa
o próximo, reduzindo tremor de borda. O `render_matting` limpa a saída
(`shutil.rmtree`) antes de rodar pra garantir o estado limpo desde o frame 0.

Se a saída NÃO for limpa (modo resume — pula frames já existentes), o estado
recorrente **reinicia do zero** no ponto retomado → tremor naquele segmento.

## Diferenças entre os dois caminhos

| | `render_arquivo` | `render_matting` |
|---|---|---|
| Entrada | arquivo de vídeo (`cv2.VideoCapture`) | diretório de frames PNG |
| Saída | arquivo mp4 (com áudio) | diretório de PNGs compostos |
| Áudio | remux do original (`ffmpeg -map 1:a:0?`) | não — exige `exportar_video` depois |
| Fundo blur | sim (`fundo_desfocado` por frame) | não (só imagem ou vídeo) |
| Fundo none | sim (passthrough) | não |
| Chamador | [[entities/camera-app]] | `app.py` (modo Studio) |
| Resume | não (lê o arquivo do início) | sim (pula PNGs já existentes — mas quebra coerência temporal) |

## Relacionados

[[entities/render-video]] · [[concepts/rvm-matting]] · [[concepts/realtime-matting]] ·
[[entities/camera-app]] · [[entities/live-mode]] · [[index]]
