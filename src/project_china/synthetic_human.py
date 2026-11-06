import argparse
import csv
import math
from collections.abc import Iterable, Iterator
from itertools import chain
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from project_china.frames import DepthFrame

WIDTH = 256
HEIGHT = 384
FRAME_COUNT = 120
FRAME_INTERVAL_MS = 50
_VIEW_WIDTH = 1.90
_PIXEL_SIZE = _VIEW_WIDTH / WIDTH
_VIEW_TOP = 1.82
_FloatMap = NDArray[np.float64]
_Point = tuple[float, float, float]


def _ellipsoid(
    front: _FloatMap,
    x: _FloatMap,
    y: _FloatMap,
    center: _Point,
    radii: _Point,
    angle: float = 0,
) -> None:
    dx, dy = x - center[0], y - center[1]
    cosine, sine = math.cos(angle), math.sin(angle)
    local_x = cosine * dx + sine * dy
    local_y = -sine * dx + cosine * dy
    squared_radius = (local_x / radii[0]) ** 2 + (local_y / radii[1]) ** 2
    surface = center[2] - radii[2] * np.sqrt(
        np.maximum(0, 1 - squared_radius)
    )
    np.minimum(
        front, np.where(squared_radius <= 1, surface, np.inf), out=front
    )


def _tube(
    front: _FloatMap,
    x: _FloatMap,
    y: _FloatMap,
    start: _Point,
    end: _Point,
    start_radius: float,
    end_radius: float,
) -> None:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        raise ValueError("A limb must have a nonzero projected length.")
    position = np.clip(
        ((x - start[0]) * dx + (y - start[1]) * dy) / length_squared,
        0,
        1,
    )
    radius = start_radius + (end_radius - start_radius) * position
    squared_radius = (
        (x - start[0] - position * dx) ** 2
        + (y - start[1] - position * dy) ** 2
    ) / radius**2
    center_depth = start[2] + position * (end[2] - start[2])
    surface = center_depth - 0.85 * radius * np.sqrt(
        np.maximum(0, 1 - squared_radius)
    )
    np.minimum(
        front, np.where(squared_radius <= 1, surface, np.inf), out=front
    )


def _extend(
    point: _Point, direction: tuple[float, float], length: float, dz: float = 0
) -> _Point:
    return (
        point[0] + direction[0] * length,
        point[1] + direction[1] * length,
        point[2] + dz,
    )


def _torso(
    front: _FloatMap, x: _FloatMap, y: _FloatMap, breathing: float
) -> None:
    levels = (-0.200, -0.170, -0.100, 0.050, 0.150, 0.320, 0.440, 0.510, 0.555)
    widths = (0, 0.110, 0.170, 0.150, 0.145, 0.175, 0.207, 0.207, 0)
    thicknesses = (0.010, 0.070, 0.115, 0.105, 0.100, 0.115, 0.110, 0.060, 0.010)
    width = np.zeros_like(y)
    thickness = np.zeros_like(y)
    for index in range(len(levels) - 1):
        position = np.clip(
            (y - levels[index]) / (levels[index + 1] - levels[index]), 0, 1
        )
        blend = position**2 * (3 - 2 * position)
        inside = (y >= levels[index]) & (y <= levels[index + 1])
        width = np.where(
            inside, widths[index] + blend * (widths[index + 1] - widths[index]), width
        )
        thickness = np.where(
            inside,
            thicknesses[index] + blend * (thicknesses[index + 1] - thicknesses[index]),
            thickness,
        )
    width *= 1 + 0.007 * breathing * np.exp(-((y - 0.350) / 0.180) ** 2)
    squared_radius = (x / np.maximum(width, 1e-9)) ** 2
    surface = 0.010 - thickness * np.sqrt(np.maximum(0, 1 - squared_radius))
    surface -= 0.004 * np.exp(
        -((np.abs(x) - 0.080) / 0.055) ** 2 - ((y - 0.385) / 0.090) ** 2
    )
    visible = (width > 0) & (squared_radius <= 1)
    np.minimum(front, np.where(visible, surface, np.inf), out=front)


