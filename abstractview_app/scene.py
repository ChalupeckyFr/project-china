"""Grafická scéna s ostrou pouští, skleněnými panely a kresleným Fištrónem."""

from __future__ import annotations

import base64
import math
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from abstractview_app.theme import (
    PRESET_COLOR_MAP,
    ThemePalette,
    hex_to_rgb,
    lerp_rgb,
)

_AA_IMAGE_CACHE: dict[tuple, tk.PhotoImage] = {}
_DUNE_BG_CACHE: dict[tuple, NDArray[np.uint8]] = {}
_FISTRON_SPRITE_CACHE: dict[tuple, NDArray[np.uint8]] = {}


def clear_tk_photo_cache() -> None:
    """Odstraní snímky vázané na předchozí instanci Tcl/Tk."""
    _AA_IMAGE_CACHE.clear()


def _clear_cache_if_large() -> None:
    if len(_AA_IMAGE_CACHE) > 400:
        _AA_IMAGE_CACHE.clear()
    if len(_DUNE_BG_CACHE) > 6:
        _DUNE_BG_CACHE.clear()
    if len(_FISTRON_SPRITE_CACHE) > 96:
        _FISTRON_SPRITE_CACHE.clear()


def _alpha_composite_roi(
    dst_rgb: NDArray[np.uint8],
    src_rgba: NDArray[np.uint8],
    center_x: float,
    center_y: float,
) -> None:
    """Vloží RGBA sprite do RGB obrazu s alfa-blendingem a ořezem na hranicích."""
    dh, dw, _ = dst_rgb.shape
    sh, sw, _ = src_rgba.shape
    x0 = round(center_x - sw * 0.5)
    y0 = round(center_y - sh * 0.5)
    x1 = x0 + sw
    y1 = y0 + sh

    cx0 = max(0, x0)
    cy0 = max(0, y0)
    cx1 = min(dw, x1)
    cy1 = min(dh, y1)
    if cx0 >= cx1 or cy0 >= cy1:
        return

    sx0 = cx0 - x0
    sy0 = cy0 - y0
    sx1 = sx0 + (cx1 - cx0)
    sy1 = sy0 + (cy1 - cy0)

    roi_dst = dst_rgb[cy0:cy1, cx0:cx1]
    roi_src = src_rgba[sy0:sy1, sx0:sx1]
    alpha = roi_src[:, :, 3:4].astype(np.float32) * (1.0 / 255.0)
    blended = (
        roi_src[:, :, :3].astype(np.float32) * alpha
        + roi_dst.astype(np.float32) * (1.0 - alpha)
    )
    dst_rgb[cy0:cy1, cx0:cx1] = blended.astype(np.uint8)


