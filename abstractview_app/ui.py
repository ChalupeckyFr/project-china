"""Kompletní dynamické a responzivní uživatelské rozhraní AbstractView."""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.wintypes
import math
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import psutil
import pygame

from abstractview_app.config import (
    ALL_EFFECT_KEYS,
    BODY_PARTS,
    GRAFFITI_UNLOCK_SIZE,
    OBJECT_EFFECTS,
    PATTERN_STYLES,
    SHAPE_EFFECTS,
    AppSettings,
    SettingsStore,
)
from abstractview_app.renderer import AbstractViewEngine
from abstractview_app.samples import (
    SAMPLE_POSES,
    discover_camera_ports,
    render_sample_thumbnail_ppm,
)
from abstractview_app.theme import (
    METRICS,
    PRESET_COLOR_MAP,
    PRESET_COLORS,
    ThemePalette,
    get_palette,
)


def _get_monitor_geometry(hwnd: int) -> tuple[int, int, int, int] | None:
    """Zjistí přesné rozměry a pozici monitoru, na kterém se okno nachází (Windows API)."""
    try:
        user32 = ctypes.windll.user32
        MONITOR_DEFAULTTONEAREST = 2
        hmonitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if not hmonitor:
            return None

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.DWORD),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.wintypes.DWORD),
            ]

        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            r = info.rcMonitor
            return (r.left, r.top, r.right - r.left, r.bottom - r.top)
    except (AttributeError, OSError, ValueError):
        return None
    return None


class HoverButton(tk.Label):
    """Vlastní stylované tlačítko s podporou hover efektu, ořezu a témat."""

    def __init__(
        self,
        master: tk.Widget,
        text: str,
        command: Callable[[], None],
        palette: ThemePalette,
        variant: str = "secondary",
        font_size: int = METRICS.font_size_body,
        bold: bool = False,
        padx: int = 12,
        pady: int = 7,
    ) -> None:
        weight = "bold" if bold else "normal"
        super().__init__(
            master,
            text=text,
            font=(METRICS.font_family, font_size, weight),
            padx=padx,
            pady=pady,
            cursor="hand2",
            bd=1,
            relief="solid",
        )
        self._command = command
        self._palette = palette
        self._variant = variant
        self._hovered = False
        self._disabled = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.apply_palette(palette)

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self._refresh_colors()

    def set_disabled(self, disabled: bool) -> None:
        self._disabled = disabled
        self.configure(cursor="arrow" if disabled else "hand2")
        self._refresh_colors()

    def apply_palette(self, palette: ThemePalette) -> None:
        self._palette = palette
        self._refresh_colors()

    def _refresh_colors(self) -> None:
        p = self._palette
        if self._disabled:
            bg = p.bg_elevated
            fg = p.text_muted
            border = p.border
        elif self._variant == "active":
            bg = p.accent_hover if self._hovered else p.accent
            fg = p.accent_text
            border = p.border_focus
        elif self._variant == "play":
            bg = p.play_hover if self._hovered else p.play_bg
            fg = p.play_text
            border = p.play_glow
        elif self._variant == "danger":
            bg = p.danger_hover if self._hovered else p.danger
            fg = "#FFFFFF"
            border = p.danger
        else:
            bg = p.bg_hover if self._hovered else p.bg_elevated
            fg = p.text_primary
            border = p.border_focus if self._hovered else p.border

        self.configure(
            bg=bg,
            fg=fg,
            highlightbackground=border,
            highlightcolor=border,
            highlightthickness=1,
            bd=0,
        )

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._refresh_colors()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._refresh_colors()

    def _on_click(self, _event: tk.Event) -> None:
        if not self._disabled and self._command is not None:
            self._command()


class SmoothSlider(tk.Frame):
    """Dynamický posuvník s popiskem, čitelnou hodnotou a hover odezvou."""

    def __init__(
        self,
        master: tk.Widget,
        label: str,
        min_val: float,
        max_val: float,
        initial_val: float,
        on_change: Callable[[float], None],
        palette: ThemePalette,
        step: float = 1.0,
        formatter: Callable[[float], str] | None = None,
    ) -> None:
        super().__init__(master, bg=palette.bg_card)
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.step = float(step)
        self.value = float(initial_val)
        self._on_change = on_change
        self._palette = palette
        self._formatter = formatter or (lambda v: f"{round(v)}")
        self._hovered = False

        self.columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=palette.bg_card)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        header.columnconfigure(0, weight=1)

        self.lbl_title = tk.Label(
            header,
            text=label,
            font=(METRICS.font_family, METRICS.font_size_body),
            bg=palette.bg_card,
            fg=palette.text_secondary,
            anchor="w",
        )
        self.lbl_title.grid(row=0, column=0, sticky="w")

        self.lbl_value = tk.Label(
            header,
            text=self._formatter(self.value),
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
            bg=palette.bg_card,
            fg=palette.text_primary,
            anchor="e",
        )
        self.lbl_value.grid(row=0, column=1, sticky="e")

        self.canvas = tk.Canvas(
            self,
            height=24,
            bg=palette.bg_card,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.canvas.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_pointer)
        self.canvas.bind("<B1-Motion>", self._on_pointer)

    def set_value(self, new_val: float, notify: bool = False) -> None:
        clamped = max(self.min_val, min(self.max_val, float(new_val)))
        if self.step > 0:
            steps = round((clamped - self.min_val) / self.step)
            clamped = self.min_val + steps * self.step
            clamped = max(self.min_val, min(self.max_val, clamped))
        self.value = clamped
        self.lbl_value.configure(text=self._formatter(self.value))
        self._redraw()
        if notify:
            self._on_change(self.value)

    def set_formatter(self, formatter: Callable[[float], str]) -> None:
        self._formatter = formatter
        self.lbl_value.configure(text=self._formatter(self.value))

    def apply_palette(self, palette: ThemePalette) -> None:
        self._palette = palette
        self.configure(bg=palette.bg_card)
        self.lbl_title.master.configure(bg=palette.bg_card)
        self.lbl_title.configure(bg=palette.bg_card, fg=palette.text_secondary)
        self.lbl_value.configure(bg=palette.bg_card, fg=palette.text_primary)
        self.canvas.configure(bg=palette.bg_card)
        self._redraw()

    def _on_enter(self, _e: tk.Event) -> None:
        self._hovered = True
        self._redraw()

    def _on_leave(self, _e: tk.Event) -> None:
        self._hovered = False
        self._redraw()

    def _on_pointer(self, event: tk.Event) -> None:
        w = max(1, self.canvas.winfo_width())
        pad = 10
        usable = max(1, w - 2 * pad)
        ratio = max(0.0, min(1.0, (event.x - pad) / usable))
        raw = self.min_val + ratio * (self.max_val - self.min_val)
        self.set_value(raw, notify=True)

    def _redraw(self) -> None:
        self.canvas.delete("all")
        w = max(40, self.canvas.winfo_width())
        h = max(20, self.canvas.winfo_height())
        cy = h // 2
        pad = 10
        usable = max(1, w - 2 * pad)
        span = max(1e-9, self.max_val - self.min_val)
        ratio = max(0.0, min(1.0, (self.value - self.min_val) / span))
        thumb_x = pad + ratio * usable

        p = self._palette
        # Dráha posuvníku
        self.canvas.create_line(
            pad,
            cy,
            w - pad,
            cy,
            fill=p.slider_track,
            width=6,
            capstyle="round",
        )
        # Vyplněná část
        if thumb_x > pad:
            self.canvas.create_line(
                pad,
                cy,
                thumb_x,
                cy,
                fill=p.slider_fill,
                width=6,
                capstyle="round",
            )
        # Jezdec
        r = 8 if self._hovered else 7
        thumb_col = p.slider_thumb_hover if self._hovered else p.slider_thumb
        self.canvas.create_oval(
            thumb_x - r,
            cy - r,
            thumb_x + r,
            cy + r,
            fill=thumb_col,
            outline=p.accent,
            width=2,
        )


