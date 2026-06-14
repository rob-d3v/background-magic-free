"""
camera_app.py — App de câmera ao vivo do lumina-bg (GUI desktop).

Troca o fundo da webcam em tempo real (MediaPipe matting) e dá os controles de um
app de câmera de verdade:
  - escolher entre as câmeras do PC
  - gravar vídeo e tirar foto (vão pra galeria)
  - zoom, enquadramento (pan), espelhar
  - brilho, contraste, saturação, nitidez
  - fundo: nenhum / desfocado / imagem
  - publicar numa câmera virtual (OBS Virtual Camera) p/ Meet/Zoom/OBS
  - abrir a galeria do conteúdo gerado

Rodar:
    python camera_app.py
"""

import os
import sys
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

from config import Paths
from agentes.matting_live import LiveMatter, cobrir, fundo_desfocado, VideoFundo
from agentes.ajustes import aplicar_ajustes

CAP_W, CAP_H, FPS = 960, 540, 20


def listar_cameras():
    """Lista (índice, nome) das câmeras, excluindo a própria câmera virtual."""
    try:
        from pygrabber.dshow_graph import FilterGraph
        nomes = FilterGraph().get_input_devices()
        cams = [(i, n) for i, n in enumerate(nomes) if "OBS Virtual" not in n]
        if cams:
            return cams
    except Exception:
        pass
    # fallback: sonda índices 0..3
    cams = []
    for i in range(4):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if sys.platform == "win32" else 0)
        if cap.isOpened():
            cams.append((i, f"Câmera {i}"))
            cap.release()
    return cams or [(0, "Câmera 0")]


