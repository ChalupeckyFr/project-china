"""2.5D volume targets inside depth silhouettes.

Pure geometry over the depth matrix; it knows nothing about CSV parsing or
drawing. The interior is filled from one fixed hexagonal lattice with a small
static jitter, so the fill is homogeneous without random clumps or gaps. The
lattice is anchored to the body: each keyframe shifts it horizontally by the
weighted centre of the thick body core (torso), so torso targets ride along
with the weight shift instead of re-sampling. The vertical centre and the
spread of the core jump when hanging arms merge with it at the armpits, so
they are not used. A
lattice point is a target while it lies inside the silhouette. Between
keyframes the signed distance fields and anchors of both keyframes are
blended, so the silhouette grows and shrinks smoothly; every target keeps its
lattice index as a stable identity. Each target also carries the axis across
the local limb (from the structure tensor of the signed distance), a limb
weight from the local half-width and its depth inside the silhouette, so a
renderer can spread limb particles across the bone.
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
# Body core: pixels deeper than this share of the deepest inside distance.
_CORE_SHARE = 0.5
# Local half-width (grid pixels) at or below the first value is a full limb,
# at or above the second no limb (torso); in between it blends smoothly.
LIMB_HALF_WIDTH = (12.0, 16.0)
_HALF_WIDTH_REACH = 10
_AXIS_SIGMA = 3.0

_Points = NDArray[np.float64]
_Values = NDArray[np.float64]
_Map = NDArray[np.float32]


@dataclass(frozen=True)
class BodyAnchor:
    """Weighted horizontal centre (grid pixels) of the thick body core."""

    centre_x: float


@dataclass(frozen=True)
class FillLattice:
    """Fixed fill points in the coordinates of ``reference``; the index is the id."""

    points: _Points
    spacing: float
    reference: BodyAnchor | None = None

    @property
    def count(self) -> int:
        return len(self.points)


@dataclass(frozen=True)
class FillField:
    """One keyframe sampled at every lattice point placed by its anchor.

    ``axis`` holds the structure tensor components (Jxx - Jyy, 2 Jxy) of the
    signed distance; ``half_width`` is the local half-width in grid pixels.
    """

    points: _Points
    signed_distance: _Values
    depth: _Values
    axis: _Points
    half_width: _Values


@dataclass(frozen=True)
class FillTargets:
    """Lattice points inside the silhouette of one rendered frame.

    ``axes`` are unit vectors across the local limb (perpendicular to the
    bone), ``limb`` is 1 on thin limbs and 0 on the torso, ``room`` is the
    distance to the silhouette edge in grid pixels.
    """

    ids: NDArray[np.intp]
    points: _Points
    depth: _Values
    axes: _Points
    limb: _Values
    room: _Values


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


def _inside_distance(mask: NDArray[np.uint8]) -> _Map:
    # The zero border keeps the transform finite when the mask fills the grid.
    padded = cv2.copyMakeBorder(mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    inside = cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return inside[1:-1, 1:-1]


def body_anchor(mask: NDArray[np.uint8]) -> BodyAnchor | None:
    """Horizontal centre of the body core, weighted by depth below the core
    threshold, so it changes continuously when limbs move."""
    mask = np.asarray(mask, dtype=np.uint8)
    if not mask.any():
        return None
    inside = _inside_distance(mask)
    weight = np.maximum(inside - _CORE_SHARE * inside.max(), 0)
    columns = np.nonzero(weight)[1]
    weights = weight[weight > 0].astype(np.float64)
    if not len(columns):
        columns = np.nonzero(mask)[1]
        weights = np.ones(len(columns))
    return BodyAnchor(float(columns @ weights / weights.sum()))


def anchor_points(
    points: _Points, reference: BodyAnchor | None, anchor: BodyAnchor | None
) -> _Points:
    """Place lattice points given in ``reference`` coordinates by ``anchor``."""
    if reference is None or anchor is None:
        return points
    return points + (anchor.centre_x - reference.centre_x, 0.0)


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
    anchors = [body_anchor(mask) for mask in masks]
    reference = next((anchor for anchor in anchors if anchor is not None), None)

    def needed(lattice: FillLattice) -> int:
        return max(
            int(
                np.count_nonzero(
                    _sample(field, anchor_points(lattice.points, reference, anchor))
                    <= _INSIDE
                )
            )
            for field, anchor in zip(fields, anchors, strict=True)
        )

    lattice = hex_lattice(grid_size, spacing, seed)
    for _ in range(_FIT_ATTEMPTS):
        required = needed(lattice)
        if required <= budget:
            break
        spacing *= math.sqrt(required / budget) * 1.002
        lattice = hex_lattice(grid_size, spacing, seed)
    return FillLattice(lattice.points, lattice.spacing, reference)


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
    inside = _inside_distance(mask)
    outside = cv2.distanceTransform(
        np.where(body, 0, 255).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    # Pixel centres sit half a pixel from the edge between them.
    return np.where(body, 0.5 - inside, outside - 0.5).astype(np.float32)


def _cross_section(
    mask: NDArray[np.uint8], signed: _Map
) -> tuple[_Map, _Map, _Map]:
    """Structure tensor components of the signed distance and local half-width.

    On a limb the distance gradient points across the bone on both sides of
    its axis; the doubled-angle tensor averages them into one axis even on
    the medial line, where the gradient itself cancels out.
    """
    gradient_y, gradient_x = np.gradient(signed)
    blur = (0, 0)
    cosine = cv2.GaussianBlur(gradient_x**2 - gradient_y**2, blur, _AXIS_SIGMA)
    sine = cv2.GaussianBlur(2 * gradient_x * gradient_y, blur, _AXIS_SIGMA)
    size = 2 * _HALF_WIDTH_REACH + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    half_width = cv2.dilate(_inside_distance(mask), kernel)
    return cosine, sine, half_width


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
    """One keyframe sampled at the lattice points placed by its body anchor.

    The signed distance comes from the whole binary silhouette, i.e. the
    union of every body part, so there is no inner edge in armpits or at
    joints; only the outer border is an edge.
    """
    mask = np.asarray(selection.mask, dtype=np.uint8)
    points = anchor_points(lattice.points, lattice.reference, body_anchor(mask))
    signed = _signed_distance(mask)
    cosine, sine, half_width = _cross_section(mask, signed)
    return FillField(
        points,
        _sample(signed, points),
        _sample(depth, points),
        np.column_stack((_sample(cosine, points), _sample(sine, points))),
        _sample(half_width, points),
    )


def fill_targets(
    lattice: FillLattice, current: FillField, following: FillField, alpha: float
) -> FillTargets:
    """Lattice points inside the blended silhouette, all values blended."""
    eased = smoothstep(alpha)

    def blend(before: _Values, after: _Values) -> _Values:
        return before + (after - before) * eased

    distance = blend(current.signed_distance, following.signed_distance)
    ids = np.flatnonzero(distance <= _INSIDE)
    tensor = blend(current.axis[ids], following.axis[ids])
    angle = 0.5 * np.arctan2(tensor[:, 1], tensor[:, 0])
    low, high = LIMB_HALF_WIDTH
    width = blend(current.half_width[ids], following.half_width[ids])
    thickness = np.clip((width - low) / (high - low), 0, 1)
    return FillTargets(
        ids,
        blend(current.points[ids], following.points[ids]),
        blend(current.depth[ids], following.depth[ids]),
        np.column_stack((np.cos(angle), np.sin(angle))),
        1 - thickness * thickness * (3 - 2 * thickness),
        -distance[ids],
    )


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