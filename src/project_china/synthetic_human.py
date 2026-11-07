import argparse
import csv
import math
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from project_china.frames import DepthFrame

WIDTH = 256
HEIGHT = 384
FRAME_INTERVAL_MS = 50
# The arms repeat every 6 s and breathing every 4 s; the 12 s loop holds two
# arm cycles and three breaths, so both close seamlessly.
ARM_CYCLE_FRAMES = 120
BREATH_PERIOD_FRAMES = 80
FRAME_COUNT = 240
_VIEW_WIDTH = 1.90
_PIXEL_SIZE = _VIEW_WIDTH / WIDTH
_VIEW_TOP = 1.82
_FloatMap = NDArray[np.float64]
_Point = tuple[float, float, float]
_Radii = tuple[float, float]

# Body dimensions in metres; the camera looks along +z, smaller z is closer.
HEAD_RADII: _Radii = (0.082, 0.112)
HEAD_WIDTH = 2 * HEAD_RADII[0]
NECK_WIDTH = 0.46 * HEAD_WIDTH
SHOULDER_WIDTH = 0.41
WAIST_WIDTH = 0.75 * SHOULDER_WIDTH
_SHOULDER_HEIGHT = 0.475
_CROTCH_HEIGHT = -0.200
TORSO_HEIGHT = _SHOULDER_HEIGHT - _CROTCH_HEIGHT

# Polynomial smooth-minimum factor, expressed in head widths (about 2.5 cm).
SMIN_K = 0.15
_BLEND = SMIN_K * HEAD_WIDTH
_EDGE_FALLOFF = 0.010
# Depth bulge is this fraction of the local half-width.
DEPTH_RATIO = 0.75
# Gaussian sigmas in grid pixels smoothing the edge distance, thickness and
# segment planes.
_EDGE_SMOOTHING = 2.0
_THICKNESS_SMOOTHING = 3.0
_PLANE_SMOOTHING = 4.0

REST_ARM_ANGLE = 8.0
RAISED_ARM_ANGLE = 158.0
SHOULDER_LIFT = 0.065 * TORSO_HEIGHT
SHOULDER_INSET = 0.020
# The forearm follows the upper arm with this phase lag of the motion cycle
# (radians), so the arm swings as two segments instead of one rigid board.
FOREARM_PHASE_LAG = 0.175
# Constant elbow bend towards the side the forearm trails while raising.
ELBOW_REST_FLEX = 4.0
# Sternum and shoulder girdle rise with arms above horizontal (~2.4 grid px).
CHEST_LIFT = 0.018
# Breathing changes chest width and shoulder height by this share of the
# torso width.
BREATH_AMPLITUDE = 0.025
# Wrists and palms are held in front of the arm plane (metres towards the
# camera), so palms are among the closest points like the middle of the chest.
WRIST_FORWARD = 0.040
PALM_FORWARD = 0.075
_UPPER_ARM_LENGTH = 0.300
_FOREARM_LENGTH = 0.255


@dataclass(frozen=True)
class HumanPose:
    """Pose parameters of one frame; angles are in degrees from hanging down."""

    raised: float
    upper_arm_angle: float
    forearm_angle: float
    elbow_flex: float
    shoulder_lift: float
    shoulder_inset: float
    chest_lift: float
    breath_lift: float
    chest_scale: float
    sway: float


def _ease_in_out_sine(value: float) -> float:
    """sin^2 easing: zero speed at both turning points, peak slope pi/2."""
    return math.sin(math.pi / 2 * value) ** 2


def _smoothstep(value: float) -> float:
    value = min(max(value, 0.0), 1.0)
    return value * value * (3 - 2 * value)


