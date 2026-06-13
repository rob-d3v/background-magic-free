"""
Agente Live — Matting em tempo real (MediaPipe Selfie Segmentation)

Para o modo AO VIVO (webcam → OBS / Google Meet / stream) não dá pra usar
rembg/u2net (lento) nem IC-Light (pesado, GPU). Aqui o recorte da pessoa é feito
com o MediaPipe Selfie Segmentation — a mesma tecnologia do "fundo desfocado" do
Google Meet —, que roda a ~30fps em CPU.

Diferença pro modo studio (offline): aqui NÃO há reiluminação IC-Light. Faz-se
recorte + composição sobre o novo fundo, com um casamento de cor leve opcional
(color-match) e suavização de borda (feather). A "magia" de reiluminar a pessoa
pra casar com o ambiente continua sendo do modo gravado (ver [[components/relighting]]).

Saída: array BGR (OpenCV) pronto pra ser enviado a uma câmera virtual
(ver live.py) ou exibido num preview.
"""

import os
import urllib.request

import cv2
import numpy as np


# A build slim do MediaPipe (cp313) só traz a Tasks API (ImageSegmenter) — a API
# legacy `mp.solutions.selfie_segmentation` não existe. Usamos o ImageSegmenter
# com o modelo Selfie Segmenter (.tflite), baixado e cacheado em ./models.
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
    "selfie_segmenter/float16/latest/selfie_segmenter.tflite"
)
_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "selfie_segmenter.tflite")


