import itertools
import math

import numpy as np
import pytest

from project_china import morph
from project_china.selection import select_depth_regions
from project_china.synthetic_human import FRAME_COUNT, FRAME_INTERVAL_MS, human_frame

SQUARE = ((0, 0), (8, 0), (8, 8), (0, 8))
BODY = ((0, 0), (10, 0), (10, 20), (0, 20))
BODY_WITH_ARM = (
    (0, 0),
    (10, 0),
    (10, 4),
    (24, 4),
    (24, 6),
    (10, 6),
    (10, 20),
    (0, 20),
)


def _signed_area(points: np.ndarray) -> float:
    following = np.roll(points, -1, axis=0)
    return float(
        np.sum(points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1]) / 2
    )


def test_resample_returns_fixed_evenly_spaced_clockwise_points() -> None:
    points = morph.prepare_contour(BODY).resample(64)

    assert points.shape == (64, 2)
    steps = np.hypot(*np.diff(np.vstack((points, points[:1])), axis=0).T)
    spacing = 60 / 64
    # Chords that cut one of the four corners are shorter than the arc step.
    assert np.count_nonzero(np.isclose(steps, spacing)) >= 60
    assert steps.max() == pytest.approx(spacing)
    assert _signed_area(points) > 0
    assert tuple(points[0]) == pytest.approx((5.0, 0.0))


def test_resample_unifies_winding_order() -> None:
    clockwise = morph.prepare_contour(SQUARE).resample(32)
    counter_clockwise = morph.prepare_contour(SQUARE[::-1]).resample(32)

    np.testing.assert_allclose(clockwise, counter_clockwise, atol=1e-9)


def test_quadrant_anchors_land_on_fixed_indices() -> None:
    shape = morph.prepare_contour(SQUARE)
    points = shape.resample(64)

    assert shape.has_quadrants
    assert tuple(points[0]) == pytest.approx((4.0, 0.0))
    assert tuple(points[16]) == pytest.approx((8.0, 4.0))
    assert tuple(points[32]) == pytest.approx((4.0, 8.0))
    assert tuple(points[48]) == pytest.approx((0.0, 4.0))


