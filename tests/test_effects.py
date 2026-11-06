import math

import pygame
import pytest

from project_china.effects import StarEffect


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


def test_particles_are_distributed_around_the_whole_outline() -> None:
    effect = StarEffect((320, 240))
    outline = (
        tuple((20 + index * 4, 20) for index in range(36))
        + tuple((220, 20 + index * 4) for index in range(36))
        + tuple((220 - index * 4, 160) for index in range(36))
        + tuple((20, 160 - index * 4) for index in range(36))
    )

    for _ in range(240):
        effect.update(16, outline)

    lower_left_particles = sum(
        x < 60 and y > 80 for x, y in effect.particle_positions
    )
    assert lower_left_particles >= 3


def test_background_stars_twinkle(monkeypatch: pytest.MonkeyPatch) -> None:
    surface = pygame.Surface((320, 240))
    effect = StarEffect((320, 240))
    monkeypatch.setattr(effect, "_particles", [])
    surface.fill((5, 8, 24))
    effect.draw(surface, 1000)
    first_image = pygame.surfarray.array3d(surface).copy()

    surface.fill((5, 8, 24))
    effect.draw(surface, 1350)
    second_image = pygame.surfarray.array3d(surface)

    assert not (first_image == second_image).all()


@pytest.mark.parametrize("elapsed_ms", (350, 600, 1000, 3350, 3600))
def test_star_positions_do_not_change_without_updates(elapsed_ms: int) -> None:
    background = (5, 8, 24)
    surface = pygame.Surface((320, 240))
    effect = StarEffect((320, 240))

    surface.fill(background)
    effect.draw(surface, 1000)
    reference_mask = (pygame.surfarray.array3d(surface) != background).any(axis=2)

    surface.fill(background)
    effect.draw(surface, elapsed_ms)
    current_mask = (pygame.surfarray.array3d(surface) != background).any(axis=2)

    assert reference_mask.any()
    assert (reference_mask == current_mask).all()
