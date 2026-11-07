import math

import numpy as np
import pygame
import pytest

from project_china.effects import BodyTargets, StarEffect


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


def test_particle_count_can_be_increased() -> None:
    assert len(StarEffect((320, 240)).particle_positions) == 72
    assert len(StarEffect((320, 240), 360).particle_positions) == 360


@pytest.mark.parametrize("count", (0, -1))
def test_particle_count_must_be_positive(count: int) -> None:
    with pytest.raises(ValueError, match="Particle count must be positive"):
        StarEffect((320, 240), count)


def test_background_stars_twinkle() -> None:
    surface = pygame.Surface((320, 240))
    effect = StarEffect((320, 240))
    surface.fill((5, 8, 24))
    effect._draw_stars(surface, 1000)
    first_image = pygame.surfarray.array3d(surface).copy()

    surface.fill((5, 8, 24))
    effect._draw_stars(surface, 1350)
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

def _settle(effect: StarEffect, targets: object, ticks: int = 300) -> None:
    for _ in range(ticks):
        effect.update(16, targets)


def test_spring_lags_behind_a_jump_and_overshoots() -> None:
    effect = StarEffect((320, 240), 1)
    _settle(effect, ((100, 120),))

    trail: list[float] = []
    for _ in range(90):
        effect.update(16, ((200, 120),))
        trail.append(effect.particle_positions[0][0])

    assert trail[0] < 120
    assert trail[2] < 170
    assert max(trail) > 205
    assert abs(trail[-1] - 200) <= 3


def test_settled_particles_keep_a_small_jitter_around_targets() -> None:
    effect = StarEffect((320, 240), 200)
    target = (160.0, 120.0)
    _settle(effect, (target,), 600)

    distances = [
        math.dist(position, target) for position in effect.particle_positions
    ]
    assert min(distances) >= 1.2
    assert max(distances) <= 2.8
    assert len({round(distance, 2) for distance in distances}) > 50


def test_near_particles_are_larger_and_brighter_than_far_ones() -> None:
    effect = StarEffect((320, 240), 2)
    body = BodyTargets(
        np.array(((100.0, 120.0), (220.0, 120.0))), np.array((800.0, 1000.0))
    )
    _settle(effect, body)
    near, far = effect.particle_nearness
    assert near == pytest.approx(1, abs=0.01)
    assert far == pytest.approx(0, abs=0.01)

    surface = pygame.Surface((320, 240))
    surface.fill((0, 0, 0))
    effect._draw_particles(surface, 0)
    image = pygame.surfarray.array3d(surface)[:, :, 2].astype(int)

    def glow(x: float, y: float) -> tuple[int, int, int]:
        patch = image[round(x) - 4 : round(x) + 5, round(y) - 4 : round(y) + 5]
        return patch.sum(), patch.max(), int((patch > 0).sum())

    (near_x, near_y), (far_x, far_y) = effect.particle_positions
    near_sum, near_peak, near_area = glow(near_x, near_y)
    far_sum, far_peak, far_area = glow(far_x, far_y)
    assert near_peak >= 0.8 * 255 * 0.85
    assert far_peak <= 0.5 * 255 * 1.3
    assert near_area > far_area
    assert near_sum > 2 * far_sum


def test_volume_particles_follow_volume_targets() -> None:
    effect = StarEffect((320, 240), 4, 6)
    body = BodyTargets(
        np.array(((60.0, 60.0),)),
        np.array((900.0,)),
        np.array(((200.0, 150.0),)),
        np.array((900.0,)),
    )
    _settle(effect, body)

    positions = effect.particle_positions
    assert effect.particle_count == 10
    assert all(math.dist(position, (60, 60)) < 3 for position in positions[:4])
    assert all(math.dist(position, (200, 150)) < 3 for position in positions[4:])


@pytest.mark.parametrize("count", (-1, -10))
def test_volume_count_must_not_be_negative(count: int) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        StarEffect((320, 240), 10, count)


def test_fast_limbs_push_nearby_stars_which_then_return_home() -> None:
    effect = StarEffect((320, 240), 10)
    homes = effect.star_positions
    index = int(np.argmin(np.hypot(homes[:, 0] - 160, homes[:, 1] - 120)))
    star_x, star_y = homes[index]
    column = np.column_stack((np.zeros(9), np.linspace(-20, 20, 9)))

    def limb(x: float) -> BodyTargets:
        return BodyTargets(column + (x, star_y))

    effect.update(16, limb(star_x - 10))
    for step in range(1, 5):
        effect.update(16, limb(star_x - 10 + step * 5))

    pushed = effect.star_positions
    assert pushed[index, 0] > star_x + 1
    far = np.hypot(homes[:, 0] - star_x, homes[:, 1] - star_y) > 120
    np.testing.assert_array_equal(pushed[far], homes[far])

    _settle(effect, limb(star_x + 10), 400)
    np.testing.assert_allclose(effect.star_positions, homes, atol=0.05)


def test_slow_limbs_leave_stars_at_rest() -> None:
    effect = StarEffect((320, 240), 10)
    homes = effect.star_positions
    column = np.column_stack((np.zeros(9), np.linspace(-20, 20, 9)))
    for step in range(60):
        effect.update(16, BodyTargets(column + (100 + step, 120)))

    np.testing.assert_array_equal(effect.star_positions, homes)


def test_particle_state_is_preallocated() -> None:
    effect = StarEffect((320, 240), 20, 30)
    surface = pygame.Surface((320, 240))
    arrays = {
        name: getattr(effect, name)
        for name in (
            "_position",
            "_velocity",
            "_target",
            "_star_position",
            "_star_velocity",
            "_light",
            "_weights",
        )
    }
    column = np.column_stack((np.zeros(9), np.linspace(-20, 20, 9)))
    for step in range(30):
        body = BodyTargets(
            column + (100 + 8 * step, 120),
            np.linspace(800, 1000, 9),
            column + (110 + 8 * step, 120),
            np.linspace(850, 950, 9),
        )
        effect.update(16, body)
        effect.draw(surface, step * 16)
    effect.update(400, ())

    for name, array in arrays.items():
        assert getattr(effect, name) is array, name
