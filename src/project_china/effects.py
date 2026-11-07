"""Star renderer: smoothly following body particles over a reactive starfield.

The renderer receives screen-space targets (outline and volume points with
their depth and stable volume ids); it does not read CSV files or depth
matrices. All particle state lives in arrays allocated once in
:class:`StarEffect`, so the animation loop never creates or deletes particle
objects.
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
# Overdamped follow: each reference tick (1/60 s) a particle covers this
# share of the remaining distance, never more than MAX_TICK_DISTANCE pixels,
# so it can neither overshoot nor shoot out of the silhouette.
FOLLOW_RATE = 0.25
MAX_TICK_DISTANCE = 10.0
# Volume particles without a target fade out in place within about this time.
FADE_MS = 120.0
# Volume particles flying to a distant new target stay dark until they are
# this close (screen pixels), so no visible star crosses outside the body.
TRANSIT_FADE = (8.0, 20.0)
# Rounds of nearest-free-target matching before the rest is paired in order.
_MATCH_ROUNDS = 24

# Static scatter around each target, slowly orbiting, in screen pixels.
# Volume targets already sit on a jittered lattice, so they move only a little.
JITTER_RANGE = (1.5, 2.5)
VOLUME_JITTER_RANGE = (0.3, 0.6)
_JITTER_SPIN = (0.3, 0.9)

# Depth shading: nearness 0 (receding edges), 0.5 (middle) and 1 (closest
# chest, muscles, palms) map piecewise linearly to the radius of a soft disc
# in screen pixels and to its peak alpha. Near particles also turn warmer.
DEPTH_LEVELS = (0.0, 0.5, 1.0)
DEPTH_RADIUS = (1.5, 2.4, 4.0)
DEPTH_ALPHA = (0.22, 0.55, 0.95)
COLD_COLOR = (170, 192, 255)
WARM_COLOR = (255, 238, 210)
_MIN_WEIGHT = 0.05
_TWINKLE = 0.15
_SPLAT_OFFSETS = np.arange(-4, 6, dtype=np.float64)
_SPLAT_SIZE = len(_SPLAT_OFFSETS)

# Background stars stirred by fast limbs: pushed away perpendicular to the
# bone, dragged along the swing with some turbulence, then pulled back home.
REPULSION_RADIUS = 32.0
_FAST_LIMB_SPEED = 150.0
REPULSION_GAIN = 0.6
SWING_GAIN = 0.8
_TURBULENCE = 0.35
_PUSH_RATE = 12.0
_BONE_SPAN = 3
_STAR_RETURN_STIFFNESS = 6.0
# Share of star velocity kept per reference tick (1/60 s).
STAR_DAMPING = 0.92
_STAR_REST = 0.01

_Points = NDArray[np.float64]
_Values = NDArray[np.float64]


@dataclass(frozen=True)
class BodyTargets:
    """Screen targets of one rendered frame.

    Depths are raw values from the depth matrix; smaller is closer to the
    camera. Missing depths render every particle as near. ``volume_ids``
    identify volume targets across frames; without them the index is used.
    """

    outline: _Points
    outline_depth: _Values | None = None
    volume: _Points | None = None
    volume_depth: _Values | None = None
    volume_ids: NDArray[np.intp] | None = None


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
        self._speed = np.zeros(total)
        self._assigned = np.zeros(total, dtype=np.bool_)
        self._presence = np.ones(total)
        self._slot_id = np.full(volume_count, -1, dtype=np.intp)
        self._previous_outline: _Points | None = None
        self._has_targets = False
        self._attraction_strength = 0.0

        self._light = np.zeros((self._width, self._height), dtype=np.float32)
        self._light_surface = pygame.Surface(size)
        self._warmth = np.zeros((self._width, self._height), dtype=np.float32)
        splat = (total, _SPLAT_SIZE, _SPLAT_SIZE)
        self._weights = np.zeros(splat)
        self._columns = np.zeros(splat, dtype=np.intp)
        self._rows = np.zeros(splat, dtype=np.intp)

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
    def particle_presence(self) -> _Values:
        """Opacity factor of each particle; volume particles without a target fade to 0."""
        return self._presence.copy()

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
        if not len(outline):
            self._assigned[...] = False
            self._slot_id[...] = -1

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
        self._assigned[:count] = True

        if self._volume_count:
            if len(volume):
                source, source_near = volume, nearness(volume_depth, len(volume))
                ids = (
                    np.arange(len(volume))
                    if body.volume_ids is None
                    else np.asarray(body.volume_ids, dtype=np.intp)
                )
            else:
                source, source_near = outline, outline_near
                ids = np.arange(len(outline))
            self._match_volume(source, source_near, ids)

    def _match_volume(self, points: _Points, near: _Values, ids: NDArray[np.intp]) -> None:
        """Keep each volume particle on its target id; pair the rest by proximity.

        A particle whose target id is still present keeps it, so targets never
        swap between body parts. Released particles take the nearest free
        target; particles left without one stay where they are and fade out.
        """
        start = self._outline_count
        slots = self._slot_id
        order = np.argsort(ids, kind="stable")
        sorted_ids = ids[order]
        found = np.searchsorted(sorted_ids, slots).clip(0, max(len(ids) - 1, 0))
        keeps = (slots >= 0) & (len(ids) > 0)
        if len(ids):
            keeps &= sorted_ids[found] == slots
        owner = np.full(len(ids), -1, dtype=np.intp)
        kept = np.flatnonzero(keeps)
        target_of = np.full(len(slots), -1, dtype=np.intp)
        target_of[kept] = order[found[kept]]
        owner[target_of[kept]] = kept

        free = np.flatnonzero(~keeps)
        open_targets = np.flatnonzero(owner < 0)
        positions = self._position[start:]
        for _ in range(_MATCH_ROUNDS):
            if not len(free) or not len(open_targets):
                break
            offset = positions[free, None, :] - points[None, open_targets, :]
            distance = np.hypot(offset[..., 0], offset[..., 1])
            choice = np.argmin(distance, axis=1)
            # Each wanted target goes to its closest applicant.
            ranking = np.lexsort((distance[np.arange(len(free)), choice], choice))
            first = np.ones(len(ranking), dtype=np.bool_)
            first[1:] = choice[ranking][1:] != choice[ranking][:-1]
            winners = ranking[first]
            target_of[free[winners]] = open_targets[choice[winners]]
            owner[open_targets[choice[winners]]] = free[winners]
            free = np.delete(free, winners)
            open_targets = np.flatnonzero(owner < 0)
        pairs = min(len(free), len(open_targets))
        target_of[free[:pairs]] = open_targets[:pairs]

        assigned = target_of >= 0
        slots[...] = -1
        slots[assigned] = ids[target_of[assigned]]
        self._assigned[start:] = assigned
        self._target[start:][assigned] = points[target_of[assigned]]
        self._target_nearness[start:][assigned] = near[target_of[assigned]]

    def _step_particles(self, delta_ms: int) -> None:
        ticks = delta_ms / _REFERENCE_TICK_MS
        if ticks <= 0:
            return
        seconds = delta_ms / 1000
        strength = self._attraction_strength
        self._jitter_angle += self._jitter_spin * seconds
        fade = 1 - math.exp(-delta_ms / FADE_MS)

        if self._has_targets and strength > 0:
            np.multiply(
                np.column_stack(
                    (np.cos(self._jitter_angle), np.sin(self._jitter_angle))
                ),
                self._jitter_radius[:, None],
                out=self._jittered,
            )
            self._jittered += self._target
            assigned = self._assigned
            self._nearness[assigned] += (
                self._target_nearness[assigned] - self._nearness[assigned]
            ) * min(1.0, strength)

            # Exponential approach (never past the target), capped per tick.
            share = 1 - (1 - FOLLOW_RATE * strength) ** ticks
            np.subtract(self._jittered, self._position, out=self._offset)
            self._offset *= share
            self._offset[~assigned] = 0
            np.hypot(self._offset[:, 0], self._offset[:, 1], out=self._speed)
            max_move = MAX_TICK_DISTANCE * ticks
            too_fast = self._speed > max_move
            if too_fast.any():
                self._offset[too_fast] *= (max_move / self._speed[too_fast])[:, None]
            self._position += self._offset

            np.subtract(self._jittered, self._position, out=self._offset)
            np.hypot(self._offset[:, 0], self._offset[:, 1], out=self._speed)
            near, far = TRANSIT_FADE
            goal = np.clip((far - self._speed) / (far - near), 0, 1)
            goal[: self._outline_count] = 1
            goal *= assigned
            self._presence += (goal - self._presence) * fade
        else:
            self._presence += (1 - self._presence) * fade

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
        tangent = np.roll(outline, -_BONE_SPAN, axis=0) - np.roll(outline, _BONE_SPAN, axis=0)
        tangent /= np.maximum(np.hypot(tangent[:, 0], tangent[:, 1]), 1e-9)[:, None]
        points, limb_velocity, bone = outline[fast], velocity[fast], tangent[fast]
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
        offset = offset[touched]
        # Repulsion: the part of the offset perpendicular to the bone.
        along = np.einsum("spk,pk->sp", offset, bone)
        normal = offset - along[..., None] * bone[None, :, :]
        normal /= np.maximum(np.hypot(normal[..., 0], normal[..., 1]), 1e-9)[..., None]
        speed = np.hypot(limb_velocity[:, 0], limb_velocity[:, 1])
        share = weight / total[touched, None]
        repel = np.einsum("sp,spk->sk", share * speed[None, :], normal)
        swing = share @ limb_velocity
        across = np.column_stack((-swing[:, 1], swing[:, 0]))
        swirl = self._turbulence.uniform(-_TURBULENCE, _TURBULENCE, len(stars))
        push = REPULSION_GAIN * repel + SWING_GAIN * swing + across * swirl[:, None]
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
        damping = STAR_DAMPING ** (step * 1000 / _REFERENCE_TICK_MS)
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
        """Additive soft discs: sub-pixel positions, depth-driven size, alpha and hue."""
        x, y = self._position[:, 0], self._position[:, 1]
        wave = (np.sin(elapsed_ms / 180 + self._phase) + 1) / 2
        near = self._nearness
        alpha = (
            np.interp(near, DEPTH_LEVELS, DEPTH_ALPHA)
            * (1 - _TWINKLE + _TWINKLE * wave)
            * self._presence
        )
        radius = np.interp(near, DEPTH_LEVELS, DEPTH_RADIUS)

        columns = np.floor(x)[:, None] + _SPLAT_OFFSETS
        rows = np.floor(y)[:, None] + _SPLAT_OFFSETS
        inverse = 1 / radius[:, None] ** 2
        horizontal = (columns + 0.5 - x[:, None]) ** 2 * inverse
        vertical = (rows + 0.5 - y[:, None]) ** 2 * inverse
        np.add(horizontal[:, :, None], vertical[:, None, :], out=self._weights)
        np.subtract(1, self._weights, out=self._weights)
        np.maximum(self._weights, 0, out=self._weights)
        np.square(self._weights, out=self._weights)
        self._weights[self._weights < _MIN_WEIGHT] = 0
        self._weights *= alpha[:, None, None]
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
        span = bottom - top

        weights = self._weights[visible]
        cells = (columns_hit - left) * span + (rows_hit - top)
        light = self._light[left:right, top:bottom]
        warmth = self._warmth[left:right, top:bottom]
        size = (right - left) * span
        light[...] = np.bincount(cells, weights, size).reshape(right - left, span)
        warm_weights = weights * np.broadcast_to(near[:, None, None], self._weights.shape)[visible]
        warmth[...] = np.bincount(cells, warm_weights, size).reshape(right - left, span)
        np.divide(warmth, np.maximum(light, 1e-6), out=warmth)
        np.minimum(light, 1, out=light)
        pixels = pygame.surfarray.pixels3d(self._light_surface)
        try:
            for channel, (cold, warm) in enumerate(zip(COLD_COLOR, WARM_COLOR, strict=True)):
                pixels[left:right, top:bottom, channel] = light * (cold + (warm - cold) * warmth)
        finally:
            del pixels
        surface.blit(
            self._light_surface,
            (left, top),
            pygame.Rect(left, top, right - left, bottom - top),
            special_flags=pygame.BLEND_RGB_ADD,
        )