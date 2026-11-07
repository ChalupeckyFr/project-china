"""2.5D volume targets inside depth silhouettes.

Pure geometry over the depth matrix; it knows nothing about CSV parsing or
drawing. The interior is filled from one fixed hexagonal lattice in grid
coordinates with a small static jitter, so the fill is homogeneous without
random clumps or gaps. A lattice point is a target while it lies inside the
silhouette. Between keyframes the signed distance fields of both keyframes
are blended, so the silhouette grows and shrinks smoothly while the targets
never move; every target keeps its lattice index as a stable identity.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from project_china.frames import DepthFrame
from project_china.morph import MORPH_POINT_COUNT, ContourShape, smoothstep
from project_china.selection import DepthSelection

# Static lattice jitter radius in grid pixels (about 1 screen pixel).
FILL_JITTER = 0.5
# Lattice fitted so the fullest keyframe uses at most this share of particles;
# blended silhouettes between keyframes get the rest.
_FIT_HEADROOM = 0.97
_FIT_ATTEMPTS = 30
# A target must lie this deep inside, so its nearest pixel is a body pixel.
_INSIDE = -0.5

_Points = NDArray[np.float64]
_Values = NDArray[np.float64]
_Map = NDArray[np.float32]


@dataclass(frozen=True)
class FillLattice:
    """Fixed fill points in grid coordinates; the index is the target id."""

    points: _Points
    spacing: float

    @property
    def count(self) -> int:
        return len(self.points)


@dataclass(frozen=True)
class FillField:
    """Signed distance (negative inside) and depth at every lattice point."""

    signed_distance: _Values
    depth: _Values


@dataclass(frozen=True)
class FillTargets:
    """Lattice points inside the silhouette of one rendered frame."""

    ids: NDArray[np.intp]
    points: _Points
    depth: _Values


def hex_lattice(
    grid_size: tuple[int, int], spacing: float, seed: int = 11
) -> FillLattice:
    """Hexagonal lattice over the grid, each point jittered by ``FILL_JITTER``."""
    if spacing <= 0:
        raise ValueError("Lattice spacing must be positive.")
    width, height = grid_size
    rows = np.arange(0.0, height, spacing * math.sqrt(3) / 2)
    columns = np.arange(0.0, width + spacing, spacing)
    x = columns[None, :] + np.where(np.arange(len(rows)) % 2, spacing / 2, 0.0)[:, None]
    y = np.broadcast_to(rows[:, None], x.shape)
    points = np.column_stack((x.ravel(), y.ravel()))
    points = points[points[:, 0] <= width - 1]
    generator = np.random.default_rng(seed)
    angle = generator.uniform(0, math.tau, len(points))
    radius = FILL_JITTER * np.sqrt(generator.random(len(points)))
    points += np.column_stack((np.cos(angle), np.sin(angle))) * radius[:, None]
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    return FillLattice(points, spacing)



def fit_lattice(
    grid_size: tuple[int, int],
    masks: Sequence[NDArray[np.uint8]],
    count: int,
    seed: int = 11,
) -> FillLattice:
    """Densest lattice whose fullest silhouette needs at most ``count`` targets.

    Every target then gets its own particle; particles left over in smaller
    silhouettes fade out in the renderer instead of crowding the body.
    """
    if count < 0:
        raise ValueError("Volume particle count must not be negative.")
    masks = [np.asarray(mask, dtype=np.uint8) for mask in masks]
    area = max((int(np.count_nonzero(mask)) for mask in masks), default=0)
    if count == 0 or area == 0:
        return FillLattice(np.empty((0, 2)), 0.0)
    budget = _FIT_HEADROOM * count
    spacing = math.sqrt(2 * area / (math.sqrt(3) * budget))
    fields = [_signed_distance(mask) for mask in masks]
    lattice = hex_lattice(grid_size, spacing, seed)
    for _ in range(_FIT_ATTEMPTS):
        needed = max(
            int(np.count_nonzero(_sample(field, lattice.points) <= _INSIDE))
            for field in fields
        )
        if needed <= budget:
            break
        spacing *= math.sqrt(needed / budget) * 1.002
        lattice = hex_lattice(grid_size, spacing, seed)
    return lattice


def filled_depth(frame: DepthFrame, selection: DepthSelection) -> _Map:
    """Depth matrix where every pixel outside the silhouette takes the depth
    of its nearest silhouette pixel, so sampling near the edge stays smooth."""
    depths = np.asarray(frame.depths, dtype=np.float32)
    mask = selection.mask != 0
    if not mask.any():
        return depths
    outside = np.where(mask, 0, 255).astype(np.uint8)
    _, labels = cv2.distanceTransformWithLabels(
        outside, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
    )
    # Silhouette pixels are labelled 1..N in row-major order.
    return depths[mask][labels - 1]


def _signed_distance(mask: NDArray[np.uint8]) -> _Map:
    body = mask != 0
    if not body.any():
        return np.full(mask.shape, np.float32(1e6))
    # The zero border keeps the transform finite when the mask fills the grid.
    padded = cv2.copyMakeBorder(mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    inside = cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    outside = cv2.distanceTransform(
        np.where(body, 0, 255).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    # Pixel centres sit half a pixel from the edge between them.
    return np.where(body, 0.5 - inside[1:-1, 1:-1], outside - 0.5).astype(np.float32)


def _sample(values: _Map, points: _Points) -> _Values:
    if not len(points):
        return np.empty(0)
    x = points[:, 0].astype(np.float32).reshape(1, -1)
    y = points[:, 1].astype(np.float32).reshape(1, -1)
    sampled = cv2.remap(
        values, x, y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )
    return sampled.ravel().astype(np.float64)


def fill_field(
    lattice: FillLattice, selection: DepthSelection, depth: _Map
) -> FillField:
    """Signed distance and depth of one keyframe at the lattice points.

    The signed distance comes from the whole binary silhouette, i.e. the
    union of every body part, so there is no inner edge in armpits or at
    joints; only the outer border is an edge.
    """
    return FillField(
        _sample(_signed_distance(selection.mask), lattice.points),
        _sample(depth, lattice.points),
    )


def fill_targets(
    lattice: FillLattice, current: FillField, following: FillField, alpha: float
) -> FillTargets:
    """Lattice points inside the blended silhouette with blended depth."""
    eased = smoothstep(alpha)
    distance = current.signed_distance + (
        following.signed_distance - current.signed_distance
    ) * eased
    ids = np.flatnonzero(distance <= _INSIDE)
    depth = current.depth[ids] + (following.depth[ids] - current.depth[ids]) * eased
    return FillTargets(ids, lattice.points[ids], depth)


def outline_depths(
    depth: _Map, shapes: Sequence[ContourShape], count: int = MORPH_POINT_COUNT
) -> tuple[_Values, ...]:
    """Depth at the resampled outline points of every contour."""
    return tuple(_sample(depth, shape.resample(count)) for shape in shapes)


def morph_outline_depths(
    pairs: Sequence[tuple[_Values | None, _Values | None]], alpha: float
) -> _Values:
    """Interpolate outline depths in the order of :func:`morph.morph_contours`."""
    eased = smoothstep(alpha)
    parts = [
        after if before is None else before if after is None
        else before + (after - before) * eased
        for before, after in pairs
        if before is not None or after is not None
    ]
    return np.concatenate(parts) if parts else np.empty(0)