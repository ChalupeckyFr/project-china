import math

import numpy as np
import pygame
import pytest

from project_china.effects import (
    DEPTH_ALPHA,
    DEPTH_RADIUS,
    JITTER_RANGE,
    MAX_TICK_DISTANCE,
    REPULSION_RADIUS,
    STAR_DAMPING,
    VOLUME_JITTER_RANGE,
    BodyTargets,
    StarEffect,
)


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


def test_spring_lags_behind_a_jump_without_overshoot() -> None:
    effect = StarEffect((320, 240), 1)
    _settle(effect, ((100, 120),))

    trail: list[float] = []
    for _ in range(90):
        effect.update(16, ((200, 120),))
        trail.append(effect.particle_positions[0][0])

    # Critically damped: still behind the target two ticks after the jump,
    # then it closes in monotonically and never passes the target.
    assert trail[0] < 130
    assert trail[1] < 160
    assert trail[2] < 185
    assert max(trail) <= 200 + JITTER_RANGE[1]
    assert abs(trail[-1] - 200) <= 3


def test_spring_follows_a_moving_target_and_stops_without_overshoot() -> None:
    effect = StarEffect((320, 240), 1)
    _settle(effect, ((40, 120),))

    lags: list[float] = []
    for tick in range(120):
        target = 40 + 4 * min(tick + 1, 60)
        effect.update(16, ((target, 120),))
        x = effect.particle_positions[0][0]
        if tick < 60:
            lags.append(target - x)
        assert x <= 280 + JITTER_RANGE[1]

    # A fast limb leaves a short kinetic trail behind it, not a lasting one.
    assert 5 < max(lags) < 25
    assert abs(effect.particle_positions[0][0] - 280) <= 3


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
    image = pygame.surfarray.array3d(surface).astype(int)

    def glow(x: float, y: float) -> tuple[int, int, int, np.ndarray]:
        patch = image[round(x) - 6 : round(x) + 7, round(y) - 6 : round(y) + 7]
        level = patch.max(axis=2)
        return level.sum(), level.max(), int((level > 0).sum()), patch.sum(axis=(0, 1))

    (near_x, near_y), (far_x, far_y) = effect.particle_positions
    near_sum, near_peak, near_area, near_rgb = glow(near_x, near_y)
    far_sum, far_peak, far_area, far_rgb = glow(far_x, far_y)
    # Near: alpha 0.9-1.0 (minus twinkle); far: alpha 0.15-0.30.
    assert near_peak >= 0.9 * 0.85 * 255
    assert far_peak <= 0.30 * 255
    # Near disc radius 3.5-4.5 px covers many pixels, far 1.2-1.8 px a few.
    assert near_area >= 3 * far_area
    assert near_sum > 8 * far_sum
    # Near particles are warmer (red over blue), far ones cold.
    assert near_rgb[0] > near_rgb[2]
    assert far_rgb[2] > far_rgb[0]


def test_depth_shading_ranges_follow_the_brief() -> None:
    far, middle, near = zip(DEPTH_RADIUS, DEPTH_ALPHA, strict=True)
    assert 1.2 <= far[0] <= 1.8 and 0.15 <= far[1] <= 0.30
    assert 2.0 <= middle[0] <= 2.8 and 0.45 <= middle[1] <= 0.65
    assert 3.5 <= near[0] <= 4.5 and 0.9 <= near[1] <= 1.0


def _volume_body(points, ids=None) -> BodyTargets:
    points = np.asarray(points, dtype=np.float64)
    return BodyTargets(
        np.array(((60.0, 60.0),)),
        np.array((900.0,)),
        points,
        np.full(len(points), 900.0),
        None if ids is None else np.asarray(ids, dtype=np.intp),
    )


def test_volume_particles_follow_volume_targets() -> None:
    effect = StarEffect((320, 240), 40, 3)
    targets = ((200.0, 150.0), (240.0, 150.0), (220.0, 190.0))
    _settle(effect, _volume_body(targets), 600)

    positions = effect.particle_positions
    assert effect.particle_count == 43
    outline = [math.dist(position, (60, 60)) for position in positions[:40]]
    assert 1.2 <= min(outline) and max(outline) <= 2.8
    # Each target gets exactly one particle; the lattice already breaks rows,
    # so volume particles keep only a small jitter.
    nearest = [min(math.dist(p, t) for t in targets) for p in positions[40:]]
    assert max(nearest) <= VOLUME_JITTER_RANGE[1] + 0.01
    claimed = {min(range(3), key=lambda i: math.dist(p, targets[i])) for p in positions[40:]}
    assert claimed == {0, 1, 2}