class GraffitiCanvasWidget(tk.Frame):
    """Kreslicí plátno se zaoblenými rohy a čárkovaným okrajem pro funkci Graffiti."""

    def __init__(
        self,
        master: tk.Widget,
        settings: AppSettings,
        on_stroke_updated: Callable[[], None],
        palette: ThemePalette,
    ) -> None:
        super().__init__(master, bg=palette.bg_card)
        self.settings = settings
        self._on_updated = on_stroke_updated
        self._palette = palette
        self._current_points: list[list[float]] = []

        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            height=170,
            bg=palette.bg_elevated,
            highlightthickness=0,
            bd=0,
            cursor="crosshair",
        )
        self.canvas.grid(row=0, column=0, sticky="ew")

        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._start_stroke)
        self.canvas.bind("<B1-Motion>", self._move_stroke)
        self.canvas.bind("<ButtonRelease-1>", self._end_stroke)

    def apply_palette(self, palette: ThemePalette) -> None:
        self._palette = palette
        self.configure(bg=palette.bg_card)
        self.canvas.configure(bg=palette.bg_elevated)
        self.redraw()

    def clear_strokes(self) -> None:
        self.settings.graffiti_strokes.clear()
        self.redraw()
        self._on_updated()

    def _norm_coords(self, event: tk.Event) -> list[float]:
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        nx = max(0.03, min(0.97, event.x / w))
        ny = max(0.05, min(0.95, event.y / h))
        return [round(nx, 4), round(ny, 4)]

    def _start_stroke(self, event: tk.Event) -> None:
        if not self.settings.is_graffiti_unlocked:
            return
        pt = self._norm_coords(event)
        self._current_points = [pt]
        self.settings.graffiti_strokes.append(
            {
                "color": self.settings.graffiti_brush_color,
                "eraser": self.settings.graffiti_eraser,
                "size": self.settings.graffiti_brush_size,
                "points": self._current_points,
            }
        )
        self.redraw()
        self._on_updated()

    def _move_stroke(self, event: tk.Event) -> None:
        if not self.settings.is_graffiti_unlocked or not self._current_points:
            return
        pt = self._norm_coords(event)
        last = self._current_points[-1]
        if math.hypot(pt[0] - last[0], pt[1] - last[1]) >= 0.008:
            self._current_points.append(pt)
            self.redraw()
            self._on_updated()

    def _end_stroke(self, _event: tk.Event) -> None:
        if self._current_points:
            self._current_points = []
            self._on_updated()

    def redraw(self) -> None:
        self.canvas.delete("all")
        w = max(60, self.canvas.winfo_width())
        h = max(60, self.canvas.winfo_height())
        p = self._palette

        # Zaoblený obdélník s čárkovaným okrajem
        r = 16
        pad = 6
        x1, y1, x2, y2 = pad, pad, w - pad, h - pad
        dash = (6, 4)
        border_col = (
            p.accent if self.settings.is_graffiti_unlocked else p.border
        )

        # Čárkované hrany a oblouky v rozích
        self.canvas.create_line(
            x1 + r, y1, x2 - r, y1, fill=border_col, width=2, dash=dash
        )
        self.canvas.create_line(
            x1 + r, y2, x2 - r, y2, fill=border_col, width=2, dash=dash
        )
        self.canvas.create_line(
            x1, y1 + r, x1, y2 - r, fill=border_col, width=2, dash=dash
        )
        self.canvas.create_line(
            x2, y1 + r, x2, y2 - r, fill=border_col, width=2, dash=dash
        )
        self.canvas.create_arc(
            x1,
            y1,
            x1 + 2 * r,
            y1 + 2 * r,
            start=90,
            extent=90,
            style="arc",
            outline=border_col,
            width=2,
        )
        self.canvas.create_arc(
            x2 - 2 * r,
            y1,
            x2,
            y1 + 2 * r,
            start=0,
            extent=90,
            style="arc",
            outline=border_col,
            width=2,
        )
        self.canvas.create_arc(
            x1,
            y2 - 2 * r,
            x1 + 2 * r,
            y2,
            start=180,
            extent=90,
            style="arc",
            outline=border_col,
            width=2,
        )
        self.canvas.create_arc(
            x2 - 2 * r,
            y2 - 2 * r,
            x2,
            y2,
            start=270,
            extent=90,
            style="arc",
            outline=border_col,
            width=2,
        )

        if not self.settings.is_graffiti_unlocked:
            self.canvas.create_text(
                w // 2,
                h // 2,
                text=f"Zvětši Velikost tvarů alespoň na {GRAFFITI_UNLOCK_SIZE} pro odemknutí kreslení Graffiti",
                fill=p.text_muted,
                font=(METRICS.font_family, METRICS.font_size_body),
                width=max(120, w - 36),
            )
            return

        if not self.settings.graffiti_strokes:
            self.canvas.create_text(
                w // 2,
                h // 2,
                text="Kresli myší sem do plátna – motiv se okamžitě promítne na tvary",
                fill=p.text_muted,
                font=(METRICS.font_family, METRICS.font_size_small),
                width=max(120, w - 36),
            )

        for stroke in self.settings.graffiti_strokes:
            pts = stroke.get("points", [])
            if not pts:
                continue
            eraser = bool(stroke.get("eraser", False))
            c_key = stroke.get("color", "red")
            hex_c = (
                p.bg_elevated
                if eraser
                else PRESET_COLOR_MAP.get(c_key, PRESET_COLORS[0]).hex_code
            )
            size = max(2, int(stroke.get("size", 8)))
            flat: list[float] = []
            for nx, ny in pts:
                flat.extend((nx * w, ny * h))
            if len(pts) == 1:
                cx, cy = flat[0], flat[1]
                rad = size * 0.6
                self.canvas.create_oval(
                    cx - rad,
                    cy - rad,
                    cx + rad,
                    cy + rad,
                    fill=hex_c,
                    outline=hex_c,
                )
            else:
                self.canvas.create_line(
                    *flat,
                    fill=hex_c,
                    width=size,
                    capstyle="round",
                    joinstyle="round",
                    smooth=True,
                )


class OutputDisplayWindow:
    """Samostatné přesouvatelné a škálovatelné okno pro přehrávání výstupu s podporou
    čistého fullscreenu (bez horní lišty) na libovolném monitoru."""

    def __init__(
        self,
        root: tk.Tk,
        engine: AbstractViewEngine,
        settings_provider: Callable[[], AppSettings],
        palette_provider: Callable[[], ThemePalette],
        on_closed: Callable[[], None],
    ) -> None:
        self.root = root
        self.engine = engine
        self._get_settings = settings_provider
        self._get_palette = palette_provider
        self._on_closed = on_closed

        self.window = tk.Toplevel(root)
        self.window.title("AbstractView – Živý výstup")
        self.window.geometry("960x720")
        self.window.minsize(420, 320)
        self.window.configure(bg="#050816")

        self.is_fullscreen = False
        self._saved_geometry = "960x720+120+80"
        self._photo: tk.PhotoImage | None = None
        self._last_mouse_move = time.monotonic()
        self._overlay_visible = True

        self.canvas = tk.Canvas(
            self.window, bg="#050816", highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)
        self._image_item = self.canvas.create_image(0, 0, anchor="nw")

        # Plovoucí tlačítko pro přepnutí na celou obrazovku (bez horní lišty)
        palette = self._get_palette()
        self.btn_fullscreen = HoverButton(
            self.canvas,
            text="⛶  Celá obrazovka (F11)",
            command=self.toggle_fullscreen,
            palette=palette,
            variant="active",
            font_size=9,
            bold=True,
            padx=10,
            pady=5,
        )
        self._btn_window_id = self.canvas.create_window(
            940, 16, anchor="ne", window=self.btn_fullscreen
        )

        # Klávesové zkratky a ovládání
        self.window.bind("<F11>", lambda _e: self.toggle_fullscreen())
        self.window.bind("<f>", lambda _e: self.toggle_fullscreen())
        self.window.bind("<F>", lambda _e: self.toggle_fullscreen())
        self.window.bind("<Escape>", lambda _e: self.exit_fullscreen())
        self.canvas.bind("<Double-Button-1>", lambda _e: self.toggle_fullscreen())
        self.canvas.bind("<Motion>", self._on_mouse_motion)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

    def _on_canvas_configure(self, event: tk.Event) -> None:
        w = max(320, int(event.width))
        self.canvas.coords(self._btn_window_id, w - 16, 16)

    def _on_mouse_motion(self, _event: tk.Event) -> None:
        self._last_mouse_move = time.monotonic()
        if not self._overlay_visible:
            self._overlay_visible = True
            self.canvas.itemconfigure(self._btn_window_id, state="normal")

    def toggle_fullscreen(self) -> None:
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self) -> None:
        if self.is_fullscreen:
            return
        self._saved_geometry = self.window.geometry()
        self.window.update_idletasks()
        hwnd = self.window.winfo_id()
        mon_rect = _get_monitor_geometry(hwnd)

        self.is_fullscreen = True
        # Odstraníme horní lištu okna a roztáhneme přesně na monitor, kde okno leží
        self.window.overrideredirect(True)
        if mon_rect is not None:
            mx, my, mw, mh = mon_rect
            self.window.geometry(f"{mw}x{mh}+{mx}+{my}")
        else:
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            self.window.geometry(f"{sw}x{sh}+0+0")

        self.btn_fullscreen.configure(text="✕  Ukončit celou obrazovku (Esc)")
        self.window.focus_force()

    def exit_fullscreen(self) -> None:
        if not self.is_fullscreen:
            return
        self.is_fullscreen = False
        self.window.overrideredirect(False)
        self.window.geometry(self._saved_geometry)
        self.btn_fullscreen.configure(text="⛶  Celá obrazovka (F11)")
        self.window.focus_force()

    def render_tick(self, elapsed_ms: float, delta_ms: float) -> str:
        if not self.window.winfo_exists():
            return "stars"

        # Automatické skrytí plovoucího tlačítka po 2.5 s nečinnosti myši ve fullscreenu
        if (
            self.is_fullscreen
            and self._overlay_visible
            and (time.monotonic() - self._last_mouse_move) > 2.5
        ):
            self._overlay_visible = False
            self.canvas.itemconfigure(self._btn_window_id, state="hidden")

        cw = max(320, self.canvas.winfo_width())
        ch = max(240, self.canvas.winfo_height())
        # Vykreslujeme v nativním rozlišení až 960x720 (nebo okně) pro maximální FPS
        render_w = min(960, cw)
        render_h = min(720, ch)
        self.engine.set_surface_size(render_w, render_h)

        surf, active_eff = self.engine.render_step(
            self._get_settings(), elapsed_ms, delta_ms
        )
        if (cw, ch) != (render_w, render_h):
            display_surf = pygame.transform.smoothscale(surf, (cw, ch))
        else:
            display_surf = surf

        ppm_header = f"P6 {cw} {ch} 255\n".encode("ascii")
        ppm_data = ppm_header + pygame.image.tobytes(display_surf, "RGB")
        self._photo = tk.PhotoImage(width=cw, height=ch, data=ppm_data, format="PPM")
        self.canvas.itemconfigure(self._image_item, image=self._photo)
        return active_eff

    def close(self) -> None:
        try:
            if self.window.winfo_exists():
                self.window.destroy()
        finally:
            self._on_closed()


