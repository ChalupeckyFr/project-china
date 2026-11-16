import itertools

import cv2
import numpy as np
import pytest

from project_china.frames import DepthFrame
from project_china.morph import MORPH_POINT_COUNT, prepare_contours
from project_china.selection import select_depth_regions
from project_china.synthetic_human import human_frame
from project_china.volume import (
    FILL_JITTER,
    body_anchor,
    fill_field,
    fill_targets,
    filled_depth,
    fit_lattice,
    hex_lattice,
    morph_outline_depths,
    outline_depths,
)

_FRAMES = (0, 30, 60, 90)


def _keyframes(indices, count: int = 1500):
    frames = [human_frame(index) for index in indices]
    selections = [select_depth_regions(frame) for frame in frames]
    lattice = fit_lattice(
        (len(frames[0].depths[0]), len(frames[0].depths)),
        [selection.mask for selection in selections],
        count,
    )
    fields = [
        fill_field(lattice, selection, filled_depth(frame, selection))
        for frame, selection in zip(frames, selections, strict=True)
    ]
    return frames, selections, lattice, fields


def _pixels(points):
    return np.rint(points[:, 1]).astype(int), np.rint(points[:, 0]).astype(int)


def test_fill_targets_lie_inside_the_silhouette() -> None:
    frames, selections, lattice, fields = _keyframes(_FRAMES)

    for frame, selection, field in zip(frames, selections, fields, strict=True):
        fill = fill_targets(lattice, field, field, 0)
        mask = selection.mask != 0
        assert mask[_pixels(fill.points)].all()
        source = np.asarray(frame.depths, dtype=np.float64)[mask]
        assert source.min() <= fill.depth.min() and fill.depth.max() <= source.max()


def test_fitted_lattice_never_needs_more_targets_than_particles() -> None:
    _, _, lattice, fields = _keyframes(range(0, 120, 3), count=1500)

    keyframes = [len(fill_targets(lattice, field, field, 0).ids) for field in fields]
    blended = [
        len(fill_targets(lattice, before, after, 0.5).ids)
        for before, after in itertools.pairwise(fields)
    ]
    assert max(keyframes + blended) <= 1500
    # The lattice is fitted tightly, so almost every particle is used.
    assert min(keyframes) > 0.9 * 1500
    assert min(blended) > 0.8 * 1500


