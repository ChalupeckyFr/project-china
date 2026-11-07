from pathlib import Path

import cv2
import numpy as np
import pytest

from project_china.frames import load_depth_csv
from project_china.selection import select_depth_regions
from project_china.synthetic_human import (
    _PIXEL_SIZE,
    _VIEW_TOP,
    _VIEW_WIDTH,
    ARM_CYCLE_FRAMES,
    BREATH_AMPLITUDE,
    BREATH_PERIOD_FRAMES,
    CHEST_LIFT,
    FOREARM_PHASE_LAG,
    FRAME_COUNT,
    FRAME_INTERVAL_MS,
    HEAD_WIDTH,
    HEIGHT,
    SHOULDER_WIDTH,
    TORSO_HEIGHT,
    WIDTH,
    _arm_joints,
    _capsule,
    _smin,
    human_frame,
    human_pose,
    write_human_csv,
)


def _mask(frame_index: int) -> np.ndarray:
    return select_depth_regions(human_frame(frame_index)).mask != 0


def _row(y: float) -> int:
    return int((_VIEW_TOP - y) / _PIXEL_SIZE)


def _column(x: float) -> int:
    return int((x + _VIEW_WIDTH / 2) / _PIXEL_SIZE)


def _run_width(mask: np.ndarray, y: float, x: float) -> float:
    """Width in metres of the contiguous horizontal run through (x, y)."""
    line, start = mask[_row(y)], _column(x)
    assert line[start]
    left = right = start
    while line[left - 1]:
        left -= 1
    while line[right + 1]:
        right += 1
    return (right - left + 1) * _PIXEL_SIZE


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

    for first, second in ((0, 1), (29, 30), (59, 60), (119, 120), (239, 0)):
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
    with pytest.raises(ValueError, match="Frame index"):
        human_pose(frame_index)


def test_torso_has_chest_narrow_waist_and_pelvis() -> None:
    mask = _mask(60)
    waist = min(_run_width(mask, y / 100, 0.0) for y in range(5, 31))
    chest = _run_width(mask, 0.31, 0.0)
    pelvis = _run_width(mask, -0.06, 0.0)

    assert 0.68 <= waist / SHOULDER_WIDTH <= 0.80
    assert chest > waist + 0.04
    assert pelvis > waist + 0.02


def test_neck_is_about_half_of_the_plain_elliptic_head() -> None:
    mask = _mask(0)
    head = _run_width(mask, 0.76, 0.0)
    neck = _run_width(mask, 0.64, 0.0)

    assert head == pytest.approx(HEAD_WIDTH, abs=2 * _PIXEL_SIZE)
    assert 0.43 <= neck / head <= 0.52
    head_rows = [_run_width(mask, y / 1000, 0.0) for y in range(700, 841, 7)]
    peak = int(np.argmax(head_rows))
    # A convex ellipse narrows monotonically away from its widest row.
    assert all(np.diff(head_rows[: peak + 1]) >= -1e-9)
    assert all(np.diff(head_rows[peak:]) <= 1e-9)


def test_limbs_taper_towards_wrists_and_ankles() -> None:
    lowered = _mask(0)
    for side in (-1, 1):
        assert _run_width(lowered, -0.30, side * 0.097) > 1.6 * _run_width(
            lowered, -0.78, side * 0.113
        )

    horizontal = _mask(30)
    for side in (-1, 1):
        near_shoulder = np.count_nonzero(horizontal[:, _column(side * 0.33)])
        near_wrist = np.count_nonzero(horizontal[:, _column(side * 0.70)])
        assert near_shoulder > 1.3 * near_wrist


def test_depth_falls_off_smoothly_from_segment_centres() -> None:
    frame_index = 60
    depths = np.asarray(human_frame(frame_index).depths)
    mask = _mask(frame_index)

    for y in (0.31, 0.76):
        row = _row(y)
        columns = np.flatnonzero(mask[row])
        centre = depths[row, _column(0.0)]
        assert centre + 10 < depths[row, columns.min()]
        assert centre + 10 < depths[row, columns.max()]

    inner = cv2.erode(mask.astype(np.uint8), np.ones((7, 7), np.uint8)) != 0
    horizontal = np.abs(np.diff(depths, axis=1))[inner[:, 1:] & inner[:, :-1]]
    vertical = np.abs(np.diff(depths, axis=0))[inner[1:] & inner[:-1]]
    assert max(horizontal.max(), vertical.max()) < 8


@pytest.mark.parametrize("frame_index", (0, 30, 60, 90, 119, 150, 239))
def test_depth_has_no_seams_between_body_segments(frame_index: int) -> None:
    depths = np.asarray(human_frame(frame_index).depths, dtype=np.float64)
    inner = cv2.erode(_mask(frame_index).astype(np.uint8), np.ones((7, 7), np.uint8)) != 0
    # Face relief (nose, eye sockets) is deliberate, so the head is skipped.
    inner[: _row(0.66)] = False

    curvature = np.abs(cv2.Laplacian(depths, cv2.CV_64F))[inner]
    # Per-segment depth before the union peaked at 18 along seams and axes.
    assert curvature.max() < 1.5


def test_depths_are_not_rounded_to_whole_units() -> None:
    depths = np.asarray(human_frame(30).depths, dtype=np.float64)
    body = depths[_mask(30)]
    assert np.count_nonzero(body != np.round(body)) > 0.95 * body.size


