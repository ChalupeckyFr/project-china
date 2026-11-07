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
    VolumePicks,
    VolumeShape,
    build_volumes,
    morph_volumes,
    sample_volume,
    volume_picks,
)

_SCREEN_SIZE = (960, 720)
_BACKGROUND = (5, 8, 24)
_GRID_MARGIN = 24
MAX_TARGET_SPEED = 900.0

_Keyframe = tuple[DepthSelection, tuple[ContourShape, ...], tuple[VolumeShape, ...]]


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


def _pair_volumes(
    pairs: tuple[tuple[ContourShape | None, ContourShape | None], ...],
    current: tuple[ContourShape, ...],
    current_volumes: tuple[VolumeShape, ...],
    following: tuple[ContourShape, ...],
    following_volumes: tuple[VolumeShape, ...],
) -> tuple[tuple[VolumeShape | None, VolumeShape | None], ...]:
    # ContourShape holds arrays, so pairs are mapped back by identity.
    volume_of = {
        id(shape): volume
        for shapes, volumes in ((current, current_volumes), (following, following_volumes))
        for shape, volume in zip(shapes, volumes, strict=True)
    }
    return tuple(
        (
            None if before is None else volume_of[id(before)],
            None if after is None else volume_of[id(after)],
        )
        for before, after in pairs
    )


def _body_targets(
    keyframe: _Keyframe,
    next_keyframe: _Keyframe,
    alpha: float,
    picks: VolumePicks,
    transform: tuple[float, float, float],
) -> BodyTargets:
    _, current_shapes, current_volumes = keyframe
    _, next_shapes, next_volumes = next_keyframe
    pairs = match_contours(current_shapes, next_shapes)
    outline = morph_contours(pairs, alpha)
    volume = morph_volumes(
        _pair_volumes(
            pairs, current_shapes, current_volumes, next_shapes, next_volumes
        ),
        alpha,
    )
    points, depths = sample_volume(volume, picks)
    return BodyTargets(
        _to_screen(outline, transform),
        volume.outline_depth,
        _to_screen(points, transform) if picks.count else None,
        depths if picks.count else None,
    )


def _keyframe(frame: DepthFrame, selection: DepthSelection) -> _Keyframe:
    shapes = prepare_contours(selection.contours)
    return selection, shapes, build_volumes(frame, selection, shapes)


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
        keyframe = _keyframe(frame, selection)
        targets = _body_targets(
            keyframe,
            keyframe,
            0,
            volume_picks(effects.volume_count),
            _grid_transform(surface.get_size(), _frame_grid_size(frame)),
        )

    effects.update(delta_ms, targets)
    effects.draw(surface, elapsed_ms)


class _KeyframeCache:
    def __init__(self, sequence: DepthSequence) -> None:
        self._frames = sequence.frames
        self._entries: dict[int, _Keyframe] = {}

    def get(self, index: int) -> _Keyframe:
        entry = self._entries.get(index)
        if entry is None:
            frame = self._frames[index]
            entry = _keyframe(frame, select_depth_regions(frame))
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
    keyframes = _KeyframeCache(sequence)
    picks = volume_picks(volume_count)
    previous_outline: NDArray[np.float64] | None = None
    previous_volume: NDArray[np.float64] | None = None

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
                picks,
                _grid_transform(screen.get_size(), _frame_grid_size(current_frame)),
            )
            max_step = MAX_TARGET_SPEED * delta_ms / 1000
            outline = limit_speed(previous_outline, body.outline, max_step)
            volume = body.volume
            if volume is not None:
                volume = limit_speed(previous_volume, volume, max_step)
            previous_outline, previous_volume = outline, volume

            render_frame(
                screen,
                current_frame,
                keyframe[0],
                effects,
                elapsed_ms,
                delta_ms,
                targets=BodyTargets(
                    outline, body.outline_depth, volume, body.volume_depth
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
