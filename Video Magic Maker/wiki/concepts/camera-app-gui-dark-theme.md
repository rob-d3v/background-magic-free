---
title: camera-app-gui — Dark theme and scrollable control panel
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["camera_app.py"]
tags: [concept, ui, tkinter, ttk, theme, dark-mode, camera-app-gui]
status: stable
---
# camera-app-gui — Dark theme and scrollable control panel

`CameraApp._setup_style` and `_build_ui` implement a modern dark visual design
using ttk's `clam` theme as a base, with a scrollable right-panel that prevents
controls from being clipped when the window is resized short.

## Why a custom theme

Tkinter's default theme looks dated and ignores the system dark-mode preference.
The app previously used a plain grid layout where controls would be clipped (go
off-screen/invisible) when the window height was reduced. The redesign fixed both
problems simultaneously.

## Colour palette (`self.COL`)

Defined in `_setup_style` as a dict stored on `self.COL`:

| Key | Hex | Used for |
|---|---|---|
| `bg` | `#16161f` | Root window background, video area background |
| `panel` | `#20202e` | Right control panel, slider troughs |
| `card` | `#2c2c40` | Combobox field background, button default background |
| `txt` | `#e6e6f0` | Primary label text, slider values |
| `mute` | `#8a8aa6` | Secondary/muted labels, status bar text |
| `accent` | `#7c6cf0` | Accent buttons (Accent.TButton), slider active thumb |
| `accent2` | `#6757d8` | Accent button hover state |
| `rec` | `#e0556b` | Record button (Rec.TButton) |

## ttk style configuration

`_setup_style` calls `ttk.Style().theme_use("clam")` to set the base, then
configures named styles:

| Style name | Purpose |
|---|---|
| `TFrame` | All frames use `panel` background |
| `TLabel` | Segoe UI 9pt, `txt` on `panel` |
| `Muted.TLabel` | Segoe UI 8pt, `mute` colour — for help text |
| `Status.TLabel` | Segoe UI 9pt, `mute` on `bg` — status bar |
| `TLabelframe` / `.Label` | Solid border in `card` colour; label in `accent`, bold 8pt |
| `TButton` | `card` background, 0 border, 7px padding |
| `Accent.TButton` | `accent` background, white text, bold 9pt, 8px padding |
| `Rec.TButton` | `rec` background, white text, bold 9pt — recording button |
| `TCheckbutton` | `panel` background; indicator turns `accent` when checked |
| `TRadiobutton` | Same as checkbutton |
| `TCombobox` | `card` field background, `txt` foreground |
| `Vertical.TScrollbar` | `card` thumb on `panel` trough |

The combobox dropdown listbox (a plain Tk `Listbox` inside ttk) cannot be styled
via `ttk.Style`; it is coloured via `root.option_add`:

```python
root.option_add("*TCombobox*Listbox.background", C["card"])
root.option_add("*TCombobox*Listbox.foreground", C["txt"])
root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
```

## Scrollable control panel

The right panel is built with a `tk.Canvas` + `ttk.Scrollbar` + inner `ttk.Frame`:

```
rightwrap (ttk.Frame, sticky="ns")
  └── _canvas (tk.Canvas, width=340, no highlight border)
  └── Scrollbar (vertical, linked to _canvas.yview)
      └── ctl (ttk.Frame, created inside canvas via create_window)
          └── [all control sections — ttk.Labelframe groups]
```

The inner frame `ctl` resizes to fit its children; a `<Configure>` bind updates
`scrollregion` to match. Mouse-wheel scrolling uses `bind_all("<MouseWheel>")` →
`yview_scroll(int(-e.delta / 120), "units")`.

This replaces the old fixed grid layout (counter `r`) which clipped controls when
the window height was less than the total control height.

## Layout of control sections

All sections inside `ctl` use `ttk.Labelframe` with `pack(fill="x")`. Internal
widgets use `pack` (not grid). The sections in order:

1. **CAMARA & MOTOR** — camera combobox, engine combobox
2. **FUNDO** — radio group (none/blur/image/video), image/video pickers, blur slider
3. **AJUSTES DE IMAGEM** — mirror/refine checkboxes, zoom/pan/brightness/contrast/
   saturation/sharpness sliders, reset button
4. **GRAVAR & STREAM** — record + photo buttons, virtual camera toggle, gallery button
5. **VIDEO (EDITAR & RENDERIZAR)** — load video button, video bar (hidden until loaded)

## Slider helper (`_slider`)

All sliders are created by `_slider(parent, label, lo, hi, val, cb, res=1)`:
- Creates a `ttk.Frame` row with a fixed-width label (`width=11`) and a `tk.Scale`
  (`orient="horizontal"`, `length=140`, `sliderlength=18`, `sliderrelief="flat"`).
- Colours the Scale explicitly with palette values (`bg=panel`, `fg=txt`,
  `troughcolor=card`, `activebackground=accent`).
- Binds `<ButtonRelease-1>` to `_save_config` (save on release, not every drag tick).
- Returns the `tk.Scale` widget for later `set()`/reset calls.

## Window geometry and topmost behaviour

```python
root.geometry("1180x720")
root.minsize(760, 520)
root.lift()
root.attributes("-topmost", True)
root.after(900, lambda: root.attributes("-topmost", False))
root.focus_force()
```

`-topmost` is set at startup and released after 900 ms so the window comes to the
front without staying pinned above all others permanently. See
[[decisions/camera-app-gui-lazy-matter-init]] for the startup context.

## Video area responsiveness

The video `tk.Label` lives in a frame configured with `columnconfigure(0, weight=1)`
and `rowconfigure(0, weight=1)`, so it expands to fill available space. `_tick`
scales the PIL image to fit `video.winfo_width() × video.winfo_height()` while
maintaining aspect ratio (`min(vw/pil.width, vh/pil.height)` scale factor, BILINEAR
resize). This replaced a fixed 960×540 display that left dead space.

## Related

[[entities/camera-app]] · [[concepts/camera-app-gui-dual-thread-frame-pipeline]] ·
[[decisions/camera-app-gui-lazy-matter-init]] · [[index]]
