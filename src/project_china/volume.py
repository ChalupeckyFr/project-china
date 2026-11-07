"""2.5D volume targets sampled inside depth silhouettes.

Pure geometry over the depth matrix; it knows nothing about CSV parsing or
drawing. Every point of the outer outline casts a ray inwards to the middle
of the body. Rays only form a continuous coordinate grid that morphs between
keyframes; particles sit at random continuous positions on them with density
``1 - 0.8 * inward``, which fills the whole interior evenly with a slightly
denser edge. Depth look is left to the renderer (size and alpha), never to
gaps in the fill.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from project_china.frames import DepthFrame
from project_china.morph import MORPH_POINT_COUNT, ContourShape, smoothstep
from project_china.selection import DepthSelection

VOLUME_LAYERS = 16
# Fill density P = 1 - EDGE_BIAS * inward along each ray: the whole body is
# filled and the edge is only mildly denser than the middle.
EDGE_BIAS = 0.8
_RAY_STEP = 0.5
# Grid pixels the edge distance may drop before a ray stops at the ridge.
_RIDGE_TOLERANCE = 0.75
_NORMAL_WINDOW = 8
# Gaussian sigma in outline points smoothing ray lengths.
_REACH_SMOOTHING = 4.0
# Rays reach slightly past the medial axis so both sides overlap there.
_REACH_OVERSHOOT = 1.3
_MIN_REACH_WEIGHT = 0.5

_Points = NDArray[np.float64]
_Values = NDArray[np.float64]


@dataclass(frozen=True)
class VolumeShape:
    """Outline points with evenly spaced lookup points along inward rays.

    ``layers[i]`` runs from the edge at ``outline[i]`` towards the middle
    of the body; ``reach[i]`` is the ray length in grid pixels.
    """

    outline: _Points
    outline_depth: _Values
    layers: NDArray[np.float64]
    layer_depth: NDArray[np.float64]
    reach: _Values
    centroid: _Points


@dataclass(frozen=True)
class VolumeTargets:
    """Morphed volume of all contours; ``points_per_contour`` per shape."""

    outline: _Points
    outline_depth: _Values
    layers: NDArray[np.float64]
    layer_depth: NDArray[np.float64]
    reach: _Values
    points_per_contour: int


@dataclass(frozen=True)
class VolumePicks:
    """Fixed sampling coordinates of volume particles.

    ``along`` selects an outline position by the cumulative ray length,
    ``inward`` the normalised distance from the edge (0) to the middle of
    the body (1). ``inward`` is drawn continuously, never from fixed layers.
    """

    along: _Values
    inward: _Values

    @property
    def count(self) -> int:
        return len(self.along)


def volume_picks(count: int, seed: int = 7) -> VolumePicks:
    """Stochastic picks with density ``1 - EDGE_BIAS * inward``.

    Inverse transform sampling of that density gives
    ``inward = (1 - sqrt(1 - c * (2 - c) * u)) / c`` with ``c = EDGE_BIAS``
    for uniform ``u``.
    """
    if count < 0:
        raise ValueError("Volume particle count must not be negative.")
    generator = np.random.default_rng(seed)
    along = (np.arange(count) + generator.random(count)) / max(count, 1)
    uniform = generator.random(count)
    bias = EDGE_BIAS
    inward = (1 - np.sqrt(1 - bias * (2 - bias) * uniform)) / bias
    return VolumePicks(along, inward)


def reference_weights(volumes: Sequence[Sequence[VolumeShape]]) -> _Values | None:
    """Mean ray length per outline point over single-contour keyframes.

    Distributing particles along the outline by these fixed weights keeps
    every particle on the same outline point in every frame. Weights of the
    current frame would make a change at one limb shift particles along the
    whole body. Returns ``None`` unless every keyframe has one contour.
    """
    if not volumes or any(len(shapes) != 1 for shapes in volumes):
        return None
    return np.mean([shapes[0].reach for shapes in volumes], axis=0) + _MIN_REACH_WEIGHT


def _pixels(
    points: NDArray[np.float64], shape: tuple[int, int]
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.bool_]]:
    columns = np.rint(points[..., 0]).astype(np.intp)
    rows = np.rint(points[..., 1]).astype(np.intp)
    inside = (columns >= 0) & (columns < shape[1]) & (rows >= 0) & (rows < shape[0])
    return np.clip(rows, 0, shape[0] - 1), np.clip(columns, 0, shape[1] - 1), inside


def _inside(mask: NDArray[np.bool_], points: NDArray[np.float64]) -> NDArray[np.bool_]:
    rows, columns, valid = _pixels(points, mask.shape)
    return valid & mask[rows, columns]


def _depth_at(
    depths: NDArray[np.float64],
    mask: NDArray[np.bool_],
    points: NDArray[np.float64],
    fallback: NDArray[np.float64],
) -> _Values:
    rows, columns, valid = _pixels(points, mask.shape)
    inside = valid & mask[rows, columns]
    return np.where(inside, depths[rows, columns], fallback)


def _inward_normals(points: _Points, mask: NDArray[np.bool_]) -> _Points:
    # A wide tangent window keeps normals steady in concave armpits and crotch.
    tangent = np.roll(points, -_NORMAL_WINDOW, axis=0) - np.roll(
        points, _NORMAL_WINDOW, axis=0
    )
    length = np.hypot(tangent[:, 0], tangent[:, 1])
    safe = np.where(length > 0, length, 1.0)
    # Clockwise on screen (y down): rotating the tangent this way points inwards.
    normals = np.column_stack((-tangent[:, 1], tangent[:, 0])) / safe[:, None]
    normals[length == 0] = 0
    if np.count_nonzero(_inside(mask, points - 2 * normals)) > np.count_nonzero(
        _inside(mask, points + 2 * normals)
    ):
        normals = -normals
    return normals


def _smooth_closed(values: _Values, sigma: float) -> _Values:
    """Gaussian smoothing of values along a closed outline."""
    radius = int(np.ceil(3 * sigma))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    wrapped = np.concatenate((values[-radius:], values, values[:radius]))
    return np.convolve(wrapped, kernel, mode="valid")


def build_volume(
    shape: ContourShape,
    depths: NDArray[np.float64],
    mask: NDArray[np.bool_],
    inscribed: NDArray[np.float32],
    max_reach: float,
    count: int = MORPH_POINT_COUNT,
) -> VolumeShape:
    """Sample evenly spaced lookup points on inward rays of one contour.

    Each ray ends on the medial axis, where the distance from the edge
    (``inscribed``) stops growing, so rays from opposite edges meet in the
    middle. Unlike the first exit from the mask, this end does not jump when
    a ray in an armpit starts or stops slipping past a limb. The even spacing
    carries no density; particles interpolate between the lookup points.
    """
    outline = shape.resample(count)
    normals = _inward_normals(outline, mask)

    steps = np.arange(1, int(np.ceil(2 * max_reach / _RAY_STEP)) + 2) * _RAY_STEP
    probes = outline[:, None, :] + normals[:, None, :] * steps[None, :, None]
    rows, columns, valid = _pixels(probes, mask.shape)
    distance = np.where(valid, inscribed[rows, columns], 0.0)
    peak = np.maximum.accumulate(distance, axis=1)
    falling = distance < peak - _RIDGE_TOLERANCE
    stop = np.where(falling.any(axis=1), np.argmax(falling, axis=1), len(steps))
    before_stop = np.arange(len(steps))[None, :] < stop[:, None]
    ridge = np.argmax(np.where(before_stop, distance, -np.inf), axis=1)
    inside = _inside(mask, probes)
    leaving = np.argmin(inside, axis=1)
    exit_distance = np.where(inside.all(axis=1), steps[-1], steps[leaving])
    # Where the medial axis branches (shoulders, armpits) neighbouring rays
    # end on different branches; smoothing along the outline turns that
    # switch into a gradual change, the exit keeps every ray in the body.
    reach = np.minimum(
        _smooth_closed(steps[ridge], _REACH_SMOOTHING) * _REACH_OVERSHOOT,
        np.maximum(exit_distance - _RAY_STEP, 0),
    )
    reach = np.minimum(reach, max_reach)
    reach[~np.any(normals, axis=1)] = 0

    fractions = np.linspace(0.0, 1.0, VOLUME_LAYERS)
    layers = outline[:, None, :] + normals[:, None, :] * (
        reach[:, None] * fractions[None, :]
    )[..., None]
    outline_depth = _depth_at(
        depths,
        mask,
        outline,
        _depth_at(depths, mask, outline + normals, np.full(len(outline), np.nan)),
    )
    if np.isnan(outline_depth).any():
        known = outline_depth[~np.isnan(outline_depth)]
        fill = known.mean() if len(known) else float(depths[mask].mean()) if mask.any() else 0.0
        outline_depth = np.nan_to_num(outline_depth, nan=fill)
    layer_depth = _depth_at(
        depths, mask, layers, np.repeat(outline_depth[:, None], VOLUME_LAYERS, axis=1)
    )
    return VolumeShape(outline, outline_depth, layers, layer_depth, reach, shape.centroid)


def build_volumes(
    frame: DepthFrame,
    selection: DepthSelection,
    shapes: Sequence[ContourShape],
    count: int = MORPH_POINT_COUNT,
) -> tuple[VolumeShape, ...]:
    """Volume of every prepared contour of one keyframe, in the same order."""
    if not shapes:
        return ()
    depths = np.asarray(frame.depths, dtype=np.float64)
    mask = selection.mask != 0
    # The zero border keeps the transform finite when the mask fills the grid.
    padded = cv2.copyMakeBorder(selection.mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    inscribed = cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    max_reach = 1.5 * float(inscribed.max()) + 1
    inscribed = inscribed[1:-1, 1:-1]
    return tuple(
        build_volume(shape, depths, mask, inscribed, max_reach, count) for shape in shapes
    )


VolumePair = tuple[VolumeShape | None, VolumeShape | None]


def _shrunk(shape: VolumeShape, weight: float) -> VolumeShape:
    centre = shape.centroid
    return VolumeShape(
        centre + (shape.outline - centre) * weight,
        shape.outline_depth,
        centre + (shape.layers - centre) * weight,
        shape.layer_depth,
        shape.reach * weight,
        centre,
    )


def morph_volumes(
    pairs: Sequence[VolumePair], alpha: float, count: int = MORPH_POINT_COUNT
) -> VolumeTargets:
    """Interpolate paired volumes exactly like :func:`morph.morph_contours`."""
    eased = smoothstep(alpha)
    parts: list[VolumeShape] = []
    for before, after in pairs:
        if before is None and after is None:
            continue
        if before is None or after is None:
            shape = after if before is None else before
            parts.append(_shrunk(shape, eased if before is None else 1 - eased))
            continue
        parts.append(
            VolumeShape(
                *(
                    first + (second - first) * eased
                    for first, second in (
                        (before.outline, after.outline),
                        (before.outline_depth, after.outline_depth),
                        (before.layers, after.layers),
                        (before.layer_depth, after.layer_depth),
                        (before.reach, after.reach),
                        (before.centroid, after.centroid),
                    )
                )
            )
        )
    if not parts:
        return VolumeTargets(
            np.empty((0, 2)),
            np.empty(0),
            np.empty((0, VOLUME_LAYERS, 2)),
            np.empty((0, VOLUME_LAYERS)),
            np.empty(0),
            count,
        )
    return VolumeTargets(
        np.vstack([part.outline for part in parts]),
        np.concatenate([part.outline_depth for part in parts]),
        np.concatenate([part.layers for part in parts]),
        np.concatenate([part.layer_depth for part in parts]),
        np.concatenate([part.reach for part in parts]),
        count,
    )


def sample_volume(
    volume: VolumeTargets,
    picks: VolumePicks,
    weights: _Values | None = None,
) -> tuple[_Points, _Values]:
    """Return points and depths of volume particles inside ``volume``.

    Outline positions are chosen in proportion to the ray length, so wide
    parts such as the torso get as many particles per area as thin limbs.
    Fixed ``weights`` (see :func:`reference_weights`) pin every particle to
    one outline point; without them the current ray lengths are used.
    """
    point_count = len(volume.outline)
    if point_count == 0 or picks.count == 0:
        return np.empty((0, 2)), np.empty(0)

    if weights is None or len(weights) != point_count:
        weights = volume.reach + _MIN_REACH_WEIGHT
    cumulative = np.concatenate(((0.0,), np.cumsum(weights)))
    position = np.interp(
        picks.along * cumulative[-1], cumulative, np.arange(point_count + 1)
    )
    first = np.minimum(np.floor(position).astype(np.intp), point_count - 1)
    blend = np.clip(position - first, 0, 1)
    per_contour = volume.points_per_contour
    second = first + 1
    wraps = (second // per_contour != first // per_contour) | (second >= point_count)
    second = np.where(wraps, first - (first % per_contour), second)

    layer = picks.inward * (VOLUME_LAYERS - 1)
    inner = np.minimum(np.floor(layer).astype(np.intp), VOLUME_LAYERS - 2)
    inner = np.maximum(inner, 0)
    depth_blend = np.clip(layer - inner, 0, 1)

    def bilinear(values: NDArray[np.float64]) -> NDArray[np.float64]:
        def along_ray(index: NDArray[np.intp]) -> NDArray[np.float64]:
            low = values[index, inner]
            high = values[index, inner + 1]
            weight = depth_blend.reshape((-1,) + (1,) * (low.ndim - 1))
            return low + (high - low) * weight

        start, end = along_ray(first), along_ray(second)
        weight = blend.reshape((-1,) + (1,) * (start.ndim - 1))
        return start + (end - start) * weight

    return bilinear(volume.layers), bilinear(volume.layer_depth)
