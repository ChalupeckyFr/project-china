import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

_COLUMNS = ("frame", "time_ms", "x", "y", "depth")


class DepthCsvError(ValueError):
    """Raised when a depth-frame CSV does not match the agreed format."""


@dataclass(frozen=True)
class DepthFrame:
    frame: int
    time_ms: float
    depths: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class DepthSequence:
    frames: tuple[DepthFrame, ...]


@dataclass
class _FrameBuilder:
    time_ms: float
    depths: dict[tuple[int, int], float]


def load_depth_csv(path: str | Path) -> DepthSequence:
    """Load and validate a CSV sequence without writing depth data."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        return _read_depth_csv(stream)


def _read_depth_csv(stream: TextIO) -> DepthSequence:
    reader = csv.reader(stream, strict=True)

    try:
        header = next(reader)
    except StopIteration as exc:
        raise DepthCsvError("CSV file is empty.") from exc
    except csv.Error as exc:
        raise DepthCsvError(
            f"Malformed CSV near line {reader.line_num}."
        ) from exc

    if tuple(header) != _COLUMNS:
        raise DepthCsvError("CSV header must be exactly frame,time_ms,x,y,depth.")

    builders: dict[int, _FrameBuilder] = {}
    frame_order: list[int] = []

    try:
        for row in reader:
            line_number = reader.line_num
            if len(row) != len(_COLUMNS):
                raise DepthCsvError(
                    f"Expected {len(_COLUMNS)} fields at line {line_number}."
                )

            frame = _parse_integer(row[0], "frame", line_number)
            time_ms = _parse_finite_number(row[1], "time_ms", line_number)
            x = _parse_integer(row[2], "x", line_number)
            y = _parse_integer(row[3], "y", line_number)
            depth = _parse_finite_number(row[4], "depth", line_number)

            if x < 0 or y < 0:
                raise DepthCsvError(
                    f"Coordinates must be non-negative at line {line_number}."
                )

            builder = builders.get(frame)
            if builder is None:
                builders[frame] = _FrameBuilder(time_ms, {})
                frame_order.append(frame)
                builder = builders[frame]
            elif builder.time_ms != time_ms:
                raise DepthCsvError(
                    f"Frame {frame} has conflicting times at line {line_number}."
                )

            point = (x, y)
            if point in builder.depths:
                raise DepthCsvError(
                    f"Frame {frame} has a duplicate point at line {line_number}."
                )
            builder.depths[point] = depth
    except csv.Error as exc:
        raise DepthCsvError(
            f"Malformed CSV near line {reader.line_num}."
        ) from exc

    if not frame_order:
        raise DepthCsvError("CSV contains no frames.")

    frames: list[DepthFrame] = []
    expected_dimensions: tuple[int, int] | None = None
    previous_time: float | None = None

    for frame_id in frame_order:
        builder = builders[frame_id]
        if previous_time is not None and builder.time_ms <= previous_time:
            raise DepthCsvError("Frame times must increase strictly.")
        previous_time = builder.time_ms

        width = max(x for x, _ in builder.depths) + 1
        height = max(y for _, y in builder.depths) + 1
        if len(builder.depths) != width * height:
            raise DepthCsvError(
                f"Frame {frame_id} does not contain a complete rectangular grid."
            )

        dimensions = (width, height)
        if expected_dimensions is None:
            expected_dimensions = dimensions
        elif dimensions != expected_dimensions:
            raise DepthCsvError("All frames must use the same grid dimensions.")

        depth_rows = tuple(
            tuple(builder.depths[(x, y)] for x in range(width))
            for y in range(height)
        )
        frames.append(DepthFrame(frame_id, builder.time_ms, depth_rows))

    return DepthSequence(tuple(frames))


def _parse_integer(value: str, field: str, line_number: int) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise DepthCsvError(
            f"Invalid integer in '{field}' at line {line_number}."
        ) from exc


def _parse_finite_number(value: str, field: str, line_number: int) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise DepthCsvError(
            f"Invalid number in '{field}' at line {line_number}."
        ) from exc

    if not math.isfinite(number):
        raise DepthCsvError(
            f"Non-finite number in '{field}' at line {line_number}."
        )
    return number