def test_surplus_volume_particles_fade_out_in_place() -> None:
    effect = StarEffect((320, 240), 4, 5)
    targets = ((200.0, 150.0), (240.0, 150.0))
    _settle(effect, _volume_body(targets), 120)
    before = np.array(effect.particle_positions[4:])

    _settle(effect, _volume_body(targets), 60)

    presence = effect.particle_presence[4:]
    after = np.array(effect.particle_positions[4:])
    assert np.count_nonzero(presence > 0.99) == 2
    assert np.count_nonzero(presence < 0.01) == 3
    # Faded particles stay where they are instead of crowding the body.
    faded = presence < 0.01
    assert np.abs(after[faded] - before[faded]).max() < 0.5
    assert (effect.particle_presence[:4] > 0.99).all()

    _settle(effect, (), 400)
    assert (effect.particle_presence > 0.99).all()


def test_volume_particles_keep_their_target_id_while_it_exists() -> None:
    effect = StarEffect((320, 240), 4, 3)
    targets = np.array(((100.0, 120.0), (140.0, 120.0), (180.0, 120.0)))
    _settle(effect, _volume_body(targets, (7, 8, 9)))
    owners = [
        int(np.argmin(np.hypot(*(targets - p).T))) for p in effect.particle_positions[4:]
    ]

    # Same ids in another order and with one id gone: nobody swaps targets.
    shuffled = targets[[2, 0]]
    effect.update(16, _volume_body(shuffled, (9, 7)))
    effect.update(16, _volume_body(shuffled, (9, 7)))
    after = effect.particle_positions[4:]
    for particle, owner in enumerate(owners):
        if owner == 1:
            continue
        assert math.dist(after[particle], targets[owner]) <= VOLUME_JITTER_RANGE[1] + 0.5


def test_released_volume_particle_takes_the_nearest_free_target() -> None:
    effect = StarEffect((320, 240), 4, 2)
    _settle(effect, _volume_body(((100.0, 120.0), (200.0, 120.0)), (1, 2)))
    near_left = int(np.argmin([p[0] for p in effect.particle_positions[4:]]))

    # Target 1 vanishes, a new one appears next to it and one far away.
    body = _volume_body(((110.0, 120.0), (200.0, 120.0), (300.0, 120.0)), (3, 2, 4))
    _settle(effect, body, 120)

    assert math.dist(effect.particle_positions[4 + near_left], (110, 120)) <= 1.0


def test_particles_never_move_more_than_the_tick_limit() -> None:
    effect = StarEffect((320, 240), 1, 1)
    _settle(effect, _volume_body(((100.0, 120.0),)))

    previous = np.array(effect.particle_positions)
    steps = []
    for _ in range(40):
        effect.update(16, BodyTargets(np.array(((300.0, 60.0),)), None, np.array(((10.0, 230.0),))))
        current = np.array(effect.particle_positions)
        steps.append(np.hypot(*(current - previous).T).max())
        previous = current

    assert max(steps) <= MAX_TICK_DISTANCE * 16 / (1000 / 60) + 1e-9
    assert max(steps) > 0.9 * MAX_TICK_DISTANCE * 16 / (1000 / 60)

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


def test_swinging_limb_pushes_stars_away_from_the_bone_and_along_the_swing() -> None:
    effect = StarEffect((320, 240), 10)
    homes = effect.star_positions
    index = int(np.argmin(np.hypot(homes[:, 0] - 160, homes[:, 1] - 120)))
    star_x, star_y = homes[index]
    # A long vertical bone just left of the star, sweeping upwards along itself.
    bone = np.column_stack((np.zeros(31), np.linspace(-60, 60, 31)))

    def limb(y: float) -> BodyTargets:
        return BodyTargets(bone + (star_x - 12, y))

    effect.update(16, limb(star_y + 20))
    effect.update(16, limb(star_y + 15))
    effect.update(16, limb(star_y + 10))

    velocity = effect._star_velocity[index]
    # Perpendicular repulsion to the right, tangential drag upwards.
    assert velocity[0] > 0
    assert velocity[1] < 0
    assert 25 <= REPULSION_RADIUS <= 40


def test_pushed_stars_lose_velocity_by_the_damping_factor_each_tick() -> None:
    assert 0.90 <= STAR_DAMPING <= 0.94
    effect = StarEffect((320, 240), 10)
    effect._star_velocity[0] = (100.0, 0.0)
    effect._stars_resting = False

    effect._step_stars(1 / 60)

    assert effect._star_velocity[0, 0] == pytest.approx(100 * STAR_DAMPING)


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
            "_target",
            "_presence",
            "_slot_id",
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
