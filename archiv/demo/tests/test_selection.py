import numpy as np

from project_china.frames import DepthFrame
from project_china.selection import select_depth_regions


def test_selects_both_inclusive_depth_boundaries() -> None:
    frame = DepthFrame(0, 0, ((749, 750, 1000, 1001),))

    selection = select_depth_regions(frame)

    assert selection.mask.dtype == np.uint8
    assert selection.mask.tolist() == [[0, 255, 255, 0]]
    assert len(selection.contours) == 1


def test_returns_contours_for_all_separate_regions() -> None:
    frame = DepthFrame(
        0,
        0,
        (
            (750, 1200, 1000),
            (1200, 1200, 1200),
            (1000, 1200, 750),
        ),
    )

    selection = select_depth_regions(frame)
    contour_points = {
        tuple(int(value) for value in point[0])
        for contour in selection.contours
        for point in contour
    }

    assert len(selection.contours) == 4
    assert contour_points == {(0, 0), (2, 0), (0, 2), (2, 2)}


def test_returns_a_separate_region_inside_a_hole() -> None:
    frame = DepthFrame(
        0,
        0,
        (
            (750, 750, 750, 750, 750),
            (750, 1200, 1200, 1200, 750),
            (750, 1200, 1000, 1200, 750),
            (750, 1200, 1200, 1200, 750),
            (750, 750, 750, 750, 750),
        ),
    )

    selection = select_depth_regions(frame)
    contour_points = [
        {tuple(int(value) for value in point[0]) for point in contour}
        for contour in selection.contours
    ]

    assert len(selection.contours) == 2
    assert {(2, 2)} in contour_points


def test_frame_without_target_has_empty_mask_and_contours() -> None:
    frame = DepthFrame(0, 0, ((749, 1001),))

    selection = select_depth_regions(frame)

    assert not np.any(selection.mask)
    assert selection.contours == ()
