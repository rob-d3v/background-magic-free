---
tags: [concept, realtime, matting, rvm, robustvideomatting, torch, live]
date: 2026-06-13
status: stable
source: agentes/matting_rvm.py
---

# RVM — RobustVideoMatting (matting de alta qualidade)

**RVM (RobustVideoMatting)** é o motor de recorte de **alta qualidade**,
alternativa ao MediaPipe ([[concepts/realtime-matting]]). Implementado em
`agentes/matting_rvm.py` (classe `RVMMatter`). Resolve de verdade os problemas de
borda do MediaPipe: rosto/cabelo "comidos", bolhas de falso-positivo no ombro e
franja de halo.

> **Serve dois caminhos.** O mesmo `RVMMatter` é usado no **live** em tempo real
> ([[components/live-mode]]) **e** no **render offline HD** do modo Studio
> ([[components/render-video]]). No live a coerência temporal é um bônus; no
> **render offline** ela **brilha**: sem pressão de fps, os frames são processados
> em ordem e o estado recorrente reduz o tremor de borda ao longo do vídeo (o
> live, frame-isolado, e o `compor`/rembg não têm essa vantagem).

## O que é
Rede de **video matting** que produz um **alpha matte verdadeiro** por frame — uma
máscara de transparência contínua e alinhada à silhueta real — em vez de uma
**confidence mask de baixa resolução** (o que o Selfie Segmenter do MediaPipe
entrega, internamente 256²). Por isso o alpha do RVM já vem **limpo**: não precisa
do pipeline de refino de borda do MediaPipe (guided filter / threshold / erode /
abertura morfológica). O `compor()` do RVM só aplica `feather` opcional e
`color_match` leve.

Além do alpha (`pha`), o RVM devolve um **foreground descontaminado** (`fgr`) que o
`compor()` usa como cor da pessoa — ver "Foreground descontaminado" abaixo.

### Alpha real vs confidence mask
- **Confidence mask (MediaPipe):** probabilidade por pixel de "ser pessoa", em
  baixa-res, suave e desalinhada da borda → precisa de threshold + morfologia +
  guided filter pra ficar usável; ainda assim sobra franja/halo em fundo claro.
- **Alpha matte (RVM):** o modelo é treinado pra estimar a transparência da borda
  (incluindo cabelo fino) diretamente. Sai colado no contorno real, sem bolhas e
  sem halo — daí dispensar os hacks de morfologia.

## Modelo e carga
- **Variante `mobilenetv3`**, carregada via torch.hub:
  `torch.hub.load("PeterL1n/RobustVideoMatting", "mobilenetv3", trust_repo=True)`.
- Pesos `rvm_mobilenetv3.pth` (**~15MB**) baixados e cacheados pelo **torch.hub** na
  primeira carga (~12s).
- `trust_repo=True` é **obrigatório**: sem ele, o torch.hub trava pedindo
  confirmação interativa (não dá pra responder num app/CLI).

## Estado recorrente (coerência temporal)
RVM é uma rede **recorrente**: mantém um estado `rec=[None]*4` que é passado entre
frames (`_fgr, pha, *rec = model(src, *rec, downsample_ratio=dr)`). Isso dá
**coerência temporal** — menos tremor/flicker na borda do que processar cada frame
isolado. O estado é **resetado** (`rec=[None]*4`) se a **resolução do frame mudar**
(`_last_shape`), senão a forma do estado não bate com o novo frame.

`RVMMatter.reset()` zera o estado recorrente (`rec=[None]*4`, `_last_shape=None`)
sob demanda — usado **entre clipes** e **antes de um preview de 1 frame** (no modo
Studio, `app.py` chama `.reset()` no `RVMMatter` cacheado antes de cada preview HD —
ver [[components/render-video]]).

## downsample_ratio
`downsample_ratio=0.4` (default no `RVMMatter`): o modelo processa internamente uma
versão reduzida do frame na **rede coarse** pra estimar o alpha e reprojeta na
resolução cheia. É o botão de **velocidade × precisão de borda** do RVM — menor =
mais rápido, borda um pouco mais grossa.

> **0.4 é o ratio de tempo real.** Mira ~512px no maior lado — bom pro live. No
> **render offline** (sem pressão de fps) vale subir o ratio pra ganhar detalhe de
> cabelo: o `render_video.py` calcula um **`_dr_qualidade(w,h)`** mirando ~720px.
> Ver "downsample_ratio de qualidade no render offline" abaixo e
> [[components/render-video]].

### downsample_ratio de qualidade no render offline
No render offline (`agentes/render_video.py`, [[components/render-video]]) o RVM usa
um ratio **maior** que o default, calculado por:

```
_dr_qualidade(w, h) = clamp(720 / max(w, h), 0.35, 0.7)
```

Mira a rede coarse em **~720px** no maior lado (mais detalhe de cabelo) em vez de
~512px. Ex.: **720p → dr ≈ 0.56**, **1080p → dr ≈ 0.375**. Como o render é offline,
vale o custo extra. `_build_matter(engine, dr=None)` aceita o ratio; `render_matting`
e `render_arquivo` passam `_dr_qualidade(w,h)` quando `engine=="rvm"`. Verificado:
render RVM com `fgr` + dr de qualidade funciona, áudio preservado.

