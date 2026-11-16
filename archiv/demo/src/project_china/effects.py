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
# Overdamped follow: each reference tick (1/60 s) a particle wants to cover
# this share of the remaining distance, never more than MAX_TICK_DISTANCE
# pixels. Its velocity changes by at most MAX_TICK_ACCELERATION pixels per
# tick, and a step never exceeds the remaining distance, so a particle
# neither overshoots nor oscillates when the arms stop at a turning point.
FOLLOW_RATE = 0.25
MAX_TICK_DISTANCE = 10.0
MAX_TICK_ACCELERATION = 2.0
# Volume particles without a target fade out in place within about this time.
FADE_MS = 120.0
# Volume particles flying to a distant new target stay dark until they are
# this close (screen pixels), so no visible star crosses outside the body.
TRANSIT_FADE = (8.0, 20.0)
# Rounds of nearest-free-target matching before the rest is paired in order.
_MATCH_ROUNDS = 24
# A released volume particle takes a free target only this close (screen
# pixels). Farther new targets are taken by hidden pooled particles, which
# respawn on the spot and fade in, so no star crosses the body and flickers.
MATCH_RADIUS = 12.0
_HIDDEN = 0.05

# Static scatter around each target, slowly orbiting, in screen pixels.
# Volume targets already sit on a jittered lattice, so they move only a little.
JITTER_RANGE = (1.5, 2.5)
VOLUME_JITTER_RANGE = (0.3, 0.6)
_JITTER_SPIN = (0.3, 0.9)
# Fixed scatter of limb volume particles across the bone (screen pixels):
# each particle keeps its own offset in [-LIMB_SCATTER, LIMB_SCATTER], scaled
# by how limb-like its target is and kept inside the silhouette, so a raised
# arm keeps its full width instead of collapsing into one row of stars.
LIMB_SCATTER = 3.0
_EDGE_MARGIN = 1.0

