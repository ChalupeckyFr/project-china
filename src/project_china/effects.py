import math
import random
from dataclasses import dataclass

import pygame

_BACKGROUND = (5, 8, 24)
_STAR_COLOR = (145, 170, 215)
_BRIGHT_STAR_COLOR = (225, 235, 255)
PARTICLE_COUNT = 72
_ATTRACTION_COEFFICIENT = 0.08
_ATTRACTION_RAMP_MS = 180.0
_RELEASE_TIME_MS = 700.0
_REFERENCE_TICK_MS = 1000 / 60


@dataclass(frozen=True)
class _Star:
    x: int
    y: int
    radius: int
    phase: float


@dataclass
class _Particle:
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    phase: float


class StarEffect:
    def __init__(
        self, size: tuple[int, int], particle_count: int = PARTICLE_COUNT
    ) -> None:
        if particle_count < 1:
            raise ValueError("Particle count must be positive.")
        self._width, self._height = size
        random_source = random.Random(42)
        star_count = max(100, self._width * self._height // 3000)
        self._stars = tuple(
            _Star(
                random_source.randrange(self._width),
                random_source.randrange(self._height),
                1 if random_source.random() < 0.9 else 2,
                random_source.uniform(0, math.tau),
            )
            for _ in range(star_count)
        )
        self._particles = [
            _Particle(
                random_source.uniform(0, self._width),
                random_source.uniform(0, self._height),
                random_source.uniform(-8, 8),
                random_source.uniform(-8, 8),
                random_source.uniform(0, math.tau),
            )
            for _ in range(particle_count)
        ]
        self._last_targets: tuple[tuple[float, float], ...] = ()
        self._attraction_strength = 0.0

    @property
    def attraction_strength(self) -> float:
        return self._attraction_strength

    @property
    def particle_positions(self) -> tuple[tuple[float, float], ...]:
        return tuple((particle.x, particle.y) for particle in self._particles)

    def update(
        self, delta_ms: int, targets: tuple[tuple[float, float], ...]
    ) -> None:
        if delta_ms < 0:
            raise ValueError("Elapsed time must not be negative.")

        if targets:
            self._last_targets = targets
            ramp = math.exp(-delta_ms / _ATTRACTION_RAMP_MS)
            self._attraction_strength = 1 - (
                1 - self._attraction_strength
            ) * ramp
        elif self._last_targets:
            self._attraction_strength *= math.exp(-delta_ms / _RELEASE_TIME_MS)
            if self._attraction_strength < 0.001:
                self._attraction_strength = 0.0
                self._last_targets = ()

        frame_steps = delta_ms / _REFERENCE_TICK_MS
        blend = 1 - (
            1 - _ATTRACTION_COEFFICIENT * self._attraction_strength
        ) ** frame_steps
        delta_seconds = delta_ms / 1000

        for index, particle in enumerate(self._particles):
            if self._last_targets and self._attraction_strength:
                target_x, target_y = self._last_targets[
                    index * len(self._last_targets) // len(self._particles)
                ]
                particle.x += (target_x - particle.x) * blend
                particle.y += (target_y - particle.y) * blend

            particle.x = (particle.x + particle.velocity_x * delta_seconds) % (
                self._width
            )
            particle.y = (particle.y + particle.velocity_y * delta_seconds) % (
                self._height
            )

    def draw(self, surface: pygame.Surface, elapsed_ms: int) -> None:
        for star in self._stars:
            wave = (math.sin(elapsed_ms / 240 + star.phase) + 1) / 2
            brightness = 0.45 + 0.55 * wave
            color = tuple(int(channel * brightness) for channel in _STAR_COLOR)
            if star.radius == 2:
                color = tuple(
                    int(channel * brightness) for channel in _BRIGHT_STAR_COLOR
                )
            pygame.draw.circle(surface, color, (star.x, star.y), star.radius)

        for particle in self._particles:
            wave = (math.sin(elapsed_ms / 180 + particle.phase) + 1) / 2
            brightness = 0.6 + 0.4 * wave
            color = tuple(
                int(channel * brightness) for channel in _BRIGHT_STAR_COLOR
            )
            radius = 2 if self._attraction_strength > 0.6 else 1
            pygame.draw.circle(
                surface,
                color,
                (round(particle.x), round(particle.y)),
                radius,
            )