def human_pose(frame_index: int) -> HumanPose:
    if not 0 <= frame_index < FRAME_COUNT:
        raise ValueError(f"Frame index must be between 0 and {FRAME_COUNT - 1}.")

    phase = (frame_index % ARM_CYCLE_FRAMES) / ARM_CYCLE_FRAMES
    progress = 1 - abs(2 * phase - 1)
    raised = _ease_in_out_sine(progress)
    span = RAISED_ARM_ANGLE - REST_ARM_ANGLE
    upper_arm_angle = REST_ARM_ANGLE + span * raised
    # sin^2 of the triangle wave equals (1 - cos(tau * phase)) / 2, so the
    # lag is a true phase shift of the cycle; the forearm trails the swing.
    forearm_raised = (1 - math.cos(math.tau * phase - FOREARM_PHASE_LAG)) / 2
    forearm_angle = REST_ARM_ANGLE + span * forearm_raised - ELBOW_REST_FLEX
    elevation = _smoothstep((upper_arm_angle - 90) / (RAISED_ARM_ANGLE - 90))
    breathing = math.sin(math.tau * frame_index / BREATH_PERIOD_FRAMES)
    return HumanPose(
        raised=raised,
        upper_arm_angle=upper_arm_angle,
        forearm_angle=forearm_angle,
        elbow_flex=upper_arm_angle - forearm_angle,
        shoulder_lift=SHOULDER_LIFT * elevation,
        shoulder_inset=SHOULDER_INSET * elevation,
        chest_lift=CHEST_LIFT * elevation,
        breath_lift=BREATH_AMPLITUDE * SHOULDER_WIDTH * 0.5 * (1 + breathing),
        chest_scale=1 + BREATH_AMPLITUDE * breathing + 0.015 * raised,
        sway=0.008 * math.sin(math.tau * phase),
    )


def _smin(first: _FloatMap, second: _FloatMap, k: float) -> _FloatMap:
    """Polynomial smooth minimum; infinite inputs behave like a plain min."""
    with np.errstate(invalid="ignore"):
        weight = np.clip((k - np.abs(first - second)) / k, 0, 1)
    weight = np.nan_to_num(weight, nan=0.0)
    return np.minimum(first, second) - weight * weight * k / 4


@dataclass(frozen=True)
class _Segment:
    """Signed 2D distance of one body part and the depth plane of its axis."""

    distance: _FloatMap
    plane: _FloatMap


def _ellipsoid(
    x: _FloatMap,
    y: _FloatMap,
    center: _Point,
    radii: _Radii,
    angle: float = 0.0,
) -> _Segment:
    """Ellipse silhouette; ``center[2]`` is the depth of its middle plane."""
    dx, dy = x - center[0], y - center[1]
    cosine, sine = math.cos(angle), math.sin(angle)
    local_x = (cosine * dx + sine * dy) / radii[0]
    local_y = (-sine * dx + cosine * dy) / radii[1]
    k0 = np.hypot(local_x, local_y)
    k1 = np.hypot(local_x / radii[0], local_y / radii[1])
    distance = np.where(
        k1 > 1e-12,
        k0 * (k0 - 1) / np.maximum(k1, 1e-12),
        -min(radii[0], radii[1]),
    )
    return _Segment(distance, np.full_like(x, center[2]))


def _capsule(
    x: _FloatMap,
    y: _FloatMap,
    start: _Point,
    end: _Point,
    start_radius: float,
    end_radius: float,
) -> _Segment:
    """Tapered capsule; its plane follows the depth of the axis."""
    axis_x, axis_y = end[0] - start[0], end[1] - start[1]
    length = math.hypot(axis_x, axis_y)
    if length <= abs(start_radius - end_radius):
        raise ValueError("A limb must be longer than its radius difference.")
    unit_x, unit_y = axis_x / length, axis_y / length
    px, py = x - start[0], y - start[1]
    along = px * unit_x + py * unit_y
    across = np.abs(py * unit_x - px * unit_y)

    slope = (start_radius - end_radius) / length
    normal = math.sqrt(1 - slope * slope)
    k = across * -slope + along * normal
    distance = np.where(
        k < 0,
        np.hypot(across, along) - start_radius,
        np.where(
            k > normal * length,
            np.hypot(across, along - length) - end_radius,
            across * normal + along * slope - start_radius,
        ),
    )

    position = np.clip(along / length, 0, 1)
    return _Segment(distance, start[2] + (end[2] - start[2]) * position)


def _masked_blur(values: _FloatMap, mask: NDArray[np.bool_], sigma: float) -> _FloatMap:
    """Gaussian blur that only averages pixels inside ``mask``."""
    weight = mask.astype(np.float64)
    total = cv2.GaussianBlur(values * weight, (0, 0), sigma)
    norm = cv2.GaussianBlur(weight, (0, 0), sigma)
    return np.where(mask, total / np.maximum(norm, 1e-12), 0.0)


