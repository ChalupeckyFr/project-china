import argparse
from pathlib import Path

import numpy as np
import pygame
from numpy.typing import NDArray

from project_china.effects import PARTICLE_COUNT, BodyTargets, StarEffect
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
from project_china.volume import (
    FillField,
    FillLattice,
    fill_field,
    fill_targets,
    filled_depth,
    fit_lattice,
    morph_outline_depths,
    outline_depths,
)

_SCREEN_SIZE = (960, 720)
_BACKGROUND = (5, 8, 24)
_GRID_MARGIN = 24
MAX_TARGET_SPEED = 900.0

_Values = NDArray[np.float64]
_Keyframe = tuple[
    DepthSelection, tuple[ContourShape, ...], tuple[_Values, ...], FillField | None
]


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


def _pair_depths(
    pairs: tuple[tuple[ContourShape | None, ContourShape | None], ...],
    current: tuple[ContourShape, ...],
    current_depths: tuple[_Values, ...],
    following: tuple[ContourShape, ...],
    following_depths: tuple[_Values, ...],
) -> tuple[tuple[_Values | None, _Values | None], ...]:
    # ContourShape holds arrays, so pairs are mapped back by identity.
    depth_of = {
        id(shape): depth
        for shapes, depths in ((current, current_depths), (following, following_depths))
        for shape, depth in zip(shapes, depths, strict=True)
    }
    return tuple(
        (
            None if before is None else depth_of[id(before)],
            None if after is None else depth_of[id(after)],
        )
        for before, after in pairs
    )


def _body_targets(
    keyframe: _Keyframe,
    next_keyframe: _Keyframe,
    alpha: float,
    lattice: FillLattice | None,
    transform: tuple[float, float, float],
) -> BodyTargets:
    _, current_shapes, current_depths, current_field = keyframe
    _, next_shapes, next_depths, next_field = next_keyframe
    pairs = match_contours(current_shapes, next_shapes)
    outline = morph_contours(pairs, alpha)
    outline_depth = morph_outline_depths(
        _pair_depths(pairs, current_shapes, current_depths, next_shapes, next_depths),
        alpha,
    )
    if lattice is None or current_field is None or next_field is None:
        return BodyTargets(_to_screen(outline, transform), outline_depth)
    fill = fill_targets(lattice, current_field, next_field, alpha)
    return BodyTargets(
        _to_screen(outline, transform),
        outline_depth,
        _to_screen(fill.points, transform),
        fill.depth,
        fill.ids,
    )


def _keyframe(
    frame: DepthFrame, selection: DepthSelection, lattice: FillLattice | None = None
) -> _Keyframe:
    shapes = prepare_contours(selection.contours)
    depth = filled_depth(frame, selection)
    field = None if lattice is None else fill_field(lattice, selection, depth)
    return selection, shapes, outline_depths(depth, shapes), field

def render_frame(
    surface: pygame.Surface,
    frame: DepthFrame,
    selection: DepthSelection,
    effects: StarEffect,
    elapsed_ms: int,
    delta_ms: int,
    targets: BodyTargets | None = None,
) -> None:
    """Draw one demo frame.

    ``targets`` are screen targets of an already morphed body; without them
    the outline and volume of ``selection`` are sampled directly.
    """
    surface.fill(_BACKGROUND)

    if targets is None:
        lattice = (
            fit_lattice(_frame_grid_size(frame), [selection.mask], effects.volume_count)
            if effects.volume_count
            else None
        )
        keyframe = _keyframe(frame, selection, lattice)
        targets = _body_targets(
            keyframe,
            keyframe,
            0,
            lattice,
            _grid_transform(surface.get_size(), _frame_grid_size(frame)),
        )

    effects.update(delta_ms, targets)
    effects.draw(surface, elapsed_ms)


class _KeyframeCache:
    def __init__(self, sequence: DepthSequence, volume_count: int = 0) -> None:
        self._frames = sequence.frames
        self._selections: dict[int, DepthSelection] = {}
        self._entries: dict[int, _Keyframe] = {}
        # One fill lattice for all keyframes, so fill targets never reshuffle.
        self.lattice = (
            fit_lattice(
                _frame_grid_size(self._frames[0]),
                [self.selection(index).mask for index in range(len(self._frames))],
                volume_count,
            )
            if volume_count and self._frames
            else None
        )

    def selection(self, index: int) -> DepthSelection:
        selection = self._selections.get(index)
        if selection is None:
            selection = select_depth_regions(self._frames[index])
            self._selections[index] = selection
        return selection

    def get(self, index: int) -> _Keyframe:
        entry = self._entries.get(index)
        if entry is None:
            entry = _keyframe(self._frames[index], self.selection(index), self.lattice)
            self._entries[index] = entry
        return entry

def run_demo(
    sequence: DepthSequence,
    particle_count: int = PARTICLE_COUNT,
    volume_count: int = 0,
) -> None:
    if not sequence.frames:
        raise ValueError("Cannot display an empty depth sequence.")
    if particle_count < 1:
        raise ValueError("Particle count must be positive.")
    if volume_count < 0:
        raise ValueError("Volume particle count must not be negative.")

    first_time = sequence.frames[0].time_ms
    frame_offsets = tuple(frame.time_ms - first_time for frame in sequence.frames)
    keyframes = _KeyframeCache(sequence, volume_count)
    if volume_count:
        for index in range(len(sequence.frames)):
            keyframes.get(index)
    previous_outline: NDArray[np.float64] | None = None

    pygame.init()
    try:
        screen = pygame.display.set_mode(_SCREEN_SIZE)
        pygame.display.set_caption("Project China - depth demo")
        clock = pygame.time.Clock()
        effects = StarEffect(_SCREEN_SIZE, particle_count, volume_count)
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
            keyframe = keyframes.get(current_index)
            body = _body_targets(
                keyframe,
                keyframes.get(next_index),
                alpha,
                keyframes.lattice,
                _grid_transform(screen.get_size(), _frame_grid_size(current_frame)),
            )
            # Fill targets sit on a static lattice; only the outline can jump.
            outline = limit_speed(
                previous_outline, body.outline, MAX_TARGET_SPEED * delta_ms / 1000
            )
            previous_outline = outline

            render_frame(
                screen,
                current_frame,
                keyframe[0],
                effects,
                elapsed_ms,
                delta_ms,
                targets=BodyTargets(
                    outline,
                    body.outline_depth,
                    body.volume,
                    body.volume_depth,
                    body.volume_ids,
                ),
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
    parser.add_argument(
        "--volume-particles",
        type=int,
        default=0,
        help="number of stars filling the body volume (default: 0)",
    )
    args = parser.parse_args(argv)
    if args.particles < 1:
        parser.error("--particles must be a positive integer")
    if args.volume_particles < 0:
        parser.error("--volume-particles must not be negative")

    try:
        sequence = load_depth_csv(args.csv_path)
    except (DepthCsvError, OSError) as exc:
        parser.error(str(exc))

    run_demo(sequence, args.particles, args.volume_particles)


if __name__ == "__main__":
    main()
