"""
Agente Live (qualidade) — Matting com RobustVideoMatting (RVM).

Alternativa de **alta qualidade** ao MediaPipe ([[matting_live]]). O RVM produz um
**alpha matte de verdade** (não uma confidence mask de baixa-res), então:
  - mantém cabelo e borda do rosto (não "come" o rosto)
  - não cria as bolhas de falso-positivo grudadas no ombro
  - não deixa franja de halo

Custo: roda em torch (CPU local) — ~10fps @540p, mais pesado que o MediaPipe.
Mantém estado recorrente entre frames (coerência temporal, menos tremor).

Interface drop-in com `LiveMatter.compor` — aceita e ignora os params específicos
do MediaPipe (`refine`, `threshold`, `erode`, etc.) via `**_`.

O modelo (`rvm_mobilenetv3.pth`, ~15MB) é baixado e cacheado pelo torch.hub na
primeira carga.
"""

import cv2
import numpy as np


class RVMMatter:
    def __init__(self, variant: str = "mobilenetv3", downsample_ratio: float = 0.4):
        import torch
        self._torch = torch
        self.model = torch.hub.load(
            "PeterL1n/RobustVideoMatting", variant, trust_repo=True
        )
        self.model.eval()
        self.dr = downsample_ratio
        self.rec = [None] * 4          # estado recorrente (coerência temporal)
        self._last_shape = None

    def _alpha(self, frame_bgr: np.ndarray) -> np.ndarray:
        torch = self._torch
        if frame_bgr.shape[:2] != self._last_shape:
            self.rec = [None] * 4       # reset do estado se a resolução mudar
            self._last_shape = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        src = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0)
        with torch.no_grad():
            _fgr, pha, *self.rec = self.model(src, *self.rec, downsample_ratio=self.dr)
        # .copy() porque o numpy compartilha a memória do tensor, liberada ao sair
        return pha[0, 0].numpy().copy()

    def reset(self):
        """Zera o estado recorrente (usar entre clipes / em preview de 1 frame)."""
        self.rec = [None] * 4
        self._last_shape = None

    def mask(self, frame_bgr: np.ndarray, **_) -> np.ndarray:
        return self._alpha(frame_bgr)

    def compor(self, frame_bgr, bg_bgr, color_match: float = 0.0,
               feather: int = 1, **_ignored) -> np.ndarray:
        """Compõe a pessoa sobre o fundo usando o alpha do RVM (já limpo)."""
        a = self._alpha(frame_bgr)
        if feather > 0:
            k = feather * 2 + 1
            a = cv2.GaussianBlur(a, (k, k), 0)
        a = np.clip(a, 0.0, 1.0)
        pessoa = frame_bgr.astype(np.float32)
        if color_match > 0:
            from agentes.matting_live import _color_match
            pessoa = _color_match(pessoa, bg_bgr.astype(np.float32), a, color_match)
        a = a[..., None]
        out = pessoa * a + bg_bgr.astype(np.float32) * (1.0 - a)
        return out.astype(np.uint8)

    def close(self):
        pass