## Foreground descontaminado (`fgr`) — mata a aura branca do cabelo
O RVM devolve **dois** tensores úteis por frame: o alpha `pha` **e** um foreground
`fgr` (**foreground estimado/descontaminado**). O `compor()` compõe usando o `fgr`
como cor da pessoa, não o frame original:

```
out = fgr * alpha + bg * (1 - alpha)     # correto (descontaminado)
out = frame * alpha + bg * (1 - alpha)   # antigo (aura branca)
```

**Por que a aura aparecia.** Nos pixels de borda (cabelo fino), o **frame original**
carrega uma **mistura** da cor do fundo ANTIGO (tipicamente claro). Compondo com o
frame cru, essa mistura clara vaza pro contorno do cabelo → vira uma **"aura/halo
branca"**, mesmo com o `alpha` perfeito. O `fgr` do RVM já **estima a cor pura do
foreground** (descontaminada do fundo antigo), então a borda do cabelo compõe limpa
sobre o fundo novo. Verificado: sobre fundo escuro, a aura clara some no `fgr` vs o
frame cru. Melhora a borda **no live E no render** (o preview do Studio também passa
a usar `fgr`).

## Fluxo de tensor (entrada/saída)
1. Frame **BGR** → `cv2.cvtColor` para **RGB** → `float32 / 255.0` (normaliza [0,1]).
2. `torch.from_numpy(rgb).permute(2,0,1).unsqueeze(0)` → tensor **[1, C, H, W]**.
3. `with torch.no_grad(): fgr, pha, *rec = model(src, *rec, downsample_ratio=dr)`.
4. **`_infer(frame)` devolve `(fgr_bgr, pha)`:**
   - **`fgr`** → `fgr[0].permute(1,2,0).numpy()` → RGB[0,1] → **BGR float 0..255**
     (`np.ascontiguousarray(f[:,:,::-1]) * 255`).
   - **`pha`** (alpha) → `pha[0,0].numpy().copy()`.
5. `compor()` usa o par `(fgr, pha)`; `mask()` usa só `_infer(...)[1]` (o alpha).

> **`.copy()` / `ascontiguousarray` obrigatório.** O numpy retornado **compartilha a
> memória do tensor**, que é liberada ao sair do escopo — sem `.copy()` (no `pha`)
> ou `np.ascontiguousarray` (no `fgr`, que também desfaz o slice reverso `::-1`) o
> array fica apontando para memória inválida (mesmo tipo de gotcha do `.copy()` no
> MediaPipe, em [[concepts/realtime-matting]]).

## Performance (medida, CPU, torch 2.12.0)
- **~9.6 fps @ 960×540** (104 ms/frame).
- Mais pesado que o MediaPipe no mesmo res (~15 fps refine ON / ~21 fps `--fast`).
- O custo é o forward da rede em CPU; **não** há pós-processo de borda (o alpha já
  é limpo), só `feather` + `color_match` opcionais.

## Dependência: torchvision + torch
- RVM importa `torchvision.models.mobilenetv3` → exige **torchvision** instalado.
- Instalar torchvision subiu o torch de **2.11 → 2.12 (CPU)** nesta máquina.
- A carga é via **torch.hub** (`trust_repo=True`, ver acima).

## Quando usar RVM vs MediaPipe
| | **MediaPipe** (rápido) | **RVM** (qualidade) |
|---|---|---|
| Saída | confidence mask 256² + refino | alpha matte verdadeiro |
| Borda / cabelo | come o rosto em fundo difícil; sobra franja | mantém cabelo e borda do rosto |
| Falso-positivo no ombro | bolhas (~0.55) precisam de threshold | não cria |
| Halo | precisa guided filter pra matar | não tem |
| Coerência temporal | suavização temporal manual | estado recorrente nativo |
| Perf @540p (CPU) | ~15 (refine) / ~21 (`--fast`) fps | ~9.6 fps |
| Dependências | mediapipe + opencv-contrib | torch + **torchvision** |

**Motivação concreta:** o usuário testou o live na webcam real com fundo diferente
e o **rosto/cabelo ficava "comido"** na borda — limite do MediaPipe (256² + os hacks
de morfologia agressivos que apertavam demais). RVM resolve. Use MediaPipe quando
quiser **mais fps**; RVM quando quiser **qualidade de borda** e puder pagar ~10fps.

## Interface drop-in
`RVMMatter.compor(frame_bgr, bg_bgr, color_match=0.0, feather=1, **_ignored)` tem a
**mesma assinatura** de `LiveMatter.compor` ([[components/live-mode]]): aceita e
**ignora** os params específicos do MediaPipe (`refine`, `threshold`, `erode`,
`abertura`) via `**_ignored`. Por isso a troca de motor é transparente para o
chamador (`live.py` / `camera_app.py`).

## Relacionados
[[concepts/realtime-matting]] · [[components/live-mode]] · [[components/render-video]] ·
[[components/camera-app]] · [[components/composicao]] ·
[[concepts/gpu-vram-local-vs-colab]] · [[index]]
