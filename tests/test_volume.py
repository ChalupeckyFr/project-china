import itertools

import cv2
import numpy as np
import pytest

from project_china.frames import DepthFrame
from project_china.morph import MORPH_POINT_COUNT, morph_contours, prepare_contours
from project_china.selection import select_depth_regions
from project_china.synthetic_human import human_frame
from project_china.volume import (
    EDGE_BIAS,
    VOLUME_LAYERS,
    build_volumes,
    morph_volumes,
    reference_weights,
    sample_volume,
    volume_picks,
)


def _human_volume(index: int = 30, count: int = 4000):
    frame = human_frame(index)
    selection = select_depth_regions(frame)
    shapes = prepare_contours(selection.contours)
    volumes = build_volumes(frame, selection, shapes)
    morphed = morph_volumes(tuple((volume, volume) for volume in volumes), 0)
    points, depths = sample_volume(morphed, volume_picks(count))
    return frame, selection, shapes, morphed, points, depths


def test_volume_points_lie_inside_the_silhouette() -> None:
    frame, selection, _, morphed, points, depths = _human_volume()

    mask = selection.mask != 0
    rows = np.rint(points[:, 1]).astype(int)
    columns = np.rint(points[:, 0]).astype(int)
    assert mask[rows, columns].all()
    assert morphed.layers.shape == (len(morphed.outline), VOLUME_LAYERS, 2)
    source = np.asarray(frame.depths, dtype=np.float64)[mask]
    assert source.min() <= depths.min() and depths.max() <= source.max()


