"""Smooth morphing of target outlines between depth keyframes."""

import bisect
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

MORPH_POINT_COUNT = 1024
MAX_TRANSITION_MS = 600.0

_Points = NDArray[np.float64]
ArrayLike2D = NDArray[np.integer] | NDArray[np.floating] | Sequence[Sequence[float]]
_QUARTERS = np.array((0.0, 0.25, 0.5, 0.75, 1.0))
_WHOLE = np.array((0.0, 1.0))


@dataclass(frozen=True)
class ContourShape:
    """Closed outline prepared for index-stable resampling.

    The outline runs clockwise on screen (y grows downwards) and arc position
    zero is the top anchor above the centroid. ``anchors`` holds arc positions
    of the top, right, bottom and left anchors followed by the total length,
    or only ``(0, length)`` when the quadrant anchors are not reliable.
    """

    closed_points: _Points
    cumulative: NDArray[np.float64]
    top_offset: float
    anchors: NDArray[np.float64]
    centroid: NDArray[np.float64]
    area: float

    @property
    def length(self) -> float:
        return float(self.cumulative[-1])

    @property
    def has_quadrants(self) -> bool:
        return len(self.anchors) == 5

    @property
    def anchor_fractions(self) -> NDArray[np.float64]:
        """Normalised positions of the anchors in the resampled outline.

        Each quadrant always receives a quarter of the points, so a change
        in one quadrant never shifts point indices in the other ones.
        """
        return _QUARTERS if self.has_quadrants else _WHOLE

    def sample(
        self, positions: NDArray[np.float64], fractions: NDArray[np.float64]
    ) -> _Points:
        """Return points at normalised ``positions`` in ``[0, 1)``.

        ``fractions`` maps anchors to normalised positions; it must have the
        same length as ``anchors``.
        """
        if self.length == 0:
            return np.repeat(self.closed_points[:1], len(positions), axis=0)
        relative = np.interp(positions, fractions, self.anchors)
        arc = (self.top_offset + relative) % self.length
        return np.column_stack(
            (
                np.interp(arc, self.cumulative, self.closed_points[:, 0]),
                np.interp(arc, self.cumulative, self.closed_points[:, 1]),
            )
        )

    def resample(self, count: int = MORPH_POINT_COUNT) -> _Points:
        """Return ``count`` points evenly spaced within each quadrant.

        Index zero is the top anchor; with reliable quadrants the right,
        bottom and left anchors land on indices ``count/4``, ``count/2`` and
        ``3*count/4``.
        """
        return self.sample(_positions(count), self.anchor_fractions)


def _positions(count: int) -> NDArray[np.float64]:
    if count < 1:
        raise ValueError("Point count must be positive.")
    return np.arange(count, dtype=np.float64) / count


def _signed_area(points: _Points) -> float:
    following = np.roll(points, -1, axis=0)
    return float(
        np.sum(points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1])
        / 2
    )


def _centroid(points: _Points, area: float) -> NDArray[np.float64]:
    if area == 0:
        return points.mean(axis=0)
    following = np.roll(points, -1, axis=0)
    cross = points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1]
    return np.array(
        (
            np.sum((points[:, 0] + following[:, 0]) * cross) / (6 * area),
            np.sum((points[:, 1] + following[:, 1]) * cross) / (6 * area),
        )
    )