def local_half_width(inside: _FloatMap) -> _FloatMap:
    """Radius of the largest inscribed disc covering each pixel.

    ``inside`` is the distance to the outer silhouette in grid pixels (zero
    outside). The result is the half-width of the body part a pixel belongs
    to, so it is constant across a limb instead of peaking on its axis.
    """
    radius = np.zeros_like(inside)
    for size in range(1, int(np.ceil(inside.max())) + 1):
        centres = (inside >= size).astype(np.uint8)
        disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * size + 1,) * 2)
        radius[cv2.dilate(centres, disc) != 0] = size
    return np.maximum(radius, inside)


class _Body:
    """Unites segment silhouettes with smin into one signed distance field.

    Depth is derived only after the union, from the distance to the outer
    silhouette, so overlapping segments leave no seams inside the body.
    """

    def __init__(self, shape: tuple[int, int]) -> None:
        self.distance = np.full(shape, np.inf)
        self._plane_sum = np.zeros(shape)
        self._weight_sum = np.zeros(shape)

    def add(self, segment: _Segment, blend: float = _BLEND) -> None:
        self.distance = _smin(self.distance, segment.distance, blend)
        weight = np.exp(-np.maximum(segment.distance, 0) / _EDGE_FALLOFF)
        self._plane_sum += weight * segment.plane
        self._weight_sum += weight

    def depth_surface(self) -> _FloatMap:
        """Front surface in metres; ``inf`` outside the silhouette.

        Every cross-section bulges as a parabola ``R * (1 - (1 - d / R)^2)``
        over its whole width, where ``d`` is the distance from the edge in
        the single smin-united distance field and ``R`` the smoothed local
        half-width. The parabola has zero slope on the axis, so the ridge of
        the distance field leaves no crease, and there is no flat top that
        would separate the edge from the middle of the body.
        """
        inside = self.distance <= 0
        edge = np.where(inside, -self.distance, 0.0) / _PIXEL_SIZE
        half_width = np.maximum(
            _masked_blur(local_half_width(edge), inside, _THICKNESS_SMOOTHING), 1.0
        )
        rounded_edge = _masked_blur(edge, inside, _EDGE_SMOOTHING)
        towards_axis = np.clip(rounded_edge / half_width, 0, 1)
        bulge = (
            DEPTH_RATIO
            * half_width
            * _PIXEL_SIZE
            * (1 - (1 - towards_axis) ** 2)
        )
        plane = self._plane_sum / np.maximum(self._weight_sum, 1e-12)
        plane = _masked_blur(plane, inside, _PLANE_SMOOTHING)
        return np.where(inside, plane - bulge, np.inf)


def _extend(
    point: _Point, direction: tuple[float, float], length: float, dz: float = 0
) -> _Point:
    return (
        point[0] + direction[0] * length,
        point[1] + direction[1] * length,
        point[2] + dz,
    )


@dataclass(frozen=True)
class _ArmJoints:
    shoulder: _Point
    elbow: _Point
    wrist: _Point
    palm: _Point
    forearm_direction: tuple[float, float]


def _arm_joints(pose: HumanPose, side: int, torso_x: float) -> _ArmJoints:
    shoulder = (
        torso_x + side * (SHOULDER_WIDTH / 2 - pose.shoulder_inset),
        _SHOULDER_HEIGHT + pose.shoulder_lift + pose.breath_lift,
        -0.005,
    )
    upper_angle = math.radians(pose.upper_arm_angle)
    forearm_angle = math.radians(pose.forearm_angle)
    upper_direction = (side * math.sin(upper_angle), -math.cos(upper_angle))
    forearm_direction = (side * math.sin(forearm_angle), -math.cos(forearm_angle))
    lift = math.sin(math.pi * pose.raised)
    elbow = _extend(shoulder, upper_direction, _UPPER_ARM_LENGTH, -0.030 * lift)
    wrist = _extend(
        elbow, forearm_direction, _FOREARM_LENGTH, -0.015 * pose.raised - WRIST_FORWARD
    )
    palm = _extend(wrist, forearm_direction, 0.085, WRIST_FORWARD - PALM_FORWARD)
    return _ArmJoints(shoulder, elbow, wrist, palm, forearm_direction)