def test_arm_motion_eases_in_and_out() -> None:
    raised = [human_pose(index).raised for index in range(FRAME_COUNT)]
    steps = np.abs(np.diff(raised + raised[:1]))

    assert raised[0] == 0 and raised[60] == 1
    # Two identical 6 s arm cycles per loop.
    assert raised[:ARM_CYCLE_FRAMES] == raised[ARM_CYCLE_FRAMES:]
    assert ARM_CYCLE_FRAMES * FRAME_INTERVAL_MS == 6000
    assert steps[0] < steps[29] / 10
    assert steps[59] < steps[29] / 10
    assert steps.max() <= steps[29] + 1e-12


def test_shoulder_rises_and_moves_inward_only_above_horizontal() -> None:
    for index in range(FRAME_COUNT):
        pose = human_pose(index)
        if pose.upper_arm_angle <= 90:
            assert pose.shoulder_lift == 0 and pose.shoulder_inset == 0
            assert pose.chest_lift == 0

    top = human_pose(60)
    assert 0.05 <= top.shoulder_lift / TORSO_HEIGHT <= 0.08
    assert top.shoulder_inset > 0
    # Sternum and girdle rise about 3-5 screen pixels (1.75 px per grid px).
    assert 3 <= top.chest_lift / _PIXEL_SIZE * 1.75 <= 5
    assert top.chest_lift == CHEST_LIFT


def test_forearm_trails_the_upper_arm_and_elbow_bends_while_raising() -> None:
    poses = [human_pose(index) for index in range(FRAME_COUNT)]
    upper = np.array([pose.upper_arm_angle for pose in poses])
    forearm = np.array([pose.forearm_angle for pose in poses])
    flex = np.array([pose.elbow_flex for pose in poses])

    assert 0.15 <= FOREARM_PHASE_LAG <= 0.20
    # Phase of the fundamental: the forearm lags by the configured shift.
    cycle = np.exp(-2j * np.pi * np.arange(FRAME_COUNT) / ARM_CYCLE_FRAMES)
    lag = np.angle(np.sum(upper * cycle) / np.sum(forearm * cycle))
    assert lag == pytest.approx(FOREARM_PHASE_LAG, abs=1e-6)
    # Raising: the elbow bends 15-20 degrees; never a rigid straight board.
    assert 15 <= flex[:60].max() <= 20
    assert np.abs(flex).max() <= 20
    np.testing.assert_allclose(flex, upper - forearm)


def test_chest_breathes_and_weight_shifts_in_a_closed_loop() -> None:
    poses = [human_pose(index) for index in range(FRAME_COUNT)]
    chest = [pose.chest_scale for pose in poses]
    sway = [pose.sway for pose in poses]
    breath = [pose.breath_lift for pose in poses]

    # Breathing amplitude is 2-3 % of the torso width, in chest and shoulders.
    assert 0.02 <= BREATH_AMPLITUDE <= 0.03
    assert max(chest) - min(chest) > 2 * BREATH_AMPLITUDE
    assert max(breath) - min(breath) == pytest.approx(
        BREATH_AMPLITUDE * SHOULDER_WIDTH, rel=0.01
    )
    assert max(sway) > 0.005 and min(sway) < -0.005
    assert abs(chest[-1] - chest[0]) < 0.003
    assert abs(sway[-1] - sway[0]) < 0.001


def test_breathing_cycle_lasts_about_four_seconds_and_closes_the_loop() -> None:
    breath = np.array([human_pose(index).breath_lift for index in range(FRAME_COUNT)])
    period_ms = BREATH_PERIOD_FRAMES * FRAME_INTERVAL_MS

    assert 3500 <= period_ms <= 4500
    assert FRAME_COUNT % BREATH_PERIOD_FRAMES == 0
    assert FRAME_COUNT % ARM_CYCLE_FRAMES == 0
    np.testing.assert_allclose(
        breath[BREATH_PERIOD_FRAMES:], breath[:-BREATH_PERIOD_FRAMES], atol=1e-12
    )
    # Exactly one inhale per period: the dominant frequency is the breath.
    spectrum = np.abs(np.fft.rfft(breath - breath.mean()))
    assert int(np.argmax(spectrum)) == FRAME_COUNT // BREATH_PERIOD_FRAMES


@pytest.mark.parametrize("frame_index", (0, 15, 30, 45, 60, 90))
def test_palms_are_among_the_closest_points_like_the_chest(frame_index: int) -> None:
    depths = np.asarray(human_frame(frame_index).depths)
    body = depths[_mask(frame_index)]
    nearest, farthest = body.min(), body.max()
    pose = human_pose(frame_index)

    def nearness(x: float, y: float) -> float:
        return (farthest - depths[_row(y), _column(x)]) / (farthest - nearest)

    for side in (-1, 1):
        palm = _arm_joints(pose, side, 0.6 * pose.sway).palm
        assert nearness(palm[0], palm[1]) >= 0.8
    chest = depths[_row(0.42) : _row(0.28), _column(-0.05) : _column(0.05)]
    assert (farthest - chest.min()) / (farthest - nearest) >= 0.9


def test_smooth_minimum_blends_only_close_shapes() -> None:
    first = np.array([0.0, 0.0, np.inf])
    second = np.array([0.0, 1.0, 0.5])
    blended = _smin(first, second, 0.1)

    assert blended[0] == pytest.approx(-0.025)
    assert blended[1] == 0
    assert blended[2] == 0.5


def test_capsule_rejects_limb_shorter_than_its_taper() -> None:
    x = y = np.zeros((1, 1))
    with pytest.raises(ValueError, match="radius difference"):
        _capsule(x, y, (0, 0, 0), (0, 0.01, 0), 0.05, 0.02)


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