def _ray_crossings(
    closed_points: _Points,
    cumulative: NDArray[np.float64],
    centroid: NDArray[np.float64],
    axis: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Crossings of the line through ``centroid`` along ``axis``.

    Returns signed offsets from the centroid along ``axis`` and the arc
    positions of the crossings.
    """
    across = 1 - axis
    start = closed_points[:-1]
    end = closed_points[1:]
    line = centroid[across]
    crosses = ((start[:, across] <= line) & (line < end[:, across])) | (
        (end[:, across] <= line) & (line < start[:, across])
    )
    if not crosses.any():
        return np.empty(0), np.empty(0)
    start = start[crosses]
    end = end[crosses]
    ratio = (line - start[:, across]) / (end[:, across] - start[:, across])
    offsets = start[:, axis] + ratio * (end[:, axis] - start[:, axis])
    lengths = np.diff(cumulative)[crosses]
    arcs = cumulative[:-1][crosses] + ratio * lengths
    return offsets - centroid[axis], arcs


def _nearest(
    offsets: NDArray[np.float64], arcs: NDArray[np.float64], sign: int
) -> float | None:
    distances = offsets * sign
    candidates = distances > 0
    if not candidates.any():
        return None
    return float(arcs[candidates][np.argmin(distances[candidates])])


def prepare_contour(points: ArrayLike2D) -> ContourShape:
    """Prepare one contour given as an ``(n, 2)`` array of ``x, y`` points."""
    points = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if len(points) == 0:
        raise ValueError("Contour must contain at least one point.")
    keep = np.ones(len(points), dtype=bool)
    keep[1:] = np.any(points[1:] != points[:-1], axis=1)
    points = points[keep]
    if len(points) > 1 and np.array_equal(points[0], points[-1]):
        points = points[:-1]

    area = _signed_area(points) if len(points) > 2 else 0.0
    if area < 0:
        points = points[::-1]
        area = -area
    centroid = _centroid(points, area)

    closed_points = np.vstack((points, points[:1]))
    cumulative = np.concatenate(
        ((0.0,), np.cumsum(np.hypot(*np.diff(closed_points, axis=0).T)))
    )
    length = float(cumulative[-1])
    if length == 0:
        return ContourShape(
            closed_points, cumulative, 0.0, np.array((0.0, 0.0)), centroid, area
        )

    vertical = _ray_crossings(closed_points, cumulative, centroid, axis=1)
    horizontal = _ray_crossings(closed_points, cumulative, centroid, axis=0)
    inside = area > 0 and len(vertical[0]) > 0 and bool(
        np.count_nonzero(vertical[0] < 0) % 2
    )

    top = _nearest(*vertical, sign=-1) if inside else None
    anchors = np.array((0.0, length))
    if top is not None:
        sides = (
            _nearest(*horizontal, sign=1),
            _nearest(*vertical, sign=1),
            _nearest(*horizontal, sign=-1),
        )
        if all(side is not None for side in sides):
            relative = [(side - top) % length for side in sides]
            if 0 < relative[0] < relative[1] < relative[2] < length:
                anchors = np.array((0.0, *relative, length))
    elif len(vertical[0]):
        top = float(vertical[1][np.argmin(vertical[0])])
    else:
        lowest_y = points[:, 1].min()
        candidates = np.flatnonzero(points[:, 1] == lowest_y)
        vertex = candidates[np.argmin(np.abs(points[candidates, 0] - centroid[0]))]
        top = float(cumulative[vertex])

    return ContourShape(closed_points, cumulative, top, anchors, centroid, area)


def prepare_contours(contours: Sequence[ArrayLike2D]) -> tuple[ContourShape, ...]:
    """Prepare contours ordered from the largest to the smallest area."""
    shapes = [prepare_contour(contour) for contour in contours]
    return tuple(sorted(shapes, key=lambda shape: -shape.area))


ShapePair = tuple[ContourShape | None, ContourShape | None]


def match_contours(
    previous: Sequence[ContourShape], following: Sequence[ContourShape]
) -> tuple[ShapePair, ...]:
    """Pair contours of two keyframes by the nearest centroids.

    Pairs follow the order of ``following``; contours that disappear are
    appended at the end so the shared part of the index space stays stable.
    """
    candidates = sorted(
        (
            float(np.hypot(*(before.centroid - after.centroid))),
            previous_index,
            following_index,
        )
        for previous_index, before in enumerate(previous)
        for following_index, after in enumerate(following)
    )
    partner: dict[int, int] = {}
    used: set[int] = set()
    for _, previous_index, following_index in candidates:
        if following_index in partner or previous_index in used:
            continue
        partner[following_index] = previous_index
        used.add(previous_index)

    pairs: list[ShapePair] = [
        (
            previous[partner[index]] if index in partner else None,
            after,
        )
        for index, after in enumerate(following)
    ]
    pairs.extend(
        (before, None)
        for index, before in enumerate(previous)
        if index not in used
    )
    return tuple(pairs)


def smoothstep(value: float) -> float:
    value = min(max(value, 0.0), 1.0)
    return value * value * (3 - 2 * value)


def morph_contours(
    pairs: Sequence[ShapePair],
    alpha: float,
    count: int = MORPH_POINT_COUNT,
) -> _Points:
    """Interpolate paired contours, ``count`` points per pair.

    ``alpha`` is the linear transition progress; it is eased by
    :func:`smoothstep`. New contours grow from their centroid and vanishing
    contours shrink into theirs.
    """
    positions = _positions(count)
    eased = smoothstep(alpha)
    morphed: list[_Points] = []
    for before, after in pairs:
        if before is None and after is None:
            continue
        if before is None or after is None:
            shape = after if before is None else before
            outline = shape.sample(positions, shape.anchor_fractions)
            weight = eased if before is None else 1 - eased
            morphed.append(shape.centroid + (outline - shape.centroid) * weight)
            continue

        before_points = before.sample(positions, before.anchor_fractions)
        after_points = after.sample(positions, after.anchor_fractions)
        morphed.append(before_points + (after_points - before_points) * eased)

    if not morphed:
        return np.empty((0, 2))
    return np.vstack(morphed)


def transition_for_elapsed(
    frame_offsets: Sequence[float],
    elapsed_ms: float,
    max_transition_ms: float = MAX_TRANSITION_MS,
) -> tuple[int, int, float]:
    """Return ``(previous_index, next_index, alpha)`` for a looping sequence.

    Each frame is held and then morphs into the following one during the
    last ``min(frame duration, max_transition_ms)`` milliseconds, so every
    keyframe is reached exactly at its timestamp. The last frame morphs back
    to the first one using the final frame interval.
    """
    if max_transition_ms <= 0:
        raise ValueError("Transition duration must be positive.")
    if not frame_offsets:
        raise ValueError("Frame offsets must not be empty.")
    if len(frame_offsets) == 1:
        return 0, 0, 0.0

    last_duration = frame_offsets[-1] - frame_offsets[-2]
    if last_duration <= 0:
        raise ValueError("Frame offsets must increase strictly.")
    cycle = frame_offsets[-1] + last_duration
    elapsed_ms = max(0.0, elapsed_ms) % cycle

    index = bisect.bisect_right(frame_offsets, elapsed_ms) - 1
    index = min(max(index, 0), len(frame_offsets) - 1)
    following = (index + 1) % len(frame_offsets)
    end = frame_offsets[index + 1] if following else cycle
    duration = end - frame_offsets[index]
    if duration <= 0:
        raise ValueError("Frame offsets must increase strictly.")
    transition = min(duration, max_transition_ms)
    alpha = (elapsed_ms - (end - transition)) / transition
    return index, following, min(max(alpha, 0.0), 1.0)


def limit_speed(
    previous: _Points | None, current: _Points, max_distance: float
) -> _Points:
    """Move each point from ``previous`` towards ``current`` by at most
    ``max_distance``. Without a compatible previous state ``current`` is used.
    """
    if previous is None or previous.shape != current.shape:
        return current
    if max_distance < 0:
        raise ValueError("Maximum distance must not be negative.")
    step = current - previous
    distance = np.hypot(step[:, 0], step[:, 1])
    too_far = distance > max_distance
    if not too_far.any():
        return current
    limited = current.copy()
    limited[too_far] = previous[too_far] + step[too_far] * (
        max_distance / distance[too_far]
    )[:, None]
    return limited