def _arm(
    body: _Body,
    x: _FloatMap,
    y: _FloatMap,
    pose: HumanPose,
    side: int,
    torso_x: float,
) -> None:
    joints = _arm_joints(pose, side, torso_x)
    shoulder, elbow, wrist = joints.shoulder, joints.elbow, joints.wrist
    girdle_lift = pose.chest_lift + pose.breath_lift
    neck_base = (torso_x + side * 0.035, 0.565 + 0.5 * girdle_lift, 0.005)
    trapezius_end = (shoulder[0] - side * 0.025, shoulder[1] + 0.025, 0.000)
    girdle_start = (torso_x + side * 0.060, _SHOULDER_HEIGHT - 0.020 + girdle_lift, 0.000)
    body.add(_capsule(x, y, neck_base, trapezius_end, 0.036, 0.032))
    body.add(_capsule(x, y, girdle_start, shoulder, 0.060, 0.052))
    body.add(_ellipsoid(x, y, shoulder, (0.058, 0.062)))
    body.add(_capsule(x, y, shoulder, elbow, 0.052, 0.039))
    body.add(_capsule(x, y, elbow, wrist, 0.041, 0.027))

    direction = joints.forearm_direction
    angle = math.atan2(direction[1], direction[0]) - math.pi / 2
    body.add(_ellipsoid(x, y, joints.palm, (0.044, 0.092), angle))


def human_frame(frame_index: int) -> DepthFrame:
    """Model a frontal synthetic human, not a measured person or camera scan."""
    pose = human_pose(frame_index)
    x, y = np.meshgrid(
        (np.arange(WIDTH, dtype=np.float64) + 0.5) * _PIXEL_SIZE - _VIEW_WIDTH / 2,
        _VIEW_TOP - (np.arange(HEIGHT, dtype=np.float64) + 0.5) * _PIXEL_SIZE,
    )
    body = _Body(x.shape)
    hips_x = pose.sway
    torso_x = 0.6 * pose.sway
    head_x = 0.4 * pose.sway

    body.add(
        _ellipsoid(
            x,
            y,
            (torso_x, 0.310 + pose.chest_lift, 0.005),
            (0.180 * pose.chest_scale, 0.220),
        )
    )
    body.add(
        _ellipsoid(
            x,
            y,
            (0.8 * torso_x + 0.2 * hips_x, 0.110, 0.005),
            (WAIST_WIDTH / 2, 0.220),
        )
    )
    body.add(_ellipsoid(x, y, (hips_x, -0.060, 0.008), (0.170, 0.165)))
    body.add(
        _capsule(x, y, (torso_x, 0.500, 0.010), (head_x, 0.670, 0.000),
                 NECK_WIDTH / 2, NECK_WIDTH / 2)
    )
    body.add(_ellipsoid(x, y, (head_x, 0.760, 0.0), HEAD_RADII))

    for side in (-1, 1):
        hip = (hips_x + side * 0.090, -0.135, 0.015)
        knee = (side * 0.104, -0.470, -0.004)
        ankle = (side * 0.114, -0.815, 0.012)
        body.add(_capsule(x, y, hip, knee, 0.085, 0.052))
        body.add(_capsule(x, y, knee, ankle, 0.056, 0.031))
        body.add(_ellipsoid(x, y, (side * 0.120, -0.868, -0.015),
                            (0.048, 0.068)))
        _arm(body, x, y, pose, side, torso_x)

    front = body.depth_surface()
    # Smooth facial relief instead of separate segments: eye sockets and nose.
    sockets = sum(
        0.005
        * np.exp(
            -((x - head_x - side * 0.032) / 0.018) ** 2
            - ((y - 0.785) / 0.011) ** 2
        )
        for side in (-1, 1)
    )
    nose = -0.012 * np.exp(-((x - head_x) / 0.012) ** 2 - ((y - 0.740) / 0.026) ** 2)
    front = front + np.where(np.isfinite(front), sockets + nose, 0)

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
