"""Okamžité ukázkové sekvence 3 póz člověka, náhledy a správa kamery/CSV."""

from __future__ import annotations

import contextlib
import csv
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from project_china.frames import DepthFrame, DepthSequence, load_depth_csv


@dataclass(frozen=True)
class SamplePoseInfo:
    """Metadata pro jednu ze 3 předpřipravených ukázkových sekvencí."""

    sample_id: str
    title: str
    subtitle: str
    arm_min_deg: float
    arm_max_deg: float
    Preview_frame_idx: int


SAMPLE_POSES: tuple[SamplePoseInfo, ...] = (
    SamplePoseInfo(
        sample_id="pose_calm",
        title="1. Postava – Klid a dech",
        subtitle="Ruce volně u těla, plynulé dýchání",
        arm_min_deg=8.0,
        arm_max_deg=24.0,
        Preview_frame_idx=6,
    ),
    SamplePoseInfo(
        sample_id="pose_spread",
        title="2. Postava – Rozpažení",
        subtitle="Upažení rukou do vodorovné polohy",
        arm_min_deg=12.0,
        arm_max_deg=92.0,
        Preview_frame_idx=12,
    ),
    SamplePoseInfo(
        sample_id="pose_raise",
        title="3. Postava – Vzpažení",
        subtitle="Plné zvednutí obou paží nad hlavu",
        arm_min_deg=10.0,
        arm_max_deg=156.0,
        Preview_frame_idx=12,
    ),
)

SAMPLE_POSE_MAP: dict[str, SamplePoseInfo] = {
    p.sample_id: p for p in SAMPLE_POSES
}

_SAMPLE_CACHE: dict[str, DepthSequence] = {}
_THUMB_CACHE: dict[tuple[str, int, int], bytes] = {}

_GRID_W = 64
_GRID_H = 96
_NUM_FRAMES = 24
_FRAME_STEP_MS = 100.0


def _capsule_sdf(
    px: NDArray[np.float32],
    py: NDArray[np.float32],
    ax: float,
    ay: float,
    bx: float,
    by: float,
    r1: float,
    r2: float,
) -> NDArray[np.float32]:
    dx = bx - ax
    dy = by - ay
    length_sq = max(dx * dx + dy * dy, 1e-6)
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / length_sq, 0.0, 1.0)
    cx = ax + t * dx
    cy = ay + t * dy
    r = r1 + t * (r2 - r1)
    return np.hypot(px - cx, py - cy) - r


def _smin(
    a: NDArray[np.float32], b: NDArray[np.float32], k: float = 2.2
) -> NDArray[np.float32]:
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def _build_human_matrix(
    arm_angle_deg: float, breath_phase: float, sway: float
) -> NDArray[np.float64]:
    """Vytvoří 2.5D hloubkovou matici člověka v dané póze (rozsah těla ~860..900)."""
    y_coords, x_coords = np.mgrid[0:_GRID_H, 0:_GRID_W].astype(np.float32)
    cx = (_GRID_W * 0.5) + sway * 1.4
    breath = math.sin(breath_phase) * 0.6

    # Hlava (elipsoid nahoře)
    head_y = 17.5 - breath * 0.3
    head_sdf = (
        np.hypot((x_coords - cx) / 5.2, (y_coords - head_y) / 6.8) - 1.0
    ) * 5.5

    # Krk
    neck_sdf = _capsule_sdf(x_coords, y_coords, cx, 22.0, cx, 27.5, 2.5, 3.0)

    # Trup (V-shape: širší ramena, užší pas a boky)
    torso_sdf = _capsule_sdf(
        x_coords,
        y_coords,
        cx,
        29.5 - breath * 0.4,
        cx,
        54.0,
        8.6 + breath * 0.35,
        6.4,
    )

    body_sdf = _smin(_smin(head_sdf, neck_sdf, 1.8), torso_sdf, 2.4)

    # Nohy
    for side in (-1.0, 1.0):
        hip_x = cx + side * 3.9
        knee_x = cx + side * 4.4
        ankle_x = cx + side * 4.7
        thigh = _capsule_sdf(
            x_coords, y_coords, hip_x, 54.0, knee_x, 71.0, 3.9, 3.1
        )
        calf = _capsule_sdf(
            x_coords, y_coords, knee_x, 71.0, ankle_x, 87.5, 3.0, 2.3
        )
        leg = _smin(thigh, calf, 1.4)
        body_sdf = _smin(body_sdf, leg, 2.0)

    # Paže (dvousegmentové: nadloktí + předloktí s dlaní)
    rad = math.radians(arm_angle_deg)
    elbow_rad = rad + math.radians(14.0 * math.sin(rad))
    lift = max(0.0, (arm_angle_deg - 75.0) / 85.0) * 1.8

    for side in (-1.0, 1.0):
        sh_x = cx + side * 8.2
        sh_y = 29.0 - lift - breath * 0.3
        el_x = sh_x + side * math.sin(rad) * 11.0
        el_y = sh_y + math.cos(rad) * 11.0
        wr_x = el_x + side * math.sin(elbow_rad) * 10.5
        wr_y = el_y + math.cos(elbow_rad) * 10.5

        upper = _capsule_sdf(
            x_coords, y_coords, sh_x, sh_y, el_x, el_y, 2.9, 2.5
        )
        fore = _capsule_sdf(
            x_coords, y_coords, el_x, el_y, wr_x, wr_y, 2.4, 2.0
        )
        palm = np.hypot(x_coords - wr_x, y_coords - wr_y) - 2.4
        arm = _smin(_smin(upper, fore, 1.2), palm, 1.2)
        body_sdf = _smin(body_sdf, arm, 2.0)

    inside = body_sdf <= 0.0
    edge_dist = np.where(inside, -body_sdf, 0.0)
    max_d = max(float(edge_dist.max()), 1.0)
    norm_d = np.clip(edge_dist / (max_d * 0.75), 0.0, 1.0)
    profile = 1.0 - (1.0 - norm_d) ** 2
    depths = np.where(inside, 898.0 - 36.0 * profile, 1350.0)
    return np.round(depths.astype(np.float64), 3)


