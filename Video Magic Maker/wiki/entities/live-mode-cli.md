---
title: live-mode-cli — live.py, ponto de entrada CLI do modo ao vivo
type: entity
created: 2026-06-22
updated: 2026-06-22
sources: ["live.py"]
tags: [entity, live, cli, argparse, webcam, virtualcam]
---
# live-mode-cli — live.py, ponto de entrada CLI do modo ao vivo

`live.py` é o ponto de entrada de linha de comando que conecta captura de webcam, seleção de motor, carregamento de fundo, composição e saída para câmera virtual num único loop em tempo real.

## Responsabilidades

- Parsear argumentos (`argparse`) e validar que exatamente um entre `--background` e `--blur` foi fornecido.
- Abrir a webcam via `abrir_camera()` (usa `cv2.CAP_DSHOW` no Windows para evitar latência do backend MSMF).
- Carregar ou preparar o fundo **antes** do loop (`carregar_fundo` para imagem, blur calculado por frame).
- Instanciar o motor de matting: `LiveMatter` ([[concepts/realtime-matting]]) para `--engine mediapipe` (default) ou `RVMMatter` ([[concepts/rvm-matting]]) para `--engine rvm`.
- Abrir `pyvirtualcam.Camera` a menos que `--no-virtualcam` seja passado.
- Rodar o loop por frame: leitura → espelhamento opcional → composição → envio à câmera virtual e/ou janela de preview.
- Medir fps a cada 30 frames e sobrepor no frame quando `--preview` estiver ativo.
- Liberar todos os recursos (`cap.release()`, `matter.close()`, `cam.close()`, `cv2.destroyAllWindows()`) no bloco `finally`.

## Flags principais

| Flag | Default | Efeito |
|---|---|---|
| `--background/-b` | — | Imagem de fundo estática (cover-crop para o tamanho do frame) |
| `--blur N` | — | Modo "borrar o fundo"; calculado por frame via `fundo_desfocado` |
| `--camera/-c` | `0` | Índice do dispositivo de webcam |
| `--width` | `960` | Largura de captura |
| `--height` | `540` | Altura de captura (540p é o default — ver [[decisions/live-mode-engine-selection]]) |
| `--fps` | `30` | FPS alvo passado ao `VideoCapture` e ao `pyvirtualcam.Camera` |
| `--mirror` | off | `cv2.flip(frame, 1)` antes do processamento |
| `--feather` | `3` | Raio do gaussian na borda da máscara |
| `--suavizar` | `0.55` | Peso de suavização temporal da máscara MediaPipe |
| `--color-match` | `0.0` | Desloca a cor da pessoa em direção à média do fundo |
| `--fast` | off | Passa `refine=False` ao `compor()` — pula o guided filter, mais fps |
| `--engine` | `mediapipe` | Motor de recorte: `mediapipe` (rápido) ou `rvm` (qualidade, torch) |
| `--preview` | off | Abre janela `cv2.imshow`; ESC sai |
| `--no-virtualcam` | off | Desativa pyvirtualcam; útil para testar sem a OBS Virtual Camera instalada |

## Windows: CAP_DSHOW

`abrir_camera()` passa `cv2.CAP_DSHOW` como backend em `sys.platform == "win32"`.
O backend MSMF (padrão) pode adicionar centenas de milissegundos de latência; o DSHOW tem baixa latência.
Em outras plataformas o argumento de backend é `0` (automático).

## Tratamento de erro da câmera virtual

Se `pyvirtualcam.Camera(...)` lançar exceção, o código imprime um guia legível de instalação (requisito do OBS Studio no Windows) e:
- Se `--preview` estiver ativo: continua em modo somente-preview.
- Se `--preview` não estiver ativo: sai com código 1.

## Medição de fps

A cada 30 frames o loop calcula `fps = 30.0 / tempo_decorrido`. O resultado é desenhado no frame com `cv2.putText` apenas quando `--preview` está ativo — a câmera virtual recebe o frame composto limpo, sem overlay.

## Relacionados
[[entities/live-mode]] · [[entities/live-mode-virtual-camera]] · [[entities/live-mode-background-helpers]] · [[concepts/live-mode-frame-pipeline]] · [[concepts/realtime-matting]] · [[concepts/rvm-matting]] · [[index]]
