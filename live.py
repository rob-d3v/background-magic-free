"""
live.py — Modo AO VIVO: troca o fundo da webcam em tempo real e publica numa
câmera virtual que o OBS, o Google Meet, o Zoom ou qualquer app de vídeo enxerga.

Pipeline por frame (≈30fps em CPU):
    webcam → MediaPipe matting → composição sobre o fundo → câmera virtual

Diferença do modo studio (pipeline.py / app.py): NÃO reilumina (IC-Light). Faz
recorte + composição + casamento de cor leve. Pra reiluminar de verdade, use o
modo gravado.

Pré-requisito da câmera virtual (Windows): a backend do pyvirtualcam é a
**OBS Virtual Camera**. Basta ter o OBS Studio instalado uma vez (ele registra o
dispositivo) — não precisa estar aberto. No Meet/Zoom, escolha a câmera
"OBS Virtual Camera".

Exemplos:
    python live.py --background workspace/background/bg.png
    python live.py --blur 45                 # fundo desfocado (estilo Meet)
    python live.py --background sala.jpg --camera 0 --width 1280 --height 720
    python live.py --background sala.jpg --preview --no-virtualcam   # só janela de teste
"""

import argparse
import sys
import time

import cv2

from agentes.matting_live import LiveMatter, carregar_fundo, fundo_desfocado


def parse_args():
    p = argparse.ArgumentParser(description="Troca de fundo ao vivo → câmera virtual")
    fonte = p.add_mutually_exclusive_group()
    fonte.add_argument("--background", "-b", help="Imagem de fundo (jpg/png)")
    fonte.add_argument("--blur", type=int, metavar="N",
                       help="Em vez de imagem, desfoca o próprio fundo (intensidade ímpar, ex.: 45)")
    p.add_argument("--camera", "-c", type=int, default=0, help="Índice da webcam (default 0)")
    # 960x540 ~21fps em CPU; 1280x720 ~13fps; 640x360 ~42fps. 540p é o
    # equilíbrio padrão entre fluidez e nitidez sem GPU.
    p.add_argument("--width", type=int, default=960, help="Largura de captura")
    p.add_argument("--height", type=int, default=540, help="Altura de captura")
    p.add_argument("--fps", type=int, default=30, help="FPS alvo")
    p.add_argument("--mirror", action="store_true", help="Espelha a imagem (selfie)")
    p.add_argument("--feather", type=int, default=3, help="Suavização da borda (px)")
    p.add_argument("--suavizar", type=float, default=0.55, help="Suavização temporal 0..1")
    p.add_argument("--color-match", type=float, default=0.0, help="Casamento de cor leve 0..1")
    p.add_argument("--fast", action="store_true",
                   help="Borda mais rápida (sem refino guided filter) — +fps, borda pior")
    p.add_argument("--engine", choices=["mediapipe", "rvm"], default="mediapipe",
                   help="mediapipe = rápido; rvm = qualidade (mantém cabelo, mais pesado)")
    p.add_argument("--preview", action="store_true", help="Mostra janela de preview (ESC sai)")
    p.add_argument("--no-virtualcam", action="store_true", help="Não envia p/ câmera virtual (só preview)")
    return p.parse_args()


def abrir_camera(idx: int, w: int, h: int, fps: int) -> cv2.VideoCapture:
    # CAP_DSHOW evita latência alta do backend MSMF no Windows
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
    cap = cv2.VideoCapture(idx, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, fps)
    if not cap.isOpened():
        raise RuntimeError(f"Não consegui abrir a webcam {idx}. Veja se outro app a está usando.")
    return cap


def main():
    a = parse_args()
    if not a.background and a.blur is None:
        print("Defina --background <img> ou --blur <N>.", file=sys.stderr)
        sys.exit(2)

    cap = abrir_camera(a.camera, a.width, a.height, a.fps)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("Webcam aberta mas não retornou frame.")
    h, w = frame.shape[:2]
    print(f"Webcam: {w}x{h}")

    bg_img = carregar_fundo(a.background, w, h) if a.background else None

    cam = None
    if not a.no_virtualcam:
        try:
            import pyvirtualcam
            cam = pyvirtualcam.Camera(width=w, height=h, fps=a.fps, fmt=pyvirtualcam.PixelFormat.BGR)
            print(f"Camera virtual ativa: {cam.device}  ->  selecione-a no Meet/Zoom/OBS")
        except Exception as e:
            print(
                "\nNão consegui abrir a câmera virtual.\n"
                "  Windows: instale o OBS Studio uma vez (registra a 'OBS Virtual Camera').\n"
                "  Ou rode com --preview --no-virtualcam pra só testar o recorte.\n"
                f"  Detalhe: {e}\n",
                file=sys.stderr,
            )
            if not a.preview:
                sys.exit(1)

    if a.engine == "rvm":
        from agentes.matting_rvm import RVMMatter
        print("Carregando RVM (baixa o modelo na 1a vez)...")
        matter = RVMMatter()
    else:
        matter = LiveMatter()

    print("Rodando. ESC na janela de preview (ou Ctrl+C) pra sair.")
    t0, n, fps_show = time.time(), 0, 0.0
    try:
        if True:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if a.mirror:
                    frame = cv2.flip(frame, 1)

                bg = bg_img if bg_img is not None else fundo_desfocado(frame, a.blur)
                out = matter.compor(
                    frame, bg, suavizar=a.suavizar, feather=a.feather,
                    color_match=a.color_match, refine=not a.fast,
                )

                if cam is not None:
                    cam.send(out)
                    cam.sleep_until_next_frame()

                n += 1
                if n % 30 == 0:
                    dt = time.time() - t0
                    fps_show = 30.0 / dt if dt > 0 else 0.0
                    t0 = time.time()

                if a.preview:
                    cv2.putText(out, f"{fps_show:4.1f} fps", (12, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow("lumina-bg live (ESC sai)", out)
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        matter.close()
        if cam is not None:
            cam.close()
        if a.preview:
            cv2.destroyAllWindows()
    print("Encerrado.")


if __name__ == "__main__":
    main()