def get_sample_sequence(sample_id: str) -> DepthSequence:
    """Vrátí (a uloží do mezipaměti) hloubkovou sekvenci pro zvolenou ukázku."""
    if sample_id not in SAMPLE_POSE_MAP:
        sample_id = "pose_raise"
    cached = _SAMPLE_CACHE.get(sample_id)
    if cached is not None:
        return cached

    info = SAMPLE_POSE_MAP[sample_id]
    frames: list[DepthFrame] = []
    for idx in range(_NUM_FRAMES):
        phase = idx / _NUM_FRAMES
        triangle = 1.0 - abs(2.0 * phase - 1.0)
        eased = math.sin(math.pi * 0.5 * triangle) ** 2
        angle = info.arm_min_deg + (info.arm_max_deg - info.arm_min_deg) * eased
        breath_phase = math.tau * phase
        sway = math.sin(math.tau * phase)
        mat = _build_human_matrix(angle, breath_phase, sway)
        rows = tuple(tuple(float(v) for v in row) for row in mat)
        frames.append(DepthFrame(frame=idx, time_ms=idx * _FRAME_STEP_MS, depths=rows))

    seq = DepthSequence(tuple(frames))
    _SAMPLE_CACHE[sample_id] = seq
    return seq


def render_sample_thumbnail_ppm(
    sample_id: str, width: int = 156, height: int = 116
) -> bytes:
    """Vygeneruje PPM binární obrázek náhledu ukázkové pózy pro tlačítko v UI."""
    key = (sample_id, width, height)
    if key in _THUMB_CACHE:
        return _THUMB_CACHE[key]

    seq = get_sample_sequence(sample_id)
    info = SAMPLE_POSE_MAP.get(sample_id, SAMPLE_POSES[-1])
    frame = seq.frames[min(info.Preview_frame_idx, len(seq.frames) - 1)]
    depths = np.asarray(frame.depths, dtype=np.float32)
    mask = (depths >= 750.0) & (depths <= 1000.0)

    # Vytvoříme tmavě modrý náhled se siluetou a hvězdami
    img = np.zeros((_GRID_H, _GRID_W, 3), dtype=np.uint8)
    img[:, :] = (14, 24, 48)

    rng = np.random.default_rng(hash(sample_id) & 0xFFFF)
    for _ in range(38):
        sx = int(rng.integers(0, _GRID_W))
        sy = int(rng.integers(0, _GRID_H))
        img[sy, sx] = (140, 175, 230)

    nearness = np.clip((900.0 - depths) / 38.0, 0.0, 1.0)
    img[mask, 0] = (90 + nearness[mask] * 155).astype(np.uint8)
    img[mask, 1] = (165 + nearness[mask] * 80).astype(np.uint8)
    img[mask, 2] = 255

    # Obrys zvýrazníme jasně bílo-tyrkysovou
    contours, _ = cv2.findContours(
        mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    cv2.drawContours(img, contours, -1, (235, 250, 255), 1)

    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_LINEAR)
    header = f"P6 {width} {height} 255\n".encode("ascii")
    ppm = header + resized.tobytes()
    _THUMB_CACHE[key] = ppm
    return ppm