class CameraApp:
    def __init__(self, root):
        self.root = root
        root.title("lumina-bg — Câmera ao vivo")
        root.protocol("WM_DELETE_WINDOW", self.fechar)

        self.paths = Paths().criar_dirs()
        self.galeria = os.path.join(self.paths.base, "galeria")
        os.makedirs(self.galeria, exist_ok=True)
        self._cfg_path = os.path.join(self.paths.base, "camera_app_config.json")
        c = self._load_config()    # cache das preferências (vazio na 1a vez)

        # ── estado (lido pelo worker; setado pelos callbacks na main thread) ──
        self.cams = listar_cameras()
        cam_ids = [i for i, _ in self.cams]
        salvo_cam = c.get("camera")
        self.req_cam = salvo_cam if salvo_cam in cam_ids else self.cams[0][0]
        self.cur_cam = None
        self.running = True
        self.mirror = c.get("mirror", True)
        self.refine = c.get("refine", True)
        self.bg_mode = c.get("bg_mode", "blur")     # none | blur | image | video
        self.blur = c.get("blur", 45)
        self.bg_img = None             # BGR já em cover do tamanho do frame
        self.bg_image_path = c.get("bg_image_path")
        self.bg_video = None           # VideoFundo (fundo animado em loop)
        self.bg_video_path = c.get("bg_video_path")
        self.zoom = c.get("zoom", 1.0)
        self.pan_x = c.get("pan_x", 0.0)
        self.pan_y = c.get("pan_y", 0.0)
        self.brilho = c.get("brilho", 0)
        self.contraste = c.get("contraste", 1.0)
        self.saturacao = c.get("saturacao", 1.0)
        self.nitidez = c.get("nitidez", 0.0)

        self.recording = False
        self.writer = None
        self.req_photo = False
        self.req_virtual = False
        self.virtualcam = None

        self._frame = None             # último frame processado (BGR)
        self._lock = threading.Lock()
        self._fps = 0.0
        self._paused = False
        self._rendering = False      # durante render offline: solta a webcam
        self.engine = c.get("engine", "mediapipe")

        # ── modo VÍDEO (edita um arquivo no lugar da câmera) ──
        self.source = "camera"       # camera | video
        self.video_path = None
        self._vcap = None
        self._video_total = 0
        self._video_pos = 0
        self._video_cur = -1
        self._video_raw = None       # frame cru no pos atual
        self._video_base = None      # composto (matte+fundo), antes dos ajustes
        self._dirty_base = False     # precisa refazer o recorte
        self._dirty_adj = False      # precisa só reaplicar brilho/zoom/etc
        self.matter = None       # criado no worker → janela abre instantânea

        self._build_ui()
        self._restaurar_fundo()    # recarrega imagem/vídeo de fundo salvos
        # janela aparece na hora e vem pra frente (não fica atrás de outras)
        self.root.update_idletasks()
        self.root.geometry("1180x720")
        self.root.minsize(760, 520)
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(900, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()
        self.status.config(text="Carregando recorte... (alguns segundos)")

        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()
        self._tick()

    # ─────────────────────────── UI ───────────────────────────
    def _setup_style(self):
        """Tema escuro moderno (ttk 'clam' customizado)."""
        C = {"bg": "#16161f", "panel": "#20202e", "card": "#2c2c40", "txt": "#e6e6f0",
             "mute": "#8a8aa6", "accent": "#7c6cf0", "accent2": "#6757d8", "rec": "#e0556b"}
        self.COL = C
        self.root.configure(bg=C["bg"])
        self.root.option_add("*TCombobox*Listbox.background", C["card"])
        self.root.option_add("*TCombobox*Listbox.foreground", C["txt"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
        st = ttk.Style()
        st.theme_use("clam")
        st.configure(".", background=C["panel"], foreground=C["txt"],
                     fieldbackground=C["card"], bordercolor=C["card"], focuscolor=C["panel"])
        st.configure("TFrame", background=C["panel"])
        st.configure("TLabel", background=C["panel"], foreground=C["txt"], font=("Segoe UI", 9))
        st.configure("Muted.TLabel", background=C["panel"], foreground=C["mute"], font=("Segoe UI", 8))
        st.configure("Status.TLabel", background=C["bg"], foreground=C["mute"], font=("Segoe UI", 9))
        st.configure("TLabelframe", background=C["panel"], bordercolor=C["card"], relief="solid", borderwidth=1)
        st.configure("TLabelframe.Label", background=C["panel"], foreground=C["accent"],
                     font=("Segoe UI", 8, "bold"))
        st.configure("TButton", background=C["card"], foreground=C["txt"], borderwidth=0,
                     padding=7, font=("Segoe UI", 9))
        st.map("TButton", background=[("active", "#3a3a55")])
        st.configure("Accent.TButton", background=C["accent"], foreground="#ffffff",
                     padding=8, font=("Segoe UI", 9, "bold"))
        st.map("Accent.TButton", background=[("active", C["accent2"])])
        st.configure("Rec.TButton", background=C["rec"], foreground="#ffffff",
                     padding=8, font=("Segoe UI", 9, "bold"))
        st.map("Rec.TButton", background=[("active", "#c8455a")])
        st.configure("TCheckbutton", background=C["panel"], foreground=C["txt"])
        st.map("TCheckbutton", background=[("active", C["panel"])], indicatorcolor=[("selected", C["accent"])])
        st.configure("TRadiobutton", background=C["panel"], foreground=C["txt"])
        st.map("TRadiobutton", background=[("active", C["panel"])], indicatorcolor=[("selected", C["accent"])])
        st.configure("TCombobox", fieldbackground=C["card"], background=C["card"],
                     foreground=C["txt"], arrowcolor=C["txt"], bordercolor=C["card"], padding=4)
        st.map("TCombobox", fieldbackground=[("readonly", C["card"])])
        st.configure("Vertical.TScrollbar", background=C["card"], troughcolor=C["panel"],
                     arrowcolor=C["txt"], bordercolor=C["panel"])

    def _build_ui(self):
        self._setup_style()
        C = self.COL

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        # ── vídeo (esquerda, expande com a janela) ──
        vwrap = tk.Frame(main, bg=C["bg"])
        vwrap.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.video = tk.Label(vwrap, bg=C["bg"], bd=0)
        self.video.pack(fill="both", expand=True)

        # ── controles (direita, painel rolável — nada some) ──
        rightwrap = ttk.Frame(main)
        rightwrap.grid(row=0, column=1, sticky="ns")
        self._canvas = tk.Canvas(rightwrap, bg=C["panel"], highlightthickness=0, width=340)
        sb = ttk.Scrollbar(rightwrap, orient="vertical", command=self._canvas.yview)
        ctl = ttk.Frame(self._canvas)
        ctl.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=ctl, anchor="nw", width=340)
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side="left", fill="y", expand=True)
        sb.pack(side="right", fill="y")
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(int(-e.delta / 120), "units"))

        # ── Câmera & motor ──
        f = ttk.Labelframe(ctl, text="  CÂMERA & MOTOR  ", padding=10)
        f.pack(fill="x", pady=(0, 8), padx=2)
        ttk.Label(f, text="Câmera").pack(anchor="w")
        self.cam_box = ttk.Combobox(f, state="readonly", values=[n for _, n in self.cams])
        self.cam_box.current([i for i, _ in self.cams].index(self.req_cam))
        self.cam_box.bind("<<ComboboxSelected>>", self._on_cam)
        self.cam_box.pack(fill="x", pady=(2, 8))
        ttk.Label(f, text="Motor de recorte").pack(anchor="w")
        self.eng_box = ttk.Combobox(f, state="readonly",
                                    values=["MediaPipe (rápido)", "RVM (qualidade — mantém cabelo)"])
        self.eng_box.current(1 if self.engine == "rvm" else 0)
        self.eng_box.bind("<<ComboboxSelected>>", self._on_engine)
        self.eng_box.pack(fill="x", pady=(2, 0))

        # ── Fundo ──
        f = ttk.Labelframe(ctl, text="  FUNDO  ", padding=10)
        f.pack(fill="x", pady=(0, 8), padx=2)
        self.bg_var = tk.StringVar(value=self.bg_mode)
        radios = ttk.Frame(f); radios.pack(fill="x")
        for txt, val in [("Nenhum", "none"), ("Desfocado", "blur"),
                         ("Imagem", "image"), ("Vídeo", "video")]:
            ttk.Radiobutton(radios, text=txt, variable=self.bg_var, value=val,
                            command=self._on_bg).pack(side="left", padx=(0, 8))
        ttk.Button(f, text="🖼  Escolher imagem...", command=self._pick_bg).pack(fill="x", pady=(8, 3))
        ttk.Button(f, text="🎞  Escolher vídeo...", command=self._pick_bg_video).pack(fill="x", pady=(0, 4))
        self._slider(f, "Desfoque", 5, 75, self.blur, self._set_blur)

        # ── Ajustes de imagem ──
        f = ttk.Labelframe(ctl, text="  AJUSTES DE IMAGEM  ", padding=10)
        f.pack(fill="x", pady=(0, 8), padx=2)
        self.mirror_var = tk.BooleanVar(value=self.mirror)
        ttk.Checkbutton(f, text="Espelhar (selfie)", variable=self.mirror_var,
                        command=lambda: (setattr(self, "mirror", self.mirror_var.get()),
                                         setattr(self, "_dirty_base", True), self._save_config())
                        ).pack(anchor="w")
        self.refine_var = tk.BooleanVar(value=self.refine)
        ttk.Checkbutton(f, text="Borda alta qualidade", variable=self.refine_var,
                        command=lambda: (setattr(self, "refine", self.refine_var.get()),
                                         setattr(self, "_dirty_base", True), self._save_config())
                        ).pack(anchor="w", pady=(0, 6))
        self.s_zoom = self._slider(f, "Zoom", 1.0, 4.0, self.zoom, self._set("zoom"), res=0.05)
        self.s_px = self._slider(f, "Enquadrar X", -1.0, 1.0, self.pan_x, self._set("pan_x"), res=0.05)
        self.s_py = self._slider(f, "Enquadrar Y", -1.0, 1.0, self.pan_y, self._set("pan_y"), res=0.05)
        self.s_bri = self._slider(f, "Brilho", -100, 100, self.brilho, self._set("brilho"))
        self.s_con = self._slider(f, "Contraste", 0.5, 2.0, self.contraste, self._set("contraste"), res=0.05)
        self.s_sat = self._slider(f, "Saturação", 0.0, 2.0, self.saturacao, self._set("saturacao"), res=0.05)
        self.s_nit = self._slider(f, "Nitidez", 0.0, 2.0, self.nitidez, self._set("nitidez"), res=0.05)
        ttk.Button(f, text="↺  Resetar ajustes", command=self._reset).pack(fill="x", pady=(8, 0))

        # ── Gravar & stream ──
        f = ttk.Labelframe(ctl, text="  GRAVAR & STREAM  ", padding=10)
        f.pack(fill="x", pady=(0, 8), padx=2)
        row1 = ttk.Frame(f); row1.pack(fill="x", pady=(0, 4))
        self.btn_rec = ttk.Button(row1, text="●  Gravar", style="Rec.TButton", command=self._toggle_rec)
        self.btn_rec.pack(side="left", fill="x", expand=True, padx=(0, 3))
        ttk.Button(row1, text="📷  Foto", command=self._photo).pack(side="left", fill="x", expand=True, padx=(3, 0))
        self.btn_vcam = ttk.Button(f, text="🔴  Iniciar câmera virtual (stream)",
                                   style="Accent.TButton", command=self._toggle_vcam)
        self.btn_vcam.pack(fill="x", pady=(0, 4))
        ttk.Button(f, text="🖼  Galeria", command=self._open_galeria).pack(fill="x")

        # ── VÍDEO (editar & renderizar) — substitui a câmera na tela ──
        f = ttk.Labelframe(ctl, text="  VÍDEO (EDITAR & RENDERIZAR)  ", padding=10)
        f.pack(fill="x", pady=(0, 8), padx=2)
        self.btn_carregar = ttk.Button(f, text="🎬  Carregar vídeo (editar)...",
                                       command=self._carregar_video)
        self.btn_carregar.pack(fill="x")
        # barra que só aparece quando um vídeo está carregado
        self.video_bar = ttk.Frame(f)
        fr = ttk.Frame(self.video_bar); fr.pack(fill="x", pady=(6, 2))
        ttk.Label(fr, text="Frame", width=6, anchor="w").pack(side="left")
        self.frame_slider = tk.Scale(fr, from_=0, to=1, orient="horizontal", resolution=1,
                                     command=self._video_scrub, showvalue=True, length=140,
                                     sliderlength=18, bg=C["panel"], fg=C["txt"],
                                     troughcolor=C["card"], highlightthickness=0, bd=0,
                                     sliderrelief="flat", activebackground=C["accent"],
                                     font=("Segoe UI", 7))
        self.frame_slider.pack(side="right", fill="x", expand=True)
        self.btn_aplicar = ttk.Button(self.video_bar, text="✅  Aplicar (renderizar tudo)",
                                      style="Accent.TButton", command=self._aplicar_render)
        self.btn_aplicar.pack(fill="x", pady=(2, 3))
        ttk.Button(self.video_bar, text="📷  Voltar à câmera",
                   command=self._voltar_camera).pack(fill="x")
        ttk.Label(f, style="Muted.TLabel", wraplength=300,
                  text="Carrega um vídeo no lugar da câmera. Ajuste fundo/efeitos vendo aplicado no "
                       "frame escolhido; Aplicar renderiza o vídeo todo (com áudio) na galeria."
                  ).pack(anchor="w", pady=(6, 0))

        self.status = ttk.Label(self.root, text="Iniciando...", style="Status.TLabel",
                                anchor="w", padding=(10, 5))
        self.status.pack(fill="x", side="bottom")

    def _slider(self, parent, label, lo, hi, val, cb, res=1):
        C = self.COL
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=11, anchor="w").pack(side="left")
        s = tk.Scale(row, from_=lo, to=hi, orient="horizontal", resolution=res,
                     command=cb, showvalue=True, length=140, sliderlength=18,
                     bg=C["panel"], fg=C["txt"], troughcolor=C["card"],
                     highlightthickness=0, bd=0, sliderrelief="flat",
                     activebackground=C["accent"], font=("Segoe UI", 7))
        s.set(val)
        s.bind("<ButtonRelease-1>", lambda e: self._save_config())  # salva ao soltar
        s.pack(side="right", fill="x", expand=True)
        return s

    def _set(self, attr):
        def f(v):
            setattr(self, attr, float(v))
            self._dirty_adj = True       # atualiza o preview do vídeo ao vivo
        return f

    # ─────────────────────── cache de preferências ───────────────────────
    def _load_config(self) -> dict:
        try:
            with open(self._cfg_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self):
        cfg = {
            "camera": self.req_cam, "engine": self.engine, "bg_mode": self.bg_mode,
            "blur": self.blur, "bg_image_path": self.bg_image_path,
            "bg_video_path": self.bg_video_path, "mirror": self.mirror, "refine": self.refine,
            "zoom": self.zoom, "pan_x": self.pan_x, "pan_y": self.pan_y,
            "brilho": self.brilho, "contraste": self.contraste,
            "saturacao": self.saturacao, "nitidez": self.nitidez,
        }
        try:
            with open(self._cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _restaurar_fundo(self):
        """Recarrega a imagem/vídeo de fundo salvos; se sumiram, cai pro desfoque."""
        if self.bg_mode == "image" and self.bg_image_path and os.path.exists(self.bg_image_path):
            img = cv2.imread(self.bg_image_path, cv2.IMREAD_COLOR)
            if img is not None:
                self.bg_img = cobrir(img, CAP_W, CAP_H)
            else:
                self.bg_mode = "blur"; self.bg_var.set("blur")
        elif self.bg_mode == "video" and self.bg_video_path and os.path.exists(self.bg_video_path):
            try:
                self.bg_video = VideoFundo(self.bg_video_path, CAP_W, CAP_H)
            except Exception:
                self.bg_mode = "blur"; self.bg_var.set("blur")
        elif self.bg_mode in ("image", "video"):
            self.bg_mode = "blur"; self.bg_var.set("blur")  # arquivo sumiu

    # ─────────────────────── callbacks ───────────────────────
    def _on_cam(self, _evt):
        self.req_cam = self.cams[self.cam_box.current()][0]
        self._save_config()

    def _on_engine(self, _evt):
        novo = "rvm" if self.eng_box.current() == 1 else "mediapipe"
        if novo == self.engine:
            return
        self.status.config(text="Carregando motor (RVM baixa o modelo na 1a vez)...")
        self.root.update_idletasks()
        self._paused = True
        time.sleep(0.1)  # deixa o worker terminar o frame atual
        try:
            if novo == "rvm":
                from agentes.matting_rvm import RVMMatter
                nova = RVMMatter()
            else:
                nova = LiveMatter()
        except Exception as e:
            self._paused = False
            self.eng_box.current(0 if self.engine == "mediapipe" else 1)
            messagebox.showerror("Motor", f"Não consegui carregar o RVM.\n\n{e}")
            return
        antiga = self.matter
        self.matter = nova
        self.engine = novo
        try:
            antiga.close()
        except Exception:
            pass
        self._paused = False
        self._dirty_base = True
        self._save_config()

    def _on_bg(self):
        self.bg_mode = self.bg_var.get()
        self._dirty_base = True
        self._save_config()

    def _set_blur(self, v):
        self.blur = int(float(v)) | 1
        self._dirty_base = True

    def _pick_bg(self):
        p = filedialog.askopenfilename(
            title="Imagem de fundo",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Todos", "*.*")])
        if not p:
            return
        img = cv2.imread(p, cv2.IMREAD_COLOR)
        if img is None:
            messagebox.showerror("Erro", "Não consegui ler essa imagem.")
            return
        self.bg_img = cobrir(img, CAP_W, CAP_H)
        self.bg_image_path = p
        self.bg_var.set("image")
        self.bg_mode = "image"
        self._dirty_base = True
        self._save_config()

    def _pick_bg_video(self):
        p = filedialog.askopenfilename(
            title="Vídeo de fundo",
            filetypes=[("Vídeos", "*.mp4 *.mov *.avi *.mkv *.webm"), ("Todos", "*.*")])
        if not p:
            return
        try:
            novo = VideoFundo(p, CAP_W, CAP_H)
        except Exception as e:
            messagebox.showerror("Erro", f"Não consegui abrir esse vídeo.\n\n{e}")
            return
        antigo = self.bg_video
        self.bg_video = novo
        self.bg_video_path = p
        if antigo:
            antigo.close()
        self.bg_var.set("video")
        self.bg_mode = "video"
        self._dirty_base = True
        self._save_config()

    def _reset(self):
        for s, v in [(self.s_zoom, 1.0), (self.s_px, 0.0), (self.s_py, 0.0),
                     (self.s_bri, 0), (self.s_con, 1.0), (self.s_sat, 1.0), (self.s_nit, 0.0)]:
            s.set(v)
        self._dirty_adj = True
        self._save_config()

    def _toggle_rec(self):
        if not self.recording:
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.galeria, f"video_{ts}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.writer = cv2.VideoWriter(path, fourcc, FPS, (CAP_W, CAP_H))
            self._rec_path = path
            self.recording = True
            self.btn_rec.config(text="■ Parar")
        else:
            self.recording = False
            self.btn_rec.config(text="● Gravar")
            if self.writer:
                self.writer.release()
                self.writer = None
            messagebox.showinfo("Gravado", f"Vídeo salvo na galeria:\n{self._rec_path}")

    def _photo(self):
        self.req_photo = True

    def _toggle_vcam(self):
        if not self.req_virtual:
            self.req_virtual = True
            self.btn_vcam.config(text="■ PARAR stream (câmera virtual)")
        else:
            self.req_virtual = False
            self.btn_vcam.config(text="🔴 Iniciar câmera virtual (stream)")

    # ─────────────────────── render de vídeo (com preview) ───────────────────────
    def _bg_for_frame(self, frame):
        """Resolve o fundo (BGR) no tamanho do `frame` conforme o modo atual."""
        h, w = frame.shape[:2]
        if self.bg_mode == "video" and self.bg_video_path and os.path.exists(self.bg_video_path):
            cap = cv2.VideoCapture(self.bg_video_path)
            ok, bf = cap.read()
            cap.release()
            if ok:
                return cobrir(bf, w, h)
        elif self.bg_mode == "image" and self.bg_image_path and os.path.exists(self.bg_image_path):
            raw = cv2.imread(self.bg_image_path, cv2.IMREAD_COLOR)
            if raw is not None:
                return cobrir(raw, w, h)
        return fundo_desfocado(frame, int(self.blur) | 1)

    def _compose_base(self, frame):
        """Recorta a pessoa e compõe no fundo (SEM ajustes) — base do preview/render."""
        if self.matter is None:
            self.matter = LiveMatter()
        if hasattr(self.matter, "reset"):
            self.matter.reset()
        if self.bg_mode == "none":
            return frame.copy()
        bg = self._bg_for_frame(frame)
        return self.matter.compor(frame, bg, color_match=0.12, refine=self.refine)

    def _carregar_video(self):
        """Carrega um vídeo PRA EDITAR no lugar da câmera (modo vídeo, na tela principal)."""
        p = filedialog.askopenfilename(
            title="Vídeo pra editar/renderizar",
            filetypes=[("Vídeos", "*.mp4 *.mov *.avi *.mkv *.webm"), ("Todos", "*.*")])
        if not p:
            return
        cap = cv2.VideoCapture(p)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        cap.release()
        if total <= 0:
            messagebox.showerror("Erro", "Não consegui ler esse vídeo.")
            return
        if self._vcap is not None:
            self._vcap.release()
            self._vcap = None
        self.video_path = p
        self._video_total = total
        self._video_cur = -1
        self._video_raw = None
        self._video_base = None
        self._video_pos = total // 2
        self.source = "video"          # worker solta a webcam e passa a usar o vídeo
        self._dirty_base = True
        self.frame_slider.config(to=max(0, total - 1))
        self.frame_slider.set(self._video_pos)
        self.video_bar.pack(fill="x", pady=(8, 0))
        self.btn_carregar.config(text="🔁  Trocar vídeo...")
        self.status.config(text=f"MODO VÍDEO — {os.path.basename(p)} ({total} frames)")

    def _video_scrub(self, v):
        """Slider de frame: escolhe qual frame do vídeo previsualizar."""
        self._video_pos = int(float(v))

    def _voltar_camera(self):
        """Tira o vídeo e volta pra webcam ao vivo."""
        self.source = "camera"
        if self._vcap is not None:
            self._vcap.release()
            self._vcap = None
        self.video_path = None
        self.cur_cam = None            # força o worker a reabrir a webcam
        self.video_bar.pack_forget()
        self.btn_carregar.config(text="🎬  Carregar vídeo (editar)...")
        self.status.config(text="Modo câmera.")

    def _aplicar_render(self):
        """Renderiza o vídeo carregado inteiro com as configs atuais, salva na galeria."""
        if not self.video_path:
            return
        src = self.video_path
        ts = time.strftime("%Y%m%d_%H%M%S")
        out = os.path.join(self.galeria, f"render_{ts}.mp4")
        engine, bg_mode = self.engine, self.bg_mode
        bg_ip = self.bg_image_path if bg_mode == "image" else None
        bg_vp = self.bg_video_path if bg_mode == "video" else None
        blur, refine = self.blur, self.refine
        self.btn_aplicar.config(state="disabled", text="🎬 Renderizando...")
        self._rendering = True       # solta a webcam/vídeo-preview durante o render (libera CPU)

        def fim(msg_ok=None, err=None):
            self._rendering = False
            self.btn_aplicar.config(state="normal", text="✅  Aplicar (renderizar tudo)")
            if err:
                messagebox.showerror("Erro no render", err)
            else:
                self.status.config(text="Render pronto.")
                messagebox.showinfo("Pronto", msg_ok)

        def work():
            from agentes.render_video import render_arquivo
            try:
                def pcb(i, tot):
                    txt = f"Renderizando {i}/{tot}..." if tot else f"Renderizando frame {i}..."
                    self.root.after(0, lambda: self.status.config(text=txt))
                render_arquivo(src, out, engine=engine, bg_mode=bg_mode, bg_image_path=bg_ip,
                               bg_video_path=bg_vp, blur=blur, refine=refine, progress_cb=pcb)
                self.root.after(0, lambda: fim(msg_ok=f"Vídeo renderizado salvo na galeria:\n{out}"))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda: fim(err=msg))

        threading.Thread(target=work, daemon=True).start()

    def _open_galeria(self):
        try:
            if sys.platform == "win32":
                os.startfile(self.galeria)
            elif sys.platform == "darwin":
                import subprocess; subprocess.Popen(["open", self.galeria])
            else:
                import subprocess; subprocess.Popen(["xdg-open", self.galeria])
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ─────────────────────── worker ───────────────────────
    def _abrir(self, idx):
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
        cap = cv2.VideoCapture(idx, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_H)
        cap.set(cv2.CAP_PROP_FPS, FPS)
        return cap

    def _loop(self):
        cap = None
        if self.matter is None:
            self.matter = LiveMatter()
        t0, n = time.time(), 0
        while self.running:
            if self._rendering:        # render offline: solta a câmera (libera CPU/webcam)
                if cap is not None:
                    cap.release()
                    cap = None
                    self.cur_cam = None
                with self._lock:
                    self._frame = None
                time.sleep(0.1)
                continue

            if self.source == "video":     # MODO VÍDEO: webcam parada, edita o arquivo
                if cap is not None:        # solta a webcam (não te filma)
                    cap.release()
                    cap = None
                    self.cur_cam = None
                if self.video_path and self._vcap is None:
                    self._vcap = cv2.VideoCapture(self.video_path)
                if self._vcap is None:
                    time.sleep(0.05)
                    continue
                if self._video_pos != self._video_cur:     # usuário trocou o frame
                    self._vcap.set(cv2.CAP_PROP_POS_FRAMES, self._video_pos)
                    ok, fr = self._vcap.read()
                    if ok:
                        self._video_raw = fr
                    self._video_cur = self._video_pos
                    self._dirty_base = True
                if self._video_raw is not None and (self._dirty_base or self._dirty_adj):
                    if self._dirty_base or self._video_base is None:
                        self._video_base = self._compose_base(self._video_raw)
                        self._dirty_base = False
                    out = aplicar_ajustes(
                        self._video_base, zoom=self.zoom, pan_x=self.pan_x, pan_y=self.pan_y,
                        brilho=int(self.brilho), contraste=self.contraste,
                        saturacao=self.saturacao, nitidez=self.nitidez)
                    self._dirty_adj = False
                    with self._lock:
                        self._frame = out
                time.sleep(0.03)
                continue

            if self.req_cam != self.cur_cam:
                if cap:
                    cap.release()
                cap = self._abrir(self.req_cam)
                self.cur_cam = self.req_cam
            if cap is None or not cap.isOpened():
                time.sleep(0.1)
                continue
            if self._paused:           # troca de motor em andamento
                time.sleep(0.05)
                continue
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.03)
                continue
            frame = cv2.resize(frame, (CAP_W, CAP_H))
            if self.mirror:
                frame = cv2.flip(frame, 1)

            if self.bg_mode == "none":
                out = frame
            else:
                if self.bg_mode == "video" and self.bg_video is not None:
                    try:
                        bg = self.bg_video.proximo()
                    except Exception:
                        bg = fundo_desfocado(frame, self.blur)
                elif self.bg_mode == "image" and self.bg_img is not None:
                    bg = self.bg_img
                else:
                    bg = fundo_desfocado(frame, self.blur)
                out = self.matter.compor(frame, bg, color_match=0.12, refine=self.refine)

            out = aplicar_ajustes(
                out, zoom=self.zoom, pan_x=self.pan_x, pan_y=self.pan_y,
                brilho=int(self.brilho), contraste=self.contraste,
                saturacao=self.saturacao, nitidez=self.nitidez,
            )

            if self.recording and self.writer:
                self.writer.write(out)
            if self.req_photo:
                self.req_photo = False
                ts = time.strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(os.path.join(self.galeria, f"foto_{ts}.png"), out)
            self._handle_vcam(out)

            with self._lock:
                self._frame = out
            n += 1
            if n % 10 == 0:
                dt = time.time() - t0
                self._fps = 10.0 / dt if dt > 0 else 0.0
                t0 = time.time()
        if cap:
            cap.release()

    def _handle_vcam(self, out):
        if self.req_virtual and self.virtualcam is None:
            try:
                import pyvirtualcam
                self.virtualcam = pyvirtualcam.Camera(
                    width=CAP_W, height=CAP_H, fps=FPS, fmt=pyvirtualcam.PixelFormat.BGR)
            except Exception as e:
                self.req_virtual = False
                self.root.after(0, lambda: messagebox.showerror(
                    "Câmera virtual",
                    "Não consegui abrir a câmera virtual.\nInstale o OBS Studio uma vez "
                    f"(registra a OBS Virtual Camera).\n\n{e}"))
                return
        if not self.req_virtual and self.virtualcam is not None:
            self.virtualcam.close()
            self.virtualcam = None
        if self.virtualcam is not None:
            self.virtualcam.send(out)

    # ─────────────────────── display ───────────────────────
    def _tick(self):
        with self._lock:
            f = None if self._frame is None else self._frame.copy()
        if f is not None:
            rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            # escala o vídeo pra caber na área disponível, mantendo proporção
            vw = max(320, self.video.winfo_width())
            vh = max(180, self.video.winfo_height())
            scale = min(vw / pil.width, vh / pil.height)
            if scale > 0 and abs(scale - 1.0) > 0.02:
                pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))),
                                 Image.BILINEAR)
            img = ImageTk.PhotoImage(pil)
            self.video.configure(image=img)
            self.video.image = img
            if self.source == "video":
                nome = os.path.basename(self.video_path) if self.video_path else ""
                self.status.config(
                    text=f"  MODO VÍDEO — {nome}   frame {self._video_pos}/{max(0, self._video_total - 1)}"
                         "   (ajuste e clique Aplicar)")
            else:
                rec = "   ● REC" if self.recording else ""
                vc = "   🔴 stream ativo" if self.virtualcam is not None else ""
                self.status.config(text=f"  {self._fps:4.1f} fps    captura {CAP_W}x{CAP_H}{rec}{vc}")
        self.root.after(33, self._tick)

    def fechar(self):
        self._save_config()       # garante o cache atualizado ao sair
        self.running = False
        time.sleep(0.1)
        if self.writer:
            self.writer.release()
        if self.virtualcam:
            self.virtualcam.close()
        if self.bg_video:
            self.bg_video.close()
        if self._vcap is not None:
            self._vcap.release()
        try:
            self.matter.close()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
