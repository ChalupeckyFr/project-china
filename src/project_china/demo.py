import argparse
import bisect
import math
from pathlib import Path

import pygame

from project_china.effects import StarEffect
from project_china.frames import (
    DepthCsvError,
    DepthFrame,
    DepthSequence,
    load_depth_csv,
)
from project_china.selection import DepthSelection, select_depth_regions

_SCREEN_SIZE = (960, 720)
_BACKGROUND = (5, 8, 24)
_CONTOUR_COLOR = (80, 155, 255)
_CONTOUR_SAMPLE_SPACING = 6
_OBJECT_COLOR = (220, 235, 255)
_OBJECT_RADIUS = 12


def _sample_contour(
    points: tuple[tuple[int, int], ...]
) -> tuple[tuple[int, int], ...]:
    if len(points) < 2:
        return points

    sampled: list[tuple[int, int]] = []
    following_points = points[1:] + points[:1]
    for (x0, y0), (x1, y1) in zip(points, following_points, strict=True):
        steps = max(
            1,
            math.ceil(
                math.hypot(x1 - x0, y1 - y0) / _CONTOUR_SAMPLE_SPACING
            ),
        )
        for step in range(steps):
            ratio = step / steps
            sampled.append(
                (
                    round(x0 + (x1 - x0) * ratio),
                    round(y0 + (y1 - y0) * ratio),
                )
            )
    return tuple(sampled)


def _frame_index_for_elapsed(
    frame_offsets: tuple[float, ...], elapsed_ms: int
) -> int:
    index = bisect.bisect_right(frame_offsets, elapsed_ms) - 1
    return min(max(index, 0), len(frame_offsets) - 1)


def render_frame(
    surface: pygame.Surface,
    frame: DepthFrame,
    selection: DepthSelection,
    effects: StarEffect,
    elapsed_ms: int,
    delta_ms: int,
) -> None:
    surface.fill(_BACKGROUND)

    grid_height = len(frame.depths)
    grid_width = len(frame.depths[0])
    margin = 24
    scale = min(
        (surface.get_width() - 2 * margin) / grid_width,
        (surface.get_height() - 2 * margin) / grid_height,
    )
    left = (surface.get_width() - grid_width * scale) / 2
    top = (surface.get_height() - grid_height * scale) / 2
    contour_points: list[tuple[tuple[int, int], ...]] = []

    for contour in selection.contours:
        points = tuple(
            (
                round(left + (int(x) + 0.5) * scale),
                round(top + (int(y) + 0.5) * scale),
            )
            for x, y in contour.reshape(-1, 2)
        )
        contour_points.append(points)

    targets = tuple(
        point
        for points in contour_points
        for point in _sample_contour(points)
    )
    effects.update(delta_ms, targets)
    effects.draw(surface, elapsed_ms)

    for points in contour_points:
        if len(points) > 1:
            pygame.draw.lines(surface, _CONTOUR_COLOR, True, points, 2)
        elif points:
            pygame.draw.circle(surface, _CONTOUR_COLOR, points[0], 2)

        if points:
            center = (
                round(sum(point[0] for point in points) / len(points)),
                round(sum(point[1] for point in points) / len(points)),
            )
            pygame.draw.circle(
                surface, _OBJECT_COLOR, center, _OBJECT_RADIUS, width=1
            )


def run_demo(sequence: DepthSequence) -> None:
    if not sequence.frames:
        raise ValueError("Cannot display an empty depth sequence.")

    first_time = sequence.frames[0].time_ms
    frame_offsets = tuple(frame.time_ms - first_time for frame in sequence.frames)
    current_index = 0
    current_frame = sequence.frames[current_index]
    selection = select_depth_regions(current_frame)

    pygame.init()
    try:
        screen = pygame.display.set_mode(_SCREEN_SIZE)
        pygame.display.set_caption("Project China - depth demo")
        clock = pygame.time.Clock()
        effects = StarEffect(_SCREEN_SIZE)
        started_at = pygame.time.get_ticks()
        previous_tick = started_at
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN
                    and event.key in (pygame.K_ESCAPE, pygame.K_q)
                ):
                    running = False
            if not running:
                break

            current_tick = pygame.time.get_ticks()
            elapsed_ms = current_tick - started_at
            delta_ms = current_tick - previous_tick
            previous_tick = current_tick
            frame_index = _frame_index_for_elapsed(frame_offsets, elapsed_ms)
            if frame_index != current_index:
                current_index = frame_index
                current_frame = sequence.frames[current_index]
                selection = select_depth_regions(current_frame)

            render_frame(
                screen, current_frame, selection, effects, elapsed_ms, delta_ms
            )
            pygame.display.flip()
            clock.tick(60)
    finally:
        pygame.quit()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Play a depth-map CSV sequence.")
    parser.add_argument("csv_path", type=Path, help="path to a depth-map CSV file")
    args = parser.parse_args(argv)

    try:
        sequence = load_depth_csv(args.csv_path)
    except (DepthCsvError, OSError) as exc:
        parser.error(str(exc))

    run_demo(sequence)


if __name__ == "__main__":
    main()