def export_sample_csv(sample_id: str, path: str | Path) -> Path:
    """Uloží ukázkovou sekvenci jako platný CSV soubor na disk."""
    seq = get_sample_sequence(sample_id)
    target = Path(path)
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("frame", "time_ms", "x", "y", "depth"))
        for frame in seq.frames:
            for y, row in enumerate(frame.depths):
                for x, depth in enumerate(row):
                    writer.writerow((frame.frame, int(frame.time_ms), x, y, depth))
    return target


@dataclass(frozen=True)
class CameraDeviceInfo:
    """Informace o nalezeném portu kamery."""

    port: int
    label: str
    is_simulated: bool = False


def discover_camera_ports(max_ports: int = 4) -> list[CameraDeviceInfo]:
    """Prohledá porty zařízení s připojenou kamerou + poskytne simulovanou ToF kameru."""
    devices: list[CameraDeviceInfo] = []
    for port in range(max_ports):
        cap = None
        try:
            cap = cv2.VideoCapture(port, cv2.CAP_DSHOW)
            if cap is not None and cap.isOpened():
                devices.append(
                    CameraDeviceInfo(
                        port=port,
                        label=f"Port {port} – USB / Integrovaná kamera",
                        is_simulated=False,
                    )
                )
        except (cv2.error, OSError, RuntimeError):
            continue
        finally:
            if cap is not None:
                with contextlib.suppress(cv2.error, OSError, RuntimeError):
                    cap.release()

    # Vždy přidáme virtuální ToF senzor, aby šel výběr kamery ihned vyzkoušet
    devices.append(
        CameraDeviceInfo(
            port=99,
            label="Port ToF-Sim – Virtuální 3D hloubková kamera (Živý stream)",
            is_simulated=True,
        )
    )
    return devices


class LiveCameraDepthSource:
    """Zdroj živých hloubkových snímků z vybrané kamery nebo virtuálního ToF portu."""

    def __init__(self, port: int = 99) -> None:
        self.port = port
        self._cap: cv2.VideoCapture | None = None
        self._frame_counter = 0
        if port != 99:
            try:
                cap = cv2.VideoCapture(port, cv2.CAP_DSHOW)
                if cap is not None and cap.isOpened():
                    self._cap = cap
            except (cv2.error, OSError, RuntimeError):
                self._cap = None

    def next_frame(self, elapsed_ms: float) -> DepthFrame:
        self._frame_counter += 1
        if self._cap is not None and self._cap.isOpened():
            ok, bgr = self._cap.read()
            if ok and bgr is not None:
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                small = cv2.resize(
                    gray, (_GRID_W, _GRID_H), interpolation=cv2.INTER_AREA
                )
                # Převedeme jas na pseudo-hloubku v cílovém okně 750..1000
                blurred = cv2.GaussianBlur(small, (5, 5), 0)
                _, thresh = cv2.threshold(
                    blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                # Vybereme menší z ploch jako popředí, nebo středovou postavu
                if np.count_nonzero(thresh) > (_GRID_W * _GRID_H * 0.65):
                    thresh = 255 - thresh
                inside = thresh > 0
                norm = small.astype(np.float64) / 255.0
                depths = np.where(inside, 895.0 - norm * 35.0, 1350.0)
                rows = tuple(tuple(float(v) for v in row) for row in depths)
                return DepthFrame(
                    frame=self._frame_counter, time_ms=elapsed_ms, depths=rows
                )

        # Fallback nebo virtuální ToF port 99: plynulý interaktivní pohyb člověka
        phase = (elapsed_ms / 4000.0) % 1.0
        tri = 1.0 - abs(2.0 * phase - 1.0)
        angle = 12.0 + 138.0 * (math.sin(math.pi * 0.5 * tri) ** 2)
        breath = math.tau * (elapsed_ms / 3200.0)
        sway = math.sin(math.tau * (elapsed_ms / 5000.0)) * 1.6
        mat = _build_human_matrix(angle, breath, sway)
        rows = tuple(tuple(float(v) for v in row) for row in mat)
        return DepthFrame(
            frame=self._frame_counter, time_ms=elapsed_ms, depths=rows
        )

    def close(self) -> None:
        if self._cap is not None:
            with contextlib.suppress(cv2.error, OSError, RuntimeError):
                self._cap.release()
            self._cap = None


def load_custom_csv_sequence(path: str | Path) -> DepthSequence:
    """Načte a zvaliduje uživatelský .csv soubor pomocí existujícího modulu frames."""
    return load_depth_csv(path)
