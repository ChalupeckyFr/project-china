import argparse
import bisect
import random
from pathlib import Path

import pygame

from project_china.frames import (
    DepthCsvError,
    DepthFrame,
    DepthSequence,
    load_depth_csv,
)
from project_china.selection import DepthSelection, select_depth_regions

_SCREEN_SIZE = (960, 720)
_BACKGROUND = (5, 8, 24)
_STAR_COLOR = (145, 170, 215)
_BRIGHT_STAR_COLOR = (225, 235, 255)
_CONTOUR_COLOR = (80, 155, 255)
_CONTOUR_STAR_COLOR = (220, 235, 255)
_Star = tuple[int, int, int]


def _create_starfield(size: tuple[int, int]) -> tuple[_Star, ...]:
    width, height = size
    random_source = random.Random(42)
    count = max(100, width * height // 3000)
    return tuple(
        (
            random_source.randrange(width),
            random_source.randrange(height),
            1 if random_source.random() < 0.9 else 2,
        )
        for _ in range(count)
    )


def _frame_index_for_elapsed(
    frame_offsets: tuple[float, ...], elapsed_ms: int
) -> int:
    index = bisect.bisect_right(frame_offsets, elapsed_ms) - 1
    return min(max(index, 0), len(frame_offsets) - 1)


def render_frame(
    surface: pygame.Surface,
    frame: DepthFrame,
    selection: DepthSelection,
    stars: tuple[_Star, ...],
) -> None:
    surface.fill(_BACKGROUND)
    for x, y, radius in stars:
        color = _STAR_COLOR if radius == 1 else _BRIGHT_STAR_COLOR
        pygame.draw.circle(surface, color, (x, y), radius)

    grid_height = len(frame.depths)
    grid_width = len(frame.depths[0])
    margin = 24
    scale = min(
        (surface.get_width() - 2 * margin) / grid_width,
        (surface.get_height() - 2 * margin) / grid_height,
    )
    left = (surface.get_width() - grid_width * scale) / 2
    top = (surface.get_height() - grid_height * scale) / 2

    for contour in selection.contours:
        points = tuple(
            (
                round(left + (int(x) + 0.5) * scale),
                round(top + (int(y) + 0.5) * scale),
            )
            for x, y in contour.reshape(-1, 2)
        )
        if len(points) > 1:
            pygame.draw.lines(surface, _CONTOUR_COLOR, True, points, 2)
        elif points:
            pygame.draw.circle(surface, _CONTOUR_COLOR, points[0], 2)

        star_step = max(1, len(points) // 24)
        for point in points[::star_step]:
            pygame.draw.circle(surface, _CONTOUR_STAR_COLOR, point, 2)


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
        stars = _create_starfield(_SCREEN_SIZE)
        started_at = pygame.time.get_ticks()
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

            elapsed_ms = pygame.time.get_ticks() - started_at
            frame_index = _frame_index_for_elapsed(frame_offsets, elapsed_ms)
            if frame_index != current_index:
                current_index = frame_index
                current_frame = sequence.frames[current_index]
                selection = select_depth_regions(current_frame)

            render_frame(screen, current_frame, selection, stars)
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