def _density(selection, points):
    inscribed = cv2.distanceTransform(selection.mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    distance = inscribed[np.rint(points[:, 1]).astype(int), np.rint(points[:, 0]).astype(int)]

    def density(low: float, high: float) -> float:
        area = np.count_nonzero((inscribed > low) & (inscribed <= high))
        return np.count_nonzero((distance > low) & (distance <= high)) / area

    return density


def test_volume_edge_is_only_mildly_denser_than_the_middle() -> None:
    _, selection, _, _, points, _ = _human_volume(count=20000)
    density = _density(selection, points)

    edge, middle = density(1, 4), density(8, 40)
    assert 1.1 * middle < edge < 3 * middle


def test_volume_fills_the_body_without_dark_holes() -> None:
    for index in (0, 30, 60, 90):
        _, selection, _, _, points, _ = _human_volume(index, count=1500)

        empty = np.full(selection.mask.shape, 255, np.uint8)
        empty[np.rint(points[:, 1]).astype(int), np.rint(points[:, 0]).astype(int)] = 0
        gap = cv2.distanceTransform(empty, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        interior = cv2.erode(selection.mask, np.ones((5, 5), np.uint8)) != 0
        # 1500 particles over the body; the old (1 - t)^2.5 fill left
        # empty discs over 11 grid pixels wide in the chest.
        assert gap[interior].max() < 7.5


def test_volume_picks_follow_the_even_fill_density() -> None:
    inward = np.sort(volume_picks(20000).inward)

    # Density 1 - c t integrates to the CDF (t - c t^2 / 2) / (1 - c / 2).
    expected = (inward - EDGE_BIAS * inward**2 / 2) / (1 - EDGE_BIAS / 2)
    empirical = (np.arange(len(inward)) + 0.5) / len(inward)
    assert np.abs(expected - empirical).max() < 0.015
    # Continuous positions: no particle shares a fixed layer with another.
    assert len(np.unique(inward)) == len(inward)


def test_volume_density_has_no_rings() -> None:
    _, selection, _, _, points, _ = _human_volume(count=20000)
    density = _density(selection, points)

    shells = [density(low, low + 2) for low in range(1, 15, 2)]
    # Neighbouring shells differ smoothly, never as a dense ring next to a gap.
    assert all(
        abs(outer - inner) < 0.3 * max(outer, inner)
        for outer, inner in itertools.pairwise(shells)
    )
    assert min(shells) > 0.4 * max(shells)


def test_volume_targets_do_not_jump_between_neighbouring_keyframes() -> None:
    keyframes = []
    for index in range(20, 40):
        frame = human_frame(index)
        selection = select_depth_regions(frame)
        shapes = prepare_contours(selection.contours)
        keyframes.append((shapes, build_volumes(frame, selection, shapes)))
    weights = reference_weights([volumes for _, volumes in keyframes])
    assert weights is not None
    picks = volume_picks(1500)

    previous = None
    steps = []
    for (_, current), (_, following) in itertools.pairwise(keyframes):
        for alpha in (0, 0.25, 0.5, 0.75):
            morphed = morph_volumes(((current[0], following[0]),), alpha)
            points, _ = sample_volume(morphed, picks, weights)
            if previous is not None:
                steps.append(np.hypot(*(points - previous).T).max())
            previous = points
    # One quarter keyframe at 60 Hz; the body moves at most a few pixels, the
    # old per-frame redistribution threw targets across the body (~30 px).
    assert max(steps) < 8


def test_reference_weights_need_one_contour_in_every_keyframe() -> None:
    frame = human_frame(30)
    selection = select_depth_regions(frame)
    volumes = build_volumes(frame, selection, prepare_contours(selection.contours))

    assert reference_weights([volumes, volumes]) is not None
    assert reference_weights([volumes, volumes * 2]) is None

def test_outline_lies_only_on_the_outer_silhouette_edge() -> None:
    for index in (0, 30, 60, 90):
        _, selection, _, morphed, _, _ = _human_volume(index, count=0)

        inside = cv2.distanceTransform(selection.mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        rows = np.rint(morphed.outline[:, 1]).astype(int)
        columns = np.rint(morphed.outline[:, 0]).astype(int)
        # No outline point sits on an inner depth change or a limb joint.
        assert inside[rows, columns].max() <= 1.5


def test_volume_outline_matches_the_morphed_contour() -> None:
    _, _, shapes, morphed, _, _ = _human_volume()

    expected = morph_contours(tuple((shape, shape) for shape in shapes), 0)
    np.testing.assert_allclose(morphed.outline, expected)
    assert len(morphed.outline_depth) == len(shapes) * MORPH_POINT_COUNT


def test_volume_morph_grows_new_contours_from_their_centroid() -> None:
    frame = human_frame(30)
    selection = select_depth_regions(frame)
    shapes = prepare_contours(selection.contours)
    volume = build_volumes(frame, selection, shapes)[0]

    grown = morph_volumes(((None, volume),), 0.5)

    np.testing.assert_allclose(
        grown.outline,
        morph_contours(((None, shapes[0]),), 0.5),
    )


def test_volume_sampling_is_deterministic() -> None:
    first = _human_volume()[4]
    second = _human_volume()[4]
    np.testing.assert_array_equal(first, second)


def test_flat_tiny_silhouette_still_has_finite_volume() -> None:
    frame = DepthFrame(0, 0, ((900, 900), (900, 900)))
    selection = select_depth_regions(frame)
    shapes = prepare_contours(selection.contours)
    volumes = build_volumes(frame, selection, shapes)
    morphed = morph_volumes(tuple((volume, volume) for volume in volumes), 0)

    points, depths = sample_volume(morphed, volume_picks(50))

    assert points.shape == (50, 2)
    assert np.isfinite(points).all()
    assert (depths == 900).all()


def test_empty_inputs_give_empty_volume() -> None:
    assert build_volumes(DepthFrame(0, 0, ((0, 0), (0, 0))), select_depth_regions(
        DepthFrame(0, 0, ((0, 0), (0, 0)))
    ), ()) == ()
    empty = morph_volumes((), 0.3)
    points, depths = sample_volume(empty, volume_picks(10))
    assert points.shape == (0, 2) and depths.shape == (0,)


def test_volume_pick_count_must_not_be_negative() -> None:
    assert volume_picks(0).count == 0
    with pytest.raises(ValueError, match="must not be negative"):
        volume_picks(-1)
