"""
Ajustes de imagem para o app de câmera ao vivo (zoom, enquadramento, brilho,
contraste, saturação, nitidez). Operam sobre frames BGR (OpenCV), aplicados
**depois** da composição — afetam o quadro final como um app de câmera faria.
"""

import cv2
import numpy as np


def aplicar_ajustes(
    img: np.ndarray,
    zoom: float = 1.0,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    brilho: int = 0,
    contraste: float = 1.0,
    saturacao: float = 1.0,
    nitidez: float = 0.0,
) -> np.ndarray:
    """
    - `zoom` (1.0–4.0): amplia recortando o centro e reescalando ao tamanho original.
    - `pan_x`/`pan_y` (-1..1): enquadramento — desloca o recorte quando há zoom.
    - `brilho` (-100..100): soma direta no valor do pixel.
    - `contraste` (0.5–2.0): ganho multiplicativo.
    - `saturacao` (0–2.0): intensidade de cor (via HSV).
    - `nitidez` (0–2.0): unsharp mask (realce de borda).
    """
    h, w = img.shape[:2]

    if zoom > 1.0:
        cw, ch = int(w / zoom), int(h / zoom)
        max_x, max_y = w - cw, h - ch
        x = int((max_x / 2) * (1 + pan_x))
        y = int((max_y / 2) * (1 + pan_y))
        x = max(0, min(max_x, x))
        y = max(0, min(max_y, y))
        img = cv2.resize(img[y:y + ch, x:x + cw], (w, h), interpolation=cv2.INTER_LINEAR)

    if contraste != 1.0 or brilho != 0:
        img = cv2.convertScaleAbs(img, alpha=float(contraste), beta=float(brilho))

    if saturacao != 1.0:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] = np.clip(hsv[..., 1] * float(saturacao), 0, 255)
        img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    if nitidez > 0:
        blur = cv2.GaussianBlur(img, (0, 0), 3)
        img = cv2.addWeighted(img, 1.0 + float(nitidez), blur, -float(nitidez), 0)

    return img