def _hand(
    front: _FloatMap,
    x: _FloatMap,
    y: _FloatMap,
    wrist: _Point,
    direction: tuple[float, float],
    side: int,
) -> None:
    lateral = (side * direction[1], -side * direction[0])
    palm = _extend(wrist, direction, 0.050, -0.005)
    angle = math.atan2(direction[1], direction[0]) - math.pi / 2
    _ellipsoid(front, x, y, palm, (0.042, 0.060, 0.025), angle)

    fingers = (
        (-0.032, 0.078, 0.0085, -7),
        (-0.011, 0.088, 0.0090, -2),
        (0.011, 0.082, 0.0080, 3),
        (0.032, 0.063, 0.0065, 10),
    )
    for offset, length, radius, spread in fingers:
        base = _extend(wrist, direction, 0.096, -0.004)
        base = _extend(base, lateral, offset)
        spread_angle = math.radians(spread)
        finger_direction = (
            direction[0] * math.cos(spread_angle)
            + lateral[0] * math.sin(spread_angle),
            direction[1] * math.cos(spread_angle)
            + lateral[1] * math.sin(spread_angle),
        )
        joint = _extend(base, finger_direction, length * 0.55, -0.006)
        tip = _extend(joint, finger_direction, length * 0.45, 0.004)
        _tube(front, x, y, base, joint, radius, radius * 0.85)
        _tube(front, x, y, joint, tip, radius * 0.85, radius * 0.65)

    thumb_base = _extend(_extend(wrist, direction, 0.025), lateral, -0.031)
    thumb_joint = _extend(
        _extend(thumb_base, direction, 0.025, -0.009), lateral, -0.025
    )
    thumb_tip = _extend(
        _extend(thumb_joint, direction, 0.028, 0.002), lateral, -0.014
    )
    _tube(front, x, y, thumb_base, thumb_joint, 0.012, 0.010)
    _tube(front, x, y, thumb_joint, thumb_tip, 0.010, 0.008)


