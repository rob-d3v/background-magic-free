---
title: live-mode-edge-refinement — pipeline de refino de borda (guided filter + morfologia)
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/matting_live.py"]
tags: [concept, live, matting, edge, guided-filter, morphology, mediapipe]
---
# live-mode-edge-refinement — pipeline de refino de borda (guided filter + morfologia)

O Selfie Segmenter do MediaPipe produz uma **confidence mask suave e desalinhada** em resolução interna de ~256². Esta página documenta o pipeline completo de pós-processamento aplicado em `LiveMatter.compor()` para transformar essa máscara bruta em um alpha compositável.

Este pipeline aplica-se **apenas ao motor MediaPipe**. O [[concepts/rvm-matting]] produz um alpha matte verdadeiro que pula todos esses passos.

## Estágio 0 — Suavização temporal (em `mask()`)

Antes de qualquer processamento espacial, a confidence mask bruta é misturada com a máscara do frame anterior:

```python
m = suavizar * prev_mask + (1 - suavizar) * m   # default suavizar=0.55
```

Essa média móvel exponencial reduz o "tremor" de borda entre frames. Maior `suavizar` = movimento mais suave, mais lag.

## Estágio 1 — Guided filter (refinar_borda, default ligado)

`refinar_borda(m, frame_bgr, radius=8, eps=1e-3, escala=0.5)` alinha a máscara suave com as bordas reais da imagem usando um guided filter onde o frame fornece a estrutura de borda:

1. Reduz frame e máscara em `escala=0.5` (divide as dimensões pela metade).
2. `ximgproc.guidedFilter(guide=frame_meio, src=mask_meio, radius=8, eps=1e-3)`.
3. Redimensiona o resultado para resolução completa com interpolação bilinear.

**Por que meia resolução.** O guided filter em 720p full-res custa ~80ms/frame, inviabilizando o tempo real. Em escala 0.5× custa ~20ms. A máscara já é espacialmente suave, então o downscaling introduz pouco erro.

**Fallback.** Se `opencv-contrib-python` não estiver instalado (`ximgproc` ausente), o estágio cai para `cv2.bilateralFilter(src, 7, 0.1, 7)` — edge-aware mas com alinhamento mais fraco.

**Controlado por** `refine=True` em `compor()`. Passando `refine=False` (CLI: `--fast`) pula este estágio inteiro para maior fps.

## Estágio 2 — Binarizar no threshold

```python
alpha = (m > threshold).astype(np.float32)    # default threshold=0.6
```

**Por que 0.6.** O Selfie Segmenter atribui confiança ~1.0 ao corpo central e ~0.55 às "bolhas de ombro" — regiões onde o fundo original foi classificado incorretamente como pessoa e fundido ao contorno do corpo. Essas bolhas não podem ser removidas por análise de componentes conexos porque estão espacialmente conectadas ao corpo. O threshold 0.6 as corta de forma limpa sem afinar o corpo real (que está em ~1.0).

## Estágio 3 — Abertura morfológica (abertura, default 0 / desligado)

```python
if abertura > 0:
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*abertura+1, 2*abertura+1))
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, ker)
```

Remove protuberâncias finas da máscara binária. **Default é 0 (desligado)** porque a abertura morfológica também erode features finas reais (queixo, nariz, mechas de cabelo) — em testes ela visivelmente "comia o rosto". O passo de threshold já resolve o problema da bolha de ombro sem morfologia.

## Estágio 4 — Limpeza por componentes conexos (_maior_componente)

```python
alpha = _maior_componente(alpha)    # se limpar_ilhas=True
```

`_maior_componente` remove ilhas flutuantes espacialmente desconectadas da silhueta principal:

- Executa `cv2.connectedComponentsWithStats` (conectividade 8).
- Mantém todos os componentes cuja área >= 10% da área do maior componente.
- Remove componentes menores como falsos positivos.

O threshold de 10% preserva regiões legítimas desconectadas grandes (mão erguida, objeto segurado) enquanto descarta blobs pequenos de textura de fundo.

## Estágio 5 — Erosão

```python
ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*erode+1, 2*erode+1))
alpha = cv2.erode(alpha, ker)    # default erode=2px
```

Encolhe a máscara binária `erode` pixels para dentro. Isso elimina a franja brilhante residual (halo) onde a cor do fundo vaza nos pixels de borda da saída composta.

**Relação com feather.** Definir `erode >= feather` garante que a rampa gaussiana do próximo estágio fique inteiramente dentro do limite do corpo — a rampa nunca alcança pixels contaminados pelo fundo antigo.

## Estágio 6 — Feathering gaussiano

```python
k = feather * 2 + 1
alpha = cv2.GaussianBlur(alpha, (k, k), 0)    # default feather=3px
alpha = np.clip(alpha, 0.0, 1.0)[..., None]   # H×W×1
```

Suaviza a borda binária dura para evitar uma silhueta com aliasing na composição final. O tamanho do kernel é sempre ímpar (`2*feather+1`).

O default mudou de 5px para 3px quando o `erode=2` foi introduzido — a erosão já empurra o limite para dentro, então um feather menor atinge a mesma aparência suave sem estender demais a região de blending.

## Tabela resumo

| Estágio | Função | Default | Pode pular? |
|---|---|---|---|
| Suavização temporal | EMA `suavizar` em `mask()` | 0.55 | `suavizar=0` |
| Guided filter | `refinar_borda`, meia-res | ligado | `--fast` / `refine=False` |
| Binarizar no threshold | `m > 0.6` | 0.6 | não pode pular |
| Abertura morfológica | `MORPH_OPEN(abertura)` | **desligado (0)** | default desligado |
| Componentes conexos | `_maior_componente` | ligado | `limpar_ilhas=False` |
| Erosão | `cv2.erode(erode=2)` | 2px | `erode=0` |
| Feather gaussiano | `cv2.GaussianBlur(feather=3)` | 3px | `feather=0` |

## Histórico de design (inferido do código e comentários)

O pipeline evoluiu por problemas reportados pelo usuário:
1. Confidence mask bruta → halo + borda crua → adicionado guided filter.
2. Artefato de blob flutuante → adicionados componentes conexos.
3. Bolha de ombro conectada ao corpo (confiança 0.55) → adicionado threshold 0.6.
4. Threshold sozinho insuficiente → testada abertura morfológica → ela comia o rosto → **desligada por default**.
5. Halo residual após guided filter → adicionada erosão (2px).
6. Com erosão, o feather pôde encolher de 5px para 3px.

## Relacionados
[[concepts/realtime-matting]] · [[entities/live-mode]] · [[entities/live-mode-cli]] · [[concepts/live-mode-frame-pipeline]] · [[concepts/rvm-matting]] · [[index]]
