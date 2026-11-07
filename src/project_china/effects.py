"""Star renderer: spring-damped body particles over a reactive starfield.

The renderer receives screen-space targets (outline and volume points with
their depth); it does not read CSV files or depth matrices. All particle
state lives in arrays allocated once in :class:`StarEffect`, so the
animation loop never creates or deletes particle objects.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pygame
from numpy.typing import NDArray

_BACKGROUND = (5, 8, 24)
_STAR_COLOR = (145, 170, 215)
_BRIGHT_STAR_COLOR = (225, 235, 255)
PARTICLE_COUNT = 72
_ATTRACTION_RAMP_MS = 180.0
_RELEASE_TIME_MS = 700.0
_REFERENCE_TICK_MS = 1000 / 60
_MAX_SUBSTEPS = 120
_MAX_TICK_DISTANCE = 40.0

# Critically damped spring, rate per reference tick (1/60 s): particles lag
# behind a moving target about as far as the former 0.18 / 0.80 spring
# (~16 px on fast arms) but close in without ever overshooting it.
SPRING_RATE = 0.9
# Velocity kept per tick once the body releases the particles.
_RELEASE_DAMPING = 0.80

# Static scatter around each target, slowly orbiting, in screen pixels.
# Volume particles scatter more so they never line up into ghost contours.
JITTER_RANGE = (1.5, 2.5)
VOLUME_JITTER_RANGE = (2.0, 4.0)
_JITTER_SPIN = (0.3, 0.9)

# Depth look: far particles are small and faint, near ones 40 % larger.
FAR_ALPHA = 0.30
NEAR_ALPHA = 1.00
NEAR_SIZE_GAIN = 0.40
_BASE_SIGMA = 0.6
_GLOW_GAIN = 1.3
_MIN_WEIGHT = 0.05
_TWINKLE = 0.15
_SPLAT_OFFSETS = np.arange(-1, 3, dtype=np.float64)

# Background stars pushed by fast limbs and pulled back home.
REPULSION_RADIUS = 28.0
_FAST_LIMB_SPEED = 150.0
_TURBULENCE = 0.35
_PUSH_RATE = 12.0
_STAR_RETURN_STIFFNESS = 2.5
_STAR_DAMPING_RATE = 3.0
_STAR_REST = 0.01

_Points = NDArray[np.float64]
_Values = NDArray[np.float64]


@dataclass(frozen=True)
class BodyTargets:
    """Screen targets of one rendered frame.

    Depths are raw values from the depth matrix; smaller is closer to the
    camera. Missing depths render every particle as near.
    """

    outline: _Points
    outline_depth: _Values | None = None
    volume: _Points | None = None
    volume_depth: _Values | None = None


def _as_targets(
    targets: BodyTargets | _Points | Sequence[tuple[float, float]],
) -> BodyTargets:
    if isinstance(targets, BodyTargets):
        return targets
    return BodyTargets(np.asarray(targets, dtype=np.float64).reshape(-1, 2))


class StarEffect:
    def __init__(
        self,
        size: tuple[int, int],
        particle_count: int = PARTICLE_COUNT,
        volume_count: int = 0,
    ) -> None:
        if particle_count < 1:
            raise ValueError("Particle count must be positive.")
        if volume_count < 0:
            raise ValueError("Volume particle count must not be negative.")
        self._width, self._height = size
        self._outline_count = particle_count
        self._volume_count = volume_count
        generator = np.random.default_rng(42)

        star_count = max(100, self._width * self._height // 3000)
        self._star_home = np.column_stack(
            (
                generator.integers(0, self._width, star_count),
                generator.integers(0, self._height, star_count),
            )
        ).astype(np.float64)
        self._star_position = self._star_home.copy()
        self._star_velocity = np.zeros_like(self._star_home)
        self._star_big = generator.random(star_count) >= 0.9
        self._star_phase = generator.uniform(0, math.tau, star_count)
        self._stars_resting = True

        total = particle_count + volume_count
        self._position = np.column_stack(
            (
                generator.uniform(0, self._width, total),
                generator.uniform(0, self._height, total),
            )
        )
        self._velocity = np.zeros((total, 2))
        self._drift = generator.uniform(-8, 8, (total, 2))
        self._phase = generator.uniform(0, math.tau, total)
        self._jitter_radius = generator.uniform(*JITTER_RANGE, total)
        low, high = JITTER_RANGE
        volume_low, volume_high = VOLUME_JITTER_RANGE
        self._jitter_radius[particle_count:] = volume_low + (
            self._jitter_radius[particle_count:] - low
        ) * ((volume_high - volume_low) / (high - low))
        self._jitter_angle = generator.uniform(0, math.tau, total)
        self._jitter_spin = generator.uniform(*_JITTER_SPIN, total) * generator.choice(
            (-1.0, 1.0), total
        )
        self._nearness = np.full(total, 0.5)
        self._turbulence = generator

        self._target = np.zeros((total, 2))
        self._target_nearness = np.ones(total)
        self._jittered = np.zeros((total, 2))
        self._offset = np.zeros((total, 2))
        self._carry = np.zeros((total, 2))
        self._speed = np.zeros(total)
        self._previous_outline: _Points | None = None
        self._has_targets = False
        self._attraction_strength = 0.0

        self._light = np.zeros((self._width, self._height), dtype=np.float32)
        self._light_surface = pygame.Surface(size)
        self._weights = np.zeros((total, 4, 4))
        self._columns = np.zeros((total, 4, 4), dtype=np.intp)
        self._rows = np.zeros((total, 4, 4), dtype=np.intp)

    @property
    def attraction_strength(self) -> float:
        return self._attraction_strength

    @property
    def particle_count(self) -> int:
        return len(self._position)

    @property
    def volume_count(self) -> int:
        return self._volume_count

    @property
    def particle_positions(self) -> tuple[tuple[float, float], ...]:
        return tuple(map(tuple, self._position.tolist()))

    @property
    def particle_nearness(self) -> _Values:
        return self._nearness.copy()

    @property
    def star_positions(self) -> _Points:
        return self._star_position.copy()

    def update(
        self,
        delta_ms: int,
        targets: BodyTargets | _Points | Sequence[tuple[float, float]],
    ) -> None:
        if delta_ms < 0:
            raise ValueError("Elapsed time must not be negative.")
        body = _as_targets(targets)
        outline = np.asarray(body.outline, dtype=np.float64).reshape(-1, 2)

        if len(outline):
            self._assign_targets(body, outline)
            self._has_targets = True
            ramp = math.exp(-delta_ms / _ATTRACTION_RAMP_MS)
            self._attraction_strength = 1 - (1 - self._attraction_strength) * ramp
        elif self._has_targets:
            self._attraction_strength *= math.exp(-delta_ms / _RELEASE_TIME_MS)
            if self._attraction_strength < 0.001:
                self._attraction_strength = 0.0
                self._has_targets = False

        self._stir_stars(outline if len(outline) else None, delta_ms / 1000)
        self._step_particles(delta_ms)
        self._step_stars(delta_ms / 1000)

    def _assign_targets(self, body: BodyTargets, outline: _Points) -> None:
        volume = (
            np.empty((0, 2))
            if body.volume is None
            else np.asarray(body.volume, dtype=np.float64).reshape(-1, 2)
        )
        outline_depth = body.outline_depth
        volume_depth = body.volume_depth if len(volume) else None
        depths = [
            np.asarray(values, dtype=np.float64)
            for values in (outline_depth, volume_depth)
            if values is not None and len(values)
        ]
        if depths and outline_depth is not None:
            stacked = np.concatenate(depths)
            nearest, farthest = stacked.min(), stacked.max()
            spread = farthest - nearest
        else:
            spread = 0.0

        def nearness(values: _Values | None, count: int) -> _Values:
            if values is None or spread <= 1e-9:
                return np.ones(count)
            return (farthest - np.asarray(values, dtype=np.float64)) / spread

        outline_near = nearness(outline_depth, len(outline))
        count = self._outline_count
        index = np.arange(count) * len(outline) // count
        self._target[:count] = outline[index]
        self._target_nearness[:count] = outline_near[index]

        if self._volume_count:
            if len(volume):
                source, source_near = volume, nearness(volume_depth, len(volume))
            else:
                source, source_near = outline, outline_near
            index = np.arange(self._volume_count) * len(source) // self._volume_count
            self._target[count:] = source[index]
            self._target_nearness[count:] = source_near[index]

    def _step_particles(self, delta_ms: int) -> None:
        ticks = delta_ms / _REFERENCE_TICK_MS
        if ticks <= 0:
            return
        seconds = delta_ms / 1000
        strength = self._attraction_strength
        self._jitter_angle += self._jitter_spin * seconds

        if self._has_targets and strength > 0:
            np.multiply(
                np.column_stack(
                    (np.cos(self._jitter_angle), np.sin(self._jitter_angle))
                ),
                self._jitter_radius[:, None],
                out=self._jittered,
            )
            self._jittered += self._target
            self._nearness += (self._target_nearness - self._nearness) * min(
                1.0, strength
            )

            substeps = min(_MAX_SUBSTEPS, max(1, math.ceil(ticks)))
            step = min(1.0, ticks / substeps)
            rate = SPRING_RATE * math.sqrt(strength)
            decay = math.exp(-rate * step)
            max_move = _MAX_TICK_DISTANCE * step
            for _ in range(substeps):
                # Exact step of x'' = -rate^2 e - 2 rate x' for e = x - target.
                np.subtract(self._position, self._jittered, out=self._offset)
                np.multiply(self._offset, rate, out=self._carry)
                self._carry += self._velocity
                self._carry *= step
                self._velocity -= self._carry * rate
                self._velocity *= decay
                self._offset += self._carry
                self._offset *= decay
                self._offset += self._jittered
                # Speed cap only slows particles down, it cannot overshoot.
                self._offset -= self._position
                np.hypot(self._offset[:, 0], self._offset[:, 1], out=self._speed)
                too_fast = self._speed > max_move
                if too_fast.any():
                    scale = (max_move / self._speed[too_fast])[:, None]
                    self._offset[too_fast] *= scale
                    self._velocity[too_fast] *= scale
                self._position += self._offset
        else:
            self._velocity *= _RELEASE_DAMPING ** min(ticks, _MAX_SUBSTEPS)

        self._position += self._drift * (seconds * (1 - strength))
        if strength == 0:
            self._position[:, 0] %= self._width
            self._position[:, 1] %= self._height

    def _stir_stars(self, outline: _Points | None, seconds: float) -> None:
        previous = self._previous_outline
        if outline is None:
            self._previous_outline = None
            return
        if previous is None or previous.shape != outline.shape:
            self._previous_outline = outline.copy()
            return
        if seconds <= 0:
            return
        velocity = (outline - previous) / seconds
        previous[...] = outline

        fast = np.hypot(velocity[:, 0], velocity[:, 1]) > _FAST_LIMB_SPEED
        if not fast.any():
            return
        points, limb_velocity = outline[fast], velocity[fast]
        low = points.min(axis=0) - REPULSION_RADIUS
        high = points.max(axis=0) + REPULSION_RADIUS
        candidates = np.flatnonzero(
            np.all((self._star_position >= low) & (self._star_position <= high), axis=1)
        )
        if not len(candidates):
            return

        offset = self._star_position[candidates, None, :] - points[None, :, :]
        distance = np.hypot(offset[..., 0], offset[..., 1])
        weight = np.clip(1 - distance / REPULSION_RADIUS, 0, 1) ** 2
        total = weight.sum(axis=1)
        touched = total > 0
        if not touched.any():
            return
        stars = candidates[touched]
        weight = weight[touched]
        mean_velocity = (weight @ limb_velocity) / total[touched, None]
        across = np.column_stack((-mean_velocity[:, 1], mean_velocity[:, 0]))
        swirl = self._turbulence.uniform(-_TURBULENCE, _TURBULENCE, len(stars))
        push = mean_velocity + across * swirl[:, None]
        rate = weight.max(axis=1) * min(1.0, _PUSH_RATE * seconds)
        self._star_velocity[stars] += (push - self._star_velocity[stars]) * rate[
            :, None
        ]
        self._stars_resting = False

    def _step_stars(self, seconds: float) -> None:
        if self._stars_resting or seconds <= 0:
            return
        substeps = min(60, max(1, math.ceil(seconds * 60)))
        step = min(seconds / substeps, 1 / 60)
        damping = math.exp(-_STAR_DAMPING_RATE * step)
        for _ in range(substeps):
            self._star_velocity += (
                (self._star_home - self._star_position) * _STAR_RETURN_STIFFNESS * step
            )
            self._star_velocity *= damping
            self._star_position += self._star_velocity * step
        displacement = np.abs(self._star_position - self._star_home).max()
        if displacement < _STAR_REST and np.abs(self._star_velocity).max() < _STAR_REST:
            self._star_position[...] = self._star_home
            self._star_velocity[...] = 0
            self._stars_resting = True

    def draw(self, surface: pygame.Surface, elapsed_ms: int) -> None:
        self._draw_stars(surface, elapsed_ms)
        self._draw_particles(surface, elapsed_ms)

    def _draw_stars(self, surface: pygame.Surface, elapsed_ms: int) -> None:
        brightness = 0.45 + 0.55 * (np.sin(elapsed_ms / 240 + self._star_phase) + 1) / 2
        positions = np.rint(self._star_position).astype(np.intp).tolist()
        for (x, y), big, level in zip(
            positions, self._star_big.tolist(), brightness.tolist(), strict=True
        ):
            base = _BRIGHT_STAR_COLOR if big else _STAR_COLOR
            color = (int(base[0] * level), int(base[1] * level), int(base[2] * level))
            pygame.draw.circle(surface, color, (x, y), 2 if big else 1)

    def _draw_particles(self, surface: pygame.Surface, elapsed_ms: int) -> None:
        """Additive Gaussian splats: sub-pixel positions, depth-driven size and alpha."""
        x, y = self._position[:, 0], self._position[:, 1]
        wave = (np.sin(elapsed_ms / 180 + self._phase) + 1) / 2
        alpha = (FAR_ALPHA + (NEAR_ALPHA - FAR_ALPHA) * self._nearness) * (
            1 - _TWINKLE + _TWINKLE * wave
        )
        sigma = _BASE_SIGMA * (1 + NEAR_SIZE_GAIN * self._nearness)

        columns = np.floor(x)[:, None] + _SPLAT_OFFSETS
        rows = np.floor(y)[:, None] + _SPLAT_OFFSETS
        spread = 2 * sigma[:, None] ** 2
        horizontal = np.exp(-((columns - x[:, None]) ** 2) / spread)
        vertical = np.exp(-((rows - y[:, None]) ** 2) / spread)
        np.multiply(horizontal[:, :, None], vertical[:, None, :], out=self._weights)
        self._weights[self._weights < _MIN_WEIGHT] = 0
        self._weights *= (alpha * _GLOW_GAIN)[:, None, None]
        self._columns[...] = columns.astype(np.intp)[:, :, None]
        self._rows[...] = rows.astype(np.intp)[:, None, :]

        visible = (
            (self._weights > 0)
            & (self._columns >= 0)
            & (self._columns < self._width)
            & (self._rows >= 0)
            & (self._rows < self._height)
        )
        if not visible.any():
            return
        columns_hit = self._columns[visible]
        rows_hit = self._rows[visible]
        left, right = int(columns_hit.min()), int(columns_hit.max()) + 1
        top, bottom = int(rows_hit.min()), int(rows_hit.max()) + 1

        light = self._light[left:right, top:bottom]
        light.fill(0)
        np.add.at(self._light, (columns_hit, rows_hit), self._weights[visible])
        np.minimum(light, 1, out=light)
        pixels = pygame.surfarray.pixels3d(self._light_surface)
        try:
            for channel, value in enumerate(_BRIGHT_STAR_COLOR):
                pixels[left:right, top:bottom, channel] = light * value
        finally:
            del pixels
        surface.blit(
            self._light_surface,
            (left, top),
            pygame.Rect(left, top, right - left, bottom - top),
            special_flags=pygame.BLEND_RGB_ADD,
        )