def human_frame(frame_index: int) -> DepthFrame:
    """Model a frontal synthetic human, not a measured person or camera scan."""
    if not 0 <= frame_index < FRAME_COUNT:
        raise ValueError(f"Frame index must be between 0 and {FRAME_COUNT - 1}.")

    phase = frame_index / FRAME_COUNT
    raised = (1 - math.cos(math.tau * phase)) / 2
    breathing = math.sin(math.tau * phase)
    x, y = np.meshgrid(
        (np.arange(WIDTH, dtype=np.float64) + 0.5) * _PIXEL_SIZE - _VIEW_WIDTH / 2,
        _VIEW_TOP - (np.arange(HEIGHT, dtype=np.float64) + 0.5) * _PIXEL_SIZE,
    )
    x -= 0.006 * breathing
    front = np.full((HEIGHT, WIDTH), np.inf, dtype=np.float64)
    _torso(front, x, y, breathing)

    body = (
        ((0, 0.610, 0), (0.048, 0.077, 0.046)),
        ((0, 0.765, 0), (0.089, 0.120, 0.087)),
        ((0, 0.690, -0.003), (0.070, 0.055, 0.068)),
    )
    for center, radii in body:
        _ellipsoid(front, x, y, center, radii)

    # Eye sockets are recessed; other facial features join the visible surface.
    face_region = (np.abs(x) < 0.074) & (y > 0.704) & (y < 0.830)
    sockets = sum(
        0.005
        * np.exp(-((x - side * 0.034) / 0.019) ** 2 - ((y - 0.787) / 0.011) ** 2)
        for side in (-1, 1)
    )
    front += np.where(face_region & np.isfinite(front), sockets, 0)
    face_features = (
        ((0, 0.772, -0.080), (0.012, 0.037, 0.019)),
        ((0, 0.741, -0.095), (0.017, 0.015, 0.030)),
        ((0, 0.709, -0.071), (0.027, 0.005, 0.018)),
        ((0, 0.699, -0.068), (0.025, 0.006, 0.017)),
        ((0, 0.675, -0.031), (0.042, 0.023, 0.049)),
    )
    for center, radii in face_features:
        _ellipsoid(front, x, y, center, radii)

    for side in (-1, 1):
        _ellipsoid(
            front, x, y, (side * 0.090, 0.765, 0.008), (0.020, 0.035, 0.023)
        )
        _ellipsoid(
            front, x, y, (side * 0.049, 0.746, -0.042), (0.034, 0.031, 0.039)
        )
        _ellipsoid(
            front, x, y, (side * 0.034, 0.812, -0.061), (0.026, 0.007, 0.015)
        )
        _ellipsoid(
            front, x, y, (side * 0.013, 0.736, -0.089), (0.009, 0.010, 0.019)
        )
        hip = (side * 0.089, -0.140, 0.015)
        knee = (side * 0.105, -0.470, -0.004)
        ankle = (side * 0.116, -0.812, 0.012)
        _tube(front, x, y, hip, knee, 0.081, 0.050)
        _tube(front, x, y, knee, ankle, 0.054, 0.030)
        _ellipsoid(
            front, x, y, (side * 0.120, -0.871, -0.044), (0.049, 0.074, 0.105)
        )

        upper_angle = math.radians(8 + 150 * raised)
        forearm_angle = upper_angle + math.radians(
            15 + 20 * math.sin(math.pi * raised)
        )
        upper_direction = (side * math.sin(upper_angle), -math.cos(upper_angle))
        forearm_direction = (
            side * math.sin(forearm_angle), -math.cos(forearm_angle)
        )
        shoulder = (side * 0.205, 0.490, -0.010)
        elbow = _extend(
            shoulder, upper_direction, 0.300, -0.030 * math.sin(math.pi * raised)
        )
        wrist = _extend(elbow, forearm_direction, 0.255, -0.015 * raised)
        _ellipsoid(front, x, y, shoulder, (0.066, 0.073, 0.068))
        _tube(front, x, y, shoulder, elbow, 0.051, 0.038)
        _tube(front, x, y, elbow, wrist, 0.040, 0.026)
        _hand(front, x, y, wrist, forearm_direction, side)

    view_bottom = _VIEW_TOP - HEIGHT * _PIXEL_SIZE
    background = 1300 + 15 * (y - view_bottom) / (HEIGHT * _PIXEL_SIZE)
    depths = np.where(np.isfinite(front), 900 + 250 * front, background)
    return DepthFrame(
        frame_index,
        frame_index * FRAME_INTERVAL_MS,
        tuple(tuple(row) for row in depths.tolist()),
    )


def human_frames() -> Iterator[DepthFrame]:
    for frame_index in range(FRAME_COUNT):
        yield human_frame(frame_index)


def write_human_csv(path: Path, frames: Iterable[DepthFrame]) -> int:
    iterator = iter(frames)
    first = next(iterator, None)
    if first is None:
        raise ValueError("Cannot write an empty human sequence.")

    frame_count = 0
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("frame", "time_ms", "x", "y", "depth"))
        for frame in chain((first,), iterator):
            writer.writerows(
                (frame.frame, frame.time_ms, x, y, f"{depth:.3f}")
                for y, row in enumerate(frame.depths)
                for x, depth in enumerate(row)
            )
            frame_count += 1
    return frame_count


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic human depth CSV.")
    parser.add_argument("csv_path", type=Path, help="new CSV path; never overwritten")
    args = parser.parse_args(argv)
    print(
        f"Generating {FRAME_COUNT} frames at {WIDTH} x {HEIGHT}, "
        f"{FRAME_INTERVAL_MS} ms apart...",
        flush=True,
    )
    try:
        count = write_human_csv(args.csv_path, human_frames())
    except OSError as exc:
        parser.error(str(exc))
    print(f"Created {args.csv_path}: {count} frames, {args.csv_path.stat().st_size} bytes.")


if __name__ == "__main__":
    main()
