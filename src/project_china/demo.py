import argparse
from pathlib import Path

import numpy as np
import pygame
from numpy.typing import NDArray

from project_china.effects import PARTICLE_COUNT, StarEffect
from project_china.frames import (
    DepthCsvError,
    DepthFrame,
    DepthSequence,
    load_depth_csv,
)
from project_china.morph import (
    ContourShape,
    limit_speed,
    match_contours,
    morph_contours,
    prepare_contours,
    transition_for_elapsed,
)
from project_china.selection import DepthSelection, select_depth_regions

_SCREEN_SIZE = (960, 720)
_BACKGROUND = (5, 8, 24)
_GRID_MARGIN = 24
MAX_TARGET_SPEED = 900.0


def _grid_transform(
    surface_size: tuple[int, int], grid_size: tuple[int, int]
) -> tuple[float, float, float]:
    surface_width, surface_height = surface_size
    grid_width, grid_height = grid_size
    scale = min(
        (surface_width - 2 * _GRID_MARGIN) / grid_width,
        (surface_height - 2 * _GRID_MARGIN) / grid_height,
    )
    left = (surface_width - grid_width * scale) / 2
    top = (surface_height - grid_height * scale) / 2
    return scale, left, top


def _frame_grid_size(frame: DepthFrame) -> tuple[int, int]:
    return len(frame.depths[0]), len(frame.depths)


def _to_screen(
    grid_points: NDArray[np.float64],
    transform: tuple[float, float, float],
) -> NDArray[np.float64]:
    scale, left, top = transform
    return np.column_stack(
        (
            left + (grid_points[:, 0] + 0.5) * scale,
            top + (grid_points[:, 1] + 0.5) * scale,
        )
    ) if len(grid_points) else np.empty((0, 2))


def render_frame(
    surface: pygame.Surface,
    frame: DepthFrame,
    selection: DepthSelection,
    effects: StarEffect,
    elapsed_ms: int,
    delta_ms: int,
    targets: NDArray[np.float64] | None = None,
) -> None:
    """Draw one demo frame.

    ``targets`` are screen points of an already morphed outline; without
    them the outline of ``selection`` is resampled directly.
    """
    surface.fill(_BACKGROUND)

    if targets is None:
        shapes = prepare_contours(selection.contours)
        grid_points = morph_contours(tuple((shape, shape) for shape in shapes), 0)
        transform = _grid_transform(surface.get_size(), _frame_grid_size(frame))
        targets = _to_screen(grid_points, transform)

    effects.update(delta_ms, tuple(map(tuple, targets.tolist())))
    effects.draw(surface, elapsed_ms)


class _KeyframeCache:
    def __init__(self, sequence: DepthSequence) -> None:
        self._frames = sequence.frames
        self._entries: dict[int, tuple[DepthSelection, tuple[ContourShape, ...]]] = {}

    def get(self, index: int) -> tuple[DepthSelection, tuple[ContourShape, ...]]:
        entry = self._entries.get(index)
        if entry is None:
            selection = select_depth_regions(self._frames[index])
            entry = (selection, prepare_contours(selection.contours))
            self._entries[index] = entry
        return entry


def run_demo(
    sequence: DepthSequence, particle_count: int = PARTICLE_COUNT
) -> None:
    if not sequence.frames:
        raise ValueError("Cannot display an empty depth sequence.")
    if particle_count < 1:
        raise ValueError("Particle count must be positive.")

    first_time = sequence.frames[0].time_ms
    frame_offsets = tuple(frame.time_ms - first_time for frame in sequence.frames)
    keyframes = _KeyframeCache(sequence)
    previous_targets: NDArray[np.float64] | None = None

    pygame.init()
    try:
        screen = pygame.display.set_mode(_SCREEN_SIZE)
        pygame.display.set_caption("Project China - depth demo")
        clock = pygame.time.Clock()
        effects = StarEffect(_SCREEN_SIZE, particle_count)
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
            current_index, next_index, alpha = transition_for_elapsed(
                frame_offsets, elapsed_ms
            )
            current_frame = sequence.frames[current_index]
            selection, current_shapes = keyframes.get(current_index)
            _, next_shapes = keyframes.get(next_index)
            grid_points = morph_contours(
                match_contours(current_shapes, next_shapes), alpha
            )
            targets = _to_screen(
                grid_points,
                _grid_transform(screen.get_size(), _frame_grid_size(current_frame)),
            )
            targets = limit_speed(
                previous_targets, targets, MAX_TARGET_SPEED * delta_ms / 1000
            )
            previous_targets = targets

            render_frame(
                screen,
                current_frame,
                selection,
                effects,
                elapsed_ms,
                delta_ms,
                targets=targets,
            )
            pygame.display.flip()
            clock.tick(60)
    finally:
        pygame.quit()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Play a depth-map CSV sequence.")
    parser.add_argument("csv_path", type=Path, help="path to a depth-map CSV file")
    parser.add_argument(
        "--particles",
        type=int,
        default=PARTICLE_COUNT,
        help=f"number of stars attracted to the outline (default: {PARTICLE_COUNT})",
    )
    args = parser.parse_args(argv)
    if args.particles < 1:
        parser.error("--particles must be a positive integer")

    try:
        sequence = load_depth_csv(args.csv_path)
    except (DepthCsvError, OSError) as exc:
        parser.error(str(exc))

    run_demo(sequence, args.particles)


if __name__ == "__main__":
    main()