def test_fill_is_homogeneous_without_clumps_or_holes() -> None:
    _, selections, lattice, fields = _keyframes(_FRAMES)

    for selection, field in zip(selections, fields, strict=True):
        points = fill_targets(lattice, field, field, 0).points
        offset = points[:, None, :] - points[None, :, :]
        distance = np.hypot(offset[..., 0], offset[..., 1])
        np.fill_diagonal(distance, np.inf)
        # Jitter moves each point by at most FILL_JITTER: no clumps.
        assert distance.min() >= lattice.spacing - 2 * FILL_JITTER - 1e-9

        empty = np.full(selection.mask.shape, 255, np.uint8)
        empty[_pixels(points)] = 0
        gap = cv2.distanceTransform(empty, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        interior = cv2.erode(selection.mask, np.ones((5, 5), np.uint8)) != 0
        # No empty disc wider than one lattice cell, not even in armpits.
        assert gap[interior].max() < lattice.spacing


def test_fill_targets_keep_their_id_and_ride_with_the_body() -> None:
    _, _, lattice, fields = _keyframes(range(20, 40))

    previous = None
    previous_points = None
    for current, following in itertools.pairwise(fields):
        for alpha in (0, 0.25, 0.5, 0.75):
            fill = fill_targets(lattice, current, following, alpha)
            # The whole lattice shifts sideways with the body core, rigidly.
            shift = fill.points - lattice.points[fill.ids]
            assert np.ptp(shift[:, 0]) < 1e-9
            assert np.abs(shift[:, 1]).max() < 1e-9
            assert abs(shift[0, 0]) < 3
            if previous_points is not None:
                common, now, before = np.intersect1d(
                    fill.ids, previous, return_indices=True
                )
                assert len(common)
                # A target id never jumps between neighbouring render steps.
                moved = np.hypot(*(fill.points[now] - previous_points[before]).T)
                assert moved.max() < 0.5
            if previous is not None:
                changed = np.setxor1d(previous, fill.ids)
                # Only points at the moving silhouette edge switch on or off.
                distance = np.minimum(
                    np.abs(current.signed_distance[changed]),
                    np.abs(following.signed_distance[changed]),
                )
                assert distance.max() < 10
                assert len(changed) < 0.1 * len(fill.ids)
            previous = fill.ids
            previous_points = fill.points


def test_body_anchor_moves_continuously_with_the_weight_shift() -> None:
    centres = [
        body_anchor(select_depth_regions(human_frame(index)).mask).centre_x
        for index in range(0, 240, 4)
    ]
    assert max(abs(b - a) for a, b in itertools.pairwise(centres)) < 0.5
    assert np.ptp(centres) < 3


def test_limb_targets_know_the_bone_axis_and_the_room_to_the_edge() -> None:
    _, _, lattice, fields = _keyframes((0, 60))
    raised = fill_targets(lattice, fields[1], fields[1], 0)
    centre = raised.points[:, 0].mean()

    torso = (np.abs(raised.points[:, 0] - centre) < 10) & (
        (raised.points[:, 1] > 170) & (raised.points[:, 1] < 220)
    )
    assert raised.limb[torso].max() < 0.05
    # Forearms raised above the head are vertical: the axis across them is horizontal.
    forearm = raised.points[:, 1] < 110
    assert forearm.sum() > 30
    assert raised.limb[forearm].mean() > 0.9
    assert np.abs(raised.axes[forearm, 0]).mean() > 0.8
    np.testing.assert_allclose(np.hypot(*raised.axes.T), 1)
    # Room is the distance to the outer edge, positive inside the silhouette.
    assert raised.room.min() >= 0
    assert raised.room.max() > 15


def test_fill_density_drops_at_most_thirty_percent_at_the_edge() -> None:
    _, selections, lattice, fields = _keyframes(_FRAMES)

    for selection, field in zip(selections, fields, strict=True):
        fill = fill_targets(lattice, field, field, 0)
        mask = selection.mask != 0
        inside = cv2.distanceTransform(
            mask.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        edge = mask & (inside <= 4)
        core = mask & (inside >= 8)
        rows, columns = _pixels(fill.points)
        density = [
            np.count_nonzero(band[rows, columns]) / np.count_nonzero(band)
            for band in (edge, core)
        ]
        assert density[0] >= 0.7 * density[1]


def test_blended_silhouette_grows_smoothly_between_keyframes() -> None:
    _, _, lattice, fields = _keyframes((0, 30))

    counts = [
        len(fill_targets(lattice, fields[0], fields[1], alpha).ids)
        for alpha in np.linspace(0, 1, 11)
    ]
    start = set(fill_targets(lattice, fields[0], fields[0], 0).ids)
    end = set(fill_targets(lattice, fields[1], fields[1], 0).ids)
    assert set(fill_targets(lattice, fields[0], fields[1], 0).ids) == start
    assert set(fill_targets(lattice, fields[0], fields[1], 1).ids) == end
    assert max(abs(b - a) for a, b in itertools.pairwise(counts)) < 0.2 * counts[0]


def test_filled_depth_extends_the_nearest_silhouette_depth() -> None:
    depths = np.zeros((7, 9), dtype=np.int64)
    depths[2:5, 3:6] = np.arange(800, 809).reshape(3, 3)
    frame = DepthFrame(0, 0, tuple(map(tuple, depths.tolist())))
    selection = select_depth_regions(frame)

    filled = filled_depth(frame, selection)

    mask = selection.mask != 0
    np.testing.assert_array_equal(filled[mask], depths[mask])
    rows, columns = np.nonzero(mask)
    for row, column in zip(*np.nonzero(~mask), strict=True):
        nearest = np.hypot(rows - row, columns - column)
        candidates = depths[rows[nearest == nearest.min()], columns[nearest == nearest.min()]]
        assert filled[row, column] in candidates


def test_outline_depths_follow_resampled_contours() -> None:
    frame = human_frame(30)
    selection = select_depth_regions(frame)
    shapes = prepare_contours(selection.contours)

    depths = outline_depths(filled_depth(frame, selection), shapes)

    assert [len(values) for values in depths] == [MORPH_POINT_COUNT] * len(shapes)
    source = np.asarray(frame.depths, dtype=np.float64)[selection.mask != 0]
    assert source.min() <= min(d.min() for d in depths)
    assert max(d.max() for d in depths) <= source.max()


def test_outline_lies_only_on_the_outer_silhouette_edge() -> None:
    for index in _FRAMES:
        selection = select_depth_regions(human_frame(index))
        outline = np.vstack([shape.resample() for shape in prepare_contours(selection.contours)])

        inside = cv2.distanceTransform(selection.mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        # No outline point sits on an inner depth change or a limb joint.
        assert inside[_pixels(outline)].max() <= 1.5


def test_outline_depth_morph_keeps_lonely_contours() -> None:
    before, after = np.full(4, 800.0), np.full(4, 900.0)

    morphed = morph_outline_depths(((before, after), (None, after), (before, None)), 0.5)

    np.testing.assert_allclose(morphed, [850.0] * 4 + [900.0] * 4 + [800.0] * 4)
    assert morph_outline_depths((), 0.5).shape == (0,)


def test_fill_is_deterministic() -> None:
    first = _keyframes((30,))[2].points
    second = _keyframes((30,))[2].points
    np.testing.assert_array_equal(first, second)


def test_flat_tiny_silhouette_still_has_finite_fill() -> None:
    frame = DepthFrame(0, 0, ((900, 900), (900, 900)))
    selection = select_depth_regions(frame)
    lattice = fit_lattice((2, 2), [selection.mask], 4)
    field = fill_field(lattice, selection, filled_depth(frame, selection))

    fill = fill_targets(lattice, field, field, 0)

    assert 0 < len(fill.ids) <= 4
    assert np.isfinite(fill.points).all()
    assert (fill.depth == 900).all()


def test_empty_inputs_give_empty_fill() -> None:
    frame = DepthFrame(0, 0, ((0, 0), (0, 0)))
    selection = select_depth_regions(frame)

    assert fit_lattice((2, 2), [selection.mask], 10).count == 0
    assert fit_lattice((2, 2), [], 10).count == 0
    lattice = hex_lattice((2, 2), 1.0)
    field = fill_field(lattice, selection, filled_depth(frame, selection))
    assert len(fill_targets(lattice, field, field, 0.3).ids) == 0


def test_invalid_lattice_parameters_are_rejected() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        fit_lattice((2, 2), [], -1)
    with pytest.raises(ValueError, match="must be positive"):
        hex_lattice((2, 2), 0)