def test_growing_limb_keeps_indices_of_the_other_quadrants() -> None:
    body = morph.prepare_contour(BODY)
    with_arm = morph.prepare_contour(BODY_WITH_ARM)
    pairs = morph.match_contours((body,), (with_arm,))
    count = 256

    start = morph.morph_contours(pairs, 0.0, count)
    end = morph.morph_contours(pairs, 1.0, count)
    np.testing.assert_allclose(start, body.resample(count), atol=1e-9)
    np.testing.assert_allclose(end, with_arm.resample(count), atol=1e-9)

    anchored_shift = np.hypot(*(end - start).T)[count // 2 :].max()
    uniform_before = body.resample(count)
    unanchored = morph.ContourShape(
        with_arm.closed_points,
        with_arm.cumulative,
        with_arm.top_offset,
        np.array((0.0, with_arm.length)),
        with_arm.centroid,
        with_arm.area,
    ).resample(count)
    unanchored_shift = np.hypot(*(unanchored - uniform_before).T)[count // 2 :].max()

    assert anchored_shift < 2.0
    assert unanchored_shift > 3 * anchored_shift


def test_limb_extrudes_continuously_during_the_transition() -> None:
    pairs = morph.match_contours(
        morph.prepare_contours((BODY,)), morph.prepare_contours((BODY_WITH_ARM,))
    )
    steps = 60
    frames = [morph.morph_contours(pairs, step / steps, 256) for step in range(steps + 1)]
    largest_step = max(
        np.hypot(*(after - before).T).max()
        for before, after in itertools.pairwise(frames)
    )
    assert largest_step < 1.0
    tip_x = [frame[:, 0].max() for frame in frames]
    assert tip_x == sorted(tip_x)
    assert tip_x[0] == pytest.approx(10.0)
    assert tip_x[-1] == pytest.approx(24.0)


def test_new_contour_grows_from_its_centroid_and_old_one_collapses() -> None:
    left = morph.prepare_contour(SQUARE)
    right = morph.prepare_contour(tuple((x + 40, y) for x, y in SQUARE))
    pairs = morph.match_contours((left,), (left, right))
    assert pairs == ((left, left), (None, right))

    start = morph.morph_contours(pairs, 0.0, 32)
    end = morph.morph_contours(pairs, 1.0, 32)
    assert start.shape == end.shape == (64, 2)
    np.testing.assert_allclose(start[32:], np.full((32, 2), (44.0, 4.0)))
    np.testing.assert_allclose(end[32:], right.resample(32))

    vanishing = morph.match_contours((left, right), (left,))
    assert vanishing == ((left, left), (right, None))
    np.testing.assert_allclose(
        morph.morph_contours(vanishing, 1.0, 32)[32:], np.full((32, 2), (44.0, 4.0))
    )


def test_contours_are_paired_by_nearest_centroid() -> None:
    big = morph.prepare_contour(BODY)
    small = morph.prepare_contour(tuple((x + 50, y) for x, y in SQUARE))
    moved_small = morph.prepare_contour(tuple((x + 52, y) for x, y in SQUARE))
    moved_big = morph.prepare_contour(tuple((x + 3, y) for x, y in BODY))

    assert morph.match_contours((small, big), (moved_big, moved_small)) == (
        (big, moved_big),
        (small, moved_small),
    )
    assert [shape.area for shape in morph.prepare_contours((SQUARE, BODY))] == [
        200.0,
        64.0,
    ]


def test_degenerate_contours_are_resampled() -> None:
    dot = morph.prepare_contour(((3, 4),))
    line = morph.prepare_contour(((0, 0), (4, 0)))

    np.testing.assert_allclose(dot.resample(8), np.full((8, 2), (3.0, 4.0)))
    assert line.resample(8).shape == (8, 2)
    assert not line.has_quadrants
    with pytest.raises(ValueError, match="at least one point"):
        morph.prepare_contour(np.empty((0, 2)))
    with pytest.raises(ValueError, match="Point count must be positive"):
        dot.resample(0)


def test_smoothstep_eases_and_clamps() -> None:
    assert morph.smoothstep(-1) == 0
    assert morph.smoothstep(0.5) == 0.5
    assert morph.smoothstep(0.25) == pytest.approx(0.15625)
    assert morph.smoothstep(2) == 1


def test_long_frames_hold_then_morph_within_capped_transition() -> None:
    offsets = (0.0, 3000.0, 6000.0)

    assert morph.transition_for_elapsed(offsets, 0) == (0, 1, 0.0)
    assert morph.transition_for_elapsed(offsets, 2400) == (0, 1, 0.0)
    assert morph.transition_for_elapsed(offsets, 2700) == (0, 1, 0.5)
    assert morph.transition_for_elapsed(offsets, 2999) == pytest.approx(
        (0, 1, 599 / 600)
    )
    assert morph.transition_for_elapsed(offsets, 3000) == (1, 2, 0.0)
    assert morph.transition_for_elapsed(offsets, 8700) == (2, 0, 0.5)
    assert morph.transition_for_elapsed(offsets, 9000) == (0, 1, 0.0)


def test_short_frames_morph_over_their_whole_duration() -> None:
    offsets = (0.0, 50.0, 100.0)

    assert morph.transition_for_elapsed(offsets, 25) == (0, 1, 0.5)
    assert morph.transition_for_elapsed(offsets, 140) == pytest.approx((2, 0, 0.8))
    with pytest.raises(ValueError, match="Transition duration must be positive"):
        morph.transition_for_elapsed(offsets, 0, 0)
    with pytest.raises(ValueError, match="must not be empty"):
        morph.transition_for_elapsed((), 0)


def test_limit_speed_caps_each_point_step() -> None:
    previous = np.array(((0.0, 0.0), (10.0, 0.0)))
    current = np.array(((30.0, 40.0), (11.0, 0.0)))

    limited = morph.limit_speed(previous, current, 5.0)

    np.testing.assert_allclose(limited, ((3.0, 4.0), (11.0, 0.0)))
    assert morph.limit_speed(None, current, 5.0) is current
    assert morph.limit_speed(previous[:1], current, 5.0) is current
    with pytest.raises(ValueError, match="must not be negative"):
        morph.limit_speed(previous, current, -1.0)


def test_human_sequence_morphs_without_jumps() -> None:
    shapes = [
        morph.prepare_contours(select_depth_regions(human_frame(index)).contours)
        for index in range(FRAME_COUNT)
    ]
    offsets = tuple(float(index * FRAME_INTERVAL_MS) for index in range(FRAME_COUNT))
    scale = 1.75
    render_step_ms = 1000 / 60
    previous = None
    largest_step = 0.0

    for tick in range(math.ceil(FRAME_COUNT * FRAME_INTERVAL_MS / render_step_ms) + 1):
        current, following, alpha = morph.transition_for_elapsed(
            offsets, tick * render_step_ms
        )
        targets = morph.morph_contours(
            morph.match_contours(shapes[current], shapes[following]), alpha
        ) * scale
        assert targets.shape == (morph.MORPH_POINT_COUNT, 2)
        if previous is not None:
            largest_step = max(largest_step, np.hypot(*(targets - previous).T).max())
        previous = targets

    # Without morphing a keyframe switch moves outline points by ~21 px.
    assert largest_step < 12.0


def test_keyframe_is_continuous_between_consecutive_transitions() -> None:
    shapes = [
        morph.prepare_contours(select_depth_regions(human_frame(index)).contours)
        for index in (34, 35, 36)
    ]

    arriving = morph.morph_contours(morph.match_contours(shapes[0], shapes[1]), 1.0)
    leaving = morph.morph_contours(morph.match_contours(shapes[1], shapes[2]), 0.0)

    np.testing.assert_allclose(arriving, leaving, atol=1e-9)
