---
title: live-mode-virtual-camera — saída pyvirtualcam / OBS Virtual Camera
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["live.py"]
tags: [entity, live, virtualcam, pyvirtualcam, obs, windows]
---
# live-mode-virtual-camera — saída pyvirtualcam / OBS Virtual Camera

A câmera virtual é o estágio de saída do [[entities/live-mode]]: uma instância de `pyvirtualcam.Camera` que expõe o stream BGR composto como dispositivo de webcam virtual no sistema operacional, visível para OBS, Google Meet, Zoom e qualquer app de videoconferência ou streaming.

## Como funciona

Após a composição (`matter.compor(...)` retorna um array BGR `uint8`), `live.py` chama:

```python
cam.send(out)                    # envia o frame BGR
cam.sleep_until_next_frame()     # sincroniza o loop com o fps alvo
```

`pyvirtualcam.Camera` é aberta uma vez antes do loop com a **resolução e fps exatos** negociados do frame real da webcam (`h, w = frame.shape[:2]`), não os valores solicitados — o dispositivo virtual sempre corresponde ao que a webcam entrega.

## Backend Windows: OBS Virtual Camera

No Windows o backend do pyvirtualcam é a **OBS Virtual Camera**, um dispositivo DirectShow virtual instalado pelo OBS Studio.
Pontos-chave:
- O OBS Studio precisa ter sido **instalado ao menos uma vez** — isso registra o dispositivo DirectShow no registry do Windows.
- O OBS **não** precisa estar em execução quando `live.py` estiver rodando.
- No Meet/Zoom/OBS o usuário seleciona **"OBS Virtual Camera"** como entrada de câmera.

## Formato de pixel

O frame é enviado como **BGR** (`pyvirtualcam.PixelFormat.BGR`), que corresponde ao layout nativo dos arrays do OpenCV — nenhuma conversão é necessária antes do envio.

## Degradação graciosa

Se `pyvirtualcam.Camera(...)` lançar exceção (OBS não instalado, driver ausente, dispositivo ocupado):
- Uma mensagem de erro legível com instruções de instalação é impressa em `stderr`.
- Se `--preview` estiver ativo, o loop continua em modo somente-preview.
- Se `--preview` não estiver ativo, o processo sai com código 1.

O flag `--no-virtualcam` pula todo o bloco pyvirtualcam (nem tenta importar), útil para testar a composição sem driver de câmera virtual.

## Sincronização de fps

`cam.sleep_until_next_frame()` bloqueia o loop até o próximo slot de frame conforme o timer da câmera virtual. Isso naturalmente limita o loop ao fps alvo e reduz o desperdício de CPU de um busy-spin.

## Relacionados
[[entities/live-mode]] · [[entities/live-mode-cli]] · [[concepts/live-mode-frame-pipeline]] · [[index]]
