from pathlib import Path

import pytest

from project_china.frames import DepthCsvError, load_depth_csv

MOVING_CSV = """\
frame,time_ms,x,y,depth
0,0,0,0,900
0,0,1,0,1750
0,0,0,1,900
0,0,1,1,1750
1,33.3,0,0,1750
1,33.3,1,0,900
1,33.3,0,1,1750
1,33.3,1,1,900
"""


def _write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "sequence.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_moving_frames_without_writing_processed_data(tmp_path: Path) -> None:
    path = _write_csv(tmp_path, MOVING_CSV)

    sequence = load_depth_csv(path)

    assert len(sequence.frames) == 2
    assert sequence.frames[0].time_ms == 0
    assert sequence.frames[0].depths == (
        (900.0, 1750.0),
        (900.0, 1750.0),
    )
    assert sequence.frames[1].time_ms == 33.3
    assert sequence.frames[1].depths == (
        (1750.0, 900.0),
        (1750.0, 900.0),
    )
    assert path.read_text(encoding="utf-8") == MOVING_CSV
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "empty"),
        ("frame,time_ms,x,y\n", "header"),
        ("frame,time_ms,x,y,depth\n0,0,0,0\n", "Expected 5 fields"),
        ("frame,time_ms,x,y,depth\n0,0,not-an-int,0,1\n", "Invalid integer"),
        (
            "frame,time_ms,x,y,depth\n0,0,0,0,not-a-number\n",
            "Invalid number",
        ),
        ("frame,time_ms,x,y,depth\n0,nan,0,0,1\n", "Non-finite number"),
        ("frame,time_ms,x,y,depth\n0,0,0,0,nan\n", "Non-finite number"),
        ("frame,time_ms,x,y,depth\n0,0,-1,0,1\n", "non-negative"),
        (
            "frame,time_ms,x,y,depth\n0,0,0,0,1\n0,0,2,0,3\n",
            "complete rectangular grid",
        ),
    ],
)
def test_rejects_invalid_csv(content: str, message: str, tmp_path: Path) -> None:
    path = _write_csv(tmp_path, content)

    with pytest.raises(DepthCsvError, match=message):
        load_depth_csv(path)


def test_rejects_duplicate_points(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "frame,time_ms,x,y,depth\n0,0,0,0,1\n0,0,0,0,2\n",
    )

    with pytest.raises(DepthCsvError, match="duplicate point"):
        load_depth_csv(path)


def test_rejects_conflicting_times_within_a_frame(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "frame,time_ms,x,y,depth\n0,0,0,0,1\n0,1,1,0,2\n",
    )

    with pytest.raises(DepthCsvError, match="conflicting times"):
        load_depth_csv(path)


def test_rejects_non_increasing_frame_times(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "frame,time_ms,x,y,depth\n0,10,0,0,1\n1,10,0,0,2\n",
    )

    with pytest.raises(DepthCsvError, match="increase strictly"):
        load_depth_csv(path)


def test_rejects_different_grid_dimensions_between_frames(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "frame,time_ms,x,y,depth\n"
        "0,0,0,0,1\n"
        "0,0,1,0,2\n"
        "1,1,0,0,3\n",
    )

    with pytest.raises(DepthCsvError, match="same grid dimensions"):
        load_depth_csv(path)