def baixar_modelo(path: str = _MODEL_PATH, url: str = _MODEL_URL) -> str:
    """Baixa o modelo Selfie Segmenter (~250KB) se ainda não estiver em cache."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"Baixando modelo de matting -> {path} ...")
    urllib.request.urlretrieve(url, path)
    return path


class LiveMatter:
    """Segmentador de pessoa em tempo real (MediaPipe Tasks ImageSegmenter)."""

    def __init__(self, model_path: str = None):
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        self._mp = mp
        model_path = model_path or baixar_modelo()
        # Lê o modelo como buffer em vez de passar o path: o loader C++ do
        # MediaPipe falha em caminhos com acento no Windows (ex.: "Repositórios").
        with open(model_path, "rb") as fh:
            model_buf = fh.read()
        opts = vision.ImageSegmenterOptions(
            base_options=python.BaseOptions(model_asset_buffer=model_buf),
            running_mode=vision.RunningMode.IMAGE,
            output_confidence_masks=True,
            output_category_mask=False,
        )
        self._seg = vision.ImageSegmenter.create_from_options(opts)
        self._prev_mask = None

    def close(self):
        self._seg.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ── matting ────────────────────────────────────────────────────────────
    def mask(self, frame_bgr: np.ndarray, suavizar: float = 0.55) -> np.ndarray:
        """
        Retorna a máscara alpha float32 [0,1] (H×W) da pessoa no frame.

        `suavizar` (0..1) aplica suavização temporal: mistura a máscara atual
        com a anterior pra reduzir o "tremor" de borda entre frames. 0 desliga.
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        res = self._seg.segment(mp_img)
        if res.confidence_masks:
            # .copy() é obrigatório: numpy_view() é uma view na memória C++ do
            # result, liberada na próxima chamada — usá-la depois segfaulta.
            m = np.array(res.confidence_masks[0].numpy_view(), dtype=np.float32, copy=True)
            m = np.squeeze(m)  # garante H×W (alguns builds retornam H×W×1)
        else:
            m = np.zeros(frame_bgr.shape[:2], dtype=np.float32)

        if suavizar > 0 and self._prev_mask is not None and self._prev_mask.shape == m.shape:
            m = suavizar * self._prev_mask + (1.0 - suavizar) * m
        self._prev_mask = m
        return m

    # ── composição ───────────────────────────────────────────────────────────
    def compor(
        self,
        frame_bgr: np.ndarray,
        bg_bgr: np.ndarray,
        suavizar: float = 0.55,
        feather: int = 3,
        threshold: float = 0.6,
        color_match: float = 0.0,
        refine: bool = True,
        erode: int = 2,
        limpar_ilhas: bool = True,
        abertura: int = 0,
    ) -> np.ndarray:
        """
        Compõe a pessoa do `frame_bgr` sobre `bg_bgr` (mesmo tamanho do frame).

        - `refine`: refina a máscara com guided filter usando o frame como guia —
          cola a borda nos contornos reais (cabelo, ombro) e some com o "halo".
        - `erode`: encolhe a máscara N px antes do feather. Mata o anel claro de
          fundo que vaza na borda (halo). 0 = não encolhe.
        - `feather`: raio do desfoque gaussiano na borda (px). 0 = borda dura.
        - `threshold`: ponto de corte da máscara. 0.6 (default) descarta as
          "bolhas" de baixa confiança que o segmentador gruda no ombro/braço
          (fundo original marcado como pessoa, ~0.55) — o corpo real fica ~1.0,
          então 0.6 não o afina. É o threshold que remove a mancha do ombro.
        - `abertura`: abertura morfológica (erode+dilate) opcional. **Default 0
          (desligada)**: ela também corta features finas reais (queixo, nariz,
          mecha de cabelo) — chega a "comer" o rosto. Use só se sobrar
          protuberância e tolere perder detalhe fino.
        - `color_match` (0..1): puxa o tom médio da pessoa pro tom do fundo, pra
          integrar sem reiluminar. 0 = desligado.
        """
        h, w = frame_bgr.shape[:2]
        m = self.mask(frame_bgr, suavizar=suavizar)
        if refine:
            m = refinar_borda(m, frame_bgr)

        # binariza, abre (corta protuberâncias), remove ilhas, encolhe, suaviza
        alpha = (m > threshold).astype(np.float32)
        if abertura > 0:
            ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (abertura * 2 + 1, abertura * 2 + 1))
            alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, ker)
        if limpar_ilhas:
            alpha = _maior_componente(alpha)
        if erode > 0:
            ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode * 2 + 1, erode * 2 + 1))
            alpha = cv2.erode(alpha, ker)
        if feather > 0:
            k = feather * 2 + 1
            alpha = cv2.GaussianBlur(alpha, (k, k), 0)
        alpha = np.clip(alpha, 0.0, 1.0)[..., None]  # H×W×1

        pessoa = frame_bgr.astype(np.float32)
        if color_match > 0:
            pessoa = _color_match(pessoa, bg_bgr.astype(np.float32), alpha[..., 0], color_match)

        out = pessoa * alpha + bg_bgr.astype(np.float32) * (1.0 - alpha)
        return out.astype(np.uint8)


# ── refino de borda ──────────────────────────────────────────────────────────

