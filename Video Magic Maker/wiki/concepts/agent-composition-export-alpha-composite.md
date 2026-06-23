---
title: "Alpha composite CPU: como compor_frame cola a pessoa no fundo"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["agentes/composicao.py"]
tags: [concept, composicao, alpha, pillow, cpu, composite]
---
# Alpha composite CPU: como compor_frame cola a pessoa no fundo

O [[entities/composicao]] usa a operação de **alpha compositing** do Pillow para
sobrepor a silhueta RGBA da pessoa sobre o fundo RGB preparado pelo
[[concepts/agent-composition-export-cover-crop]].

## A operação central

```python
base = bg.convert("RGBA")            # fundo em RGBA (alpha=255 opaco)
base.paste(person, (0, 0), person)   # cola person usando o canal A de person como máscara
return base.convert("RGB")           # descarta alpha; entrega RGB para o encoder
```

`Image.paste(im, box, mask)` — o terceiro argumento é a **máscara de opacidade**:
- Pixels onde `person.alpha = 255` (pessoa sólida) → pixel da pessoa visível.
- Pixels onde `person.alpha = 0` (fundo recortado) → pixel do fundo visível.
- Pixels com alpha intermediário (borda de recorte) → blend proporcional.

Usar o próprio `person` como máscara extrai o canal A automaticamente do modo
RGBA.

## Ajustes de pessoa antes do paste

Aplicados opcionalmente antes do paste quando os parâmetros diferem de 1.0:

```python
if ajuste_brilho != 1.0:
    person = ImageEnhance.Brightness(person).enhance(ajuste_brilho)
if ajuste_cor != 1.0:
    person = ImageEnhance.Color(person).enhance(ajuste_cor)
```

- `Brightness`: escala linear de todos os canais RGB (preserva alpha).
- `Color`: satura/dessatura em relação ao tom de cinza (preserva alpha).

O canal alpha de `person` **é preservado** após os enhancers — o paste
subsequente ainda usa o alpha original para compor. Isso é correto: queremos
ajustar a aparência da pessoa, não sua silhueta.

## Por que "sem relighting"

O alpha composite posiciona a pessoa no novo fundo, mas **não modifica a
iluminação capturada**. As sombras, reflexos e gradientes de luz da pessoa
permanecem os do ambiente original de gravação. Isso é aceitável para troca de
cenário básica, mas visualmente inconsistente com fundos de iluminação muito
diferente (ex: pessoa gravada em estúdio claro composta sobre fundo escuro
dramático).

O [[entities/relighting]] (IC-Light fbc) resolve isso condicionando a geração
no fundo, mas requer GPU. Este agente é o fallback de CPU.

## Custo

Toda a operação roda em CPU, dependendo apenas do Pillow. Sem uso de NumPy
diretamente, sem GPU. Para frames 720p/1080p o tempo por frame é tipicamente
abaixo de 50ms em hardware moderno, tornando o lote de composição mais rápido
que a remoção de fundo (rembg) ou o relighting.

## Relacionados

[[entities/composicao]] · [[entities/remocao]] · [[entities/relighting]] ·
[[concepts/agent-composition-export-cover-crop]] · [[index]]