# Depth shading: nearness 0 (receding sides), 0.5 (middle) and 1 (closest
# chest, muscles, palms) map piecewise linearly to the radius of a soft disc
# in screen pixels and to its peak alpha. Near particles also turn warmer.
# Depth is shown only by size and brightness, never by leaving gaps.
DEPTH_LEVELS = (0.0, 0.5, 1.0)
DEPTH_RADIUS = (1.5, 2.4, 3.5)
DEPTH_ALPHA = (0.35, 0.55, 0.95)
COLD_COLOR = (170, 192, 255)
WARM_COLOR = (255, 238, 210)
# Temporal smoothing per reference tick: value = previous * 0.8 + target * 0.2.
SHADING_KEEP = 0.8
_MIN_WEIGHT = 0.05
_TWINKLE = 0.15
_VOLUME_TWINKLE = 0.05
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
    camera. Missing depths render every particle as near. ``depth_range``
    (nearest, farthest) fixes the depth normalisation for the whole sequence;
    without it each frame is normalised by its own extremes. ``volume_ids``
    identify volume targets across frames; without them the index is used.
    ``volume_axes`` are unit vectors across the bone, ``volume_limb`` says how
    limb-like (0..1) each target is and ``volume_room`` is its distance from
    the outer edge in screen pixels.
    """

    outline: _Points
    outline_depth: _Values | None = None
    volume: _Points | None = None
    volume_depth: _Values | None = None
    volume_ids: NDArray[np.intp] | None = None
    volume_axes: _Points | None = None
    volume_limb: _Values | None = None
    volume_room: _Values | None = None
    depth_range: tuple[float, float] | None = None


def _limb_scatter(body: BodyTargets, count: int) -> tuple[_Points, _Values] | None:
    """Per-target scatter direction (across the bone, scaled by limb weight)
    and the largest offset that keeps a particle inside the silhouette."""
    if body.volume_axes is None or body.volume_limb is None:
        return None
    axes = np.asarray(body.volume_axes, dtype=np.float64).reshape(-1, 2)
    limb = np.asarray(body.volume_limb, dtype=np.float64)
    if len(axes) != count or len(limb) != count:
        raise ValueError("Volume axes and limb weights must match the volume targets.")
    if body.volume_room is None:
        reach = np.full(count, LIMB_SCATTER)
    else:
        room = np.asarray(body.volume_room, dtype=np.float64)
        reach = np.clip(room - _EDGE_MARGIN, 0, LIMB_SCATTER)
    return axes * limb[:, None], reach


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
        self._radius = np.full(total, DEPTH_RADIUS[1])
        self._depth_alpha = np.full(total, DEPTH_ALPHA[1])
        self._shade = np.zeros(total)
        self._twinkle = np.full(total, _TWINKLE)
        self._twinkle[particle_count:] = _VOLUME_TWINKLE
        self._scatter_share = generator.uniform(-1, 1, total)
        self._scatter = np.zeros((total, 2))
        self._turbulence = generator

        self._target = np.zeros((total, 2))
        self._target_nearness = np.ones(total)
        self._jittered = np.zeros((total, 2))
        self._offset = np.zeros((total, 2))
        self._speed = np.zeros(total)
        self._velocity = np.zeros((total, 2))
        self._change = np.zeros((total, 2))
        self._distance = np.zeros(total)
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
        if body.depth_range is not None:
            nearest, farthest = body.depth_range
            spread = farthest - nearest
        elif depths and outline_depth is not None:
            stacked = np.concatenate(depths)
            nearest, farthest = stacked.min(), stacked.max()
            spread = farthest - nearest
        else:
            spread = 0.0

        def nearness(values: _Values | None, count: int) -> _Values:
            if values is None or spread <= 1e-9:
                return np.ones(count)
            return np.clip(
                (farthest - np.asarray(values, dtype=np.float64)) / spread, 0, 1
            )

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
                across = _limb_scatter(body, len(volume))
            else:
                source, source_near = outline, outline_near
                ids = np.arange(len(outline))
                across = None
            self._match_volume(source, source_near, ids, across)

    def _match_volume(
        self,
        points: _Points,
        near: _Values,
        ids: NDArray[np.intp],
        across: tuple[_Points, _Values] | None = None,
    ) -> None:
        """Keep each volume particle on its target id; pair the rest by proximity.

        A particle whose target id is still present keeps it, so targets never
        swap between body parts. Released particles take the nearest free
        target within MATCH_RADIUS; remaining new targets go to hidden pooled
        particles, which respawn there and fade in. Only when no hidden
        particle is left (e.g. at start) do particles fly to distant targets.
        Particles left without a target stay where they are and fade out.
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
        positions = self._position[start:]
        presence = self._presence[start:]
        free = self._match_nearest(free, points, target_of, owner, MATCH_RADIUS)

        open_targets = np.flatnonzero(owner < 0)
        hidden = free[presence[free] < _HIDDEN]
        spawned = hidden[: len(open_targets)]
        target_of[spawned] = open_targets[: len(spawned)]
        owner[open_targets[: len(spawned)]] = spawned
        free = np.setdiff1d(free, spawned, assume_unique=True)

        free = self._match_nearest(free, points, target_of, owner, math.inf)
        open_targets = np.flatnonzero(owner < 0)
        pairs = min(len(free), len(open_targets))
        target_of[free[:pairs]] = open_targets[:pairs]

        assigned = target_of >= 0
        slots[...] = -1
        slots[assigned] = ids[target_of[assigned]]
        self._assigned[start:] = assigned
        chosen = target_of[assigned]
        self._target[start:][assigned] = points[chosen]
        self._target_nearness[start:][assigned] = near[chosen]
        scatter = self._scatter[start:]
        if across is None:
            scatter[...] = 0
        else:
            axes, reach = across
            # Each particle keeps its own share, so the arm width never reshuffles.
            share = self._scatter_share[start:][assigned]
            scatter[assigned] = axes[chosen] * np.clip(
                share * LIMB_SCATTER, -reach[chosen], reach[chosen]
            )[:, None]
        if len(spawned):
            # Invisible respawn: start on the target with its final shading.
            particle = start + spawned
            positions[spawned] = points[target_of[spawned]] + scatter[spawned]
            self._velocity[particle] = 0
            nearness = near[target_of[spawned]]
            self._nearness[particle] = nearness
            self._radius[particle] = np.interp(nearness, DEPTH_LEVELS, DEPTH_RADIUS)
            self._depth_alpha[particle] = np.interp(nearness, DEPTH_LEVELS, DEPTH_ALPHA)

    def _match_nearest(
        self,
        free: NDArray[np.intp],
        points: _Points,
        target_of: NDArray[np.intp],
        owner: NDArray[np.intp],
        radius: float,
    ) -> NDArray[np.intp]:
        """Give free volume particles their nearest open target within ``radius``;
        returns the particles still without a target."""
        positions = self._position[self._outline_count :]
        open_targets = np.flatnonzero(owner < 0)
        for _ in range(_MATCH_ROUNDS):
            if not len(free) or not len(open_targets):
                break
            offset = positions[free, None, :] - points[None, open_targets, :]
            distance = np.hypot(offset[..., 0], offset[..., 1])
            choice = np.argmin(distance, axis=1)
            best = distance[np.arange(len(free)), choice]
            reachable = np.flatnonzero(best <= radius)
            if not len(reachable):
                break
            # Each wanted target goes to its closest applicant.
            ranking = reachable[np.lexsort((best[reachable], choice[reachable]))]
            first = np.ones(len(ranking), dtype=np.bool_)
            first[1:] = choice[ranking][1:] != choice[ranking][:-1]
            winners = ranking[first]
            target_of[free[winners]] = open_targets[choice[winners]]
            owner[open_targets[choice[winners]]] = free[winners]
            free = np.delete(free, winners)
            open_targets = np.flatnonzero(owner < 0)
        return free

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
            self._jittered += self._scatter
            assigned = self._assigned
            self._smooth_shading(ticks, assigned)

            # Exponential approach, capped per tick, with limited acceleration.
            share = 1 - (1 - FOLLOW_RATE * strength) ** ticks
            np.subtract(self._jittered, self._position, out=self._offset)
            np.hypot(self._offset[:, 0], self._offset[:, 1], out=self._distance)
            self._offset *= share / ticks
            self._offset[~assigned] = 0
            np.hypot(self._offset[:, 0], self._offset[:, 1], out=self._speed)
            too_fast = self._speed > MAX_TICK_DISTANCE
            if too_fast.any():
                self._offset[too_fast] *= (MAX_TICK_DISTANCE / self._speed[too_fast])[:, None]
            # Velocity in pixels per tick moves towards the wanted one.
            np.subtract(self._offset, self._velocity, out=self._change)
            np.hypot(self._change[:, 0], self._change[:, 1], out=self._speed)
            max_change = MAX_TICK_ACCELERATION * ticks
            too_sudden = self._speed > max_change
            if too_sudden.any():
                self._change[too_sudden] *= (max_change / self._speed[too_sudden])[:, None]
            self._velocity += self._change
            np.multiply(self._velocity, ticks, out=self._offset)
            # A step never goes beyond the remaining distance: no overshoot.
            np.hypot(self._offset[:, 0], self._offset[:, 1], out=self._speed)
            too_far = self._speed > self._distance
            if too_far.any():
                self._offset[too_far] *= (
                    self._distance[too_far] / self._speed[too_far]
                )[:, None]
                self._velocity[too_far] = self._offset[too_far] / ticks
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
            self._velocity[...] = 0

        self._position += self._drift * (seconds * (1 - strength))
        if strength == 0:
            self._position[:, 0] %= self._width
            self._position[:, 1] %= self._height
    def _smooth_shading(self, ticks: float, assigned: NDArray[np.bool_]) -> None:
        """Exponential filter of nearness, radius and alpha towards the targets."""
        share = 1 - SHADING_KEEP**ticks
        target = self._target_nearness
        self._nearness[assigned] += (target[assigned] - self._nearness[assigned]) * share
        self._shade[...] = np.interp(target, DEPTH_LEVELS, DEPTH_RADIUS)
        self._radius[assigned] += (self._shade[assigned] - self._radius[assigned]) * share
        self._shade[...] = np.interp(target, DEPTH_LEVELS, DEPTH_ALPHA)
        self._depth_alpha[assigned] += (
            self._shade[assigned] - self._depth_alpha[assigned]
        ) * share

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
            self._depth_alpha
            * (1 - self._twinkle + self._twinkle * wave)
            * self._presence
        )
        radius = self._radius

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