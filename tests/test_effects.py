import math

import pygame

from project_china.effects import StarEffect, _flyby_position


def _mean_distance(
    positions: tuple[tuple[float, float], ...], target: tuple[int, int]
) -> float:
    return sum(
        math.hypot(x - target[0], y - target[1]) for x, y in positions
    ) / len(positions)


def test_particles_are_deterministic_and_follow_moving_targets() -> None:
    first = StarEffect((320, 240))
    second = StarEffect((320, 240))
    first_target = (80, 80)
    initial_distance = _mean_distance(first.particle_positions, first_target)

    for _ in range(60):
        first.update(16, (first_target,))
        second.update(16, (first_target,))

    assert first.particle_positions == second.particle_positions
    assert first.attraction_strength > 0.9
    assert _mean_distance(first.particle_positions, first_target) < initial_distance

    moving_target = (160, 120)
    distance_before_move = _mean_distance(first.particle_positions, moving_target)
    for _ in range(10):
        first.update(16, (moving_target,))

    assert _mean_distance(first.particle_positions, moving_target) < distance_before_move


def test_particles_release_gradually_when_target_disappears() -> None:
    effect = StarEffect((320, 240))
    target = (160, 120)
    for _ in range(30):
        effect.update(16, (target,))
    engaged_strength = effect.attraction_strength

    effect.update(350, ())

    assert 0 < effect.attraction_strength < engaged_strength
    effect.update(5000, ())
    assert effect.attraction_strength == 0


def test_stars_twinkle_and_flybys_are_periodic() -> None:
    surface = pygame.Surface((320, 240))
    effect = StarEffect((320, 240))
    surface.fill((5, 8, 24))
    effect.draw(surface, 0)
    first_image = pygame.surfarray.array3d(surface).copy()

    surface.fill((5, 8, 24))
    effect.draw(surface, 350)
    second_image = pygame.surfarray.array3d(surface)

    assert not (first_image == second_image).all()
    first_flyby = _flyby_position(350, 320, 240)
    next_flyby = _flyby_position(3350, 320, 240)
    assert first_flyby is not None
    assert next_flyby is not None
    assert first_flyby[0] == next_flyby[0]
    assert _flyby_position(1000, 320, 240) is None