class AbstractViewApp:
    """Hlavní okno aplikace AbstractView s dynamickým responzivním rozložením."""

    def __init__(
        self,
        root: tk.Tk | None = None,
        store: SettingsStore | None = None,
    ) -> None:
        self.root = root or tk.Tk()
        self.store = store or SettingsStore()
        self.settings = self.store.settings
        self.palette = get_palette(self.settings.theme_mode)

        self.root.title("AbstractView – Ovládací panel efektů")
        self.root.geometry(
            f"{METRICS.default_window_width}x{METRICS.default_window_height}"
        )
        self.root.minsize(METRICS.min_window_width, METRICS.min_window_height)
        self.root.configure(bg=self.palette.bg_primary)

        self.engine = AbstractViewEngine()
        self.engine.sync_source(self.settings)
        self.output_window: OutputDisplayWindow | None = None

        self._themed_frames: list[tuple[tk.Widget, str]] = []
        self._themed_labels: list[tuple[tk.Label, str, str]] = []
        self._buttons: list[HoverButton] = []
        self._sliders: list[SmoothSlider] = []
        self._wrap_labels: list[tk.Label] = []
        self._thumb_images: dict[str, tk.PhotoImage] = {}
        self._selected_part_tab: str = "head"
        self._current_columns: int = 0

        self._started_at = time.perf_counter()
        self._last_tick = self._started_at
        self._fps_estimate = 60.0
        self._process = psutil.Process()

        self._build_ui()
        self.refresh_all_states()
        self.apply_theme(self.settings.theme_mode, save=False)

        self.root.bind("<Configure>", self._on_root_configure)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self._schedule_loop()

    # ------------------------------------------------------------------
    # Stavba UI
    # ------------------------------------------------------------------
    def _reg_frame(self, widget: tk.Widget, role: str = "card") -> None:
        self._themed_frames.append((widget, role))

    def _reg_label(
        self, label: tk.Label, bg_role: str = "card", fg_role: str = "primary"
    ) -> None:
        self._themed_labels.append((label, bg_role, fg_role))

    def _make_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        outer = tk.Frame(
            parent,
            bg=self.palette.bg_card,
            padx=METRICS.card_padding,
            pady=METRICS.card_padding,
            highlightbackground=self.palette.border,
            highlightthickness=1,
        )
        self._reg_frame(outer, "card")
        outer.columnconfigure(0, weight=1)

        lbl = tk.Label(
            outer,
            text=title,
            font=(METRICS.font_family, METRICS.font_size_section, "bold"),
            bg=self.palette.bg_card,
            fg=self.palette.text_primary,
            anchor="w",
        )
        lbl.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._reg_label(lbl, "card", "primary")
        return outer

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        # 1. Horní lišta (Header): Název, přepínač light/dark, Resetovat možnosti vpravo nahoře
        self.header_frame = tk.Frame(
            self.root, bg=self.palette.bg_card, padx=16, pady=10
        )
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.columnconfigure(1, weight=1)
        self._reg_frame(self.header_frame, "card")

        self.lbl_brand = tk.Label(
            self.header_frame,
            text="AbstractView",
            font=(METRICS.font_family, METRICS.font_size_title, "bold"),
            bg=self.palette.bg_card,
            fg=self.palette.text_primary,
        )
        self.lbl_brand.grid(row=0, column=0, sticky="w", padx=(0, 12))
        self._reg_label(self.lbl_brand, "card", "primary")

        self.lbl_source_badge = tk.Label(
            self.header_frame,
            text=f"Zdroj: {self.engine.last_source_label}",
            font=(METRICS.font_family, METRICS.font_size_small),
            bg=self.palette.badge_bg,
            fg=self.palette.badge_text,
            padx=10,
            pady=4,
        )
        self.lbl_source_badge.grid(row=0, column=1, sticky="w")
        self._reg_label(self.lbl_source_badge, "badge", "badge")

        right_header = tk.Frame(self.header_frame, bg=self.palette.bg_card)
        right_header.grid(row=0, column=2, sticky="e")
        self._reg_frame(right_header, "card")

        self.btn_theme = HoverButton(
            right_header,
            text=f"Režim: {self.settings.theme_mode}",
            command=self.toggle_theme,
            palette=self.palette,
            variant="secondary",
            bold=True,
        )
        self.btn_theme.pack(side="left", padx=(0, 8))
        self._buttons.append(self.btn_theme)

        self.btn_reset = HoverButton(
            right_header,
            text="↺ Resetovat možnosti",
            command=self.open_reset_dialog,
            palette=self.palette,
            variant="danger",
            bold=True,
        )
        self.btn_reset.pack(side="left")
        self._buttons.append(self.btn_reset)

        # 2. Akční lišta: Nahrát CSV, Vybrat kameru a Hero tlačítko SPUSTIT ŽIVÝ VÝSTUP
        self.action_bar = tk.Frame(
            self.root, bg=self.palette.bg_primary, padx=16, pady=10
        )
        self.action_bar.grid(row=1, column=0, sticky="ew")
        self.action_bar.columnconfigure(0, weight=1)
        self.action_bar.columnconfigure(1, weight=1)
        self.action_bar.columnconfigure(2, weight=2)
        self._reg_frame(self.action_bar, "primary")

        self.btn_load_csv = HoverButton(
            self.action_bar,
            text="📂  Nahrát CSV",
            command=self.open_csv_dialog,
            palette=self.palette,
            variant="secondary",
            font_size=11,
            bold=True,
            pady=10,
        )
        self.btn_load_csv.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._buttons.append(self.btn_load_csv)

        self.btn_select_camera = HoverButton(
            self.action_bar,
            text="🎥  Vybrat kameru",
            command=self.open_camera_dialog,
            palette=self.palette,
            variant="secondary",
            font_size=11,
            bold=True,
            pady=10,
        )
        self.btn_select_camera.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self._buttons.append(self.btn_select_camera)

        self.btn_play_output = HoverButton(
            self.action_bar,
            text="▶  SPUSTIT ŽIVÝ VÝSTUP",
            command=self.toggle_output_window,
            palette=self.palette,
            variant="play",
            font_size=12,
            bold=True,
            padx=18,
            pady=10,
        )
        self.btn_play_output.grid(row=0, column=2, sticky="ew")
        self._buttons.append(self.btn_play_output)

        # 3. Scrollovatelná hlavní oblast pro karty nastavení
        scroll_host = tk.Frame(self.root, bg=self.palette.bg_primary)
        scroll_host.grid(row=2, column=0, sticky="nsew")
        scroll_host.columnconfigure(0, weight=1)
        scroll_host.rowconfigure(0, weight=1)
        self._reg_frame(scroll_host, "primary")

        self.scroll_canvas = tk.Canvas(
            scroll_host,
            bg=self.palette.bg_primary,
            highlightthickness=0,
            bd=0,
        )
        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = tk.Scrollbar(
            scroll_host, orient="vertical", command=self.scroll_canvas.yview
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.cards_container = tk.Frame(
            self.scroll_canvas, bg=self.palette.bg_primary, padx=16, pady=6
        )
        self._reg_frame(self.cards_container, "primary")
        self._cards_window_id = self.scroll_canvas.create_window(
            (0, 0), window=self.cards_container, anchor="nw"
        )

        self.cards_container.bind(
            "<Configure>",
            lambda _e: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            ),
        )
        self.scroll_canvas.bind("<Configure>", self._on_scroll_canvas_configure)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        # Vytvoření jednotlivých karet
        self._build_effects_cards()
        self._build_shuffle_card()
        self._build_shape_settings_card()
        self._build_object_settings_card()

        # 4. Stavová patička (RAM, CPU, FPS, aktivní efekt)
        self.footer_frame = tk.Frame(
            self.root, bg=self.palette.bg_card, padx=16, pady=6
        )
        self.footer_frame.grid(row=3, column=0, sticky="ew")
        self.footer_frame.columnconfigure(0, weight=1)
        self._reg_frame(self.footer_frame, "card")

        self.lbl_status = tk.Label(
            self.footer_frame,
            text="Připraveno",
            font=(METRICS.font_family, METRICS.font_size_small),
            bg=self.palette.bg_card,
            fg=self.palette.text_secondary,
            anchor="w",
        )
        self.lbl_status.grid(row=0, column=0, sticky="w")
        self._reg_label(self.lbl_status, "card", "secondary")

        self.lbl_perf = tk.Label(
            self.footer_frame,
            text="RAM: -- MB | CPU: -- %",
            font=(METRICS.font_family, METRICS.font_size_small),
            bg=self.palette.bg_card,
            fg=self.palette.text_muted,
            anchor="e",
        )
        self.lbl_perf.grid(row=0, column=1, sticky="e")
        self._reg_label(self.lbl_perf, "card", "muted")

    def _build_effects_cards(self) -> None:
        # Karta 1: Efekty tvarové
        self.card_shape_effects = self._make_card(
            self.cards_container, "Efekty tvarové"
        )
        row_frame = tk.Frame(self.card_shape_effects, bg=self.palette.bg_card)
        row_frame.grid(row=1, column=0, sticky="ew")
        self._reg_frame(row_frame, "card")

        # Hned první možnost je shuffle
        self.btn_shape_shuffle = HoverButton(
            row_frame,
            text="shuffle",
            command=self._toggle_shape_shuffle,
            palette=self.palette,
            bold=True,
        )
        self.btn_shape_shuffle.pack(side="left", padx=(0, 6), pady=3)
        self._buttons.append(self.btn_shape_shuffle)

        self.shape_effect_buttons: dict[str, HoverButton] = {}
        for eff_key, eff_label in SHAPE_EFFECTS:
            btn = HoverButton(
                row_frame,
                text=eff_label,
                command=lambda k=eff_key: self.select_effect(k),
                palette=self.palette,
            )
            btn.pack(side="left", padx=(0, 6), pady=3)
            self.shape_effect_buttons[eff_key] = btn
            self._buttons.append(btn)

        lbl_more_shape = tk.Label(
            row_frame,
            text="more coming soon",
            font=(METRICS.font_family, METRICS.font_size_small, "italic"),
            bg=self.palette.badge_bg,
            fg=self.palette.badge_text,
            padx=8,
            pady=4,
        )
        lbl_more_shape.pack(side="left", padx=(4, 0), pady=3)
        self._reg_label(lbl_more_shape, "badge", "badge")

        # Karta 2: Efekty objektové
        self.card_object_effects = self._make_card(
            self.cards_container, "Efekty objektové"
        )
        obj_row = tk.Frame(self.card_object_effects, bg=self.palette.bg_card)
        obj_row.grid(row=1, column=0, sticky="ew")
        self._reg_frame(obj_row, "card")

        # Hned první možnost je shuffle
        self.btn_object_shuffle = HoverButton(
            obj_row,
            text="shuffle",
            command=self._toggle_object_shuffle,
            palette=self.palette,
            bold=True,
        )
        self.btn_object_shuffle.pack(side="left", padx=(0, 6), pady=3)
        self._buttons.append(self.btn_object_shuffle)

        self.object_effect_buttons: dict[str, HoverButton] = {}
        for eff_key, eff_label in OBJECT_EFFECTS:
            btn = HoverButton(
                obj_row,
                text=eff_label,
                command=lambda k=eff_key: self.select_effect(k),
                palette=self.palette,
            )
            btn.pack(side="left", padx=(0, 6), pady=3)
            self.object_effect_buttons[eff_key] = btn
            self._buttons.append(btn)

        lbl_more_obj = tk.Label(
            obj_row,
            text="more coming soon",
            font=(METRICS.font_family, METRICS.font_size_small, "italic"),
            bg=self.palette.badge_bg,
            fg=self.palette.badge_text,
            padx=8,
            pady=4,
        )
        lbl_more_obj.pack(side="left", padx=(4, 0), pady=3)
        self._reg_label(lbl_more_obj, "badge", "badge")

    def _build_shuffle_card(self) -> None:
        self.card_shuffle = self._make_card(
            self.cards_container,
            "Nastavení shuffle (společné pro tvarové i objektové)",
        )

        # Posuvník 1: Po jaké době změnit (15s až 5 minut, první hodnota 1 min = 60s)
        self.slider_shuffle_interval = SmoothSlider(
            self.card_shuffle,
            label="Změnit efekt po",
            min_val=15,
            max_val=300,
            initial_val=self.settings.shuffle_interval_s,
            step=5,
            formatter=self._format_duration,
            on_change=self._on_shuffle_interval_change,
            palette=self.palette,
        )
        self.slider_shuffle_interval.grid(
            row=1, column=0, sticky="ew", pady=(0, 8)
        )
        self._sliders.append(self.slider_shuffle_interval)

        # Posuvník 2: Smooth přechod (0s až 5s, první hodnota 1s)
        self.slider_shuffle_transition = SmoothSlider(
            self.card_shuffle,
            label="Smooth přechod",
            min_val=0.0,
            max_val=5.0,
            initial_val=self.settings.shuffle_transition_s,
            step=0.25,
            formatter=lambda v: f"{v:.1f} s",
            on_change=self._on_shuffle_transition_change,
            palette=self.palette,
        )
        self.slider_shuffle_transition.grid(
            row=2, column=0, sticky="ew", pady=(0, 10)
        )
        self._sliders.append(self.slider_shuffle_transition)

        # Pořadí: normal (první hodnota), random, custom
        order_row = tk.Frame(self.card_shuffle, bg=self.palette.bg_card)
        order_row.grid(row=3, column=0, sticky="ew")
        self._reg_frame(order_row, "card")

        lbl_order = tk.Label(
            order_row,
            text="Pořadí:",
            font=(METRICS.font_family, METRICS.font_size_body),
            bg=self.palette.bg_card,
            fg=self.palette.text_secondary,
        )
        lbl_order.pack(side="left", padx=(0, 10))
        self._reg_label(lbl_order, "card", "secondary")

        self.order_buttons: dict[str, HoverButton] = {}
        for mode_key in ("normal", "random", "custom"):
            btn = HoverButton(
                order_row,
                text=mode_key,
                command=lambda m=mode_key: self._set_shuffle_order(m),
                palette=self.palette,
                bold=True,
            )
            btn.pack(side="left", padx=(0, 6))
            self.order_buttons[mode_key] = btn
            self._buttons.append(btn)

        # Panel pro custom výběr stylů (zobrazí se při volbě custom)
        self.custom_styles_frame = tk.Frame(
            self.card_shuffle, bg=self.palette.bg_card, pady=6
        )
        self.custom_styles_frame.grid(row=4, column=0, sticky="ew")
        self._reg_frame(self.custom_styles_frame, "card")

        lbl_custom_hint = tk.Label(
            self.custom_styles_frame,
            text="Aktivní styly ve frontě (kliknutím odeber/přidej):",
            font=(METRICS.font_family, METRICS.font_size_small),
            bg=self.palette.bg_card,
            fg=self.palette.text_muted,
            anchor="w",
        )
        lbl_custom_hint.pack(anchor="w", pady=(0, 4))
        self._reg_label(lbl_custom_hint, "card", "muted")

        custom_btns_row = tk.Frame(
            self.custom_styles_frame, bg=self.palette.bg_card
        )
        custom_btns_row.pack(fill="x")
        self._reg_frame(custom_btns_row, "card")

        self.custom_effect_buttons: dict[str, HoverButton] = {}
        for eff_key, eff_label in (*SHAPE_EFFECTS, *OBJECT_EFFECTS):
            btn = HoverButton(
                custom_btns_row,
                text=f"✓ {eff_label}",
                command=lambda k=eff_key: self._toggle_custom_effect(k),
                palette=self.palette,
                font_size=9,
            )
            btn.pack(side="left", padx=(0, 6), pady=2)
            self.custom_effect_buttons[eff_key] = btn
            self._buttons.append(btn)

    def _build_shape_settings_card(self) -> None:
        self.card_shape_settings = self._make_card(
            self.cards_container, "Nastavení tvarových efektů"
        )

        # Gravitace obrysu těla (0 = jen hvězdné nebe, 100 = jen obrys na černé, první hodnota 20)
        self.slider_gravity = SmoothSlider(
            self.card_shape_settings,
            label="Gravitace obrysu těla (0 = nebe, 100 = jen obrys)",
            min_val=0,
            max_val=100,
            initial_val=self.settings.gravity,
            step=1,
            formatter=lambda v: f"{round(v)} %",
            on_change=self._on_gravity_change,
            palette=self.palette,
        )
        self.slider_gravity.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._sliders.append(self.slider_gravity)

        # Počet objektů / hvězd v obraze (0 až 2500, první hodnota 600)
        self.slider_star_count = SmoothSlider(
            self.card_shape_settings,
            label="Počet hvězd v obraze",
            min_val=0,
            max_val=2500,
            initial_val=self.settings.star_count,
            step=25,
            on_change=self._on_star_count_change,
            palette=self.palette,
        )
        self.slider_star_count.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self._sliders.append(self.slider_star_count)

        # Četnost padajících hvězd
        self.slider_shooting_stars = SmoothSlider(
            self.card_shape_settings,
            label="Četnost padajících hvězd",
            min_val=0,
            max_val=100,
            initial_val=self.settings.shooting_stars_freq,
            step=5,
            formatter=lambda v: f"{round(v)} %",
            on_change=self._on_shooting_stars_change,
            palette=self.palette,
        )
        self.slider_shooting_stars.grid(
            row=3, column=0, sticky="ew", pady=(0, 8)
        )
        self._sliders.append(self.slider_shooting_stars)

        # Rychlost problikávání
        self.slider_twinkle = SmoothSlider(
            self.card_shape_settings,
            label="Rychlost problikávání hvězd",
            min_val=0,
            max_val=100,
            initial_val=self.settings.twinkle_speed,
            step=5,
            formatter=lambda v: f"{round(v)} %",
            on_change=self._on_twinkle_change,
            palette=self.palette,
        )
        self.slider_twinkle.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        self._sliders.append(self.slider_twinkle)

        # Síla víření pro Polární prach
        self.slider_nebula_swirl = SmoothSlider(
            self.card_shape_settings,
            label="Síla víření (Polární prach)",
            min_val=0,
            max_val=100,
            initial_val=self.settings.nebula_swirl,
            step=5,
            formatter=lambda v: f"{round(v)} %",
            on_change=self._on_nebula_swirl_change,
            palette=self.palette,
        )
        self.slider_nebula_swirl.grid(row=5, column=0, sticky="ew")
        self._sliders.append(self.slider_nebula_swirl)

    def _build_object_settings_card(self) -> None:
        self.card_object_settings = self._make_card(
            self.cards_container,
            "Nastavení objektového efektu – Prstence tvarů",
        )

        lbl_parts_summary = tk.Label(
            self.card_object_settings,
            text="Hlava: Zaoblené koule · Trup (V): Otočené jehlany · Ruce: Válce · Nohy: Kvádry",
            font=(METRICS.font_family, METRICS.font_size_small),
            bg=self.palette.badge_bg,
            fg=self.palette.badge_text,
            padx=10,
            pady=5,
            anchor="w",
            justify="left",
        )
        lbl_parts_summary.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._reg_label(lbl_parts_summary, "badge", "badge")
        self._wrap_labels.append(lbl_parts_summary)

        # 1. Rychlost obíhání (začíná na 0 = na místě, až 100 = rychle létají)
        self.slider_orbit_speed = SmoothSlider(
            self.card_object_settings,
            label="Rychlost obíhání prstenců (0 = na místě)",
            min_val=0,
            max_val=100,
            initial_val=self.settings.orbit_speed,
            step=1,
            formatter=lambda v: "Stojí (0)" if v < 0.5 else f"{round(v)} %",
            on_change=self._on_orbit_speed_change,
            palette=self.palette,
        )
        self.slider_orbit_speed.grid(
            row=2, column=0, sticky="ew", pady=(0, 8)
        )
        self._sliders.append(self.slider_orbit_speed)

        # 2. Velikost tvarů (určuje i jejich počet; od 60 odemyká Graffiti)
        self.slider_shape_size = SmoothSlider(
            self.card_object_settings,
            label="Velikost tvarů (automaticky upravuje počet)",
            min_val=10,
            max_val=100,
            initial_val=self.settings.shape_size,
            step=1,
            formatter=self._format_shape_size,
            on_change=self._on_shape_size_change,
            palette=self.palette,
        )
        self.slider_shape_size.grid(
            row=3, column=0, sticky="ew", pady=(0, 10)
        )
        self._sliders.append(self.slider_shape_size)

        # 3. Vzor tvarů (Čistá barva, Tahy štětcem, Spirála, Tečky, Graffiti)
        pattern_frame = tk.Frame(
            self.card_object_settings, bg=self.palette.bg_card
        )
        pattern_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self._reg_frame(pattern_frame, "card")

        lbl_pat = tk.Label(
            pattern_frame,
            text="Vzor tvarů:",
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
            bg=self.palette.bg_card,
            fg=self.palette.text_secondary,
            anchor="w",
        )
        lbl_pat.pack(anchor="w", pady=(0, 4))
        self._reg_label(lbl_pat, "card", "secondary")

        pat_btns_row = tk.Frame(pattern_frame, bg=self.palette.bg_card)
        pat_btns_row.pack(fill="x")
        self._reg_frame(pat_btns_row, "card")

        self.pattern_buttons: dict[str, HoverButton] = {}
        for pat_key, pat_label in PATTERN_STYLES:
            btn = HoverButton(
                pat_btns_row,
                text=pat_label,
                command=lambda k=pat_key: self._select_pattern(k),
                palette=self.palette,
                font_size=9,
                bold=True,
                padx=10,
                pady=6,
            )
            btn.pack(side="left", padx=(0, 6), pady=2)
            self.pattern_buttons[pat_key] = btn
            self._buttons.append(btn)

        # 4. Režim barev: Společná pro vše vs. Pokročilé (podle částí těla)
        color_mode_row = tk.Frame(
            self.card_object_settings, bg=self.palette.bg_card
        )
        color_mode_row.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        self._reg_frame(color_mode_row, "card")

        lbl_cmode = tk.Label(
            color_mode_row,
            text="Nastavení barev:",
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
            bg=self.palette.bg_card,
            fg=self.palette.text_secondary,
        )
        lbl_cmode.pack(side="left", padx=(0, 8))
        self._reg_label(lbl_cmode, "card", "secondary")

        self.btn_color_global = HoverButton(
            color_mode_row,
            text="Společná barva",
            command=lambda: self._set_color_mode("global"),
            palette=self.palette,
            font_size=9,
        )
        self.btn_color_global.pack(side="left", padx=(0, 6))
        self._buttons.append(self.btn_color_global)

        self.btn_color_per_part = HoverButton(
            color_mode_row,
            text="Pokročilé (části těla)",
            command=lambda: self._set_color_mode("per_part"),
            palette=self.palette,
            font_size=9,
        )
        self.btn_color_per_part.pack(side="left")
        self._buttons.append(self.btn_color_per_part)

        # Záložky částí těla (zobrazují se v pokročilém režimu)
        self.part_tabs_frame = tk.Frame(
            self.card_object_settings, bg=self.palette.bg_card
        )
        self.part_tabs_frame.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        self._reg_frame(self.part_tabs_frame, "card")

        self.part_tab_buttons: dict[str, HoverButton] = {}
        for part_key, part_label, shape_desc in BODY_PARTS:
            btn = HoverButton(
                self.part_tabs_frame,
                text=f"{part_label} ({shape_desc.split()[-1]})",
                command=lambda k=part_key: self._select_part_tab(k),
                palette=self.palette,
                font_size=9,
                padx=8,
                pady=4,
            )
            btn.pack(side="left", padx=(0, 5), pady=2)
            self.part_tab_buttons[part_key] = btn
            self._buttons.append(btn)

        # Výběr Primární a Sekundární barvy z 10 presetů
        self.swatches_container = tk.Frame(
            self.card_object_settings, bg=self.palette.bg_card
        )
        self.swatches_container.grid(
            row=7, column=0, sticky="ew", pady=(0, 10)
        )
        self._reg_frame(self.swatches_container, "card")

        self.primary_swatch_btns = self._build_color_swatch_row(
            self.swatches_container,
            "Primární barva (podklad tvaru):",
            is_primary=True,
        )
        self.secondary_swatch_btns = self._build_color_swatch_row(
            self.swatches_container,
            "Sekundární barva (štětec / spirála / tečky):",
            is_primary=False,
        )

        # 5. Sekce Graffiti editoru (plátno se zaoblenými rohy a čárkovaným okrajem)
        self.graffiti_section = tk.Frame(
            self.card_object_settings, bg=self.palette.bg_card
        )
        self.graffiti_section.grid(row=8, column=0, sticky="ew", pady=(4, 0))
        self.graffiti_section.columnconfigure(0, weight=1)
        self._reg_frame(self.graffiti_section, "card")

        graf_header = tk.Frame(self.graffiti_section, bg=self.palette.bg_card)
        graf_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._reg_frame(graf_header, "card")

        lbl_graf = tk.Label(
            graf_header,
            text="Graffiti editor (1. Barva · 2. Guma · 3. Velikost):",
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
            bg=self.palette.bg_card,
            fg=self.palette.text_primary,
        )
        lbl_graf.pack(side="left")
        self._reg_label(lbl_graf, "card", "primary")

        self.btn_graf_clear = HoverButton(
            graf_header,
            text="Vymazat plátno",
            command=lambda: self.graffiti_widget.clear_strokes(),
            palette=self.palette,
            font_size=9,
            padx=8,
            pady=3,
        )
        self.btn_graf_clear.pack(side="right")
        self._buttons.append(self.btn_graf_clear)

        self.btn_graf_eraser = HoverButton(
            graf_header,
            text="🧽 Guma",
            command=self._toggle_graffiti_eraser,
            palette=self.palette,
            font_size=9,
            bold=True,
            padx=10,
            pady=3,
        )
        self.btn_graf_eraser.pack(side="right", padx=(0, 6))
        self._buttons.append(self.btn_graf_eraser)

        # Barvy štětce pro Graffiti
        graf_colors_row = tk.Frame(
            self.graffiti_section, bg=self.palette.bg_card
        )
        graf_colors_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self._reg_frame(graf_colors_row, "card")

        self.graf_color_btns: dict[str, tk.Label] = {}
        for preset in PRESET_COLORS:
            swatch = tk.Label(
                graf_colors_row,
                text="  ",
                bg=preset.hex_code,
                width=2,
                height=1,
                cursor="hand2",
                relief="solid",
                bd=1,
            )
            swatch.pack(side="left", padx=(0, 5), pady=2)
            swatch.bind(
                "<Button-1>",
                lambda _e, k=preset.key: self._select_graffiti_color(k),
            )
            self.graf_color_btns[preset.key] = swatch

        # Posuvník velikosti tahu v Graffiti
        self.slider_graf_size = SmoothSlider(
            self.graffiti_section,
            label="Velikost štětce / gumy",
            min_val=2,
            max_val=28,
            initial_val=self.settings.graffiti_brush_size,
            step=1,
            formatter=lambda v: f"{round(v)} px",
            on_change=self._on_graf_size_change,
            palette=self.palette,
        )
        self.slider_graf_size.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self._sliders.append(self.slider_graf_size)

        # Samotné kreslicí plátno se zaoblenými rohy a čárkovaným okrajem
        self.graffiti_widget = GraffitiCanvasWidget(
            self.graffiti_section,
            settings=self.settings,
            on_stroke_updated=self._on_graffiti_stroke_updated,
            palette=self.palette,
        )
        self.graffiti_widget.grid(row=3, column=0, sticky="ew")

    def _build_color_swatch_row(
        self, parent: tk.Widget, title: str, is_primary: bool
    ) -> dict[str, tk.Label]:
        block = tk.Frame(parent, bg=self.palette.bg_card)
        block.pack(fill="x", pady=(0, 6))
        self._reg_frame(block, "card")

        lbl = tk.Label(
            block,
            text=title,
            font=(METRICS.font_family, METRICS.font_size_small),
            bg=self.palette.bg_card,
            fg=self.palette.text_secondary,
            anchor="w",
        )
        lbl.pack(anchor="w", pady=(0, 3))
        self._reg_label(lbl, "card", "secondary")

        row = tk.Frame(block, bg=self.palette.bg_card)
        row.pack(fill="x")
        self._reg_frame(row, "card")

        btns: dict[str, tk.Label] = {}
        for preset in PRESET_COLORS:
            sw = tk.Label(
                row,
                text=preset.label[:3],
                font=(METRICS.font_family, 8, "bold"),
                bg=preset.hex_code,
                fg="#111827"
                if preset.key in ("white", "yellow", "light_green", "light_blue")
                else "#FFFFFF",
                padx=6,
                pady=3,
                cursor="hand2",
                bd=2,
                relief="flat",
            )
            sw.pack(side="left", padx=(0, 4), pady=2)
            sw.bind(
                "<Button-1>",
                lambda _e, k=preset.key, prim=is_primary: self._select_shape_color(
                    k, prim
                ),
            )
            btns[preset.key] = sw
        return btns

    # ------------------------------------------------------------------
    # Formátování a obsluha událostí nastavení
    # ------------------------------------------------------------------
    @staticmethod
    def _format_duration(seconds: float) -> str:
        s = round(seconds)
        if s < 60:
            return f"{s} s"
        mins = s // 60
        rem = s % 60
        return f"{mins} min" if rem == 0 else f"{mins} min {rem:02d} s"

    def _format_shape_size(self, val: float) -> str:
        self.settings.shape_size = round(val)
        cnt = self.settings.computed_shape_count
        unlock = (
            " · Graffiti odemknuto"
            if self.settings.is_graffiti_unlocked
            else f" · Graffiti od {GRAFFITI_UNLOCK_SIZE}"
        )
        return f"{round(val)} ({cnt} tvarů{unlock})"

    def select_effect(self, effect_key: str) -> None:
        if effect_key in ALL_EFFECT_KEYS:
            self.settings.active_effect = effect_key
            self.store.save()
            self.refresh_all_states()

    def _toggle_shape_shuffle(self) -> None:
        self.settings.shape_shuffle = not self.settings.shape_shuffle
        self.store.save()
        self.refresh_all_states()

    def _toggle_object_shuffle(self) -> None:
        self.settings.object_shuffle = not self.settings.object_shuffle
        self.store.save()
        self.refresh_all_states()

    def _on_shuffle_interval_change(self, val: float) -> None:
        self.settings.shuffle_interval_s = round(val)
        self.store.save()

    def _on_shuffle_transition_change(self, val: float) -> None:
        self.settings.shuffle_transition_s = round(float(val), 2)
        self.store.save()

    def _set_shuffle_order(self, order: str) -> None:
        self.settings.shuffle_order = order
        self.store.save()
        self.refresh_all_states()

    def _toggle_custom_effect(self, eff_key: str) -> None:
        enabled = list(self.settings.custom_enabled_effects)
        if eff_key in enabled:
            if len(enabled) > 1:
                enabled.remove(eff_key)
        else:
            enabled.append(eff_key)
        self.settings.custom_enabled_effects = enabled
        self.store.save()
        self.refresh_all_states()

    def _on_gravity_change(self, val: float) -> None:
        self.settings.gravity = round(val)
        self.store.save()

    def _on_star_count_change(self, val: float) -> None:
        self.settings.star_count = round(val)
        self.store.save()

    def _on_shooting_stars_change(self, val: float) -> None:
        self.settings.shooting_stars_freq = round(val)
        self.store.save()

    def _on_twinkle_change(self, val: float) -> None:
        self.settings.twinkle_speed = round(val)
        self.store.save()

    def _on_nebula_swirl_change(self, val: float) -> None:
        self.settings.nebula_swirl = round(val)
        self.store.save()

    def _on_orbit_speed_change(self, val: float) -> None:
        self.settings.orbit_speed = round(val)
        self.store.save()

    def _on_shape_size_change(self, val: float) -> None:
        self.settings.shape_size = round(val)
        if (
            self.settings.pattern_style == "graffiti"
            and not self.settings.is_graffiti_unlocked
        ):
            self.settings.pattern_style = "solid"
        self.store.save()
        self.refresh_all_states()

    def _select_pattern(self, pattern_key: str) -> None:
        if pattern_key == "graffiti" and not self.settings.is_graffiti_unlocked:
            return
        self.settings.pattern_style = pattern_key
        self.store.save()
        self.refresh_all_states()

    def _set_color_mode(self, mode: str) -> None:
        self.settings.color_mode = mode
        self.store.save()
        self.refresh_all_states()

    def _select_part_tab(self, part_key: str) -> None:
        self._selected_part_tab = part_key
        self.refresh_all_states()

    def _select_shape_color(self, color_key: str, is_primary: bool) -> None:
        if self.settings.color_mode == "per_part":
            entry = self.settings.part_colors.setdefault(
                self._selected_part_tab,
                {"primary": "light_blue", "secondary": "white"},
            )
            if is_primary:
                entry["primary"] = color_key
            else:
                entry["secondary"] = color_key
        else:
            if is_primary:
                self.settings.primary_color = color_key
            else:
                self.settings.secondary_color = color_key
        self.store.save()
        self.refresh_all_states()

    def _select_graffiti_color(self, color_key: str) -> None:
        self.settings.graffiti_brush_color = color_key
        self.settings.graffiti_eraser = False
        if self.settings.is_graffiti_unlocked:
            self.settings.pattern_style = "graffiti"
        self.store.save()
        self.refresh_all_states()

    def _toggle_graffiti_eraser(self) -> None:
        self.settings.graffiti_eraser = not self.settings.graffiti_eraser
        self.store.save()
        self.refresh_all_states()

    def _on_graf_size_change(self, val: float) -> None:
        self.settings.graffiti_brush_size = round(val)
        self.store.save()

    def _on_graffiti_stroke_updated(self) -> None:
        if self.settings.is_graffiti_unlocked:
            self.settings.pattern_style = "graffiti"
        self.engine.notify_graffiti_changed()
        self.store.save()
        self.refresh_all_states()

    # ------------------------------------------------------------------
    # Aktualizace stavů prvků v UI
    # ------------------------------------------------------------------
    def refresh_all_states(self) -> None:
        s = self.settings

        # Tlačítka efektů a shuffle
        self.btn_shape_shuffle.set_variant(
            "active" if s.shape_shuffle else "secondary"
        )
        self.btn_object_shuffle.set_variant(
            "active" if s.object_shuffle else "secondary"
        )

        for k, btn in self.shape_effect_buttons.items():
            btn.set_variant(
                "active" if s.active_effect == k else "secondary"
            )
        for k, btn in self.object_effect_buttons.items():
            btn.set_variant(
                "active" if s.active_effect == k else "secondary"
            )

        # Pořadí shuffle (normal, random, custom)
        for k, btn in self.order_buttons.items():
            btn.set_variant("active" if s.shuffle_order == k else "secondary")

        if s.shuffle_order == "custom":
            self.custom_styles_frame.grid()
        else:
            self.custom_styles_frame.grid_remove()

        all_labels = dict((*SHAPE_EFFECTS, *OBJECT_EFFECTS))
        for k, btn in self.custom_effect_buttons.items():
            on = k in s.custom_enabled_effects
            btn.configure(text=f"{'✓' if on else '✕'} {all_labels[k]}")
            btn.set_variant("active" if on else "secondary")

        # Vzor tvarů a Graffiti zámek
        graf_btn = self.pattern_buttons["graffiti"]
        if s.is_graffiti_unlocked:
            graf_btn.configure(text="Graffiti")
            graf_btn.set_disabled(False)
        else:
            graf_btn.configure(text=f"🔒 Graffiti (od {GRAFFITI_UNLOCK_SIZE})")
            graf_btn.set_disabled(True)

        for k, btn in self.pattern_buttons.items():
            if k == "graffiti" and not s.is_graffiti_unlocked:
                continue
            btn.set_variant("active" if s.pattern_style == k else "secondary")

        # Režim barev (Společná vs Pokročilé po částech těla)
        self.btn_color_global.set_variant(
            "active" if s.color_mode == "global" else "secondary"
        )
        self.btn_color_per_part.set_variant(
            "active" if s.color_mode == "per_part" else "secondary"
        )

        if s.color_mode == "per_part":
            self.part_tabs_frame.grid()
            for pk, btn in self.part_tab_buttons.items():
                btn.set_variant(
                    "active" if pk == self._selected_part_tab else "secondary"
                )
            active_prim = s.part_colors.get(self._selected_part_tab, {}).get(
                "primary", s.primary_color
            )
            active_sec = s.part_colors.get(self._selected_part_tab, {}).get(
                "secondary", s.secondary_color
            )
        else:
            self.part_tabs_frame.grid_remove()
            active_prim = s.primary_color
            active_sec = s.secondary_color

        for k, sw in self.primary_swatch_btns.items():
            sw.configure(
                relief="solid" if k == active_prim else "flat",
                highlightbackground=self.palette.text_primary,
                highlightthickness=2 if k == active_prim else 0,
            )
        for k, sw in self.secondary_swatch_btns.items():
            sw.configure(
                relief="solid" if k == active_sec else "flat",
                highlightbackground=self.palette.text_primary,
                highlightthickness=2 if k == active_sec else 0,
            )

        # Graffiti nástroje
        self.btn_graf_eraser.set_variant(
            "active" if s.graffiti_eraser else "secondary"
        )
        for k, sw in self.graf_color_btns.items():
            selected = (k == s.graffiti_brush_color) and (not s.graffiti_eraser)
            sw.configure(
                highlightbackground=self.palette.text_primary,
                highlightthickness=2 if selected else 0,
            )
        self.graffiti_widget.redraw()

        # Odznak zdroje
        self.engine.sync_source(s)
        self.lbl_source_badge.configure(
            text=f"Zdroj: {self.engine.last_source_label}"
        )

        # Hero tlačítko výstupu
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        ):
            self.btn_play_output.configure(text="●  ŽIVÝ VÝSTUP AKTIVNÍ")
        else:
            self.btn_play_output.configure(text="▶  SPUSTIT ŽIVÝ VÝSTUP")

    # ------------------------------------------------------------------
    # Přepínání light / dark tématu
    # ------------------------------------------------------------------
    def toggle_theme(self) -> None:
        next_mode = "light" if self.settings.theme_mode == "dark" else "dark"
        self.apply_theme(next_mode, save=True)

    def apply_theme(self, mode: str, save: bool = True) -> None:
        self.settings.theme_mode = "light" if mode == "light" else "dark"
        self.palette = get_palette(self.settings.theme_mode)
        p = self.palette

        self.root.configure(bg=p.bg_primary)
        self.scroll_canvas.configure(bg=p.bg_primary)
        self.btn_theme.configure(text=f"Režim: {self.settings.theme_mode}")

        for widget, role in self._themed_frames:
            if not widget.winfo_exists():
                continue
            bg = p.bg_primary if role == "primary" else p.bg_card
            widget.configure(bg=bg)
            if int(widget.cget("highlightthickness")) > 0:
                widget.configure(highlightbackground=p.border)

        for lbl, bg_role, fg_role in self._themed_labels:
            if not lbl.winfo_exists():
                continue
            bg = (
                p.badge_bg
                if bg_role == "badge"
                else (p.bg_primary if bg_role == "primary" else p.bg_card)
            )
            fg = (
                p.badge_text
                if fg_role == "badge"
                else (
                    p.text_primary
                    if fg_role == "primary"
                    else (
                        p.text_secondary
                        if fg_role == "secondary"
                        else p.text_muted
                    )
                )
            )
            lbl.configure(bg=bg, fg=fg)

        for btn in self._buttons:
            if btn.winfo_exists():
                btn.apply_palette(p)

        for slider in self._sliders:
            if slider.winfo_exists():
                slider.apply_palette(p)

        self.graffiti_widget.apply_palette(p)
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        ):
            self.output_window.btn_fullscreen.apply_palette(p)

        self.refresh_all_states()
        if save:
            self.store.save()

    # ------------------------------------------------------------------
    # Dynamické a responzivní rozložení při změně velikosti okna
    # ------------------------------------------------------------------
    def _on_root_configure(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        self._relayout_cards(event.width)

    def _on_scroll_canvas_configure(self, event: tk.Event) -> None:
        self.scroll_canvas.itemconfigure(
            self._cards_window_id, width=event.width
        )
        self._relayout_cards(event.width)

    def _relayout_cards(self, width: int) -> None:
        cols = 2 if width >= METRICS.compact_breakpoint else 1
        wrap_px = max(200, (width // cols) - 64)
        for lbl in self._wrap_labels:
            if lbl.winfo_exists():
                lbl.configure(wraplength=wrap_px)

        if cols == self._current_columns:
            return
        self._current_columns = cols

        for c in range(2):
            self.cards_container.columnconfigure(c, weight=0)

        if cols == 2:
            self.cards_container.columnconfigure(0, weight=1, uniform="col")
            self.cards_container.columnconfigure(1, weight=1, uniform="col")

            self.card_shape_effects.grid(
                row=0, column=0, sticky="nsew", padx=(0, 6), pady=6
            )
            self.card_object_effects.grid(
                row=0, column=1, sticky="nsew", padx=(6, 0), pady=6
            )
            self.card_shuffle.grid(
                row=1, column=0, columnspan=2, sticky="ew", pady=6
            )
            self.card_shape_settings.grid(
                row=2, column=0, sticky="nsew", padx=(0, 6), pady=6
            )
            self.card_object_settings.grid(
                row=2, column=1, sticky="nsew", padx=(6, 0), pady=6
            )
        else:
            self.cards_container.columnconfigure(0, weight=1)
            self.card_shape_effects.grid(
                row=0, column=0, columnspan=1, sticky="ew", padx=0, pady=5
            )
            self.card_object_effects.grid(
                row=1, column=0, columnspan=1, sticky="ew", padx=0, pady=5
            )
            self.card_shuffle.grid(
                row=2, column=0, columnspan=1, sticky="ew", padx=0, pady=5
            )
            self.card_shape_settings.grid(
                row=3, column=0, columnspan=1, sticky="ew", padx=0, pady=5
            )
            self.card_object_settings.grid(
                row=4, column=0, columnspan=1, sticky="ew", padx=0, pady=5
            )

    def _on_mousewheel(self, event: tk.Event) -> None:
        delta = -1 * int(event.delta / 120) if event.delta else 0
        if delta != 0:
            self.scroll_canvas.yview_scroll(delta, "units")

    # ------------------------------------------------------------------
    # Dialogy: Nahrát CSV (3 ukázkové náhledy + průzkumník), Kamera, Reset
    # ------------------------------------------------------------------
    def open_csv_dialog(self) -> tk.Toplevel:
        p = self.palette
        dlg = tk.Toplevel(self.root)
        dlg.title("Nahrát CSV – Ukázkové pózy nebo vlastní soubor")
        dlg.geometry("620x390")
        dlg.minsize(480, 340)
        dlg.configure(bg=p.bg_primary, padx=18, pady=16)
        dlg.transient(self.root)

        lbl_head = tk.Label(
            dlg,
            text="Vyber jednu z 3 ukázkových póz člověka, nebo nahraj vlastní .csv soubor:",
            font=(METRICS.font_family, METRICS.font_size_section, "bold"),
            bg=p.bg_primary,
            fg=p.text_primary,
            anchor="w",
        )
        lbl_head.pack(fill="x", pady=(0, 12))

        samples_row = tk.Frame(dlg, bg=p.bg_primary)
        samples_row.pack(fill="both", expand=True, pady=(0, 14))
        for idx in range(len(SAMPLE_POSES)):
            samples_row.columnconfigure(idx, weight=1)

        for idx, pose in enumerate(SAMPLE_POSES):
            card = tk.Frame(
                samples_row,
                bg=p.bg_card,
                padx=10,
                pady=10,
                highlightbackground=p.accent
                if (
                    self.settings.source_type == "sample"
                    and self.settings.sample_id == pose.sample_id
                )
                else p.border,
                highlightthickness=2,
                cursor="hand2",
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=5)

            ppm = render_sample_thumbnail_ppm(pose.sample_id, 156, 116)
            photo = tk.PhotoImage(width=156, height=116, data=ppm, format="PPM")
            self._thumb_images[pose.sample_id] = photo

            img_lbl = tk.Label(
                card, image=photo, bg=p.bg_card, bd=0, cursor="hand2"
            )
            img_lbl.pack(pady=(0, 8))

            t_lbl = tk.Label(
                card,
                text=pose.title,
                font=(METRICS.font_family, METRICS.font_size_body, "bold"),
                bg=p.bg_card,
                fg=p.text_primary,
                cursor="hand2",
            )
            t_lbl.pack()

            s_lbl = tk.Label(
                card,
                text=pose.subtitle,
                font=(METRICS.font_family, METRICS.font_size_small),
                bg=p.bg_card,
                fg=p.text_secondary,
                wraplength=165,
                cursor="hand2",
            )
            s_lbl.pack(pady=(2, 6))

            def _pick_sample(sid: str = pose.sample_id) -> None:
                self.activate_sample_pose(sid)
                if dlg.winfo_exists():
                    dlg.destroy()

            for w in (card, img_lbl, t_lbl, s_lbl):
                w.bind("<Button-1>", lambda _e, fn=_pick_sample: fn())

        bottom_row = tk.Frame(dlg, bg=p.bg_primary)
        bottom_row.pack(fill="x")

        btn_browse = HoverButton(
            bottom_row,
            text="📁  Nahrát vlastní .csv z počítače...",
            command=lambda: self._browse_csv_file(dlg),
            palette=p,
            variant="active",
            font_size=11,
            bold=True,
            padx=16,
            pady=9,
        )
        btn_browse.pack(side="left")

        btn_close = HoverButton(
            bottom_row,
            text="Zavřít",
            command=dlg.destroy,
            palette=p,
            variant="secondary",
        )
        btn_close.pack(side="right")
        return dlg

    def activate_sample_pose(self, sample_id: str) -> None:
        self.settings.source_type = "sample"
        self.settings.sample_id = sample_id
        self.store.save()
        self.engine.sync_source(self.settings)
        self.refresh_all_states()

    def load_csv_path(self, path: str | Path) -> bool:
        with contextlib.suppress(OSError, ValueError):
            self.settings.source_type = "csv"
            self.settings.csv_path = str(Path(path).resolve())
            self.engine.sync_source(self.settings)
            if self.settings.source_type == "csv":
                self.store.save()
                self.refresh_all_states()
                return True
        return False

    def _browse_csv_file(self, parent_dlg: tk.Toplevel | None = None) -> None:
        file_path = filedialog.askopenfilename(
            parent=parent_dlg or self.root,
            title="Vyber hloubkový soubor CSV",
            filetypes=[("CSV soubory", "*.csv")],
        )
        if file_path:
            self.load_csv_path(file_path)
            if parent_dlg is not None and parent_dlg.winfo_exists():
                parent_dlg.destroy()

    def open_camera_dialog(self) -> tk.Toplevel:
        p = self.palette
        dlg = tk.Toplevel(self.root)
        dlg.title("Vybrat kameru – Připojené porty zařízení")
        dlg.geometry("520x320")
        dlg.minsize(420, 260)
        dlg.configure(bg=p.bg_primary, padx=18, pady=16)
        dlg.transient(self.root)

        lbl_head = tk.Label(
            dlg,
            text="Vyber port připojené kamery (okamžitě spustí přehrávání s efektem):",
            font=(METRICS.font_family, METRICS.font_size_section, "bold"),
            bg=p.bg_primary,
            fg=p.text_primary,
            anchor="w",
        )
        lbl_head.pack(fill="x", pady=(0, 12))

        ports_frame = tk.Frame(dlg, bg=p.bg_primary)
        ports_frame.pack(fill="both", expand=True, pady=(0, 12))

        cameras = discover_camera_ports()
        for cam in cameras:
            is_curr = (
                self.settings.source_type == "camera"
                and self.settings.camera_port == cam.port
            )
            btn = HoverButton(
                ports_frame,
                text=f"🎥  {cam.label}",
                command=lambda port=cam.port: self._pick_camera_port(port, dlg),
                palette=p,
                variant="active" if is_curr else "secondary",
                font_size=10,
                bold=True,
                pady=10,
            )
            btn.pack(fill="x", pady=4)

        btn_close = HoverButton(
            dlg, text="Zavřít", command=dlg.destroy, palette=p
        )
        btn_close.pack(anchor="e")
        return dlg

    def _pick_camera_port(
        self, port: int, dlg: tk.Toplevel | None = None
    ) -> None:
        self.settings.source_type = "camera"
        self.settings.camera_port = port
        self.store.save()
        self.engine.sync_source(self.settings)
        self.refresh_all_states()
        if dlg is not None and dlg.winfo_exists():
            dlg.destroy()
        if (
            self.output_window is None
            or not self.output_window.window.winfo_exists()
        ):
            self.open_output_window()

    def open_reset_dialog(self) -> tk.Toplevel:
        p = self.palette
        dlg = tk.Toplevel(self.root)
        dlg.title("Resetovat možnosti")
        dlg.geometry("420x190")
        dlg.resizable(False, False)
        dlg.configure(bg=p.bg_primary, padx=20, pady=18)
        dlg.transient(self.root)

        lbl = tk.Label(
            dlg,
            text="Opravdu chceš vrátit všechna nastavení na jejich výchozí (první) hodnotu?",
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
            bg=p.bg_primary,
            fg=p.text_primary,
            wraplength=370,
            justify="left",
        )
        lbl.pack(fill="x", pady=(4, 22))

        btn_row = tk.Frame(dlg, bg=p.bg_primary)
        btn_row.pack(fill="x")

        btn_confirm = HoverButton(
            btn_row,
            text="✓  Potvrdit reset",
            command=lambda: self.confirm_reset(dlg),
            palette=p,
            variant="danger",
            bold=True,
            padx=16,
            pady=8,
        )
        btn_confirm.pack(side="left")

        btn_cancel = HoverButton(
            btn_row,
            text="Zrušit",
            command=dlg.destroy,
            palette=p,
            variant="secondary",
            padx=16,
            pady=8,
        )
        btn_cancel.pack(side="right")
        return dlg

    def confirm_reset(self, dlg: tk.Toplevel | None = None) -> None:
        self.settings = self.store.reset_to_defaults()
        self.graffiti_widget.settings = self.settings
        self.engine.notify_graffiti_changed()

        # Synchronizace všech posuvníků na první hodnoty
        self.slider_shuffle_interval.set_value(
            self.settings.shuffle_interval_s, notify=False
        )
        self.slider_shuffle_transition.set_value(
            self.settings.shuffle_transition_s, notify=False
        )
        self.slider_gravity.set_value(self.settings.gravity, notify=False)
        self.slider_star_count.set_value(
            self.settings.star_count, notify=False
        )
        self.slider_shooting_stars.set_value(
            self.settings.shooting_stars_freq, notify=False
        )
        self.slider_twinkle.set_value(
            self.settings.twinkle_speed, notify=False
        )
        self.slider_nebula_swirl.set_value(
            self.settings.nebula_swirl, notify=False
        )
        self.slider_orbit_speed.set_value(
            self.settings.orbit_speed, notify=False
        )
        self.slider_shape_size.set_value(
            self.settings.shape_size, notify=False
        )
        self.slider_graf_size.set_value(
            self.settings.graffiti_brush_size, notify=False
        )

        self.apply_theme(self.settings.theme_mode, save=False)
        self.refresh_all_states()
        if dlg is not None and dlg.winfo_exists():
            dlg.destroy()

    # ------------------------------------------------------------------
    # Správa výstupního okna a hlavní smyčka
    # ------------------------------------------------------------------
    def toggle_output_window(self) -> OutputDisplayWindow:
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        ):
            self.output_window.window.lift()
            self.output_window.window.focus_force()
            return self.output_window
        return self.open_output_window()

    def open_output_window(self) -> OutputDisplayWindow:
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        ):
            return self.output_window

        self.output_window = OutputDisplayWindow(
            root=self.root,
            engine=self.engine,
            settings_provider=lambda: self.settings,
            palette_provider=lambda: self.palette,
            on_closed=self._on_output_closed,
        )
        self.refresh_all_states()
        return self.output_window

    def _on_output_closed(self) -> None:
        self.output_window = None
        if self.root.winfo_exists():
            self.refresh_all_states()

    def _schedule_loop(self) -> None:
        if not self.root.winfo_exists():
            return
        now = time.perf_counter()
        elapsed_ms = (now - self._started_at) * 1000.0
        delta_ms = max(1.0, (now - self._last_tick) * 1000.0)
        self._last_tick = now
        inst_fps = 1000.0 / max(1.0, delta_ms)
        self._fps_estimate = self._fps_estimate * 0.9 + inst_fps * 0.1

        active_eff = self.settings.active_effect
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        ):
            active_eff = self.output_window.render_tick(elapsed_ms, delta_ms)

        # Aktualizace stavové patičky jednou za ~20 snímků
        if int(elapsed_ms // 16) % 20 == 0:
            mem_mb = self._process.memory_info().rss / (1024 * 1024)
            cpu_pct = self._process.cpu_percent(interval=None)
            eff_names = dict((*SHAPE_EFFECTS, *OBJECT_EFFECTS))
            shuffle_tag = (
                " [shuffle]"
                if (self.settings.shape_shuffle or self.settings.object_shuffle)
                else ""
            )
            self.lbl_status.configure(
                text=f"Aktivní efekt: {eff_names.get(active_eff, active_eff)}{shuffle_tag}  |  {self.engine.last_source_label}"
            )
            self.lbl_perf.configure(
                text=f"RAM: {mem_mb:.0f} MB  |  CPU: {cpu_pct:.1f} %  |  FPS: {min(60.0, self._fps_estimate):.0f}"
            )

        self.root.after(16, self._schedule_loop)

    def shutdown(self) -> None:
        self.store.save()
        if self.output_window is not None:
            self.output_window.close()
        self.engine.close()
        if self.root.winfo_exists():
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
