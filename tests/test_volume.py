import itertools

import cv2
import numpy as np
import pytest

from project_china.frames import DepthFrame
from project_china.morph import MORPH_POINT_COUNT, morph_contours, prepare_contours
from project_china.selection import select_depth_regions
from project_china.synthetic_human import human_frame
from project_china.volume import (
    FRESNEL_POWER,
    VOLUME_LAYERS,
    build_volumes,
    morph_volumes,
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


def test_volume_is_densest_at_the_edges() -> None:
    _, selection, _, _, points, _ = _human_volume()

    inscribed = cv2.distanceTransform(selection.mask, cv2.DIST_L2, 5)
    distance = inscribed[np.rint(points[:, 1]).astype(int), np.rint(points[:, 0]).astype(int)]

    def density(low: float, high: float) -> float:
        area = np.count_nonzero((inscribed > low) & (inscribed <= high))
        return np.count_nonzero((distance > low) & (distance <= high)) / area

    assert density(0, 4) > 1.3 * density(8, 40)


def test_volume_picks_follow_the_stochastic_fresnel_density() -> None:
    inward = np.sort(volume_picks(20000).inward)

    # Density (1 - t)^2.5 integrates to the CDF 1 - (1 - t)^3.5.
    expected = 1 - (1 - inward) ** (FRESNEL_POWER + 1)
    empirical = (np.arange(len(inward)) + 0.5) / len(inward)
    assert np.abs(expected - empirical).max() < 0.015
    # Continuous positions: no particle shares a fixed layer with another.
    assert len(np.unique(inward)) == len(inward)


def test_volume_density_falls_steadily_without_rings() -> None:
    _, selection, _, _, points, _ = _human_volume(count=20000)

    inscribed = cv2.distanceTransform(selection.mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    distance = inscribed[np.rint(points[:, 1]).astype(int), np.rint(points[:, 0]).astype(int)]

    def density(low: float, high: float) -> float:
        area = np.count_nonzero((inscribed > low) & (inscribed <= high))
        return np.count_nonzero((distance > low) & (distance <= high)) / area

    shells = [density(low, low + 2) for low in (1, 3, 5, 7)]
    assert all(outer > inner for outer, inner in itertools.pairwise(shells))


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
