from pathlib import Path

import cv2
import numpy as np
import pytest

from project_china.frames import load_depth_csv
from project_china.selection import select_depth_regions
from project_china.synthetic_human import (
    FRAME_COUNT,
    HEIGHT,
    WIDTH,
    human_frame,
    write_human_csv,
)


@pytest.mark.parametrize("frame_index", range(FRAME_COUNT))
def test_detailed_human_is_connected_and_inside_the_grid(frame_index: int) -> None:
    frame = human_frame(frame_index)
    depths = np.asarray(frame.depths)
    selection = select_depth_regions(frame)

    assert depths.shape == (HEIGHT, WIDTH)
    assert depths.size == 98_304
    assert np.isfinite(depths).all()
    assert np.count_nonzero(selection.mask) > 10_000
    assert len(selection.contours) == 1
    assert not selection.mask[0, :].any()
    assert not selection.mask[-1, :].any()
    assert not selection.mask[:, 0].any()
    assert not selection.mask[:, -1].any()
    foreground = depths[selection.mask != 0]
    assert np.ptp(foreground) > 20
    assert (depths[selection.mask == 0] > 1000).all()


def test_human_raises_hands_above_head_and_returns_smoothly() -> None:
    lowered = select_depth_regions(human_frame(0)).mask != 0
    raised = select_depth_regions(human_frame(60)).mask != 0
    assert np.flatnonzero(raised.any(axis=1))[0] + 40 < np.flatnonzero(
        lowered.any(axis=1)
    )[0]

    for first, second in ((0, 1), (29, 30), (59, 60), (119, 0)):
        first_mask = select_depth_regions(human_frame(first)).mask != 0
        second_mask = select_depth_regions(human_frame(second)).mask != 0
        first_distance = cv2.distanceTransform(
            (~first_mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        second_distance = cv2.distanceTransform(
            (~second_mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        assert max(
            first_distance[second_mask].max(), second_distance[first_mask].max()
        ) <= 10


def test_human_csv_round_trips_through_the_demo_loader(tmp_path: Path) -> None:
    path = tmp_path / "human.csv"
    frames = (human_frame(0), human_frame(60))
    assert write_human_csv(path, frames) == 2

    sequence = load_depth_csv(path)
    assert [frame.time_ms for frame in sequence.frames] == [0, 3000]
    assert [frame.frame for frame in sequence.frames] == [0, 60]
    for original, loaded in zip(frames, sequence.frames, strict=True):
        assert np.max(
            np.abs(np.asarray(original.depths) - np.asarray(loaded.depths))
        ) <= 0.0005


def test_generation_is_deterministic() -> None:
    assert human_frame(30) == human_frame(30)


@pytest.mark.parametrize("frame_index", (-1, FRAME_COUNT))
def test_invalid_frame_indices_are_rejected(frame_index: int) -> None:
    with pytest.raises(ValueError, match="Frame index"):
        human_frame(frame_index)


def test_writer_does_not_overwrite_existing_data(tmp_path: Path) -> None:
    path = tmp_path / "human.csv"
    path.write_text("existing data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_human_csv(path, (human_frame(0),))
    assert path.read_text(encoding="utf-8") == "existing data"


def test_empty_sequence_is_rejected_without_creating_a_file(tmp_path: Path) -> None:
    path = tmp_path / "human.csv"
    with pytest.raises(ValueError, match="empty human sequence"):
        write_human_csv(path, ())
    assert not path.exists()
