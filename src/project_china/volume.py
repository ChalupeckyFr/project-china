"""2.5D volume targets sampled inside depth silhouettes.

Pure geometry over the depth matrix; it knows nothing about CSV parsing or
drawing. Every outline point casts a ray inwards to the middle of the body;
layers along the ray are spaced by the depth gradient, so they crowd near
the steep edges and thin out towards flat centres of the torso, head and
limbs.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from project_china.frames import DepthFrame
from project_china.morph import MORPH_POINT_COUNT, ContourShape, smoothstep
from project_china.selection import DepthSelection

VOLUME_LAYERS = 12
_RAY_SAMPLES = 24
_RAY_STEP = 0.5
_GRADIENT_FLOOR = 0.25
_MIN_REACH_WEIGHT = 0.5

_Points = NDArray[np.float64]
_Values = NDArray[np.float64]


@dataclass(frozen=True)
class VolumeShape:
    """Outline points with depth-weighted layers along inward rays.

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
    ``inward`` the position between the edge layer (0) and the deepest
    layer (1).
    """

    along: _Values
    inward: _Values

    @property
    def count(self) -> int:
        return len(self.along)


def volume_picks(count: int, seed: int = 7) -> VolumePicks:
    if count < 0:
        raise ValueError("Volume particle count must not be negative.")
    generator = np.random.default_rng(seed)
    along = (np.arange(count) + generator.random(count)) / max(count, 1)
    return VolumePicks(along, generator.random(count))


def depth_gradient(depths: NDArray[np.float64], mask: NDArray[np.bool_]) -> _Values:
    """Depth slope per grid pixel using only neighbours inside ``mask``."""
    return np.hypot(_axis_gradient(depths, mask, 1), _axis_gradient(depths, mask, 0))


def _axis_gradient(
    depths: NDArray[np.float64], mask: NDArray[np.bool_], axis: int
) -> _Values:
    difference = np.diff(depths, axis=axis)
    valid = np.logical_and(
        np.take(mask, range(1, mask.shape[axis]), axis=axis),
        np.take(mask, range(mask.shape[axis] - 1), axis=axis),
    )
    difference = np.where(valid, difference, 0.0)
    pad_after = [(0, 0), (0, 0)]
    pad_before = [(0, 0), (0, 0)]
    pad_after[axis] = (0, 1)
    pad_before[axis] = (1, 0)
    forward = np.pad(difference, pad_after)
    backward = np.pad(difference, pad_before)
    forward_valid = np.pad(valid, pad_after)
    backward_valid = np.pad(valid, pad_before)
    count = forward_valid.astype(np.float64) + backward_valid
    return np.where(count > 0, (forward + backward) / np.maximum(count, 1), 0.0)


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
    tangent = np.roll(points, -2, axis=0) - np.roll(points, 2, axis=0)
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


def build_volume(
    shape: ContourShape,
    depths: NDArray[np.float64],
    mask: NDArray[np.bool_],
    gradient: _Values,
    max_reach: float,
    count: int = MORPH_POINT_COUNT,
) -> VolumeShape:
    """Sample layers on inward rays of one contour.

    Each ray ends halfway across the body (capped by ``max_reach``), so rays
    from opposite edges meet in the middle. Layers sit at equal quantiles of
    ``floor + slope``, which crowds them where the surface turns away.
    """
    outline = shape.resample(count)
    normals = _inward_normals(outline, mask)

    steps = np.arange(1, int(np.ceil(2 * max_reach / _RAY_STEP)) + 2) * _RAY_STEP
    probes = outline[:, None, :] + normals[:, None, :] * steps[None, :, None]
    inside = _inside(mask, probes)
    leaving = np.argmin(inside, axis=1)
    exit_distance = np.where(inside.all(axis=1), steps[-1], steps[leaving])
    reach = np.minimum(exit_distance / 2, max_reach)
    reach[~np.any(normals, axis=1)] = 0

    samples = (np.arange(_RAY_SAMPLES) + 0.5) / _RAY_SAMPLES
    ray_points = (
        outline[:, None, :]
        + normals[:, None, :] * (reach[:, None] * samples[None, :])[..., None]
    )
    rows, columns, valid = _pixels(ray_points, mask.shape)
    slope = np.where(valid, gradient[rows, columns], 0.0)
    scale = np.median(gradient[mask]) if mask.any() else 0.0
    weight = _GRADIENT_FLOOR + (slope / scale if scale > 0 else np.zeros_like(slope))
    cumulative = np.cumsum(weight, axis=1)
    cumulative = np.concatenate(
        (np.zeros((len(outline), 1)), cumulative / cumulative[:, -1:]), axis=1
    )

    quantiles = (np.arange(VOLUME_LAYERS) + 0.5) / VOLUME_LAYERS
    segment = np.clip(
        (cumulative[:, None, :] < quantiles[None, :, None]).sum(axis=2) - 1,
        0,
        _RAY_SAMPLES - 1,
    )
    low = np.take_along_axis(cumulative, segment, axis=1)
    high = np.take_along_axis(cumulative, segment + 1, axis=1)
    within = (quantiles[None, :] - low) / np.maximum(high - low, 1e-12)
    fractions = (segment + within) / _RAY_SAMPLES

    layers = outline[:, None, :] + normals[:, None, :] * (
        reach[:, None] * fractions
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
    gradient = depth_gradient(depths, mask)
    # The zero border keeps the transform finite when the mask fills the grid.
    padded = cv2.copyMakeBorder(selection.mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    inscribed = cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    max_reach = 1.5 * float(inscribed.max()) + 1
    return tuple(
        build_volume(shape, depths, mask, gradient, max_reach, count) for shape in shapes
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
    volume: VolumeTargets, picks: VolumePicks
) -> tuple[_Points, _Values]:
    """Return points and depths of volume particles inside ``volume``.

    Outline positions are chosen in proportion to the ray length, so wide
    parts such as the torso get as many particles per area as thin limbs.
    """
    point_count = len(volume.outline)
    if point_count == 0 or picks.count == 0:
        return np.empty((0, 2)), np.empty(0)

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