def render_aa_slider_photo(
    width: int,
    height: int,
    ratio: float,
    hovered: bool,
    palette: ThemePalette,
) -> tk.PhotoImage:
    """Vykreslí hladký anti-aliased posuvník s kulatým kolečkem bez pixelace."""
    w = max(48, int(width))
    h = max(22, int(height))
    scale = 2
    key = (
        "slider_alpha", w, h, round(ratio, 4), hovered,
        palette.slider_track, palette.slider_fill, palette.border,
        palette.accent, palette.slider_thumb_hover if hovered else palette.slider_thumb,
    )
    cached = _AA_IMAGE_CACHE.get(key)
    if cached is not None:
        return cached
    _clear_cache_if_large()
    img = np.zeros((h * scale, w * scale, 4), dtype=np.uint8)
    cy = h * scale // 2
    left = 12 * scale
    right = (w - 12) * scale
    tx = round(left + max(0.0, min(1.0, ratio)) * (right - left))
    cv2.line(img, (left, cy), (right, cy), (*hex_to_rgb(palette.slider_track), 255), 6 * scale, cv2.LINE_AA)
    if tx > left:
        cv2.line(img, (left, cy), (tx, cy), (*hex_to_rgb(palette.slider_fill), 255), 6 * scale, cv2.LINE_AA)
    rad = round((8.6 if hovered else 7.8) * scale)
    cv2.circle(img, (tx, cy + 2), rad + 2, (*hex_to_rgb(palette.border), 255), -1, cv2.LINE_AA)
    cv2.circle(img, (tx, cy), rad, (*hex_to_rgb(palette.accent), 255), -1, cv2.LINE_AA)
    cv2.circle(
        img, (tx, cy), max(1, rad - 4),
        (*hex_to_rgb(palette.slider_thumb_hover if hovered else palette.slider_thumb), 255),
        -1, cv2.LINE_AA,
    )
    out = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
    alpha = out[:, :, 3].astype(np.float32)
    visible = alpha > 0
    rgb = out[:, :, :3].astype(np.float32)
    rgb[visible] *= (255.0 / alpha[visible])[:, None]
    out[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    ok, png = cv2.imencode(".png", cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
    if not ok:
        raise ValueError("Nepodařilo se vykreslit posuvník.")
    photo = tk.PhotoImage(data=base64.b64encode(png.tobytes()), format="png")
    _AA_IMAGE_CACHE[key] = photo
    return photo


def render_aa_pill_button_photo(
    width: int, height: int, bg_hex: str, border_hex: str,
) -> tk.PhotoImage:
    """Vrátí zaoblené tlačítko s průhledným a vyhlazeným okolím."""
    w = max(36, int(width))
    h = max(24, int(height))
    key = ("pill_alpha", w, h, bg_hex, border_hex)
    cached = _AA_IMAGE_CACHE.get(key)
    if cached is not None:
        return cached

    _clear_cache_if_large()
    scale = 2
    rgba = np.zeros((h * scale, w * scale, 4), dtype=np.uint8)
    cy = h * scale // 2
    r = max(1, round((h * .5 - 1.5) * scale))
    x1, x2 = r + scale, w * scale - r - scale
    cv2.line(rgba, (x1, cy), (x2, cy), (*hex_to_rgb(border_hex), 255), 2 * r, cv2.LINE_AA)
    cv2.line(rgba, (x1, cy), (x2, cy), (*hex_to_rgb(bg_hex), 255), max(1, 2 * r - 3 * scale), cv2.LINE_AA)
    rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    alpha = rgba[:, :, 3].astype(np.float32)
    visible = alpha > 0
    rgb = rgba[:, :, :3].astype(np.float32)
    rgb[visible] *= (255.0 / alpha[visible])[:, None]
    rgba[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    ok, png = cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    if not ok:
        raise ValueError("Nepodařilo se vykreslit tlačítko.")
    photo = tk.PhotoImage(data=base64.b64encode(png.tobytes()), format="png")
    _AA_IMAGE_CACHE[key] = photo
    return photo


def render_aa_color_swatch_photo(
    size: int,
    color_hex: str,
    selected: bool,
    hovered: bool,
    card_bg_hex: str,
    ring_hex: str,
) -> tk.PhotoImage:
    """Vykreslí hladké kulaté barevné políčko bez písmen uvnitř."""
    s = max(20, int(size))
    key = ("swatch_sdf", s, color_hex, selected, hovered, card_bg_hex, ring_hex)
    cached = _AA_IMAGE_CACHE.get(key)
    if cached is not None:
        return cached

    _clear_cache_if_large()
    y, x = np.mgrid[0:s, 0:s].astype(np.float32)
    c = (s - 1) * 0.5
    d = np.hypot(x - c, y - c)

    card_rgb = np.array(hex_to_rgb(card_bg_hex), dtype=np.float32)
    col_rgb = np.array(hex_to_rgb(color_hex), dtype=np.float32)
    ring_rgb = np.array(hex_to_rgb(ring_hex), dtype=np.float32)

    img = np.broadcast_to(card_rgb[None, None, :], (s, s, 3)).copy()
    outer_r = s * 0.5 - 1.5

    if selected:
        a_ring = np.clip(0.5 - (d - outer_r), 0.0, 1.0)[:, :, None]
        img = img * (1.0 - a_ring) + ring_rgb[None, None, :] * a_ring
        a_gap = np.clip(0.5 - (d - (outer_r - 2.0)), 0.0, 1.0)[:, :, None]
        img = img * (1.0 - a_gap) + card_rgb[None, None, :] * a_gap
        a_col = np.clip(0.5 - (d - (outer_r - 3.8)), 0.0, 1.0)[:, :, None]
        img = img * (1.0 - a_col) + col_rgb[None, None, :] * a_col
    else:
        subtle = card_rgb * 0.65 + ring_rgb * 0.35
        a_ring = np.clip(0.5 - (d - (outer_r - 1.0)), 0.0, 1.0)[:, :, None]
        img = img * (1.0 - a_ring) + subtle[None, None, :] * a_ring
        a_col = np.clip(0.5 - (d - (outer_r - 2.4)), 0.0, 1.0)[:, :, None]
        img = img * (1.0 - a_col) + col_rgb[None, None, :] * a_col

    out = np.clip(img, 0, 255).astype(np.uint8)
    ppm = f"P6 {s} {s} 255\n".encode("ascii") + out.tobytes()
    photo = tk.PhotoImage(width=s, height=s, data=ppm, format="PPM")
    _AA_IMAGE_CACHE[key] = photo
    return photo


def render_aa_toggle_switch_photo(
    width: int,
    height: int,
    progress: float,
    card_bg_hex: str,
) -> tk.PhotoImage:
    """Vykreslí hladký posuvný přepínač (toggle switch) s kolečkem pro dark <-> light."""
    w = max(64, int(width))
    h = max(28, int(height))
    step_p = round(max(0.0, min(1.0, float(progress))) * 20) / 20.0
    key = ("toggle_sdf", w, h, step_p, card_bg_hex)
    cached = _AA_IMAGE_CACHE.get(key)
    if cached is not None:
        return cached

    _clear_cache_if_large()
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    card_rgb = np.array(hex_to_rgb(card_bg_hex), dtype=np.float32)
    track_rgb = np.array(
        lerp_rgb((24, 42, 78), (222, 198, 162), step_p), dtype=np.float32
    )
    border_rgb = np.array(
        lerp_rgb((68, 108, 178), (186, 156, 114), step_p), dtype=np.float32
    )
    knob_rgb = np.array(
        lerp_rgb((228, 240, 255), (255, 206, 68), step_p), dtype=np.float32
    )

    img = np.broadcast_to(card_rgb[None, None, :], (h, w, 3)).copy()
    cy = (h - 1) * 0.5
    cx = (w - 1) * 0.5
    rad = h * 0.5 - 2.0
    half_len = max(0.0, w * 0.5 - rad - 2.0)

    dx = np.maximum(np.abs(x - cx) - half_len, 0.0)
    d_cap = np.hypot(dx, y - cy) - rad

    a_b = np.clip(0.5 - d_cap, 0.0, 1.0)[:, :, None]
    img = img * (1.0 - a_b) + border_rgb[None, None, :] * a_b

    a_t = np.clip(0.5 - (d_cap + 1.5), 0.0, 1.0)[:, :, None]
    img = img * (1.0 - a_t) + track_rgb[None, None, :] * a_t

    x1 = cx - half_len
    x2 = cx + half_len
    knob_x = x1 + step_p * (x2 - x1)
    knob_r = rad - 3.2
    d_knob = np.hypot(x - knob_x, y - cy) - knob_r
    a_k = np.clip(0.5 - d_knob, 0.0, 1.0)[:, :, None]
    img = img * (1.0 - a_k) + knob_rgb[None, None, :] * a_k

    if step_p < 0.45:
        cut_x = knob_x + knob_r * 0.38
        cut_y = cy - knob_r * 0.18
        d_cut = np.hypot(x - cut_x, y - cut_y) - knob_r * 0.72
        a_c = np.clip(0.5 - d_cut, 0.0, 1.0)[:, :, None] * a_k
        img = img * (1.0 - a_c) + track_rgb[None, None, :] * a_c

    out = np.clip(img, 0, 255).astype(np.uint8)
    ppm = f"P6 {w} {h} 255\n".encode("ascii") + out.tobytes()
    photo = tk.PhotoImage(width=w, height=h, data=ppm, format="PPM")
    _AA_IMAGE_CACHE[key] = photo
    return photo


def render_aa_3d_button_photo(
    width: int,
    height: int,
    active: bool,
    hovered: bool,
    pressed: bool,
    bg_hex: str,
) -> tk.PhotoImage:
    """Vykreslí dokonale hladké 3D oválné tlačítko bez jakékoliv pixelace."""
    w = max(160, int(width))
    h = max(42, int(height))
    key = ("btn3d", w, h, active, hovered, pressed, bg_hex)
    cached = _AA_IMAGE_CACHE.get(key)
    if cached is not None:
        return cached

    _clear_cache_if_large()
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    bg_rgb = np.array(hex_to_rgb(bg_hex), dtype=np.float32)
    img = np.broadcast_to(bg_rgb[None, None, :], (h, w, 3)).copy()

    def blend_capsule(
        cy_c: float,
        half_len: float,
        rad: float,
        rgb_arr: NDArray[np.float32],
        aa: float = 1.1,
    ) -> None:
        nonlocal img
        cx_c = w * 0.5
        dx = np.maximum(np.abs(x - cx_c) - half_len, 0.0)
        dy = y - cy_c
        d = np.hypot(dx, dy) - rad
        a = np.clip(0.5 - d / aa, 0.0, 1.0)[:, :, None]
        img = img * (1.0 - a) + rgb_arr * a

    half_l = max(20.0, w * 0.5 - 24.0)
    rad = h * 0.36
    press_dy = 3.2 if pressed else (1.0 if hovered else 0.0)

    # 1. Měkký stín pod tlačítkem
    blend_capsule(
        h * 0.58 + 3.0,
        half_l + 2.0,
        rad + 1.0,
        np.array([8.0, 13.0, 24.0], dtype=np.float32)[None, None, :],
        aa=2.4,
    )
    # 2. 3D kovový podstavec
    blend_capsule(
        h * 0.56,
        half_l + 1.0,
        rad,
        np.array([45.0, 58.0, 82.0], dtype=np.float32)[None, None, :],
    )

    if active and not hovered:
        wall_c = np.array([5.0, 112.0, 82.0], dtype=np.float32)
        top_c1 = np.array([52.0, 211.0, 153.0], dtype=np.float32)
        top_c2 = np.array([16.0, 185.0, 129.0], dtype=np.float32)
    else:
        wall_c = np.array([159.0, 18.0, 57.0], dtype=np.float32)
        top_c1 = (
            np.array([251.0, 113.0, 133.0], dtype=np.float32)
            if hovered
            else np.array([244.0, 63.0, 94.0], dtype=np.float32)
        )
        top_c2 = (
            np.array([225.0, 29.0, 72.0], dtype=np.float32)
            if hovered
            else np.array([190.0, 18.0, 60.0], dtype=np.float32)
        )

    # 3. 3D boční stěna tlačítka
    blend_capsule(
        h * 0.52 + press_dy * 0.4, half_l, rad - 1.0, wall_c[None, None, :]
    )

    # 4. 3D horní kopule s plynulým přechodem a leskem
    cy_top = h * 0.43 + press_dy
    vg = np.clip((y - (cy_top - rad)) / (2.0 * rad), 0.0, 1.0)[:, :, None]
    dome_rgb = top_c1[None, None, :] * (1.0 - vg) + top_c2[None, None, :] * vg
    blend_capsule(cy_top, half_l, rad - 1.5, dome_rgb)

    shine_rgb = (
        dome_rgb * 0.72
        + np.array([255.0, 255.0, 255.0], dtype=np.float32)[None, None, :]
        * 0.28
    )
    blend_capsule(
        cy_top - rad * 0.46, half_l - 12.0, rad * 0.30, shine_rgb, aa=1.5
    )

    out = np.clip(img, 0, 255).astype(np.uint8)
    ppm = f"P6 {w} {h} 255\n".encode("ascii") + out.tobytes()
    photo = tk.PhotoImage(width=w, height=h, data=ppm, format="PPM")
    _AA_IMAGE_CACHE[key] = photo
    return photo


def render_fistron_sprite_rgba(
    pose: str, facing_left: bool = False,
) -> NDArray[np.uint8]:
    """Načte a uchová kreslenou pózu Fištróna včetně projekčních obrázků."""
    valid = {"sleep", "push", "walk", "hands_up", "focus", "exhausted"}
    if pose not in valid:
        raise ValueError(f"Neznámá póza Fištróna: {pose}")
    key = (pose, facing_left)
    cached = _FISTRON_SPRITE_CACHE.get(key)
    if cached is not None:
        return cached

    asset_path = Path(__file__).resolve().parent / "assets" / f"fistron_{pose}.png"
    bgra = cv2.imdecode(np.frombuffer(asset_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if bgra is None or bgra.ndim != 3 or bgra.shape[2] != 4:
        raise FileNotFoundError(f"Chybí obrázek pózy Fištróna: {asset_path}")
    rgba = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA)
    points = cv2.findNonZero((rgba[:, :, 3] > 24).astype(np.uint8))
    if points is None:
        raise ValueError(f"Prázdný obrázek pózy Fištróna: {asset_path}")
    x, y, w, h = cv2.boundingRect(points)
    crop = rgba[y:y+h, x:x+w]
    max_w, max_h = (
        (150, 120) if pose == "sleep" else
        (145, 178) if pose == "push" else (162, 178)
    )
    scale = min(max_w / w, max_h / h)
    dw, dh = max(1, round(w * scale)), max(1, round(h * scale))
    sprite = cv2.resize(crop, (dw, dh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((190, 200, 4), dtype=np.uint8)
    x0 = 190 - dw if pose == "push" else (190 - dw) // 2
    y0 = 184 - dh
    canvas[y0:y0+dh, x0:x0+dw] = sprite
    if facing_left:
        canvas = cv2.flip(canvas, 1)
    _FISTRON_SPRITE_CACHE[key] = canvas
    return canvas


def _render_dunes_base(
    width: int,
    height: int,
    light_progress: float,
    active_effect: str,
    primary_color_key: str,
    orbit_direction: int = 1,
) -> NDArray[np.uint8]:
    """Ostrá krajina v plném rozlišení; náročné plochy kreslí OpenCV polygony."""
    t = round(max(0.0, min(1.0, light_progress)) * 25) / 25.0
    key = (width, height, t, active_effect, primary_color_key, orbit_direction)
    cached = _DUNE_BG_CACHE.get(key)
    if cached is not None:
        return cached
    _clear_cache_if_large()
    w, h = width, height

    def color(dark: tuple[int, int, int], light: tuple[int, int, int]) -> tuple[int, int, int]:
        return lerp_rgb(dark, light, t)

    top = np.array(color((10, 20, 48), (186, 88, 46)), dtype=np.float32)
    bottom = np.array(color((42, 84, 152), (246, 184, 118)), dtype=np.float32)
    vertical = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    sky = (top[None, :] * (1.0 - vertical) + bottom[None, :] * vertical).astype(np.uint8)
    img = np.broadcast_to(sky[:, None, :], (h, w, 3)).copy()

    phase = t if orbit_direction >= 0 else 1.0 - t
    incoming = (0.08 + 0.36 * phase, 0.80 - 0.40 * math.sin(phase * math.pi * 0.5))
    outgoing = (0.44 + 0.46 * phase, 0.40 + 0.40 * math.sin(phase * math.pi * 0.5))
    sun = incoming if orbit_direction >= 0 else outgoing
    moon = outgoing if orbit_direction >= 0 else incoming

    if t > 0.01:
        center = (round(sun[0] * w), round(sun[1] * h))
        radius = max(9, round(min(w, h) * 0.045))
        cv2.circle(img, center, radius + 9, color((100, 93, 126), (251, 205, 138)), -1, cv2.LINE_AA)
        cv2.circle(img, center, radius, (255, 243, 210), -1, cv2.LINE_AA)
    if t < 0.99:
        center = (round(moon[0] * w), round(moon[1] * h))
        radius = max(8, round(min(w, h) * 0.029))
        if active_effect == "nebula":
            moon_color = (204, 182, 255)
        elif active_effect == "rings":
            preset = PRESET_COLOR_MAP.get(primary_color_key)
            moon_color = lerp_rgb(preset.rgb if preset else (180, 220, 255), (255, 255, 255), 0.55)
        else:
            moon_color = (227, 237, 255)
        cv2.circle(img, center, radius + 5, color((70, 98, 150), (190, 166, 146)), -1, cv2.LINE_AA)
        cv2.circle(img, center, radius, moon_color, -1, cv2.LINE_AA)

    if t < 0.8:
        for sx, sy, radius in ((.12,.34,3),(.64,.42,3),(.72,.29,3),(.25,.25,2),(.35,.22,2),(.42,.31,2),(.55,.27,2),(.67,.20,2),(.84,.32,2),(.18,.42,2)):
            px, py = round(sx * w), round(sy * h)
            cv2.circle(img, (px, py), radius, (245, 248, 255), -1, cv2.LINE_AA)

    def dune(
        peak_x: float, peak_y: float, left_drop: float, right_drop: float,
        base: tuple[int, int, int], ridge: tuple[int, int, int],
    ) -> None:
        xs = np.arange(0, w + 8, 8, dtype=np.float32)
        nx = xs / max(1, w)
        dx = nx - peak_x
        slopes = np.where(dx < 0, left_drop, right_drop)
        crest = peak_y + slopes * (np.abs(dx) ** 1.28)
        ys = np.rint(crest * h).astype(np.int32)
        contour = np.column_stack((xs.astype(np.int32), ys)).tolist()
        polygon = np.array(contour + [(w, h), (0, h)], dtype=np.int32)
        cv2.fillPoly(img, [polygon], base, lineType=cv2.LINE_AA)
        cv2.polylines(img, [np.array(contour, dtype=np.int32)], False, ridge, 2, cv2.LINE_AA)

    dune(.84, .48, .46, .65, color((30, 63, 120), (174, 77, 38)), color((58, 105, 172), (228, 126, 75)))
    dune(.14, .60, .55, .40, color((36, 73, 139), (213, 112, 62)), color((69, 120, 195), (246, 161, 105)))
    dune(.62, .68, .42, .48, color((20, 43, 91), (177, 76, 39)), color((55, 103, 180), (236, 132, 80)))

    _DUNE_BG_CACHE[key] = img
    return img


def _draw_aa_rounded_rect(
    img: NDArray[np.uint8],
    rect: tuple[int, int, int, int],
    radius: float,
    fill_rgb: tuple[int, int, int],
    border_rgb: tuple[int, int, int],
) -> None:
    """Rychlé zaoblené karty; hrany kreslí OpenCV přímo do cílového obrazu."""
    x1, y1, x2, y2 = rect
    if x2 <= x1 or y2 <= y1:
        return
    r = min(round(radius), (x2 - x1) // 2, (y2 - y1) // 2)

    def fill_rounded(box: tuple[int, int, int, int], rad: int, color: tuple[int, int, int]) -> None:
        xa, ya, xb, yb = box
        cv2.rectangle(img, (xa + rad, ya), (xb - rad, yb), color, -1, cv2.LINE_AA)
        cv2.rectangle(img, (xa, ya + rad), (xb, yb - rad), color, -1, cv2.LINE_AA)
        for cx in (xa + rad, xb - rad):
            for cy in (ya + rad, yb - rad):
                cv2.circle(img, (cx, cy), rad, color, -1, cv2.LINE_AA)

    fill_rounded(rect, r, border_rgb)
    fill_rounded((x1 + 2, y1 + 2, x2 - 2, y2 - 2), max(0, r - 2), fill_rgb)


def _draw_desert_glass_panel(
    img: NDArray[np.uint8],
    rect: tuple[int, int, int, int],
    light_progress: float,
    active: bool = False,
) -> None:
    """A translucent glass window which keeps the desert visible behind controls."""
    x1, y1, x2, y2 = rect
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
    if x2 - x1 < 44 or y2 - y1 < 44:
        return
    roi = img[y1:y2, x1:x2]
    h, w = roi.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    r = min(26, w // 2, h // 2)
    cv2.rectangle(mask, (r, 0), (w-r, h), 255, -1)
    cv2.rectangle(mask, (0, r), (w, h-r), 255, -1)
    for cx in (r, w-r):
        for cy in (r, h-r):
            cv2.circle(mask, (cx, cy), r, 255, -1)
    # The scene remains visible through the glass. Only this panel ROI is blended.
    tint = np.empty_like(roi)
    tint[:] = (24, 43, 76) if light_progress < .5 else (238, 207, 174)
    glass = cv2.addWeighted(roi, .61, tint, .39, 0)
    cv2.copyTo(glass, mask, roi)
    edge = (
        (255, 209, 115) if light_progress < .5 else (102, 49, 22)
    ) if active else (
        (126, 192, 255) if light_progress < .5 else (255, 239, 208)
    )
    outlines, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(roi, outlines, -1, edge, 2 if active else 1, cv2.LINE_AA)
    cv2.line(img, (x1+30, y1+3), (x2-30, y1+3), edge, 2, cv2.LINE_AA)
    cv2.line(img, (x1+22, y1+51), (x2-22, y1+51), edge, 1, cv2.LINE_AA)


def render_aa_rounded_panel_photo(
    width: int, height: int, fill_hex: str, border_hex: str, parent_hex: str
) -> tk.PhotoImage:
    """Zaoblené pozadí kreslicího pole v nativním rozlišení widgetu."""
    w, h = max(60, width), max(60, height)
    key = ("rounded_panel", w, h, fill_hex, border_hex, parent_hex)
    cached = _AA_IMAGE_CACHE.get(key)
    if cached is not None:
        return cached
    _clear_cache_if_large()
    img = np.empty((h, w, 3), dtype=np.uint8)
    img[:] = hex_to_rgb(parent_hex)
    _draw_aa_rounded_rect(
        img, (4, 4, w - 4, h - 4), 16.0,
        hex_to_rgb(fill_hex), hex_to_rgb(border_hex),
    )
    ppm = f"P6 {w} {h} 255\n".encode("ascii") + img.tobytes()
    photo = tk.PhotoImage(width=w, height=h, data=ppm, format="PPM")
    _AA_IMAGE_CACHE[key] = photo
    return photo


def _draw_aa_projection_screen(
    img: NDArray[np.uint8],
    stage_center: tuple[float, float],
    light_progress: float,
) -> None:
    """Vykreslí čisté plátno; název efektu doplňuje ostrý text Tk canvasu."""
    sx, sy = stage_center
    pw, ph = 216, 134
    x1 = round(sx - pw * 0.5)
    y1 = round(sy - ph - 8.0)
    x2 = x1 + pw
    y2 = y1 + ph

    frame_rgb = lerp_rgb((58, 92, 152), (142, 112, 82), light_progress)
    # Nožičky stojanu (vyhlazené přes LINE_AA)
    cv2.line(
        img,
        (round(sx - 46), y2),
        (round(sx - 62), y2 + 24),
        frame_rgb,
        3,
        cv2.LINE_AA,
    )
    cv2.line(
        img,
        (round(sx + 46), y2),
        (round(sx + 62), y2 + 24),
        frame_rgb,
        3,
        cv2.LINE_AA,
    )

    # Zaoblená deska promítacího plátna
    _draw_aa_rounded_rect(
        img, (x1, y1, x2, y2), radius=14.0, fill_rgb=(8, 15, 32), border_rgb=frame_rgb
    )

@dataclass
class SmashParticle:
    """Cartoon částice vystřelená při úderu Fištróna do 3D tlačítka."""

    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: str
    kind: str  # 'star', 'spark', 'text'
    life: float = 1.0
    text: str = ""


@dataclass
class FistronCompanion:
    """Stav Fištróna, jeho pelíšku a přechodů mezi kreslenými pózami."""

    x: float = 420.0
    y: float = 380.0
    target_x: float = 420.0
    target_y: float = 380.0
    screen_x: float = 420.0
    screen_y: float = 380.0
    state: str = "sleeping"
    light_move: str = "hands_up"
    move_timer: float = 0.0
    breath_phase: float = 0.0
    smash_timer: float = 0.0
    impact_spawned: bool = False
    dash_trail: list[tuple[float, float, float]] = field(default_factory=list)
    is_dashing: bool = False
    facing_left: bool = False
    panel_on_right: bool = False
    particles: list[SmashParticle] = field(default_factory=list)

    def trigger_button_smash(self, btn_cx: float, btn_cy: float) -> None:
        """Připraví úder přesně nad skutečným středem tlačítka."""
        self.state = "button_windup"
        self.smash_timer = 1.0
        self.impact_spawned = False
        self.x = btn_cx
        self.y = btn_cy - 92.0
        self.target_x = self.x
        self.target_y = self.y

        self.particles.clear()

    def _spawn_impact(self, btn_cx: float, btn_cy: float) -> None:
        self.impact_spawned = True
        colors = (
            "#FACC15",
            "#EF4444",
            "#38BDF8",
            "#4ADE80",
            "#FFFFFF",
            "#FB923C",
        )
        for i in range(28):
            ang = (i / 28.0) * math.tau
            spd = 100.0 + (i % 4) * 31.0
            self.particles.append(
                SmashParticle(
                    x=btn_cx + math.cos(ang) * 10.0,
                    y=btn_cy - 70.0 + math.sin(ang) * 9.0,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd - 35.0,
                    size=20.0 + (i % 4) * 7.0 if i < 18 else 7.0,
                    color=colors[i % len(colors)],
                    kind="dust" if i < 18 else "star",
                    life=0.48 if i < 18 else 0.60,
                )
            )
        self.particles.append(
            SmashParticle(
                x=btn_cx - 48.0,
                y=btn_cy - 52.0,
                vx=-28.0,
                vy=-65.0,
                size=14.0,
                color="#FACC15",
                kind="text",
                life=0.60,
                text="BUM!",
            )
        )
        self.particles.append(
            SmashParticle(
                x=btn_cx + 48.0,
                y=btn_cy - 48.0,
                vx=32.0,
                vy=-60.0,
                size=13.0,
                color="#FFFFFF",
                kind="text",
                life=0.60,
                text="PRÁSK!",
            )
        )

    def update(
        self,
        dt: float,
        light_progress: float,
        settings_open: bool,
        panel_rect: tuple[int, int, int, int] | None,
        button_hovered: bool,
        button_center: tuple[float, float],
        stage_center: tuple[float, float],
        home_center: tuple[float, float] | None = None,
        panel_dragging: bool = False,
        idle_time: float = 0.0,
        viewport_width: float = 960.0,
    ) -> None:
        self.screen_x, self.screen_y = stage_center
        self.breath_phase = (self.breath_phase + dt * 2.4) % math.tau
        self.move_timer += dt

        alive_p: list[SmashParticle] = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 190.0 * dt
            p.life -= dt
            if p.life > 0:
                alive_p.append(p)
        self.particles = alive_p

        self.dash_trail = [
            (tx, ty, life - dt * 4.5)
            for tx, ty, life in self.dash_trail
            if life - dt * 4.5 > 0
        ]

        if self.smash_timer > 0.0:
            self.smash_timer = max(0.0, self.smash_timer - dt)
            if self.smash_timer > 0.67:
                self.state = "button_windup"
            else:
                if not self.impact_spawned:
                    self._spawn_impact(*button_center)
                self.state = "button_smash"
            self.target_x = button_center[0]
            self.target_y = button_center[1] - 92.0
        elif button_hovered:
            self.state = "button_ready"
            self.target_x = button_center[0]
            self.target_y = button_center[1] - 92.0
        elif panel_dragging and settings_open and panel_rect is not None:
            self.state = "pushing_panel"
            px1, py1, px2, py2 = panel_rect
            self.panel_on_right = px1 < 155 and viewport_width - px2 > 155
            self.target_x = (
                float(px2) + 100.0 if self.panel_on_right
                else max(60.0, float(px1) - 100.0)
            )
            self.target_y = float(min(button_center[1] - 90.0, py2 - 80.0, py1 + 148.0))
        else:
            sx, sy = home_center if home_center is not None else stage_center
            self.state = "sleeping" if light_progress < 0.5 else "resting"
            self.target_x = sx
            self.target_y = sy + 6.0

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        self.is_dashing = dist > 20.0 and self.state not in ("button_smash", "button_windup", "pushing_panel")
        if self.is_dashing and abs(dx) > 1.0:
            self.facing_left = dx < 0.0
        if dist > 70.0 and len(self.dash_trail) < 5:
            self.dash_trail.append((self.x, self.y, 0.28))

        travel = min(dist, max(0.0, dt) * 2800.0)
        if dist > 1e-6:
            self.x += dx * (travel / dist)
            self.y += dy * (travel / dist)


def render_complete_scene_photo(
    width: int,
    height: int,
    light_progress: float,
    active_effect: str,
    primary_color_key: str,
    fistron: FistronCompanion,
    stage_center: tuple[float, float],
    card_rects: list[tuple[int, int, int, int]],
    palette: ThemePalette,
    orbit_direction: int = 1,
    glass_rects: tuple[tuple[int, int, int, int], ...] = (),
    active_panel_rect: tuple[int, int, int, int] | None = None,
) -> tk.PhotoImage:
    """Složí poušť, prosklené panely a kreslené pózy Fištróna."""
    w = max(320, int(width))
    h = max(240, int(height))

    base = _render_dunes_base(
        w, h, light_progress, active_effect, primary_color_key, orbit_direction
    )
    frame = base.copy()

    # 1. Promítací plátno bez siluet a obrysových animací.
    _draw_aa_projection_screen(
        frame,
        stage_center=stage_center,
        light_progress=light_progress,
    )

    # 2. Zaoblené pozadí všech viditelných karet nastavení (s měkkým stínem a 20px rohy)
    card_fill = hex_to_rgb(palette.bg_card)
    card_border = hex_to_rgb(palette.border)
    for rect in card_rects:
        if rect in glass_rects:
            _draw_desert_glass_panel(frame, rect, light_progress, rect == active_panel_rect)
        else:
            _draw_aa_rounded_rect(
                frame, rect, radius=20.0, fill_rgb=card_fill, border_rgb=card_border
            )

    # Kreslený Fištrón mění připravené pózy; během přesunu se
    # animuje posunem a drobným nadskakováním.
    pose = (
        "push" if fistron.state == "pushing_panel" else
        "walk" if fistron.is_dashing else
        "sleep" if fistron.state in ("sleeping", "resting") else
        "focus" if fistron.state in ("button_ready", "button_windup") else
        "exhausted" if fistron.state == "button_smash" else
        "hands_up"
    )
    direction = -1 if fistron.facing_left else 1
    bunny_rgba = render_fistron_sprite_rgba(
        pose, facing_left=(pose == "walk" and fistron.facing_left)
        or (pose == "push" and fistron.panel_on_right)
    )
    if fistron.is_dashing:
        for offset in (52, 70, 88):
            x0 = round(fistron.x - direction * offset)
            y0 = round(fistron.y + 38 + offset * 0.15)
            cv2.line(frame, (x0, y0), (x0 + direction * 24, y0), (231, 222, 207), 2, cv2.LINE_AA)
    bob = math.sin(fistron.move_timer * 27.0) * 4.0 if fistron.is_dashing else 0.0
    _alpha_composite_roi(frame, bunny_rgba, fistron.x, fistron.y + bob)

    # 5. Cartoon částice při úderu do 3D tlačítka
    for p in fistron.particles:
        if p.kind != "text":
            col = (242, 232, 211) if p.kind == "dust" else hex_to_rgb(p.color)
            rad = max(2, round(p.size * (0.8 if p.kind == "dust" else 0.5)))
            cv2.circle(
                frame,
                (round(p.x), round(p.y)),
                rad,
                col,
                -1,
                cv2.LINE_AA,
            )
            if p.kind == "dust":
                cv2.circle(
                    frame, (round(p.x), round(p.y)), rad,
                    (174, 157, 139), 2, cv2.LINE_AA,
                )

    ppm = f"P6 {w} {h} 255\n".encode("ascii") + frame.tobytes()
    return tk.PhotoImage(width=w, height=h, data=ppm, format="PPM")

