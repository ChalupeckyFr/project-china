import math
from pathlib import Path

import pygame
import pytest

from project_china import demo
from project_china.effects import StarEffect
from project_china.frames import DepthFrame, DepthSequence, load_depth_csv
from project_china.selection import select_depth_regions
from project_china.synthetic_human import human_frame

EXAMPLE_CSV = (
    Path(__file__).resolve().parents[1] / "examples" / "moving_object.csv"
)


def test_example_frames_loop_every_three_seconds() -> None:
    sequence = load_depth_csv(EXAMPLE_CSV)
    offsets = tuple(frame.time_ms - sequence.frames[0].time_ms for frame in sequence.frames)

    assert offsets == (0, 3000, 6000)
    for elapsed_ms, expected_index in (
        (0, 0),
        (2999, 0),
        (3000, 1),
        (5999, 1),
        (6000, 2),
        (8999, 2),
        (9000, 0),
        (12000, 1),
        (18000, 0),
    ):
        assert demo._frame_index_for_elapsed(offsets, elapsed_ms) == expected_index


def test_frame_index_preserves_uneven_and_fractional_intervals() -> None:
    offsets = (0.0, 1000.0, 3500.0)
    assert demo._frame_index_for_elapsed(offsets, -1) == 0
    assert demo._frame_index_for_elapsed(offsets, 3499) == 1
    assert demo._frame_index_for_elapsed(offsets, 3500) == 2
    assert demo._frame_index_for_elapsed(offsets, 5999) == 2
    assert demo._frame_index_for_elapsed(offsets, 6000) == 0
    assert demo._frame_index_for_elapsed(offsets, 7000) == 1

    fractional_offsets = (0.0, 250.5, 751.5)
    assert demo._frame_index_for_elapsed(fractional_offsets, 1252.49) == 2
    assert demo._frame_index_for_elapsed(fractional_offsets, 1252.5) == 0


def test_frame_index_holds_a_single_frame() -> None:
    assert demo._frame_index_for_elapsed((0.0,), 100_000) == 0


def test_frame_index_rejects_an_invalid_final_interval() -> None:
    with pytest.raises(ValueError, match="Frame offsets must increase strictly"):
        demo._frame_index_for_elapsed((0.0, 0.0), 0)


def test_sample_contour_interpolates_between_vertices() -> None:
    sampled = demo._sample_contour(((0, 0), (24, 0), (24, 24), (0, 24)))

    assert len(sampled) > 4
    assert (6, 0) in sampled
    assert (24, 6) in sampled


def test_main_reports_invalid_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text("frame,time_ms,x,y\n", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        demo.main([str(csv_path)])

    assert error.value.code == 2
    assert "CSV header must be exactly" in capsys.readouterr().err


def test_main_passes_particle_count_to_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        demo,
        "run_demo",
        lambda sequence, particle_count: calls.append(
            (len(sequence.frames), particle_count)
        ),
    )

    demo.main([str(EXAMPLE_CSV), "--particles", "360"])
    demo.main([str(EXAMPLE_CSV)])

    assert calls == [(3, 360), (3, 72)]


@pytest.mark.parametrize("value", ("0", "-5"))
def test_main_rejects_non_positive_particle_count(
    capsys: pytest.CaptureFixture[str], value: str
) -> None:
    with pytest.raises(SystemExit) as error:
        demo.main([str(EXAMPLE_CSV), "--particles", value])

    assert error.value.code == 2
    assert "--particles must be a positive integer" in capsys.readouterr().err


def test_run_demo_uses_requested_particle_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    events = iter(([], [pygame.event.Event(pygame.QUIT)]))
    monkeypatch.setattr(pygame.event, "get", lambda: next(events))
    counts: list[int] = []

    def record_frame(
        _surface: pygame.Surface,
        _frame: DepthFrame,
        _selection: demo.DepthSelection,
        effects: StarEffect,
        _elapsed_ms: int,
        _delta_ms: int,
    ) -> None:
        counts.append(len(effects.particle_positions))

    monkeypatch.setattr(demo, "render_frame", record_frame)

    demo.run_demo(load_depth_csv(EXAMPLE_CSV), 360)

    assert counts == [360]
    with pytest.raises(ValueError, match="Particle count must be positive"):
        demo.run_demo(load_depth_csv(EXAMPLE_CSV), 0)


@pytest.mark.parametrize(
    ("particle_count", "max_gap"), ((72, 30.0), (360, 8.0))
)
def test_more_stars_cover_the_human_outline_densely(
    monkeypatch: pytest.MonkeyPatch, particle_count: int, max_gap: float
) -> None:
    frame = human_frame(30)
    selection = select_depth_regions(frame)
    surface = pygame.Surface((960, 720))
    effects = StarEffect((960, 720), particle_count)
    targets: list[tuple[int, int]] = []
    update = effects.update

    def record_update(
        delta_ms: int, contour_targets: tuple[tuple[int, int], ...]
    ) -> None:
        targets[:] = contour_targets
        update(delta_ms, contour_targets)

    monkeypatch.setattr(effects, "update", record_update)
    for tick in range(240):
        demo.render_frame(surface, frame, selection, effects, tick * 16, 16)

    positions = effects.particle_positions
    largest_gap = max(
        min(math.dist(target, position) for position in positions)
        for target in targets
    )
    assert largest_gap <= max_gap
    if particle_count == 72:
        assert largest_gap > 8.0


