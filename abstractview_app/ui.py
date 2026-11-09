"""Responzivní panel AbstractView s pouští, sklem a hologramem Fištróna."""

from __future__ import annotations

import base64
import contextlib
import ctypes
import ctypes.wintypes
import math
import queue
import sys
import threading
import time
import tkinter as tk
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog

import cv2
import numpy as np
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
from abstractview_app.scene import (
    FistronCompanion,
    clear_tk_photo_cache,
    render_aa_3d_button_photo,
    render_aa_color_swatch_photo,
    render_aa_pill_button_photo,
    render_aa_rounded_panel_photo,
    render_aa_slider_photo,
    render_complete_scene_photo,
)
from abstractview_app.theme import (
    METRICS,
    PRESET_COLOR_MAP,
    PRESET_COLORS,
    ThemePalette,
    get_palette,
    hex_to_rgb,
    interpolate_palette,
    lerp_rgb,
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


def center_window_on_screen(win: tk.Toplevel | tk.Tk, width: int, height: int) -> None:
    """Vycentruje dialogové okno přesně doprostřed obrazovky."""
    win.update_idletasks()
    sw = max(width, win.winfo_screenwidth())
    sh = max(height, win.winfo_screenheight())
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


class RoundedPanelFrame(tk.Frame):
    """Nativně oříznutý panel, jehož rohy se přesouvají spolu s obsahem."""

    def __init__(self, master: tk.Widget, **kwargs: object) -> None:
        super().__init__(master, **kwargs)
        self._region_size: tuple[int, int] | None = None
        self.bind("<Configure>", self._update_round_region, add="+")

    def _update_round_region(self, event: tk.Event) -> None:
        size = (int(event.width), int(event.height))
        if sys.platform != "win32" or size == self._region_size or min(size) < 8:
            return
        gdi32 = ctypes.windll.gdi32
        user32 = ctypes.windll.user32
        gdi32.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
        gdi32.CreateRoundRectRgn.restype = ctypes.c_void_p
        user32.SetWindowRgn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        user32.SetWindowRgn.restype = ctypes.c_int
        region = gdi32.CreateRoundRectRgn(0, 0, size[0] + 1, size[1] + 1, 38, 38)
        if region:
            if user32.SetWindowRgn(ctypes.c_void_p(self.winfo_id()), region, 1):
                self._region_size = size
            else:
                gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
                gdi32.DeleteObject(region)


class DayNightSwitch(tk.Canvas):
    """Přepínač s vyhlazenou kresbou slunce a měsíce."""

    def __init__(self, master: tk.Widget, command: Callable[[], None], palette: ThemePalette) -> None:
        super().__init__(master, width=186, height=38, bg=palette.bg_card, bd=0,
                         highlightthickness=0, cursor="hand2")
        self._command = command
        self._palette = palette
        self._progress = 0.0
        self._photo: tk.PhotoImage | None = None
        self.bind("<Button-1>", lambda _event: self._command())
        self.bind("<Configure>", lambda _event: self.redraw())
        self.redraw()

    def set_progress(self, progress: float, palette: ThemePalette) -> None:
        progress = max(0.0, min(1.0, float(progress)))
        if abs(progress - self._progress) < .001 and palette == self._palette:
            return
        self._progress = progress
        self._palette = palette
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        p = self._progress
        bg = self._palette.bg_card
        self.configure(bg=bg)

        scale = 4
        width, height = 92, 38
        image = np.empty((height * scale, width * scale, 3), dtype=np.uint8)
        image[:] = hex_to_rgb(bg)
        track = lerp_rgb((28, 48, 83), (239, 210, 167), p)
        edge = lerp_rgb((88, 128, 186), (202, 150, 97), p)
        orb = lerp_rgb((237, 244, 255), (255, 211, 75), p)
        start = (20 * scale, 19 * scale)
        end = (72 * scale, 19 * scale)
        cv2.line(image, start, end, edge, 29 * scale, cv2.LINE_AA)
        cv2.line(image, start, end, track, 26 * scale, cv2.LINE_AA)
        x = (72 - 52 * p) * scale
        y = 19 * scale
        sun = max(0.0, min(1.0, (p - .28) / .55))
        if sun > .05:
            for index in range(8):
                angle = index * math.tau / 8 + p * math.pi
                inner = (x + math.cos(angle) * 11 * scale,
                         y + math.sin(angle) * 11 * scale)
                outer = (x + math.cos(angle) * (11 + 3 * sun) * scale,
                         y + math.sin(angle) * (11 + 3 * sun) * scale)
                cv2.line(image, tuple(map(round, inner)), tuple(map(round, outer)),
                         orb, max(1, round(2 * sun * scale)), cv2.LINE_AA)
        cv2.circle(image, (round(x), y), 9 * scale, edge, -1, cv2.LINE_AA)
        cv2.circle(image, (round(x), y), 8 * scale, orb, -1, cv2.LINE_AA)
        moon = max(0.0, min(1.0, (0.72 - p) / .55))
        if moon > .05:
            cv2.circle(image, (round(x + 4 * moon * scale),
                               round(y - 3 * moon * scale)),
                       round(7 * moon * scale), track, -1, cv2.LINE_AA)
        image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        ok, png = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if ok:
            self._photo = tk.PhotoImage(data=base64.b64encode(png.tobytes()), format="png")
            self.create_image(47, 0, anchor="nw", image=self._photo)
        self.create_text(21, 19, text="day", fill=self._palette.text_primary if p > .5 else self._palette.text_muted,
                         font=(METRICS.font_family, 10, "bold"))
        self.create_text(162, 19, text="night", fill=self._palette.text_primary if p < .5 else self._palette.text_muted,
                         font=(METRICS.font_family, 10, "bold"))


class HoverButton(tk.Label):
    """Vyhlazené kulaté (pill) tlačítko s čitelným tučným písmem a podporou hoveru."""

    def __init__(
        self,
        master: tk.Widget,
        text: str,
        command: Callable[[], None],
        palette: ThemePalette,
        variant: str = "secondary",
        font_size: int = METRICS.font_size_body,
        bold: bool = True,
        padx: int = 14,
        pady: int = 7,
    ) -> None:
        weight = "bold" if bold else "normal"
        super().__init__(
            master,
            text=text,
            font=(METRICS.font_family, font_size, weight),
            compound="center",
            padx=0,
            pady=0,
            cursor="hand2",
            bd=0,
            highlightthickness=0,
        )
        self._command = command
        self._palette = palette
        self._variant = variant
        self._hovered = False
        self._disabled = False
        self._pad_x = padx
        self._pad_y = pady
        self._pill_photo: tk.PhotoImage | None = None

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.apply_palette(palette)

    @property
    def variant(self) -> str:
        return self._variant

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self._refresh_visual()

    def set_disabled(self, disabled: bool) -> None:
        self._disabled = disabled
        self.configure(cursor="arrow" if disabled else "hand2")
        self._refresh_visual()

    def set_text(self, text: str) -> None:
        if self.cget("text") != text:
            self.configure(text=text)
            self._refresh_visual()

    def apply_palette(self, palette: ThemePalette) -> None:
        self._palette = palette
        self._refresh_visual()

    def _refresh_visual(self) -> None:
        p = self._palette
        parent_bg = p.bg_card
        with contextlib.suppress(tk.TclError):
            parent_bg = str(self.master.cget("bg"))

        if self._disabled:
            bg = p.bg_elevated
            fg = p.text_muted
            border = p.border
        elif self._variant == "shuffle":
            bg = p.shuffle_hover if self._hovered else p.shuffle_bg
            fg = "#FFFFFF"
            border = "#C4B5FD"
        elif self._variant == "active":
            bg = p.accent_hover if self._hovered else p.accent
            fg = p.accent_text
            border = p.border_focus
        elif self._variant == "inspect":
            bg = p.bg_hover if self._hovered else p.bg_elevated
            fg = p.text_primary
            border = p.accent_hover
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

        txt = str(self.cget("text"))
        w = max(56, len(txt) * 8 + self._pad_x * 2)
        h = max(30, 18 + self._pad_y * 2)
        self._pill_photo = render_aa_pill_button_photo(w, h, bg, border)
        self.configure(
            image=self._pill_photo,
            fg=fg,
            bg=parent_bg,
        )

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._refresh_visual()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._refresh_visual()

    def _on_click(self, _event: tk.Event) -> None:
        if not self._disabled and self._command is not None:
            self._command()


class ThreeDSmashButton(tk.Canvas):
    """Kompaktní, dokonale vyhlazené oválné 3D červené tlačítko.

    - Při běžícím výstupu a najetí myší změní nápis na '■  UKONČIT VÝSTUP'.
    - Při najetí myší k němu přiběhne hologram Fištróna, zvedne tlapky a při kliknutí
      do něj praští s cartoon partikly.
    """

    def __init__(
        self,
        master: tk.Widget,
        command: Callable[[], None],
        on_hover_change: Callable[[bool], None],
        palette: ThemePalette,
    ) -> None:
        super().__init__(
            master,
            width=224,
            height=48,
            bg=palette.bg_card,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._command = command
        self._on_hover_change = on_hover_change
        self._palette = palette
        self._is_active_output = False
        self._hovered = False
        self._pressed = False
        self._btn_photo: tk.PhotoImage | None = None
        self._impact_started: float | None = None

        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    @property
    def is_hovered(self) -> bool:
        return self._hovered

    @property
    def current_label(self) -> str:
        if self._is_active_output:
            if self._hovered:
                return "■  UKONČIT VÝSTUP"
            return "●  ŽIVÝ VÝSTUP AKTIVNÍ"
        return "▶  SPUSTIT ŽIVÝ VÝSTUP"

    def set_output_active(self, active: bool) -> None:
        if self._is_active_output != active:
            self._is_active_output = active
            self.redraw()

    def apply_palette(self, palette: ThemePalette) -> None:
        self._palette = palette
        self.configure(bg=palette.bg_card)
        self.redraw()

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._on_hover_change(True)
        self.redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._on_hover_change(False)
        self.redraw()

    def _on_press(self, _event: tk.Event) -> None:
        self._pressed = True
        self.redraw()

    def _on_release(self, _event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self.redraw()
        if was_pressed and self._command is not None:
            self._command()

    def start_impact(self) -> None:
        self._impact_started = time.perf_counter()
        self._animate_impact()

    def _animate_impact(self) -> None:
        if not self.winfo_exists() or self._impact_started is None:
            return
        if time.perf_counter() - self._impact_started >= 0.65:
            self._impact_started = None
            self.redraw()
            return
        self.redraw()
        self.after(25, self._animate_impact)

    def redraw(self) -> None:
        self.delete("all")
        w = max(200, min(260, self.winfo_width() if self.winfo_width() > 50 else 224))
        h = max(44, min(56, self.winfo_height() if self.winfo_height() > 20 else 48))

        self._btn_photo = render_aa_3d_button_photo(
            w,
            h,
            self._is_active_output,
            self._hovered,
            self._pressed,
            self._palette.bg_card,
        )
        self.create_image(0, 0, anchor="nw", image=self._btn_photo)

        press_offset = 3 if self._pressed else (1 if self._hovered else 0)
        self.create_text(
            w // 2,
            round(h * 0.43) + press_offset,
            text=self.current_label,
            fill="#FFFFFF",
            font=(METRICS.font_family, 10, "bold"),
        )
        if self._impact_started is not None:
            age = time.perf_counter() - self._impact_started
            if age < 0.52:
                opacity_shape = math.sin(min(1.0, age / 0.52) * math.pi)
                for i in range(13):
                    angle = i * math.tau / 13.0
                    spread = (12 + age * 125) * (0.7 + (i % 3) * .16)
                    cx = w * .5 + math.cos(angle) * spread
                    cy = h * .48 + math.sin(angle) * spread * .45
                    radius = max(2, (8 + (i % 4) * 3) * opacity_shape)
                    self.create_oval(
                        cx-radius, cy-radius, cx+radius, cy+radius,
                        fill="#F3E8D4", outline="#B9A889", width=1,
                    )
                self.create_oval(
                    w*.5-15*opacity_shape, h*.48-13*opacity_shape,
                    w*.5+15*opacity_shape, h*.48+13*opacity_shape,
                    fill="#FFF7E7", outline="",
                )


class SmoothSlider(tk.Frame):
    """Vyhlazený (nepixelovaný) posuvník s popiskem, čitelnou hodnotou a hover odezvou."""

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
        self._slider_photo: tk.PhotoImage | None = None

        self.columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=palette.bg_card)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        header.columnconfigure(0, weight=1)

        self.lbl_title = tk.Label(
            header,
            text=label,
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
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
            height=26,
            bg=palette.bg_card,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.canvas.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Map>", lambda _e: self._redraw())
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

    def apply_palette(self, palette: ThemePalette, quick: bool = False) -> None:
        self._palette = palette
        self.configure(bg=palette.bg_card)
        self.lbl_title.master.configure(bg=palette.bg_card)
        self.lbl_title.configure(bg=palette.bg_card, fg=palette.text_secondary)
        self.lbl_value.configure(bg=palette.bg_card, fg=palette.text_primary)
        self.canvas.configure(bg=palette.bg_card)
        if self.winfo_ismapped() and not quick:
            self._redraw()

    def _on_enter(self, _e: tk.Event) -> None:
        self._hovered = True
        self._redraw()

    def _on_leave(self, _e: tk.Event) -> None:
        self._hovered = False
        self._redraw()

    def _on_pointer(self, event: tk.Event) -> None:
        w = max(1, self.canvas.winfo_width())
        pad = 12
        usable = max(1, w - 2 * pad)
        ratio = max(0.0, min(1.0, (event.x - pad) / usable))
        raw = self.min_val + ratio * (self.max_val - self.min_val)
        self.set_value(raw, notify=True)

    def _redraw(self) -> None:
        self.canvas.delete("all")
        w = max(60, self.canvas.winfo_width())
        h = max(22, self.canvas.winfo_height())
        span = max(1e-9, self.max_val - self.min_val)
        ratio = max(0.0, min(1.0, (self.value - self.min_val) / span))
        self._slider_photo = render_aa_slider_photo(w, h, ratio, self._hovered, self._palette)
        self.canvas.create_image(0, 0, anchor="nw", image=self._slider_photo)


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
        self._background_photo: tk.PhotoImage | None = None

        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            height=155,
            bg=palette.bg_card,
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
        self.canvas.configure(bg=palette.bg_card)
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

        self._background_photo = render_aa_rounded_panel_photo(
            w, h, p.bg_elevated, p.accent if self.settings.is_graffiti_unlocked else p.border,
            p.bg_card,
        )
        self.canvas.create_image(0, 0, anchor="nw", image=self._background_photo)

        if not self.settings.is_graffiti_unlocked:
            self.canvas.create_text(
                w // 2,
                h // 2,
                text=f"Zvětši Velikost tvarů alespoň na {GRAFFITI_UNLOCK_SIZE} pro odemknutí kreslení Graffiti",
                fill=p.text_muted,
                font=(METRICS.font_family, METRICS.font_size_body, "bold"),
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
                    smooth=False,
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

        palette = self._get_palette()
        self.btn_fullscreen = HoverButton(
            self.canvas,
            text="⛶  Celá obrazovka (F11)",
            command=self.toggle_fullscreen,
            palette=palette,
            variant="active",
            font_size=9,
            bold=True,
            padx=12,
            pady=5,
        )
        self._btn_window_id = self.canvas.create_window(
            940, 16, anchor="ne", window=self.btn_fullscreen
        )

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
        self.window.overrideredirect(True)
        if mon_rect is not None:
            mx, my, mw, mh = mon_rect
            self.window.geometry(f"{mw}x{mh}+{mx}+{my}")
        else:
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            self.window.geometry(f"{sw}x{sh}+0+0")

        self.btn_fullscreen.set_text("✕  Ukončit celou obrazovku (Esc)")
        self.window.focus_force()

    def exit_fullscreen(self) -> None:
        if not self.is_fullscreen:
            return
        self.is_fullscreen = False
        self.window.overrideredirect(False)
        self.window.geometry(self._saved_geometry)
        self.btn_fullscreen.set_text("⛶  Celá obrazovka (F11)")
        self.window.focus_force()

    def render_tick(self, elapsed_ms: float, delta_ms: float) -> str:
        if not self.window.winfo_exists():
            return "stars"

        if (
            self.is_fullscreen
            and self._overlay_visible
            and (time.monotonic() - self._last_mouse_move) > 2.5
        ):
            self._overlay_visible = False
            self.canvas.itemconfigure(self._btn_window_id, state="hidden")

        cw = max(320, self.canvas.winfo_width())
        ch = max(240, self.canvas.winfo_height())
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
    """Hlavní okno AbstractView s pouští, nastavením a hologramem Fištróna."""

    OUTPUT_IMPACT_DELAY_MS = 70
    OUTPUT_ACTION_DELAY_MS = 180

    def __init__(
        self,
        root: tk.Tk | None = None,
        store: SettingsStore | None = None,
    ) -> None:
        self.root = root or tk.Tk()
        clear_tk_photo_cache()
        self.store = store or SettingsStore()
        self.settings = self.store.settings
        self._light_progress: float = (
            1.0 if self.settings.theme_mode == "light" else 0.0
        )
        self._target_light_progress: float = self._light_progress
        self._orbit_direction = 1 if self._light_progress >= 0.5 else -1
        self.palette = get_palette(self.settings.theme_mode)

        self.root.title("AbstractView – Ovládací panel efektů")
        default_geometry = (
            f"{METRICS.default_window_width}x{METRICS.default_window_height}"
        )
        self._last_normal_geometry = self.settings.window_geometry or default_geometry
        try:
            self.root.geometry(self._last_normal_geometry)
        except tk.TclError:
            self._last_normal_geometry = default_geometry
            self.root.geometry(default_geometry)
        self.root.minsize(METRICS.min_window_width, METRICS.min_window_height)
        self.root.configure(bg=self.palette.bg_primary)

        self.engine = AbstractViewEngine()
        self.engine.sync_source(self.settings)
        self.output_window: OutputDisplayWindow | None = None
        self._pending_output_action: str | None = None

        self.open_panels: list[str] = list(self.settings.open_panels)
        self.active_panel: str | None = self.open_panels[-1] if self.open_panels else None
        self.open_effect_settings: str | None = (
            self.settings.active_effect if self.active_panel in ("shape", "object") else None
        )
        self._dragging_panel: str | None = None
        self._drag_origin: tuple[float, float, float, float] | None = None
        self._last_activity = time.perf_counter()
        self.fistron = FistronCompanion()

        self._themed_frames: list[tuple[tk.Widget, str]] = []
        self._themed_labels: list[tuple[tk.Label, str, str]] = []
        self._buttons: list[HoverButton] = []
        self._sliders: list[SmoothSlider] = []
        self._wrap_labels: list[tk.Label] = []
        self._thumb_images: dict[str, tk.PhotoImage] = {}
        self._swatch_photos: dict[tuple, tk.PhotoImage] = {}
        self._selected_part_tab: str = "head"
        self._current_columns: int = 1
        self._scene_photo: tk.PhotoImage | None = None
        self._visible_card_rects: list[tuple[int, int, int, int]] = []
        self._glass_rects: list[tuple[int, int, int, int]] = []
        self._open_settings_rect: tuple[int, int, int, int] | None = None
        self._panel_rects: dict[str, tuple[int, int, int, int]] = {}
        self._panel_sizes: dict[str, tuple[int, int, int]] = {}
        self._top_card_rects: list[tuple[int, int, int, int]] = []
        self._last_layout_width = 0
        self._panel_content_dirty = True
        self._last_panel_content_signature: tuple | None = None

        self._started_at = time.perf_counter()
        self._last_tick = self._started_at
        self._fps_estimate = 60.0
        self._last_scene_render = 0.0
        self._last_status_update = 0.0
        self._last_palette_step: float | None = None
        self._last_detail_palette_step: int | None = None
        self._scene_dirty = True
        self._scene_height = METRICS.default_window_height
        self._process = psutil.Process()

        self._build_ui()
        self.refresh_all_states()
        self.apply_theme(self.settings.theme_mode, save=False, animate=False)
        self.root.update_idletasks()
        self._finalize_initial_layout()

        self.root.bind("<Configure>", self._on_root_configure)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.after_idle(self._restore_window_state)
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

    def _source_caption(self) -> str:
        if self.settings.source_type == "sample":
            label = {
                "pose_calm": "Ukázka · Klid",
                "pose_spread": "Ukázka · Rozpažení",
                "pose_raise": "Ukázka · Vzpažení",
            }.get(self.settings.sample_id, "Ukázka")
        elif self.settings.source_type == "camera":
            label = (
                "Virtuální kamera" if self.settings.camera_port == 99
                else f"Kamera · Port {self.settings.camera_port}"
            )
        else:
            name = Path(self.settings.csv_path).name
            label = f"CSV · {name[:18]}{'…' if len(name) > 18 else ''}"
        return f"▣  {label}  ▾"

    def _make_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Vytvoří vnitřní obsah karty (její zaoblené rohy a stín kreslí scéna kolem ní)."""
        inner = tk.Frame(
            parent,
            bg=self.palette.bg_card,
            padx=6,
            pady=4,
            bd=0,
            highlightthickness=0,
        )
        inner.columnconfigure(0, weight=1)
        self._reg_frame(inner, "card")

        lbl = tk.Label(
            inner,
            text=title,
            font=(METRICS.font_family, METRICS.font_size_section, "bold"),
            bg=self.palette.bg_card,
            fg=self.palette.text_primary,
            anchor="w",
        )
        lbl.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._reg_label(lbl, "card", "primary")
        inner.inner = inner  # type: ignore[attr-defined]
        inner.title_label = lbl  # type: ignore[attr-defined]
        return inner

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # 1. Horní lišta (Header): Název, odznak zdroje, posuvný přepínač light/dark, Reset vpravo nahoře
        self.header_frame = tk.Frame(
            self.root, bg=self.palette.bg_card, padx=18, pady=10
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
        self.lbl_brand.grid(row=0, column=0, sticky="w", padx=(0, 14))
        self._reg_label(self.lbl_brand, "card", "primary")

        self.lbl_source_badge = HoverButton(
            self.header_frame,
            text=self._source_caption(),
            command=self.open_csv_dialog,
            palette=self.palette,
            variant="inspect",
            font_size=METRICS.font_size_small,
            padx=12,
            pady=5,
        )
        self.lbl_source_badge.grid(row=0, column=1, sticky="w")
        self._buttons.append(self.lbl_source_badge)

        right_header = tk.Frame(self.header_frame, bg=self.palette.bg_card)
        right_header.grid(row=0, column=2, sticky="e")
        self._reg_frame(right_header, "card")

        self.btn_theme = DayNightSwitch(
            right_header, command=self.toggle_theme, palette=self.palette,
        )
        self.btn_theme.pack(side="left", padx=(0, 12))

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

        # 2. Střední scéna s pouští, panelem nastavení a Fištrónem.
        scene_host = tk.Frame(self.root, bg=self.palette.bg_primary)
        scene_host.grid(row=1, column=0, sticky="nsew")
        scene_host.columnconfigure(0, weight=1)
        scene_host.rowconfigure(0, weight=1)
        self._reg_frame(scene_host, "primary")

        self.scroll_canvas = tk.Canvas(
            scene_host,
            bg=self.palette.bg_primary,
            highlightthickness=0,
            bd=0,
        )
        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = tk.Scrollbar(
            scene_host, orient="vertical", command=self._scroll_scene
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.scroll_canvas.configure(yscrollcommand=self._sync_scene_scroll)

        self.cards_container = tk.Frame(
            self.scroll_canvas, bg=self.palette.bg_primary, padx=0, pady=0
        )
        self._reg_frame(self.cards_container, "primary")

        self._build_effects_cards()
        self._panel_shells: dict[str, RoundedPanelFrame] = {}
        self._panel_close_labels: dict[str, tk.Label] = {}
        for key in ("shuffle", "shape", "object"):
            shell = RoundedPanelFrame(scene_host, bg=self.palette.bg_card, padx=12, pady=10)
            close = tk.Label(
                shell, text="✕", bg=self.palette.bg_card,
                fg=self.palette.text_primary, font=(METRICS.font_family, 13, "bold"),
                cursor="hand2", padx=4,
            )
            self._panel_shells[key] = shell
            self._panel_close_labels[key] = close
            self._reg_frame(shell, "card")
            self._reg_label(close, "card", "primary")
            close.bind("<ButtonPress-1>", lambda _e, k=key: self._close_panel(k))
        self._build_shuffle_card()
        self._build_shape_settings_card()
        self._build_object_settings_card()
        for key, card in (
            ("shuffle", self.card_shuffle),
            ("shape", self.card_shape_settings),
            ("object", self.card_object_settings),
        ):
            card.pack(fill="x")
            title_label = card.title_label  # type: ignore[attr-defined]
            title_label.configure(cursor="fleur")
            title_label.grid_configure(padx=(0, 30))
            for widget in (self._panel_shells[key], title_label):
                widget.bind("<ButtonPress-1>", lambda e, k=key: self._start_panel_drag(k, e))
                widget.bind("<B1-Motion>", self._drag_panel)
                widget.bind("<ButtonRelease-1>", self._finish_panel_drag)
            close = self._panel_close_labels[key]
            close.place(relx=1.0, x=-8, y=7, anchor="ne")
            close.lift()
        self._scene_image_id = self.scroll_canvas.create_image(
            0, 0, anchor="nw"
        )
        self._projection_effect_title = self.scroll_canvas.create_text(
            0, 0, anchor="center", text="", width=184, justify="center",
            fill="#F3F6FF", font=(METRICS.font_family, 16, "bold"),
        )
        self._glass_caption_shuffle = self.scroll_canvas.create_text(
            0, 0, anchor="nw", text="SHUFFLE",
            fill=self.palette.text_primary,
            font=(METRICS.font_family, 11, "bold"), state="hidden",
        )
        self._glass_caption_effect = self.scroll_canvas.create_text(
            0, 0, anchor="nw", text="TVAROVÝ EFEKT",
            fill=self.palette.text_primary,
            font=(METRICS.font_family, 11, "bold"), state="hidden",
        )
        self._glass_caption_object = self.scroll_canvas.create_text(
            0, 0, anchor="nw", text="OBJEKTOVÝ EFEKT",
            fill=self.palette.text_primary,
            font=(METRICS.font_family, 11, "bold"), state="hidden",
        )
        self._panel_title_items = {
            "shuffle": self._glass_caption_shuffle,
            "shape": self._glass_caption_effect,
            "object": self._glass_caption_object,
        }
        self._panel_close_items = {
            key: self.scroll_canvas.create_text(
                0, 0, text="✕", font=(METRICS.font_family, 13, "bold"),
                fill=self.palette.text_primary, state="hidden",
            ) for key in self._panel_title_items
        }
        self._win_shape_effects = self.scroll_canvas.create_window(
            120, 22, anchor="nw", window=self.card_shape_effects
        )
        self._win_object_effects = self.scroll_canvas.create_window(
            120, 118, anchor="nw", window=self.card_object_effects
        )
        self._win_shuffle_card = self.scroll_canvas.create_rectangle(0, 0, 0, 0, state="hidden")
        self._win_shape_settings = self.scroll_canvas.create_rectangle(0, 0, 0, 0, state="hidden")
        self._win_object_settings = self.scroll_canvas.create_rectangle(0, 0, 0, 0, state="hidden")
        self._panel_window_items = {
            "shuffle": self._win_shuffle_card,
            "shape": self._win_shape_settings,
            "object": self._win_object_settings,
        }
        self._panel_cards = self._panel_shells
        for key, item in self._panel_title_items.items():
            self.scroll_canvas.tag_bind(item, "<ButtonPress-1>", lambda e, k=key: self._start_panel_drag(k, e))
            self.scroll_canvas.tag_bind(item, "<B1-Motion>", self._drag_panel)
            self.scroll_canvas.tag_bind(item, "<ButtonRelease-1>", self._finish_panel_drag)
            self.scroll_canvas.tag_bind(self._panel_close_items[key], "<ButtonPress-1>", lambda _e, k=key: self._close_panel(k))
            self._bind_panel_focus(self._panel_cards[key], key)

        self.scroll_canvas.bind("<Configure>", self._on_scroll_canvas_configure)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Motion>", self._record_activity, add="+")
        self.root.bind_all("<KeyPress>", self._record_activity, add="+")

        # 3. Spodní akční lišta: všechny 3 prvky vycentrované uprostřed jako kompaktní lišta
        self.action_bar = tk.Frame(
            self.root,
            bg=self.palette.bg_card,
            padx=16,
            pady=8,
            highlightbackground=self.palette.border,
            highlightthickness=1,
        )
        self.action_bar.grid(row=2, column=0, sticky="ew")
        self._reg_frame(self.action_bar, "card")

        center_dock = tk.Frame(self.action_bar, bg=self.palette.bg_card)
        center_dock.pack(anchor="center")
        self._reg_frame(center_dock, "card")

        self.btn_load_csv = HoverButton(
            center_dock,
            text="📂  Nahrát CSV",
            command=self.open_csv_dialog,
            palette=self.palette,
            variant="secondary",
            font_size=10,
            bold=True,
            padx=18,
            pady=8,
        )
        self.btn_load_csv.pack(side="left", padx=8)
        self._buttons.append(self.btn_load_csv)

        self.btn_select_camera = HoverButton(
            center_dock,
            text="🎥  Vybrat kameru",
            command=self.open_camera_dialog,
            palette=self.palette,
            variant="secondary",
            font_size=10,
            bold=True,
            padx=18,
            pady=8,
        )
        self.btn_select_camera.pack(side="left", padx=8)
        self._buttons.append(self.btn_select_camera)

        self.btn_play_output = ThreeDSmashButton(
            center_dock,
            command=self.on_smash_play_button,
            on_hover_change=self._on_play_button_hover,
            palette=self.palette,
        )
        self.btn_play_output.pack(side="left", padx=10)

        # 4. Stavová patička (RAM, CPU, FPS, aktivní efekt)
        self.footer_frame = tk.Frame(
            self.root, bg=self.palette.bg_card, padx=18, pady=5
        )
        self.footer_frame.grid(row=3, column=0, sticky="ew")
        self.footer_frame.columnconfigure(0, weight=1)
        self._reg_frame(self.footer_frame, "card")

        self.lbl_status = tk.Label(
            self.footer_frame,
            text="Připraveno",
            font=(METRICS.font_family, METRICS.font_size_small, "bold"),
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
            self.scroll_canvas, "Efekty tvarové"
        )
        row_frame = tk.Frame(
            self.card_shape_effects.inner, bg=self.palette.bg_card  # type: ignore[attr-defined]
        )
        row_frame.grid(row=1, column=0, sticky="ew")
        self._reg_frame(row_frame, "card")

        self.btn_shape_shuffle = HoverButton(
            row_frame,
            text="shuffle",
            command=self._toggle_shape_shuffle,
            palette=self.palette,
            bold=True,
        )
        self.btn_shape_shuffle.pack(side="left", padx=(0, 8), pady=2)
        self._buttons.append(self.btn_shape_shuffle)

        self.shape_effect_buttons: dict[str, HoverButton] = {}
        for eff_key, eff_label in SHAPE_EFFECTS:
            btn = HoverButton(
                row_frame,
                text=eff_label,
                command=lambda k=eff_key: self.on_effect_button_clicked(k),
                palette=self.palette,
                bold=True,
            )
            btn.pack(side="left", padx=(0, 8), pady=2)
            self.shape_effect_buttons[eff_key] = btn
            self._buttons.append(btn)

        lbl_more_shape = tk.Label(
            row_frame,
            text="more coming soon",
            font=(METRICS.font_family, METRICS.font_size_body, "italic"),
            bg=self.palette.bg_card,
            fg=self.palette.text_muted,
            padx=10,
        )
        lbl_more_shape.pack(side="left", pady=2)
        self._reg_label(lbl_more_shape, "card", "muted")

        # Karta 2: Efekty objektové (pod tvarovými na celou šířku)
        self.card_object_effects = self._make_card(
            self.scroll_canvas, "Efekty objektové"
        )
        obj_row = tk.Frame(
            self.card_object_effects.inner, bg=self.palette.bg_card  # type: ignore[attr-defined]
        )
        obj_row.grid(row=1, column=0, sticky="ew")
        self._reg_frame(obj_row, "card")

        self.btn_object_shuffle = HoverButton(
            obj_row,
            text="shuffle",
            command=self._toggle_object_shuffle,
            palette=self.palette,
            bold=True,
        )
        self.btn_object_shuffle.pack(side="left", padx=(0, 8), pady=2)
        self._buttons.append(self.btn_object_shuffle)

        self.object_effect_buttons: dict[str, HoverButton] = {}
        for eff_key, eff_label in OBJECT_EFFECTS:
            btn = HoverButton(
                obj_row,
                text=eff_label,
                command=lambda k=eff_key: self.on_effect_button_clicked(k),
                palette=self.palette,
                bold=True,
            )
            btn.pack(side="left", padx=(0, 8), pady=2)
            self.object_effect_buttons[eff_key] = btn
            self._buttons.append(btn)

        lbl_more_obj = tk.Label(
            obj_row,
            text="more coming soon",
            font=(METRICS.font_family, METRICS.font_size_body, "italic"),
            bg=self.palette.bg_card,
            fg=self.palette.text_muted,
            padx=10,
        )
        lbl_more_obj.pack(side="left", pady=2)
        self._reg_label(lbl_more_obj, "card", "muted")

    def _build_shuffle_card(self) -> None:
        self.card_shuffle = self._make_card(
            self._panel_shells["shuffle"],
            "Nastavení shuffle",
        )
        inner = self.card_shuffle.inner  # type: ignore[attr-defined]

        self.slider_shuffle_interval = SmoothSlider(
            inner,
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

        self.slider_shuffle_transition = SmoothSlider(
            inner,
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

        order_row = tk.Frame(inner, bg=self.palette.bg_card)
        order_row.grid(row=3, column=0, sticky="ew")
        self._reg_frame(order_row, "card")

        lbl_order = tk.Label(
            order_row,
            text="Pořadí:",
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
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
            btn.pack(side="left", padx=(0, 8))
            self.order_buttons[mode_key] = btn
            self._buttons.append(btn)

        self.custom_styles_frame = tk.Frame(
            inner, bg=self.palette.bg_card, pady=6
        )
        self.custom_styles_frame.grid(row=4, column=0, sticky="ew")
        self._reg_frame(self.custom_styles_frame, "card")

        lbl_custom_hint = tk.Label(
            self.custom_styles_frame,
            text="Aktivní styly ve frontě (kliknutím odeber/přidej):",
            font=(METRICS.font_family, METRICS.font_size_small, "bold"),
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
            self._panel_shells["shape"], "Nastavení tvarového efektu"
        )
        inner = self.card_shape_settings.inner  # type: ignore[attr-defined]

        self.slider_gravity = SmoothSlider(
            inner,
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

        self.slider_star_count = SmoothSlider(
            inner,
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

        self.slider_shooting_stars = SmoothSlider(
            inner,
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

        self.slider_twinkle = SmoothSlider(
            inner,
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

        self.slider_nebula_swirl = SmoothSlider(
            inner,
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
            self._panel_shells["object"],
            "Nastavení objektového efektu – Prstence tvarů",
        )
        inner = self.card_object_settings.inner  # type: ignore[attr-defined]

        lbl_parts_summary = tk.Label(
            inner,
            text="Hlava: Zaoblené koule · Trup (V): Otočené jehlany · Ruce: Válce · Každá noha zvlášť: Kvádry",
            font=(METRICS.font_family, METRICS.font_size_small, "bold"),
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

        self.slider_orbit_speed = SmoothSlider(
            inner,
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

        self.slider_shape_size = SmoothSlider(
            inner,
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

        pattern_frame = tk.Frame(inner, bg=self.palette.bg_card)
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
                pady=5,
            )
            btn.pack(side="left", padx=(0, 6), pady=2)
            self.pattern_buttons[pat_key] = btn
            self._buttons.append(btn)

        self.graffiti_hint = tk.Label(
            pattern_frame,
            text=f"Pro Graffiti zvětši tvary alespoň na {GRAFFITI_UNLOCK_SIZE}.",
            font=(METRICS.font_family, METRICS.font_size_small),
            bg=self.palette.bg_card,
            fg=self.palette.text_muted,
            anchor="w",
        )
        self._reg_label(self.graffiti_hint, "card", "muted")

        color_mode_row = tk.Frame(inner, bg=self.palette.bg_card)
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

        self.part_tabs_frame = tk.Frame(inner, bg=self.palette.bg_card)
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

        # Výběr Primární a Sekundární barvy (čistá kulatá barevná políčka bez písmen!)
        self.swatches_container = tk.Frame(inner, bg=self.palette.bg_card)
        self.swatches_container.grid(
            row=7, column=0, sticky="ew", pady=(0, 10)
        )
        self._reg_frame(self.swatches_container, "card")

        self.primary_swatch_block, self.primary_swatch_title, self.primary_swatch_btns = self._build_color_swatch_row(
            self.swatches_container,
            "Primární barva (podklad tvaru):",
            is_primary=True,
        )
        self.secondary_swatch_block, _, self.secondary_swatch_btns = self._build_color_swatch_row(
            self.swatches_container,
            "Sekundární barva (štětec / spirála / tečky):",
            is_primary=False,
        )

        # Graffiti editor
        self.graffiti_section = tk.Frame(inner, bg=self.palette.bg_card)
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

        graf_colors_row = tk.Frame(
            self.graffiti_section, bg=self.palette.bg_card
        )
        graf_colors_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self._reg_frame(graf_colors_row, "card")

        self.graf_color_btns: dict[str, tk.Label] = {}
        for preset in PRESET_COLORS:
            swatch = tk.Label(
                graf_colors_row,
                bg=self.palette.bg_card,
                bd=0,
                cursor="hand2",
            )
            swatch.pack(side="left", padx=(0, 6), pady=2)
            swatch.bind(
                "<Button-1>",
                lambda _e, k=preset.key: self._select_graffiti_color(k),
            )
            self.graf_color_btns[preset.key] = swatch

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

        self.graffiti_widget = GraffitiCanvasWidget(
            self.graffiti_section,
            settings=self.settings,
            on_stroke_updated=self._on_graffiti_stroke_updated,
            palette=self.palette,
        )
        self.graffiti_widget.grid(row=3, column=0, sticky="ew")

    def _build_color_swatch_row(
        self, parent: tk.Widget, title: str, is_primary: bool
    ) -> tuple[tk.Frame, tk.Label, dict[str, tk.Label]]:
        block = tk.Frame(parent, bg=self.palette.bg_card)
        block.pack(fill="x", pady=(0, 6))
        self._reg_frame(block, "card")

        lbl = tk.Label(
            block,
            text=title,
            font=(METRICS.font_family, METRICS.font_size_small, "bold"),
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
                bg=self.palette.bg_card,
                bd=0,
                cursor="hand2",
            )
            sw.pack(side="left", padx=(0, 6), pady=2)
            sw.bind(
                "<Button-1>",
                lambda _e, k=preset.key, prim=is_primary: self._select_shape_color(
                    k, prim
                ),
            )
            btns[preset.key] = sw
        return block, lbl, btns

    # ------------------------------------------------------------------
    # Formátování a obsluha událostí nastavení (body 5 a 7)
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
            panel = "object" if effect_key == "rings" else "shape"
            if panel not in self.open_panels:
                self.open_panels.append(panel)
            self.open_panels.remove(panel)
            self.open_panels.append(panel)
            self.active_panel = panel
            self.open_effect_settings = effect_key
            self.settings.open_panels = list(self.open_panels)
            self.store.save()
            self.refresh_all_states()

    def on_effect_button_clicked(self, effect_key: str) -> None:
        """Otevře nebo zaměří jeden panel pro danou skupinu efektů."""
        if effect_key not in ALL_EFFECT_KEYS:
            return
        self.settings.active_effect = effect_key
        key = "object" if effect_key == "rings" else "shape"
        if key not in self.open_panels:
            self.open_panels.append(key)
        self.active_panel = key
        self.open_panels.remove(key)
        self.open_panels.append(key)
        self.open_effect_settings = effect_key
        self.settings.open_panels = list(self.open_panels)
        self.store.save()
        self._layout_scene_windows(max(400, self.scroll_canvas.winfo_width()))
        self._update_effect_button_variants()
        self._last_activity = time.perf_counter()
        self._step_scene_and_fistron(0.0, True)

    def _toggle_shape_shuffle(self) -> None:
        enabling = not self.settings.shape_shuffle
        self.settings.shape_shuffle = enabling
        if enabling:
            if "shuffle" in self.open_panels:
                self.open_panels.remove("shuffle")
            self.open_panels.append("shuffle")
            self.active_panel = "shuffle"
        self.settings.open_panels = list(self.open_panels)
        self.store.save()
        self.refresh_all_states()

    def _toggle_object_shuffle(self) -> None:
        enabling = not self.settings.object_shuffle
        self.settings.object_shuffle = enabling
        if enabling:
            if "shuffle" in self.open_panels:
                self.open_panels.remove("shuffle")
            self.open_panels.append("shuffle")
            self.active_panel = "shuffle"
        self.settings.open_panels = list(self.open_panels)
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

        self.btn_shape_shuffle.set_variant(
            "shuffle" if s.shape_shuffle else "secondary"
        )
        self.btn_object_shuffle.set_variant(
            "shuffle" if s.object_shuffle else "secondary"
        )

        self._update_effect_button_variants()

        for k, btn in self.order_buttons.items():
            btn.set_variant("active" if s.shuffle_order == k else "secondary")

        if s.shuffle_order == "custom":
            self.custom_styles_frame.grid()
        else:
            self.custom_styles_frame.grid_remove()

        all_labels = dict((*SHAPE_EFFECTS, *OBJECT_EFFECTS))
        for k, btn in self.custom_effect_buttons.items():
            on = k in s.custom_enabled_effects
            btn.set_text(f"{'✓' if on else '✕'} {all_labels[k]}")
            btn.set_variant("active" if on else "secondary")

        graf_btn = self.pattern_buttons["graffiti"]
        if s.is_graffiti_unlocked:
            graf_btn.set_text("Graffiti")
            graf_btn.set_disabled(False)
            self.graffiti_hint.pack_forget()
        else:
            graf_btn.set_text(f"🔒 Graffiti (od {GRAFFITI_UNLOCK_SIZE})")
            graf_btn.set_disabled(True)
            self.graffiti_hint.pack(anchor="w", pady=(5, 0))

        if s.show_graffiti_editor:
            self.graffiti_section.grid()
            self.swatches_container.grid_remove()
        else:
            self.graffiti_section.grid_remove()
            self.swatches_container.grid()
            self.primary_swatch_title.configure(
                text="Barva celého tvaru:" if s.color_mode == "global" and s.pattern_style == "solid" else "Primární barva (podklad tvaru):"
            )
            if s.uses_secondary_color:
                self.secondary_swatch_block.pack(fill="x", pady=(0, 6))
            else:
                self.secondary_swatch_block.pack_forget()

        for k, btn in self.pattern_buttons.items():
            if k == "graffiti" and not s.is_graffiti_unlocked:
                continue
            btn.set_variant("active" if s.pattern_style == k else "secondary")

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

        # Čisté kulaté barevné swatche bez písmen
        for k, sw in self.primary_swatch_btns.items():
            preset = PRESET_COLOR_MAP[k]
            ph = render_aa_color_swatch_photo(
                28,
                preset.hex_code,
                k == active_prim,
                False,
                self.palette.bg_card,
                self.palette.text_primary,
            )
            self._swatch_photos[("prim", k == active_prim, k)] = ph
            sw.configure(image=ph, bg=self.palette.bg_card)

        for k, sw in self.secondary_swatch_btns.items():
            preset = PRESET_COLOR_MAP[k]
            ph = render_aa_color_swatch_photo(
                28,
                preset.hex_code,
                k == active_sec,
                False,
                self.palette.bg_card,
                self.palette.text_primary,
            )
            self._swatch_photos[("sec", k == active_sec, k)] = ph
            sw.configure(image=ph, bg=self.palette.bg_card)

        self.btn_graf_eraser.set_variant(
            "active" if s.graffiti_eraser else "secondary"
        )
        for k, sw in self.graf_color_btns.items():
            preset = PRESET_COLOR_MAP[k]
            selected = (k == s.graffiti_brush_color) and (not s.graffiti_eraser)
            ph = render_aa_color_swatch_photo(
                26,
                preset.hex_code,
                selected,
                False,
                self.palette.bg_card,
                self.palette.text_primary,
            )
            self._swatch_photos[("graf", selected, k)] = ph
            sw.configure(image=ph, bg=self.palette.bg_card)

        self.graffiti_widget.redraw()
        content_signature = (
            s.shuffle_order == "custom", s.show_graffiti_editor,
            s.color_mode == "per_part", s.uses_secondary_color,
            s.is_graffiti_unlocked,
        )
        if content_signature != self._last_panel_content_signature:
            self._panel_content_dirty = True
            self._last_panel_content_signature = content_signature
        self._layout_scene_windows(max(400, self.scroll_canvas.winfo_width()))

        self.engine.sync_source(s)
        self.lbl_source_badge.set_text(self._source_caption())

        is_out_running = (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        )
        self.btn_play_output.set_output_active(is_out_running)

    # ------------------------------------------------------------------
    # Přepínání light / dark tématu s plynulou animací
    # ------------------------------------------------------------------
    def toggle_theme(self) -> None:
        next_mode = "light" if self.settings.theme_mode == "dark" else "dark"
        self.apply_theme(next_mode, save=True, animate=True)

    def apply_theme(
        self, mode: str, save: bool = True, animate: bool = False
    ) -> None:
        self.settings.theme_mode = "light" if mode == "light" else "dark"
        self._target_light_progress = (
            1.0 if self.settings.theme_mode == "light" else 0.0
        )
        if animate:
            self._orbit_direction = 1 if self._target_light_progress > self._light_progress else -1
            self._scene_dirty = True
        else:
            self._light_progress = self._target_light_progress
            self._apply_interpolated_palette(self._light_progress)
        if save:
            self.store.save()

    def _apply_interpolated_palette(self, progress: float) -> None:
        self._last_palette_step = progress
        self.palette = interpolate_palette(progress)
        p = self.palette
        detail_step = round(progress * 8)
        redraw_details = self._last_detail_palette_step != detail_step or progress in (0.0, 1.0)
        self._last_detail_palette_step = detail_step
        final_palette = progress in (0.0, 1.0)
        glass_rgb = lerp_rgb((30, 54, 91), (222, 175, 138), progress)
        glass_bg = f"#{glass_rgb[0]:02X}{glass_rgb[1]:02X}{glass_rgb[2]:02X}"
        glass_palette = replace(p, bg_card=glass_bg)
        glass_roots = tuple(str(card) for card in (
            *self._panel_shells.values(),
        ))

        def on_glass(widget: tk.Widget) -> bool:
            name = str(widget)
            return any(name == root or name.startswith(root + ".") for root in glass_roots)

        self.root.configure(bg=p.bg_primary)
        self.scroll_canvas.configure(bg=p.bg_primary)
        self.scroll_canvas.itemconfigure(self._glass_caption_shuffle, fill=p.text_primary)
        self.scroll_canvas.itemconfigure(self._glass_caption_effect, fill=p.text_primary)
        self.scroll_canvas.itemconfigure(self._glass_caption_object, fill=p.text_primary)
        for item in self._panel_close_items.values():
            self.scroll_canvas.itemconfigure(item, fill=p.text_primary)
        self.btn_theme.set_progress(self._light_progress, p)

        for widget, role in self._themed_frames:
            if not widget.winfo_exists():
                continue
            if not final_palette and not widget.winfo_ismapped():
                continue
            if role == "primary":
                bg = p.bg_primary
            elif role == "shadow":
                bg = p.shadow_color
            elif role == "panel_header":
                bg = p.bg_elevated
            elif on_glass(widget):
                bg = glass_bg
            else:
                bg = p.bg_card
            widget.configure(bg=bg)
            if int(widget.cget("highlightthickness")) > 0:
                widget.configure(highlightbackground=p.border)

        for lbl, bg_role, fg_role in self._themed_labels:
            if not lbl.winfo_exists():
                continue
            if not final_palette and not lbl.winfo_ismapped():
                continue
            bg = (
                p.badge_bg
                if bg_role == "badge"
                else (p.bg_primary if bg_role == "primary" else (
                    p.bg_elevated if bg_role == "panel_header" else (
                        glass_bg if on_glass(lbl) else p.bg_card
                    )
                ))
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
                if redraw_details and (btn.winfo_ismapped() or final_palette):
                    btn.apply_palette(p)
                else:
                    btn._palette = p
                    if btn.winfo_ismapped():
                        btn.configure(bg=str(btn.master.cget("bg")))

        self.btn_play_output.apply_palette(p)

        for slider in self._sliders:
            if slider.winfo_exists():
                if slider.winfo_ismapped() or final_palette:
                    slider.apply_palette(glass_palette, quick=not redraw_details)
                else:
                    slider._palette = glass_palette

        if self.graffiti_widget.winfo_ismapped() or final_palette:
            self.graffiti_widget.apply_palette(p)
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
            and redraw_details
        ):
            self.output_window.btn_fullscreen.apply_palette(p)

        # Stav tlačítek se při změně motivu nemění. Jejich paleta už byla
        # aktualizována výše; opětovné rozložení všech karet by blokovalo UI.

    # ------------------------------------------------------------------
    # Dynamické rozložení karet a scény
    # ------------------------------------------------------------------
    def _on_root_configure(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        if self.root.state() == "normal" and event.width > 1 and event.height > 1:
            self._last_normal_geometry = self.root.geometry()
        self._relayout_cards(event.width)

    def _restore_window_state(self) -> None:
        if not self.root.winfo_exists():
            return
        try:
            if self.settings.window_state == "fullscreen":
                self.root.attributes("-fullscreen", True)
            elif self.settings.window_state == "zoomed":
                self.root.state("zoomed")
        except tk.TclError:
            self.settings.window_state = "normal"

    def _finalize_initial_layout(self) -> None:
        """Po prvním rozměření rezervuje scénu pro všechny panely bez pozdějšího skoku."""
        if not self.root.winfo_exists():
            return
        self._panel_content_dirty = True
        self._layout_scene_windows(max(400, self.scroll_canvas.winfo_width()))

    def _on_scroll_canvas_configure(self, event: tk.Event) -> None:
        self._layout_scene_windows(event.width, event.height)

    def _relayout_cards(self, width: int) -> None:
        self._current_columns = 2 if width >= METRICS.compact_breakpoint else 1
        self._layout_scene_windows(width)

    def _layout_scene_windows(
        self, canvas_width: int, canvas_height: int | None = None
    ) -> None:
        """Rozmístí karty a uložené plovoucí panely na jediném Tk canvasu."""
        w = max(360, int(canvas_width))
        measured_height = (
            self.scroll_canvas.winfo_height()
            if canvas_height is None
            else int(canvas_height)
        )
        ch = max(320, measured_height)
        top_w = min(660, max(340, int(w * 0.68)))
        top_inner_w = top_w - 28
        self.scroll_canvas.itemconfigure(self._win_shape_effects, width=top_inner_w)
        self.scroll_canvas.itemconfigure(self._win_object_effects, width=top_inner_w)
        self.scroll_canvas.coords(self._win_shape_effects, 32, 24)

        needs_measure = (
            not self._panel_sizes or self._panel_content_dirty
            or w != self._last_layout_width
        )
        outer_w = min(560, max(360, round(w * 0.68)))
        inner_w = outer_w - 24
        if needs_measure:
            self.card_shape_effects.update_idletasks()
            self.card_object_effects.update_idletasks()
            for card in self._panel_cards.values():
                card.update_idletasks()
            self._panel_sizes = {
                "shuffle": (outer_w, inner_w, max(150, self.card_shuffle.winfo_reqheight() + 20)),
                "shape": (outer_w, inner_w, max(195, self.card_shape_settings.winfo_reqheight() + 20)),
                "object": (outer_w, inner_w, max(310, self.card_object_settings.winfo_reqheight() + 20)),
            }
            self._panel_content_dirty = False
            self._last_layout_width = w

        h1 = max(56, self.card_shape_effects.winfo_reqheight()) + 20
        y2 = 14 + h1 + 12
        self.scroll_canvas.coords(self._win_object_effects, 32, y2 + 10)
        h2 = max(56, self.card_object_effects.winfo_reqheight()) + 20
        self._top_card_rects = [
            (18, 14, 18 + top_w, 14 + h1),
            (18, y2, 18 + top_w, y2 + h2),
        ]

        defaults = {
            "shape": (0.25, 0.31),
            "object": (0.42, 0.38),
            "shuffle": (0.10, 0.45),
        }
        self._panel_rects.clear()
        for key, item in self._panel_window_items.items():
            is_open = key in self.open_panels
            state = "normal" if is_open else "hidden"
            self.scroll_canvas.itemconfigure(item, state=state)
            self.scroll_canvas.itemconfigure(self._panel_title_items[key], state="hidden")
            self.scroll_canvas.itemconfigure(self._panel_close_items[key], state="hidden")
            if not is_open:
                self._panel_shells[key].place_forget()
                continue
            xf, yf = self.settings.panel_positions.get(key, defaults[key])
            x = round(max(160, min(w - outer_w - 8, xf * w)))
            y = round(max(8, min(ch - 36, yf * ch)))
            self._position_panel(key, x, y)

        if self.active_panel not in self.open_panels:
            self.active_panel = self.open_panels[-1] if self.open_panels else None
        self._refresh_panel_layers()
        total_h = max(ch, y2 + h2 + 52, *(rect[3] + 52 for rect in self._panel_rects.values()))
        all_panel_bottoms: list[int] = []
        for key, (_panel_w, _inner_w, panel_h) in self._panel_sizes.items():
            _xf, yf = self.settings.panel_positions.get(key, defaults[key])
            panel_y = round(max(8, min(ch - 36, yf * ch)))
            all_panel_bottoms.append(panel_y + panel_h + 52)
        total_h = max(total_h, *all_panel_bottoms)
        self._scene_height = total_h
        self._scene_dirty = True
        self.scroll_canvas.configure(scrollregion=(0, 0, w, total_h))

    def _position_panel(self, key: str, x: int, y: int) -> None:
        outer_w, _inner_w, outer_h = self._panel_sizes[key]
        rect = (x, y, x + outer_w, y + outer_h)
        self._panel_rects[key] = rect
        self._panel_shells[key].place(
            x=x,
            y=round(y - self.scroll_canvas.canvasy(0)),
            width=outer_w,
            height=outer_h,
        )

    def _get_open_settings_panel_rect(self) -> tuple[int, int, int, int] | None:
        return self._panel_rects.get(self.active_panel) if self.active_panel else None

    def _bind_panel_focus(self, widget: tk.Widget, key: str) -> None:
        widget.bind("<ButtonPress-1>", lambda e, k=key: self._panel_widget_press(k, e), add="+")
        if isinstance(widget, SmoothSlider):
            widget.canvas.bind("<B1-Motion>", lambda _e, k=key: self._mark_panel_editing(k), add="+")
        for child in widget.winfo_children():
            self._bind_panel_focus(child, key)

    def _panel_widget_press(self, key: str, event: tk.Event) -> None:
        self._focus_panel(key)
        if isinstance(event.widget, (tk.Canvas, HoverButton)):
            self._mark_panel_editing(key)

    def _mark_panel_editing(self, key: str) -> None:
        self._focus_panel(key)

    def _focus_panel(self, key: str) -> None:
        if key not in self.open_panels:
            return
        self._last_activity = time.perf_counter()
        if self.active_panel == key and self.open_panels[-1] == key:
            return
        self.active_panel = key
        self.open_panels.remove(key)
        self.open_panels.append(key)
        if key == "object":
            self.settings.active_effect = "rings"
            self.open_effect_settings = "rings"
        elif key == "shape":
            if self.settings.active_effect == "rings":
                self.settings.active_effect = "stars"
            self.open_effect_settings = self.settings.active_effect
        self._refresh_panel_layers()
        self._update_effect_button_variants()
        self.settings.open_panels = list(self.open_panels)
        self.store.save()
        self._scene_dirty = True

    def _update_effect_button_variants(self) -> None:
        any_shuffle = self.settings.shape_shuffle or self.settings.object_shuffle
        for key, btn in (*self.shape_effect_buttons.items(), *self.object_effect_buttons.items()):
            panel = "object" if key == "rings" else "shape"
            if key == self.settings.active_effect and panel in self.open_panels:
                btn.set_variant("inspect" if any_shuffle else "active")
            elif key == self.settings.active_effect and not any_shuffle:
                btn.set_variant("active")
            else:
                btn.set_variant("secondary")

    def _refresh_panel_layers(self) -> None:
        for key in self.open_panels:
            self._panel_cards[key].lift()
            self._panel_close_labels[key].lift()
        self._glass_rects = [self._panel_rects[key] for key in self.open_panels if key in self._panel_rects]
        self._visible_card_rects = list(self._top_card_rects)
        self._open_settings_rect = self._get_open_settings_panel_rect()

    def _close_panel(self, key: str) -> None:
        if key not in self.open_panels:
            return
        self.open_panels.remove(key)
        self.active_panel = self.open_panels[-1] if self.open_panels else None
        if not self.open_panels:
            self.open_effect_settings = None
        elif self.active_panel == "object":
            self.settings.active_effect = "rings"
            self.open_effect_settings = "rings"
        elif self.active_panel == "shape":
            if self.settings.active_effect == "rings":
                self.settings.active_effect = "stars"
            self.open_effect_settings = self.settings.active_effect
        self.settings.open_panels = list(self.open_panels)
        self.store.save()
        self._layout_scene_windows(max(400, self.scroll_canvas.winfo_width()))
        self._update_effect_button_variants()

    def _start_panel_drag(self, key: str, event: tk.Event) -> None:
        self._focus_panel(key)
        rect = self._panel_rects.get(key)
        if rect is None:
            return
        self._dragging_panel = key
        px = event.x_root - self.scroll_canvas.winfo_rootx()
        py = event.y_root - self.scroll_canvas.winfo_rooty()
        self._drag_origin = (
            self.scroll_canvas.canvasx(px), self.scroll_canvas.canvasy(py),
            float(rect[0]), float(rect[1]),
        )

    def _drag_panel(self, event: tk.Event) -> None:
        if self._dragging_panel is None or self._drag_origin is None:
            return
        key = self._dragging_panel
        mouse_x, mouse_y, x0, y0 = self._drag_origin
        cw = max(400, self.scroll_canvas.winfo_width())
        ch = max(320, self.scroll_canvas.winfo_height())
        outer_w = self._panel_sizes[key][0]
        px = event.x_root - self.scroll_canvas.winfo_rootx()
        py = event.y_root - self.scroll_canvas.winfo_rooty()
        x = round(max(160, min(cw - outer_w - 8, x0 + self.scroll_canvas.canvasx(px) - mouse_x)))
        y = round(max(8, min(ch - 32, y0 + self.scroll_canvas.canvasy(py) - mouse_y)))
        self.settings.panel_positions[key] = [round(x / cw, 4), round(y / ch, 4)]
        self._position_panel(key, x, y)
        self._refresh_panel_layers()
        self._scene_dirty = True
        self._last_activity = time.perf_counter()

    def _finish_panel_drag(self, _event: tk.Event) -> None:
        if self._dragging_panel is not None:
            self.store.save()
        self._dragging_panel = None
        self._drag_origin = None

    def _on_mousewheel(self, event: tk.Event) -> None:
        delta = -1 * int(event.delta / 120) if event.delta else 0
        if delta != 0:
            self.scroll_canvas.yview_scroll(delta, "units")
            self._place_panel_shells()

    def _record_activity(self, _event: tk.Event) -> None:
        self._last_activity = time.perf_counter()

    def _scroll_scene(self, *args: str) -> None:
        self.scroll_canvas.yview(*args)
        self._place_panel_shells()

    def _sync_scene_scroll(self, first: str, last: str) -> None:
        self.scrollbar.set(first, last)
        self._place_panel_shells()

    def _place_panel_shells(self) -> None:
        offset = self.scroll_canvas.canvasy(0)
        for key in self.open_panels:
            rect = self._panel_rects.get(key)
            if rect is not None:
                self._panel_shells[key].place_configure(
                    x=rect[0],
                    y=round(rect[1] - offset),
                )

    # ------------------------------------------------------------------
    # Dialogy: Nahrát CSV, Vybrat kameru, Reset (vždy uprostřed obrazovky!)
    # ------------------------------------------------------------------
    def open_csv_dialog(self) -> tk.Toplevel:
        p = self.palette
        dlg = tk.Toplevel(self.root)
        dlg.title("Nahrát CSV – Ukázkové pózy nebo vlastní soubor")
        dlg.minsize(480, 340)
        dlg.configure(bg=p.bg_primary, padx=18, pady=16)
        dlg.transient(self.root)
        center_window_on_screen(dlg, 640, 400)

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

            for w_item in (card, img_lbl, t_lbl, s_lbl):
                w_item.bind("<Button-1>", lambda _e, fn=_pick_sample: fn())

        bottom_row = tk.Frame(dlg, bg=p.bg_primary)
        bottom_row.pack(fill="x")

        btn_browse = HoverButton(
            bottom_row,
            text="📁  Nahrát vlastní .csv z počítače...",
            command=lambda: self._browse_csv_file(dlg),
            palette=p,
            variant="active",
            font_size=10,
            bold=True,
            padx=16,
            pady=8,
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
        dlg.minsize(420, 260)
        dlg.configure(bg=p.bg_primary, padx=18, pady=16)
        dlg.transient(self.root)
        center_window_on_screen(dlg, 520, 320)

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

        def show_cameras(cameras: list) -> None:
            for child in ports_frame.winfo_children():
                child.destroy()
            for cam in cameras:
                is_curr = (
                    self.settings.source_type == "camera"
                    and self.settings.camera_port == cam.port
                )
                label = (
                    "Virtuální ToF kamera (simulace)"
                    if cam.is_simulated else f"Kamera na portu {cam.port}"
                )
                btn = HoverButton(
                    ports_frame,
                    text=f"🎥  {label}",
                    command=lambda port=cam.port: self._pick_camera_port(port, dlg),
                    palette=p,
                    variant="active" if is_curr else "secondary",
                    font_size=10,
                    bold=True,
                    pady=8,
                )
                btn.pack(anchor="w", pady=4)

        # Virtuální zdroj je dostupný hned. Fyzické porty se zkoušejí mimo
        # hlavní vlákno, protože otevření některých ovladačů trvá sekundy.
        show_cameras(discover_camera_ports(max_ports=0))
        loading = tk.Label(
            ports_frame, text="Hledám připojené kamery…",
            bg=p.bg_primary, fg=p.text_secondary,
            font=(METRICS.font_family, METRICS.font_size_small),
        )
        loading.pack(anchor="w", pady=(8, 0))
        results: queue.SimpleQueue[list] = queue.SimpleQueue()

        def scan_ports() -> None:
            results.put(discover_camera_ports())

        def poll_ports() -> None:
            if not dlg.winfo_exists():
                return
            try:
                cameras = results.get_nowait()
            except queue.Empty:
                dlg.after(80, poll_ports)
                return
            show_cameras(cameras)

        threading.Thread(target=scan_ports, daemon=True).start()
        dlg.after(80, poll_ports)

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
        """Otevře potvrzovací okno resetu přesně uprostřed obrazovky (bod 4)."""
        p = self.palette
        dlg = tk.Toplevel(self.root)
        dlg.title("Resetovat možnosti")
        dlg.resizable(False, False)
        dlg.configure(bg=p.bg_primary, padx=22, pady=20)
        dlg.transient(self.root)
        center_window_on_screen(dlg, 440, 195)

        lbl = tk.Label(
            dlg,
            text="Opravdu chceš vrátit všechna nastavení na jejich výchozí (první) hodnotu?",
            font=(METRICS.font_family, METRICS.font_size_body, "bold"),
            bg=p.bg_primary,
            fg=p.text_primary,
            wraplength=390,
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
        self.open_panels = []
        self.active_panel = None
        self.open_effect_settings = None
        self.graffiti_widget.settings = self.settings
        self.engine.notify_graffiti_changed()

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

        self.apply_theme(self.settings.theme_mode, save=False, animate=False)
        self.refresh_all_states()
        if dlg is not None and dlg.winfo_exists():
            dlg.destroy()

    # ------------------------------------------------------------------
    # Správa výstupního okna, Fištróna a hlavní smyčka
    # ------------------------------------------------------------------
    def _button_center_on_scene(self) -> tuple[float, float]:
        """Převede skutečný střed tlačítka do souřadnic scény."""
        btn = self.btn_play_output
        if btn.winfo_width() <= 1 or self.scroll_canvas.winfo_width() <= 1:
            cw = max(400, self.scroll_canvas.winfo_width())
            ch = max(320, self.scroll_canvas.winfo_height())
            return cw * 0.5, ch + 20.0
        return (
            btn.winfo_rootx() - self.scroll_canvas.winfo_rootx() + btn.winfo_width() * 0.5,
            btn.winfo_rooty() - self.scroll_canvas.winfo_rooty() + btn.winfo_height() * 0.5,
        )

    def _on_play_button_hover(self, hovered: bool) -> None:
        btn_center = self._button_center_on_scene()
        if hovered:
            self.fistron.state = "button_ready"
            self.fistron.target_x = btn_center[0]
            self.fistron.target_y = btn_center[1] - 92.0

    def on_smash_play_button(self) -> None:
        """Kliknutí na 3D tlačítko: Fištrón do něj praští a zapne nebo ukončí živý výstup."""
        self.fistron.trigger_button_smash(*self._button_center_on_scene())
        if self._pending_output_action is not None:
            self.root.after_cancel(self._pending_output_action)
        self.root.after(self.OUTPUT_IMPACT_DELAY_MS, self.btn_play_output.start_impact)
        self._pending_output_action = self.root.after(
            self.OUTPUT_ACTION_DELAY_MS, self._finish_smash_output
        )

    def _finish_smash_output(self) -> None:
        self._pending_output_action = None
        if self.root.winfo_exists():
            self.toggle_output_window()

    def toggle_output_window(self) -> OutputDisplayWindow | None:
        """Pokud výstup běží, ukončí ho (bod 2); pokud neběží, otevře okno živého výstupu."""
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        ):
            self.output_window.close()
            return None
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

    def _step_scene_and_fistron(self, dt: float, render: bool = True) -> bool:
        """Aktualizuje přechod dne a noci, poušť a kresleného Fištróna."""
        if abs(self._target_light_progress - self._light_progress) > 0.002:
            step = dt * 1.4
            if self._target_light_progress > self._light_progress:
                self._light_progress = min(
                    self._target_light_progress, self._light_progress + step
                )
            else:
                self._light_progress = max(
                    self._target_light_progress, self._light_progress - step
                )
        palette_step = round(self._light_progress * 20.0) / 20.0
        palette_updated = self._last_palette_step != palette_step
        detail_changed = round(palette_step * 8) != self._last_detail_palette_step
        if palette_updated:
            self._apply_interpolated_palette(palette_step)
        self.btn_theme.set_progress(self._light_progress, self.palette)

        cw = max(400, self.scroll_canvas.winfo_width())
        ch = max(320, self.scroll_canvas.winfo_height())
        panel_rect = self._get_open_settings_panel_rect()
        settings_open = panel_rect is not None

        home_x = max(82.0, min(160.0, cw * 0.16))
        if self._glass_rects:
            home_x = max(82.0, min(home_x, min(rect[0] for rect in self._glass_rects) - 82.0))
        home_center = (home_x, max(220.0, min(ch - 92.0, ch * 0.78)))
        stage_center = (min(cw - 125.0, home_center[0] + 180.0), home_center[1] - 5.0)
        effect_names = dict((*SHAPE_EFFECTS, *OBJECT_EFFECTS))
        self.scroll_canvas.coords(
            self._projection_effect_title, stage_center[0], stage_center[1] - 75.0
        )
        self.scroll_canvas.itemconfigure(
            self._projection_effect_title,
            text=effect_names.get(self.settings.active_effect, self.settings.active_effect),
        )
        button_center = self._button_center_on_scene()

        self.fistron.update(
            dt=dt,
            light_progress=self._light_progress,
            settings_open=settings_open,
            panel_rect=panel_rect,
            button_hovered=self.btn_play_output.is_hovered,
            button_center=button_center,
            stage_center=stage_center,
            home_center=home_center,
            panel_dragging=self._dragging_panel is not None,
            idle_time=max(0.0, time.perf_counter() - self._last_activity),
            viewport_width=cw,
        )

        if not render or (palette_updated and detail_changed and 0.0 < palette_step < 1.0):
            if render:
                self._scene_dirty = True
            return False

        # Vykreslení dun, prosklených panelů a hologramu.
        # Výška kresleného pozadí nesmí záviset na otevření panelu. Jinak se
        # při změně scrollregionu přepočítají duny a celá poušť opticky poskočí.
        scene_h = max(ch, METRICS.default_window_height + 300)
        self._scene_photo = render_complete_scene_photo(
            width=cw,
            height=scene_h,
            light_progress=self._light_progress,
            active_effect=self.settings.active_effect,
            primary_color_key=self.settings.primary_color,
            fistron=self.fistron,
            stage_center=stage_center,
            card_rects=self._visible_card_rects,
            glass_rects=tuple(self._glass_rects),
            active_panel_rect=panel_rect,
            palette=self.palette,
            orbit_direction=self._orbit_direction,
        )
        self.scroll_canvas.itemconfigure(
            self._scene_image_id, image=self._scene_photo
        )

        # Textové partikly 'BUM!' / 'PRÁSK!' při úderu do tlačítka
        self.scroll_canvas.delete("fistron_text_fx")
        for p in self.fistron.particles:
            if p.kind == "text":
                self.scroll_canvas.create_text(
                    p.x,
                    p.y,
                    text=p.text,
                    fill=p.color,
                    font=(METRICS.font_family, round(p.size), "bold"),
                    tags="fistron_text_fx",
                )
        return True

    def _schedule_loop(self) -> None:
        if not self.root.winfo_exists():
            return
        now = time.perf_counter()
        elapsed_ms = (now - self._started_at) * 1000.0
        delta_ms = max(1.0, (now - self._last_tick) * 1000.0)
        self._last_tick = now
        inst_fps = 1000.0 / max(1.0, delta_ms)
        self._fps_estimate = self._fps_estimate * 0.9 + inst_fps * 0.1

        main_visible = self.root.state() != "iconic"
        render_scene = main_visible and (
            self._scene_dirty or (now - self._last_scene_render) >= (1.0 / 30.0)
        )
        scene_rendered = self._step_scene_and_fistron(
            min(0.08, delta_ms / 1000.0), render_scene
        )
        if scene_rendered:
            self._last_scene_render = now
            self._scene_dirty = False

        active_eff = self.settings.active_effect
        if (
            self.output_window is not None
            and self.output_window.window.winfo_exists()
        ):
            active_eff = self.output_window.render_tick(elapsed_ms, delta_ms)

        if now - self._last_status_update >= 0.35:
            self._last_status_update = now
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

        self.root.after(16 if main_visible or self.output_window is not None else 80, self._schedule_loop)

    def shutdown(self) -> None:
        if self._pending_output_action is not None:
            self.root.after_cancel(self._pending_output_action)
            self._pending_output_action = None
        if self.root.winfo_exists():
            try:
                if bool(self.root.attributes("-fullscreen")):
                    self.settings.window_state = "fullscreen"
                elif self.root.state() == "zoomed":
                    self.settings.window_state = "zoomed"
                else:
                    self.settings.window_state = "normal"
                    self._last_normal_geometry = self.root.geometry()
                self.settings.window_geometry = self._last_normal_geometry
            except tk.TclError:
                pass
        self.store.save()
        if self.output_window is not None:
            self.output_window.close()
        self.engine.close()
        if self.root.winfo_exists():
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