def _maior_componente(binary: np.ndarray, min_frac: float = 0.1) -> np.ndarray:
    """
    Mantém só os componentes conexos cuja área >= min_frac da maior. Remove ilhas
    flutuantes (falsos positivos do segmentador) sem perder partes legítimas
    grandes (mãos, objeto segurado). Entrada/saída float32 {0,1}.
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary.astype(np.uint8), connectivity=8
    )
    if n <= 2:  # 1 fundo + no máx 1 objeto: nada a limpar
        return binary
    areas = stats[1:, cv2.CC_STAT_AREA]
    maior = areas.max()
    manter = [i + 1 for i, a in enumerate(areas) if a >= min_frac * maior]
    return np.isin(labels, manter).astype(np.float32)




def refinar_borda(m: np.ndarray, guia_bgr: np.ndarray, radius: int = 8,
                  eps: float = 1e-3, escala: float = 0.5) -> np.ndarray:
    """
    Cola a máscara `m` (float32 [0,1]) nas bordas reais da imagem `guia_bgr` via
    guided filter (opencv-contrib `ximgproc`). Reduz halo e fixa cabelo/ombro no
    contorno verdadeiro. Sem opencv-contrib, cai num bilateral edge-aware.

    `escala` < 1.0 roda o filtro em resolução reduzida (a máscara é suave, perde
    pouco) — guided filter full-res a 720p custa ~80ms; a 0.5 cai p/ ~20ms, o que
    mantém o tempo real.
    """
    h, w = m.shape[:2]
    src = m.astype(np.float32)
    try:
        from cv2 import ximgproc
        if 0.0 < escala < 1.0:
            sw, sh = max(2, int(w * escala)), max(2, int(h * escala))
            g = cv2.resize(guia_bgr, (sw, sh), interpolation=cv2.INTER_AREA)
            s = cv2.resize(src, (sw, sh), interpolation=cv2.INTER_AREA)
            out = ximgproc.guidedFilter(np.ascontiguousarray(g), s, max(2, int(radius * escala)), eps)
            out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            out = ximgproc.guidedFilter(np.ascontiguousarray(guia_bgr), src, radius, eps)
    except Exception:
        out = cv2.bilateralFilter(src, 7, 0.1, 7)
    return np.clip(out, 0.0, 1.0)


# ── fundos ───────────────────────────────────────────────────────────────────

def cobrir(bg_bgr: np.ndarray, w: int, h: int) -> np.ndarray:
    """Redimensiona o fundo cobrindo w×h (resize + center-crop), mantém proporção."""
    ih, iw = bg_bgr.shape[:2]
    scale = max(w / iw, h / ih)
    nw, nh = int(round(iw * scale)), int(round(ih * scale))
    r = cv2.resize(bg_bgr, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    x, y = (nw - w) // 2, (nh - h) // 2
    return r[y:y + h, x:x + w]


def carregar_fundo(path: str, w: int, h: int) -> np.ndarray:
    """Carrega uma imagem de fundo e ajusta ao tamanho do frame."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fundo não encontrado: {path}")
    bg = cv2.imread(path, cv2.IMREAD_COLOR)
    if bg is None:
        raise ValueError(f"Não consegui ler a imagem de fundo: {path}")
    return cobrir(bg, w, h)


def fundo_desfocado(frame_bgr: np.ndarray, intensidade: int = 35) -> np.ndarray:
    """Fundo = o próprio frame borrado (efeito 'blur' do Meet). intensidade ímpar."""
    k = max(3, intensidade | 1)  # garante ímpar
    return cv2.GaussianBlur(frame_bgr, (k, k), 0)


class VideoFundo:
    """
    Fundo a partir de um arquivo de vídeo, em loop. Cada `proximo()` devolve o
    próximo frame do vídeo já ajustado (cover-crop) ao tamanho `w`×`h`; ao chegar
    no fim, volta pro começo. Usado no modo live (fundo animado) e no render
    offline.
    """

    def __init__(self, path: str, w: int, h: int):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise ValueError(f"Não consegui abrir o vídeo de fundo: {path}")
        self.w, self.h = w, h

    def proximo(self) -> np.ndarray:
        ok, f = self.cap.read()
        if not ok:                                   # acabou → volta pro início
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, f = self.cap.read()
            if not ok:
                raise RuntimeError("Vídeo de fundo sem frames legíveis.")
        return cobrir(f, self.w, self.h)

    def close(self):
        self.cap.release()


def _color_match(pessoa: np.ndarray, bg: np.ndarray, alpha: np.ndarray, forca: float) -> np.ndarray:
    """Aproxima a média de cor da pessoa à do fundo (integração leve, sem relight)."""
    msk = alpha > 0.5
    if msk.sum() < 100:
        return pessoa
    media_p = pessoa[msk].mean(axis=0)
    media_b = bg.reshape(-1, 3).mean(axis=0)
    desloc = (media_b - media_p) * float(forca) * 0.5
    return np.clip(pessoa + desloc, 0, 255)