@pytest.mark.parametrize(
    ("depths", "edge_point"),
    [
        (((900, 1200), (1200, 1200)), (112, 72)),
        (((900, 900), (900, 900)), (160, 72)),
    ],
)
def test_render_frame_targets_contour_without_drawing_it(
    monkeypatch: pytest.MonkeyPatch,
    depths: tuple[tuple[int, ...], ...],
    edge_point: tuple[int, int],
) -> None:
    frame = DepthFrame(0, 0, depths)
    selection = select_depth_regions(frame)
    surface = pygame.Surface((320, 240))
    effects = StarEffect((320, 240))
    targets: list[tuple[int, int]] = []

    def record_targets(
        _delta_ms: int, contour_targets: tuple[tuple[int, int], ...]
    ) -> None:
        targets.extend(contour_targets)

    monkeypatch.setattr(effects, "update", record_targets)
    monkeypatch.setattr(effects, "draw", lambda _surface, _elapsed_ms: None)

    demo.render_frame(surface, frame, selection, effects, 0, 0)

    assert edge_point in targets
    assert (pygame.surfarray.array3d(surface) == demo._BACKGROUND).all()


def test_render_frame_shows_target_with_particle_stars() -> None:
    frame = DepthFrame(0, 0, ((900, 900), (900, 900)))
    selection = select_depth_regions(frame)
    surface = pygame.Surface((320, 240))
    effects = StarEffect((320, 240))

    for tick in range(160):
        demo.render_frame(surface, frame, selection, effects, tick * 16, 16)

    outline = demo._sample_contour(((112, 72), (112, 168), (208, 168), (208, 72)))
    near_outline = [
        position
        for position in effects.particle_positions
        if min(math.dist(position, point) for point in outline) <= 3
    ]
    assert len(near_outline) >= 64
    assert sum(
        surface.get_at((round(x), round(y)))[0] >= 135
        for x, y in near_outline
    ) >= 64


@pytest.mark.parametrize(
    ("event_type", "key"),
    [
        (pygame.QUIT, None),
        (pygame.KEYDOWN, pygame.K_ESCAPE),
        (pygame.KEYDOWN, pygame.K_q),
    ],
)
def test_run_demo_renders_then_closes_on_user_request(
    monkeypatch: pytest.MonkeyPatch,
    event_type: int,
    key: int | None,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    sequence = load_depth_csv(EXAMPLE_CSV)
    events = iter(([], [pygame.event.Event(event_type, key=key)]))
    monkeypatch.setattr(pygame.event, "get", lambda: next(events))
    rendered_frames: list[int] = []
    render_frame = demo.render_frame

    def record_frame(
        surface: pygame.Surface,
        frame: DepthFrame,
        selection: demo.DepthSelection,
        effects: StarEffect,
        elapsed_ms: int,
        delta_ms: int,
    ) -> None:
        render_frame(surface, frame, selection, effects, elapsed_ms, delta_ms)
        rendered_frames.append(frame.frame)

    monkeypatch.setattr(demo, "render_frame", record_frame)

    demo.run_demo(sequence)

    assert rendered_frames == [0]
    assert len(sequence.frames[0].depths) == 4
    assert len(sequence.frames[0].depths[0]) == 4


def test_run_demo_loops_until_quit_without_resetting_animation_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    example = load_depth_csv(EXAMPLE_CSV)
    sequence = DepthSequence(
        tuple(
            DepthFrame(frame.frame, frame.time_ms + 5000, frame.depths)
            for frame in example.frames
        )
    )
    elapsed_values = (0, 2999, 3000, 5999, 6000, 8999, 9000, 12000, 18000)
    ticks = iter([10_000] + [10_000 + elapsed for elapsed in elapsed_values])
    events = iter(
        [[] for _ in elapsed_values] + [[pygame.event.Event(pygame.QUIT)]]
    )
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: next(ticks))
    monkeypatch.setattr(pygame.event, "get", lambda: next(events))

    class ImmediateClock:
        def tick(self, _fps: int) -> None:
            pass

    monkeypatch.setattr(pygame.time, "Clock", lambda: ImmediateClock())
    rendered: list[tuple[int, int]] = []

    def record_frame(
        _surface: pygame.Surface,
        frame: DepthFrame,
        _selection: demo.DepthSelection,
        _effects: StarEffect,
        elapsed_ms: int,
        _delta_ms: int,
    ) -> None:
        rendered.append((frame.frame, elapsed_ms))

    monkeypatch.setattr(demo, "render_frame", record_frame)

    demo.run_demo(sequence)

    assert [frame for frame, _ in rendered] == [0, 0, 1, 1, 2, 2, 0, 1, 0]
    assert [elapsed for _, elapsed in rendered] == list(elapsed_values)
