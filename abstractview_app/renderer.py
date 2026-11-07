"""Vykreslovací engine pro tvarové a objektové efekty + plynulé přechody (Smooth přechod)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pygame
from numpy.typing import NDArray

from abstractview_app.config import AppSettings, ShuffleScheduler
from abstractview_app.samples import (
    LiveCameraDepthSource,
    get_sample_sequence,
    load_custom_csv_sequence,
)
from abstractview_app.theme import PRESET_COLOR_MAP
from project_china.frames import DepthCsvError, DepthSequence
from project_china.morph import (
    ContourShape,
    match_contours,
    morph_contours,
    prepare_contours,
    transition_for_elapsed,
)
from project_china.selection import DepthSelection, select_depth_regions

_BG_DARK_SPACE = (5, 8, 22)
_BLACK_BG = (0, 0, 0)


@dataclass(frozen=True)
class AnatomicalRig:
    """Zjednodušený anatomický model postavy odvozený z aktuální hloubkové masky."""

    has_body: bool
    head_center: tuple[float, float]
    head_radius: float
    torso_top: tuple[float, float]
    torso_bottom: tuple[float, float]
    shoulder_half_width: float
    waist_half_width: float
    left_arm_points: tuple[tuple[float, float], ...]
    right_arm_points: tuple[tuple[float, float], ...]
    left_leg_points: tuple[tuple[float, float], ...]
    right_leg_points: tuple[tuple[float, float], ...]


def extract_anatomical_rig(
    mask: NDArray[np.uint8], surface_size: tuple[int, int]
) -> AnatomicalRig:
    """Z binární hloubkové masky odvodí zjednodušené zóny těla (hlava, V-trup, ruce, nohy)."""
    sw, sh = surface_size
    gh, gw = mask.shape
    ys, xs = np.nonzero(mask)
    if len(xs) < 12:
        cx, cy = sw * 0.5, sh * 0.5
        return AnatomicalRig(
            has_body=False,
            head_center=(cx, cy - sh * 0.25),
            head_radius=28.0,
            torso_top=(cx, cy - sh * 0.14),
            torso_bottom=(cx, cy + sh * 0.08),
            shoulder_half_width=58.0,
            waist_half_width=34.0,
            left_arm_points=((cx - 72.0, cy - 30.0), (cx - 86.0, cy + 20.0)),
            right_arm_points=((cx + 72.0, cy - 30.0), (cx + 86.0, cy + 20.0)),
            left_leg_points=((cx - 28.0, cy + 70.0), (cx - 32.0, cy + 165.0)),
            right_leg_points=((cx + 28.0, cy + 70.0), (cx + 32.0, cy + 165.0)),
        )

    margin = 24.0
    scale = min((sw - 2 * margin) / gw, (sh - 2 * margin) / gh)
    left = (sw - gw * scale) * 0.5
    top = (sh - gh * scale) * 0.5

    def to_scr(gx: float, gy: float) -> tuple[float, float]:
        return (left + (gx + 0.5) * scale, top + (gy + 0.5) * scale)

    min_y, max_y = float(ys.min()), float(ys.max())
    span_y = max(max_y - min_y, 12.0)

    # Střed trupu (v pásmu 25 % až 58 % výšky postavy)
    torso_band = (ys >= min_y + span_y * 0.24) & (ys <= min_y + span_y * 0.58)
    if np.any(torso_band):
        center_gx = float(np.median(xs[torso_band]))
    else:
        center_gx = float(np.median(xs))

    # Hlava: horních 22 % postavy blízko osy trupu
    head_band = (ys <= min_y + span_y * 0.22) & (
        np.abs(xs - center_gx) <= gw * 0.18
    )
    if np.any(head_band):
        head_gx = float(xs[head_band].mean())
        head_gy = float(ys[head_band].mean())
        head_rad_grid = max(
            3.5, float(np.percentile(np.abs(xs[head_band] - head_gx), 85))
        )
    else:
        head_gx = center_gx
        head_gy = min_y + span_y * 0.10
        head_rad_grid = span_y * 0.07

    head_center = to_scr(head_gx, head_gy)
    head_radius = max(18.0, head_rad_grid * scale * 1.15)

    # Trup (V-shape): od ramen (25 % výšky) po pas (56 % výšky)
    torso_top_gy = min_y + span_y * 0.25
    torso_bot_gy = min_y + span_y * 0.56
    shoulder_band = (
        (ys >= min_y + span_y * 0.22)
        & (ys <= min_y + span_y * 0.34)
        & (np.abs(xs - center_gx) <= gw * 0.22)
    )
    if np.any(shoulder_band):
        sh_half_grid = max(
            5.0, float(np.percentile(np.abs(xs[shoulder_band] - center_gx), 82))
        )
    else:
        sh_half_grid = span_y * 0.11

    shoulder_half_w = max(32.0, sh_half_grid * scale * 0.95)
    waist_half_w = shoulder_half_w * 0.62

    # Ruce: body nalevo a napravo od osy trupu v horních 62 % postavy
    arm_region = ys <= min_y + span_y * 0.62
    left_arm_mask = arm_region & (xs < center_gx - sh_half_grid * 0.65)
    right_arm_mask = arm_region & (xs > center_gx + sh_half_grid * 0.65)

    def extract_limb_chain(
        limb_xs: NDArray[np.intp],
        limb_ys: NDArray[np.intp],
        anchor_gx: float,
        anchor_gy: float,
        side_sign: float,
    ) -> tuple[tuple[float, float], ...]:
        if len(limb_xs) < 6:
            return (
                to_scr(anchor_gx + side_sign * 4.0, anchor_gy + 4.0),
                to_scr(anchor_gx + side_sign * 5.0, anchor_gy + 12.0),
                to_scr(anchor_gx + side_sign * 5.5, anchor_gy + 20.0),
            )
        dists = np.hypot(limb_xs - anchor_gx, limb_ys - anchor_gy)
        max_d = max(float(dists.max()), 1.0)
        pts: list[tuple[float, float]] = []
        for frac in (0.28, 0.58, 0.86):
            band = (dists >= max_d * (frac - 0.18)) & (
                dists <= max_d * (frac + 0.18)
            )
            if np.any(band):
                pts.append(
                    to_scr(float(limb_xs[band].mean()), float(limb_ys[band].mean()))
                )
        if not pts:
            pts.append(to_scr(float(limb_xs.mean()), float(limb_ys.mean())))
        return tuple(pts)

    left_arm_pts = extract_limb_chain(
        xs[left_arm_mask],
        ys[left_arm_mask],
        center_gx - sh_half_grid * 0.85,
        torso_top_gy,
        -1.0,
    )
    right_arm_pts = extract_limb_chain(
        xs[right_arm_mask],
        ys[right_arm_mask],
        center_gx + sh_half_grid * 0.85,
        torso_top_gy,
        1.0,
    )

    # Nohy: dolních 42 % postavy (levá a pravá polovina)
    leg_pts_left: list[tuple[float, float]] = []
    leg_pts_right: list[tuple[float, float]] = []
    for frac in (0.64, 0.78, 0.91):
        y_target = min_y + span_y * frac
        row_band = np.abs(ys - y_target) <= max(2.0, span_y * 0.05)
        l_mask = row_band & (xs < center_gx)
        r_mask = row_band & (xs >= center_gx)
        if np.any(l_mask):
            leg_pts_left.append(
                to_scr(float(xs[l_mask].mean()), float(ys[l_mask].mean()))
            )
        else:
            leg_pts_left.append(to_scr(center_gx - sh_half_grid * 0.45, y_target))
        if np.any(r_mask):
            leg_pts_right.append(
                to_scr(float(xs[r_mask].mean()), float(ys[r_mask].mean()))
            )
        else:
            leg_pts_right.append(to_scr(center_gx + sh_half_grid * 0.45, y_target))

    return AnatomicalRig(
        has_body=True,
        head_center=head_center,
        head_radius=head_radius,
        torso_top=to_scr(center_gx, torso_top_gy),
        torso_bottom=to_scr(center_gx, torso_bot_gy),
        shoulder_half_width=shoulder_half_w,
        waist_half_width=waist_half_w,
        left_arm_points=left_arm_pts,
        right_arm_points=right_arm_pts,
        left_leg_points=tuple(leg_pts_left),
        right_leg_points=tuple(leg_pts_right),
    )


class ShapeSpriteCache:
    """Generuje a cachuje zaoblené 2.5D tvary se vzory (čistá barva, štětec, spirála, tečky, graffiti)."""

    def __init__(self) -> None:
        self._cache: dict[tuple, pygame.Surface] = {}
        self._graffiti_surface: NDArray[np.uint8] | None = None
        self._graffiti_mask: NDArray[np.bool_] | None = None
        self._graffiti_version: int = -1

    def update_graffiti_texture(
        self, strokes: list[dict], version: int
    ) -> None:
        if version == self._graffiti_version and self._graffiti_surface is not None:
            return
        self._graffiti_version = version
        self._cache.clear()
        tex_size = 128
        canvas = np.zeros((tex_size, tex_size, 3), dtype=np.uint8)
        mask = np.zeros((tex_size, tex_size), dtype=np.uint8)

        for stroke in strokes:
            pts = stroke.get("points", [])
            if not pts:
                continue
            is_eraser = bool(stroke.get("eraser", False))
            color_key = stroke.get("color", "red")
            preset = PRESET_COLOR_MAP.get(color_key)
            rgb = preset.rgb if preset else (239, 68, 68)
            thickness = max(2, int(stroke.get("size", 8)) * 2)

            scaled_pts = np.array(
                [
                    [
                        int(np.clip(p[0] * tex_size, 0, tex_size - 1)),
                        int(np.clip(p[1] * tex_size, 0, tex_size - 1)),
                    ]
                    for p in pts
                ],
                dtype=np.int32,
            )
            if len(scaled_pts) == 1:
                cx, cy = int(scaled_pts[0, 0]), int(scaled_pts[0, 1])
                if is_eraser:
                    cv2.circle(mask, (cx, cy), thickness // 2, 0, -1)
                else:
                    cv2.circle(canvas, (cx, cy), thickness // 2, rgb, -1)
                    cv2.circle(mask, (cx, cy), thickness // 2, 255, -1)
            else:
                if is_eraser:
                    cv2.polylines(
                        mask, [scaled_pts], False, 0, thickness, cv2.LINE_AA
                    )
                else:
                    cv2.polylines(
                        canvas, [scaled_pts], False, rgb, thickness, cv2.LINE_AA
                    )
                    cv2.polylines(
                        mask, [scaled_pts], False, 255, thickness, cv2.LINE_AA
                    )

        self._graffiti_surface = canvas
        self._graffiti_mask = mask > 0

    def get_sprite(
        self,
        shape_kind: str,
        radius_px: int,
        primary_rgb: tuple[int, int, int],
        secondary_rgb: tuple[int, int, int],
        pattern_style: str,
        depth_shade: float,
    ) -> pygame.Surface:
        """Vrátí vykreslený zaoblený tvar s daným vzorem a 3D stínováním."""
        shade_bucket = round(depth_shade * 6)
        radius_px = max(6, min(48, int(radius_px)))
        key = (
            shape_kind,
            radius_px,
            primary_rgb,
            secondary_rgb,
            pattern_style,
            shade_bucket,
            self._graffiti_version if pattern_style == "graffiti" else 0,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        size = radius_px * 2 + 4
        y_grid, x_grid = np.mgrid[0:size, 0:size].astype(np.float32)
        cx = cy = (size - 1) * 0.5
        nx = (x_grid - cx) / max(radius_px, 1)
        ny = (y_grid - cy) / max(radius_px, 1)

        # Zaoblené SDF pro jednotlivé typy tvarů:
        # 1) 'sphere' (koule pro hlavu)
        # 2) 'pyramid' (otočený zaoblený jehlan pro V-trup)
        # 3) 'cylinder' (zaoblený válec pro ruce)
        # 4) 'cuboid' (zaoblený kvádr pro nohy)
        if shape_kind == "sphere":
            dist = np.hypot(nx, ny) - 0.92
        elif shape_kind == "pyramid":
            # Otočený jehlan se zaoblenými rohy (širší nahoře, špička dole)
            width_at_y = np.clip(0.58 - ny * 0.36, 0.14, 0.92)
            dx = np.abs(nx) - width_at_y
            dy = np.abs(ny) - 0.84
            outside_d = np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))
            inside_d = np.minimum(np.maximum(dx, dy), 0.0)
            dist = outside_d + inside_d - 0.14
        elif shape_kind == "cylinder":
            # Zaoblený vertikální válec (kapsle)
            dx = np.abs(nx) - 0.52
            dy = np.abs(ny) - 0.72
            dist = (
                np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))
                + np.minimum(np.maximum(dx, dy), 0.0)
                - 0.22
            )
        else:
            # Zaoblený kvádr ('cuboid')
            dx = np.abs(nx) - 0.66
            dy = np.abs(ny) - 0.66
            dist = (
                np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))
                + np.minimum(np.maximum(dx, dy), 0.0)
                - 0.20
            )

        alpha = np.clip((0.06 - dist) / 0.12, 0.0, 1.0)
        inside = alpha > 0.01

        # Základní primární barva
        rgb = np.zeros((size, size, 3), dtype=np.float32)
        rgb[:, :, 0] = primary_rgb[0]
        rgb[:, :, 1] = primary_rgb[1]
        rgb[:, :, 2] = primary_rgb[2]

        # Aplikace vzoru (sekundární barva nebo graffiti)
        sec = np.array(secondary_rgb, dtype=np.float32)
        if pattern_style == "brush":
            # Tah štětcem: organický šikmý pruh přes tvar s měkkým okrajem
            stroke_coord = nx * 0.82 + ny * 0.57 + 0.14 * np.sin(ny * 4.5)
            brush_w = np.clip(1.0 - np.abs(stroke_coord) / 0.42, 0.0, 1.0)
            brush_w = brush_w * brush_w * (0.85 + 0.15 * np.cos(nx * 6.0))
            rgb = rgb * (1.0 - brush_w[..., None]) + sec * brush_w[..., None]
        elif pattern_style == "spiral":
            # Spirála: Archimédova spirála z druhé barvy
            r_polar = np.hypot(nx, ny)
            theta_polar = np.arctan2(ny, nx)
            spiral_wave = np.sin(theta_polar * 2.0 + r_polar * 9.5)
            spiral_w = np.clip((spiral_wave - 0.15) / 0.45, 0.0, 1.0)
            rgb = rgb * (1.0 - spiral_w[..., None]) + sec * spiral_w[..., None]
        elif pattern_style == "dots":
            # Tečky: mřížka kulatých puntíků
            u = ((nx + 1.0) * 1.8) % 1.0 - 0.5
            v = ((ny + 1.0) * 1.8) % 1.0 - 0.5
            dot_d = np.hypot(u, v)
            dot_w = np.clip((0.28 - dot_d) / 0.08, 0.0, 1.0)
            rgb = rgb * (1.0 - dot_w[..., None]) + sec * dot_w[..., None]
        elif (
            pattern_style == "graffiti"
            and self._graffiti_surface is not None
            and self._graffiti_mask is not None
        ):
            # Promítnutí nakresleného graffiti na tvar
            g_tex = cv2.resize(
                self._graffiti_surface,
                (size, size),
                interpolation=cv2.INTER_LINEAR,
            )
            g_msk = cv2.resize(
                self._graffiti_mask.astype(np.uint8) * 255,
                (size, size),
                interpolation=cv2.INTER_LINEAR,
            )
            g_w = (g_msk.astype(np.float32) / 255.0)[..., None]
            rgb = rgb * (1.0 - g_w) + g_tex.astype(np.float32) * g_w

        # Jemné 3D zaoblené stínování + odlesk
        light_dir = np.clip(
            1.0 - 0.35 * np.hypot(nx + 0.28, ny + 0.28), 0.55, 1.18
        )
        depth_factor = 0.68 + 0.38 * (shade_bucket / 6.0)
        rgb = np.clip(rgb * light_dir[..., None] * depth_factor, 0.0, 255.0)

        # Sestavení RGBA Pygame Surface
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        rgba = np.zeros((size, size, 4), dtype=np.uint8)
        rgba[:, :, :3] = rgb.astype(np.uint8)
        rgba[:, :, 3] = (alpha * 245.0 * (0.72 + 0.28 * (shade_bucket / 6.0))).astype(
            np.uint8
        )
        rgba[~inside, 3] = 0

        # Překopírování do Pygame Surface
        view_rgb = pygame.surfarray.pixels3d(surf)
        view_alpha = pygame.surfarray.pixels_alpha(surf)
        view_rgb[:] = rgba[:, :, :3].swapaxes(0, 1)
        view_alpha[:] = rgba[:, :, 3].swapaxes(0, 1)
        del view_rgb
        del view_alpha

        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[key] = surf
        return surf


class DynamicStarSystem:
    """Adaptivní hvězdný a částicový systém řízený posuvníky Gravitace, Počet hvězd,
    Padající hvězdy a Rychlost problikávání."""

    def __init__(self, max_stars: int = 2500) -> None:
        self.max_stars = max_stars
        rng = np.random.default_rng(42)
        self._home_norm = rng.uniform(0.0, 1.0, (max_stars, 2))
        self._pos = np.zeros((max_stars, 2), dtype=np.float64)
        self._vel = np.zeros((max_stars, 2), dtype=np.float64)
        self._drift = rng.uniform(-14.0, 14.0, (max_stars, 2))
        self._phase = rng.uniform(0.0, math.tau, max_stars)
        self._size_tier = rng.random(max_stars)
        self._scatter_offset = rng.normal(0.0, 1.0, (max_stars, 2))
        self._initialized_size: tuple[int, int] | None = None
        self._shooting_stars: list[list[float]] = []
        self._rng = np.random.default_rng(99)

    def _ensure_size(self, size: tuple[int, int]) -> None:
        if self._initialized_size == size:
            return
        w, h = size
        self._pos[:, 0] = self._home_norm[:, 0] * w
        self._pos[:, 1] = self._home_norm[:, 1] * h
        self._initialized_size = size

    def render(
        self,
        surface: pygame.Surface,
        outline_screen: NDArray[np.float64],
        body_points_screen: NDArray[np.float64],
        settings: AppSettings,
        elapsed_ms: float,
        delta_ms: float,
        mode: str = "stars",
    ) -> None:
        w, h = surface.get_size()
        self._ensure_size((w, h))

        count = max(0, min(self.max_stars, int(settings.star_count)))
        gravity = max(0.0, min(100.0, float(settings.gravity))) / 100.0
        dt = max(0.001, min(0.1, delta_ms / 1000.0))

        # Pozadí: při gravitaci 100 je obraz jenom obrys těla na čistě černé obrazovce
        bg_keep = max(0.0, 1.0 - (gravity ** 1.6))
        bg_color = (
            round(_BG_DARK_SPACE[0] * bg_keep),
            round(_BG_DARK_SPACE[1] * bg_keep),
            round(_BG_DARK_SPACE[2] * bg_keep),
        )
        surface.fill(bg_color if gravity < 0.99 else _BLACK_BG)

        if count == 0:
            return

        pos = self._pos[:count]
        home_x = self._home_norm[:count, 0] * w
        home_y = self._home_norm[:count, 1] * h
        home = np.column_stack((home_x, home_y))

        has_body = len(outline_screen) > 0 and gravity > 0.0
        if not has_body:
            # Gravitace = 0 (nebo žádné tělo): čisté hvězdné nebe
            pull_home = (home - pos) * min(1.0, dt * 3.5)
            pos += pull_home + self._drift[:count] * dt * 0.45
            pos[:, 0] %= w
            pos[:, 1] %= h
            captured = np.zeros(count, dtype=np.bool_)
        else:
            # Kombinace obrysových a objemových bodů
            if len(body_points_screen) > 0:
                n_out = max(1, int(count * 0.42))
                idx_out = (np.arange(n_out) * len(outline_screen)) // len(
                    outline_screen
                )
                n_vol = count - n_out
                idx_vol = (np.arange(n_vol) * len(body_points_screen)) // len(
                    body_points_screen
                )
                targets = np.vstack(
                    (outline_screen[idx_out], body_points_screen[idx_vol])
                )
            else:
                idx_out = (np.arange(count) * len(outline_screen)) // len(
                    outline_screen
                )
                targets = outline_screen[idx_out]

            # Velikost plochy okolo obrysu těla, ve které se objekty přilepí k tělu:
            # gravity == 0 -> 0 px, gravity == 0.2 -> ~110 px, gravity == 1.0 -> celá obrazovka
            diag = math.hypot(w, h)
            capture_radius = (
                diag * 1.5
                if gravity >= 0.98
                else (35.0 + (gravity ** 1.15) * diag * 0.85)
            )
            dist_to_target = np.hypot(
                home[:, 0] - targets[:, 0], home[:, 1] - targets[:, 1]
            )
            captured = (dist_to_target <= capture_radius) | (gravity >= 0.98)

            # Přitažené hvězdy plynule letí na obrys/tělo
            jitter_scale = 2.2 if mode == "stars" else 6.5
            desired = np.where(
                captured[:, None],
                targets + self._scatter_offset[:count] * jitter_scale,
                home,
            )
            follow_speed = min(1.0, dt * (5.0 + gravity * 9.0))
            pos += (desired - pos) * follow_speed

            if mode == "nebula":
                swirl_strength = (settings.nebula_swirl / 100.0) * 38.0 * dt
                angle_swirl = elapsed_ms * 0.003 + self._phase[:count]
                pos[captured, 0] += np.cos(angle_swirl[captured]) * swirl_strength
                pos[captured, 1] += np.sin(angle_swirl[captured]) * swirl_strength

        # Vykreslení hvězd / částic
        twinkle_rate = (0.6 + (settings.twinkle_speed / 100.0) * 6.5) * (
            elapsed_ms / 1000.0
        )
        twinkle = 0.72 + 0.28 * np.sin(self._phase[:count] + twinkle_rate)

        # Při gravitaci -> 100 volné hvězdy na pozadí pohasnou až do 0 (černé pozadí, jen obrys těla)
        sky_visibility = max(0.0, 1.0 - (gravity ** 1.8))
        visibility = np.where(captured, 1.0, sky_visibility) * twinkle

        if mode == "nebula":
            preset = PRESET_COLOR_MAP.get(settings.nebula_color)
            base_rgb = preset.rgb if preset else (56, 189, 248)
        else:
            base_rgb = (205, 225, 255)

        xs_int = np.clip(pos[:, 0].astype(np.int32), 1, w - 2)
        ys_int = np.clip(pos[:, 1].astype(np.int32), 1, h - 2)

        # Rychlé vektorové vykreslení přímo do pixelového bufferu
        pixels = pygame.surfarray.pixels3d(surface)
        vis_mask = visibility > 0.04
        if np.any(vis_mask):
            vx = xs_int[vis_mask]
            vy = ys_int[vis_mask]
            v_alpha = visibility[vis_mask]
            v_captured = captured[vis_mask]
            v_tier = self._size_tier[:count][vis_mask]

            r_col = np.clip(
                np.where(v_captured, 255.0, base_rgb[0]) * v_alpha, 0, 255
            ).astype(np.uint8)
            g_col = np.clip(
                np.where(v_captured, 242.0, base_rgb[1]) * v_alpha, 0, 255
            ).astype(np.uint8)
            b_col = np.clip(
                np.where(v_captured, 220.0, base_rgb[2]) * v_alpha, 0, 255
            ).astype(np.uint8)

            rgb_pts = np.stack((r_col, g_col, b_col), axis=-1)
            pixels[vx, vy] = np.maximum(pixels[vx, vy], rgb_pts)

            # Větší hvězdy a hvězdy na těle dostanou 3x3 křížovou záři
            bright = v_captured | (v_tier > 0.55)
            if np.any(bright):
                bx = vx[bright]
                by = vy[bright]
                glow = (rgb_pts[bright].astype(np.uint16) * 3 // 4).astype(
                    np.uint8
                )
                pixels[bx - 1, by] = np.maximum(pixels[bx - 1, by], glow)
                pixels[bx + 1, by] = np.maximum(pixels[bx + 1, by], glow)
                pixels[bx, by - 1] = np.maximum(pixels[bx, by - 1], glow)
                pixels[bx, by + 1] = np.maximum(pixels[bx, by + 1], glow)

        del pixels

        # Padající hvězdy (pokud není gravitace 100 a četnost > 0)
        if (
            mode == "stars"
            and settings.shooting_stars_freq > 0
            and gravity < 0.98
        ):
            spawn_prob = (
                (settings.shooting_stars_freq / 100.0) * 2.2 * dt * sky_visibility
            )
            if (
                len(self._shooting_stars) < 5
                and self._rng.random() < spawn_prob
            ):
                sx = float(self._rng.uniform(w * 0.1, w * 0.85))
                sy = float(self._rng.uniform(h * 0.05, h * 0.45))
                vx_s = float(self._rng.uniform(260.0, 440.0)) * (
                    1.0 if self._rng.random() > 0.3 else -1.0
                )
                vy_s = float(self._rng.uniform(140.0, 260.0))
                self._shooting_stars.append([sx, sy, vx_s, vy_s, 0.55])

            alive: list[list[float]] = []
            for st in self._shooting_stars:
                st[0] += st[2] * dt
                st[1] += st[3] * dt
                st[4] -= dt
                if st[4] > 0 and 0 <= st[0] < w and 0 <= st[1] < h:
                    alive.append(st)
                    head_p = (int(st[0]), int(st[1]))
                    tail_p = (
                        int(st[0] - st[2] * 0.09),
                        int(st[1] - st[3] * 0.09),
                    )
                    pygame.draw.line(surface, (180, 215, 255), tail_p, head_p, 2)
                    pygame.draw.circle(surface, (255, 255, 255), head_p, 3)
            self._shooting_stars = alive


class OrbitingRingsRenderer:
    """Vykresluje objektový efekt 'Prstence tvarů' (koule u hlavy, otočené jehlany
    kolem V-trupu, válce kolem rukou, kvádry kolem nohou)."""

    def __init__(self, sprite_cache: ShapeSpriteCache) -> None:
        self._sprites = sprite_cache
        self._orbit_phase: float = 0.0

    def render(
        self,
        surface: pygame.Surface,
        rig: AnatomicalRig,
        settings: AppSettings,
        delta_ms: float,
        graffiti_version: int,
    ) -> None:
        surface.fill(_BG_DARK_SPACE)
        dt = max(0.0, min(0.1, delta_ms / 1000.0))

        # Rychlost obíhání: 0 = stojí na místě, 100 = rychle obíhají kolem těla
        speed_norm = max(0.0, min(100.0, float(settings.orbit_speed))) / 100.0
        angular_speed = (speed_norm ** 1.15) * 7.5
        self._orbit_phase = (self._orbit_phase + angular_speed * dt) % math.tau

        # Velikost tvaru (10..100) určuje poloměr i celkový počet tvarů
        size_norm = (max(10, min(100, settings.shape_size)) - 10) / 90.0
        base_radius_px = round(8 + size_norm * 25)
        total_shapes = settings.computed_shape_count

        pattern = (
            settings.pattern_style
            if (settings.pattern_style != "graffiti" or settings.is_graffiti_unlocked)
            else "solid"
        )
        if pattern == "graffiti":
            self._sprites.update_graffiti_texture(
                settings.graffiti_strokes, graffiti_version
            )

        def part_rgb(
            part_key: str,
        ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
            if settings.color_mode == "per_part":
                entry = settings.part_colors.get(part_key, {})
                p_key = entry.get("primary", settings.primary_color)
                s_key = entry.get("secondary", settings.secondary_color)
            else:
                p_key = settings.primary_color
                s_key = settings.secondary_color
            p_rgb = PRESET_COLOR_MAP.get(p_key, PRESET_COLOR_MAP["light_blue"]).rgb
            s_rgb = PRESET_COLOR_MAP.get(s_key, PRESET_COLOR_MAP["white"]).rgb
            return p_rgb, s_rgb

        # Rozdělení počtu tvarů mezi 4 části těla
        n_head = max(3, round(total_shapes * 0.16))
        n_torso = max(4, round(total_shapes * 0.34))
        n_arms = max(4, round(total_shapes * 0.26))
        n_legs = max(4, total_shapes - n_head - n_torso - n_arms)

        # Seznam položek k vykreslení: (z_depth, x, y, shape_kind, radius, prim_rgb, sec_rgb)
        draw_queue: list[
            tuple[
                float,
                float,
                float,
                str,
                int,
                tuple[int, int, int],
                tuple[int, int, int],
            ]
        ] = []

        # 1. Hlava – prstence koulí ('sphere')
        h_prim, h_sec = part_rgb("head")
        hx, hy = rig.head_center
        hr = rig.head_radius * 1.25
        for i in range(n_head):
            ring_row = i % 2
            angle = (
                (i / max(1, n_head)) * math.tau
                + self._orbit_phase * (1.2 if ring_row == 0 else -0.9)
            )
            rx = hr * (0.95 if ring_row == 0 else 0.72)
            ry = hr * 0.28
            cy_ring = hy + (-hr * 0.24 if ring_row == 0 else hr * 0.22)
            px = hx + math.cos(angle) * rx
            py = cy_ring + math.sin(angle) * ry
            z = math.sin(angle)
            draw_queue.append(
                (z, px, py, "sphere", base_radius_px, h_prim, h_sec)
            )

        # 2. Trup (V-shape) – prstence otočených jehlanů ('pyramid')
        t_prim, t_sec = part_rgb("torso")
        tx_top, ty_top = rig.torso_top
        tx_bot, ty_bot = rig.torso_bottom
        n_rings_torso = 3 if n_torso < 12 else 4
        for i in range(n_torso):
            r_idx = i % n_rings_torso
            frac_y = (r_idx + 0.5) / n_rings_torso
            cx_r = tx_top + (tx_bot - tx_top) * frac_y
            cy_r = ty_top + (ty_bot - ty_top) * frac_y
            # V-shape zúžení od ramen k pasu
            rx = (
                rig.shoulder_half_width * (1.0 - frac_y)
                + rig.waist_half_width * frac_y
            ) * 1.15
            ry = rx * 0.22
            direction = 1.0 if (r_idx % 2 == 0) else -1.0
            angle = (
                (i / max(1, n_torso)) * math.tau * 1.5
                + r_idx * 0.9
                + self._orbit_phase * direction
            )
            px = cx_r + math.cos(angle) * rx
            py = cy_r + math.sin(angle) * ry
            z = math.sin(angle)
            draw_queue.append(
                (z, px, py, "pyramid", base_radius_px, t_prim, t_sec)
            )

        # 3. Ruce – prstence válců ('cylinder')
        a_prim, a_sec = part_rgb("arms")
        arm_anchors = list(rig.left_arm_points) + list(rig.right_arm_points)
        if arm_anchors:
            for i in range(n_arms):
                ax, ay = arm_anchors[i % len(arm_anchors)]
                angle = (
                    (i / max(1, n_arms)) * math.tau
                    + i * 0.7
                    + self._orbit_phase * 1.35
                )
                rx = max(22.0, rig.shoulder_half_width * 0.42)
                ry = rx * 0.35
                px = ax + math.cos(angle) * rx
                py = ay + math.sin(angle) * ry
                z = math.sin(angle)
                draw_queue.append(
                    (
                        z,
                        px,
                        py,
                        "cylinder",
                        max(6, int(base_radius_px * 0.92)),
                        a_prim,
                        a_sec,
                    )
                )

        # 4. Nohy – prstence kvádrů ('cuboid')
        l_prim, l_sec = part_rgb("legs")
        leg_anchors = list(rig.left_leg_points) + list(rig.right_leg_points)
        if leg_anchors:
            for i in range(n_legs):
                lx, ly = leg_anchors[i % len(leg_anchors)]
                angle = (
                    (i / max(1, n_legs)) * math.tau
                    + i * 0.85
                    - self._orbit_phase * 1.1
                )
                rx = max(24.0, rig.waist_half_width * 0.62)
                ry = rx * 0.28
                px = lx + math.cos(angle) * rx
                py = ly + math.sin(angle) * ry
                z = math.sin(angle)
                draw_queue.append(
                    (
                        z,
                        px,
                        py,
                        "cuboid",
                        max(6, int(base_radius_px * 0.95)),
                        l_prim,
                        l_sec,
                    )
                )

        # Seřadíme podle Z-hloubky obíhání (zadní část prstence první, přední navrchu)
        draw_queue.sort(key=lambda item: item[0])

        for z, px, py, kind, rad, prim, sec in draw_queue:
            depth_shade = (z + 1.0) * 0.5  # 0.0 vzadu .. 1.0 vpředu
            scaled_rad = max(6, round(rad * (0.82 + 0.30 * depth_shade)))
            sprite = self._sprites.get_sprite(
                kind, scaled_rad, prim, sec, pattern, depth_shade
            )
            rect = sprite.get_rect(center=(round(px), round(py)))
            surface.blit(sprite, rect)


class AbstractViewEngine:
    """Hlavní vizualizační engine propojující zdroj (CSV/ukázka/kamera),
    výpočet obrysů a plynulé vykreslování efektů včetně Smooth přechodu."""

    def __init__(self, initial_size: tuple[int, int] = (960, 720)) -> None:
        if not pygame.get_init():
            pygame.init()
        self._size = initial_size
        self._surface_main = pygame.Surface(initial_size)
        self._surface_blend = pygame.Surface(initial_size)

        self._sprites = ShapeSpriteCache()
        self._star_system = DynamicStarSystem()
        self._rings_renderer = OrbitingRingsRenderer(self._sprites)
        self.scheduler = ShuffleScheduler(seed=42)

        self._sequence: DepthSequence = get_sample_sequence("pose_raise")
        self._frame_offsets: tuple[float, ...] = tuple(
            f.time_ms - self._sequence.frames[0].time_ms
            for f in self._sequence.frames
        )
        self._selections_cache: dict[int, DepthSelection] = {}
        self._shapes_cache: dict[int, tuple[ContourShape, ...]] = {}
        self._camera_source: LiveCameraDepthSource | None = None
        self._active_source_signature: tuple | None = None
        self.graffiti_version: int = 0
        self.last_source_label: str = "Ukázka: 3. Postava – Vzpažení"

    @property
    def surface_size(self) -> tuple[int, int]:
        return self._size

    def set_surface_size(self, width: int, height: int) -> None:
        w = max(320, int(width))
        h = max(240, int(height))
        if (w, h) != self._size:
            self._size = (w, h)
            self._surface_main = pygame.Surface(self._size)
            self._surface_blend = pygame.Surface(self._size)

    def notify_graffiti_changed(self) -> None:
        self.graffiti_version += 1

    def sync_source(self, settings: AppSettings) -> None:
        """Zajistí, že je načten odpovídající zdroj snímků (ukázka, CSV nebo kamera)."""
        sig = (settings.source_type, settings.sample_id, settings.csv_path, settings.camera_port)
        if sig == self._active_source_signature:
            return
        self._active_source_signature = sig
        self._selections_cache.clear()
        self._shapes_cache.clear()

        if self._camera_source is not None:
            self._camera_source.close()
            self._camera_source = None

        if settings.source_type == "camera":
            self._camera_source = LiveCameraDepthSource(settings.camera_port)
            self.last_source_label = f"Kamera (Port {settings.camera_port})"
            return

        if settings.source_type == "csv" and settings.csv_path:
            try:
                seq = load_custom_csv_sequence(settings.csv_path)
                self._sequence = seq
                first_t = seq.frames[0].time_ms
                self._frame_offsets = tuple(f.time_ms - first_t for f in seq.frames)
                self.last_source_label = f"CSV: {Path(settings.csv_path).name}"
                return
            except (DepthCsvError, OSError, ValueError):
                settings.source_type = "sample"

        seq = get_sample_sequence(settings.sample_id)
        self._sequence = seq
        first_t = seq.frames[0].time_ms
        self._frame_offsets = tuple(f.time_ms - first_t for f in seq.frames)
        titles = {
            "pose_calm": "Ukázka 1: Klid a dech",
            "pose_spread": "Ukázka 2: Rozpažení",
            "pose_raise": "Ukázka 3: Vzpažení",
        }
        self.last_source_label = titles.get(settings.sample_id, "Ukázka")

    def _get_selection_and_shapes(
        self, idx: int
    ) -> tuple[DepthSelection, tuple[ContourShape, ...]]:
        sel = self._selections_cache.get(idx)
        if sel is None:
            sel = select_depth_regions(self._sequence.frames[idx])
            self._selections_cache[idx] = sel
        shapes = self._shapes_cache.get(idx)
        if shapes is None:
            shapes = prepare_contours(sel.contours)
            self._shapes_cache[idx] = shapes
        return sel, shapes

    def _extract_frame_geometry(
        self, elapsed_ms: float
    ) -> tuple[NDArray[np.uint8], NDArray[np.float64], NDArray[np.float64]]:
        """Vrátí (maska, obrys_na_obrazovce, vnitřní_body_na_obrazovce)."""
        sw, sh = self._size
        margin = 24.0

        if self._camera_source is not None:
            frame = self._camera_source.next_frame(elapsed_ms)
            sel = select_depth_regions(frame)
            shapes = prepare_contours(sel.contours)
            outline_grid = (
                morph_contours(match_contours(shapes, shapes), 0.0, count=360)
                if shapes
                else np.empty((0, 2))
            )
            mask = sel.mask
        else:
            curr_idx, next_idx, alpha = transition_for_elapsed(
                self._frame_offsets, elapsed_ms
            )
            curr_sel, curr_shapes = self._get_selection_and_shapes(curr_idx)
            _, next_shapes = self._get_selection_and_shapes(next_idx)
            pairs = match_contours(curr_shapes, next_shapes)
            outline_grid = (
                morph_contours(pairs, alpha, count=360)
                if pairs
                else np.empty((0, 2))
            )
            mask = curr_sel.mask

        gh, gw = mask.shape
        scale = min((sw - 2 * margin) / gw, (sh - 2 * margin) / gh)
        left = (sw - gw * scale) * 0.5
        top = (sh - gh * scale) * 0.5

        if len(outline_grid):
            outline_screen = np.column_stack(
                (
                    left + (outline_grid[:, 0] + 0.5) * scale,
                    top + (outline_grid[:, 1] + 0.5) * scale,
                )
            )
        else:
            outline_screen = np.empty((0, 2))

        ys, xs = np.nonzero(mask)
        if len(xs):
            step = max(1, len(xs) // 600)
            body_screen = np.column_stack(
                (
                    left + (xs[::step] + 0.5) * scale,
                    top + (ys[::step] + 0.5) * scale,
                )
            )
        else:
            body_screen = np.empty((0, 2))

        return mask, outline_screen, body_screen

    def _render_single_effect(
        self,
        target_surface: pygame.Surface,
        effect_key: str,
        mask: NDArray[np.uint8],
        outline_screen: NDArray[np.float64],
        body_screen: NDArray[np.float64],
        settings: AppSettings,
        elapsed_ms: float,
        delta_ms: float,
    ) -> None:
        if effect_key == "rings":
            rig = extract_anatomical_rig(mask, self._size)
            self._rings_renderer.render(
                target_surface, rig, settings, delta_ms, self.graffiti_version
            )
        elif effect_key == "nebula":
            self._star_system.render(
                target_surface,
                outline_screen,
                body_screen,
                settings,
                elapsed_ms,
                delta_ms,
                mode="nebula",
            )
        else:
            self._star_system.render(
                target_surface,
                outline_screen,
                body_screen,
                settings,
                elapsed_ms,
                delta_ms,
                mode="stars",
            )

    def render_step(
        self, settings: AppSettings, elapsed_ms: float, delta_ms: float
    ) -> tuple[pygame.Surface, str]:
        """Vykreslí snímek do hlavního surface a vrátí (surface, klíč_aktivního_efektu)."""
        self.sync_source(settings)
        mask, outline_screen, body_screen = self._extract_frame_geometry(
            elapsed_ms
        )

        curr_eff, next_eff, blend_alpha = self.scheduler.state_at(
            settings, elapsed_ms / 1000.0
        )

        self._render_single_effect(
            self._surface_main,
            curr_eff,
            mask,
            outline_screen,
            body_screen,
            settings,
            elapsed_ms,
            delta_ms,
        )

        if next_eff is not None and next_eff != curr_eff and blend_alpha > 0.01:
            self._render_single_effect(
                self._surface_blend,
                next_eff,
                mask,
                outline_screen,
                body_screen,
                settings,
                elapsed_ms,
                0.0,
            )
            self._surface_blend.set_alpha(round(blend_alpha * 255))
            self._surface_main.blit(self._surface_blend, (0, 0))

        return self._surface_main, curr_eff

    def close(self) -> None:
        if self._camera_source is not None:
            self._camera_source.close()
            self._camera_source = None
