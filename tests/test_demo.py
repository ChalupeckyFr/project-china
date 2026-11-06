from pathlib import Path

import pygame
import pytest

from project_china import demo
from project_china.frames import DepthFrame, load_depth_csv
from project_china.selection import select_depth_regions

EXAMPLE_CSV = (
    Path(__file__).resolve().parents[1] / "examples" / "moving_object.csv"
)


def test_frame_index_tracks_elapsed_time() -> None:
    sequence = load_depth_csv(EXAMPLE_CSV)
    offsets = tuple(frame.time_ms - sequence.frames[0].time_ms for frame in sequence.frames)

    assert demo._frame_index_for_elapsed(offsets, 0) == 0
    assert demo._frame_index_for_elapsed(offsets, 499) == 0
    assert demo._frame_index_for_elapsed(offsets, 500) == 1
    assert demo._frame_index_for_elapsed(offsets, 2000) == 2


def test_main_reports_invalid_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text("frame,time_ms,x,y\n", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        demo.main([str(csv_path)])

    assert error.value.code == 2
    assert "CSV header must be exactly" in capsys.readouterr().err


def test_render_frame_draws_stars_and_contour() -> None:
    frame = DepthFrame(0, 0, ((900, 1200), (1200, 1200)))
    selection = select_depth_regions(frame)
    surface = pygame.Surface((320, 240))

    demo.render_frame(surface, frame, selection, ((10, 10, 1),))

    assert surface.get_at((10, 10))[:3] == demo._STAR_COLOR
    assert surface.get_at((112, 72))[:3] == demo._CONTOUR_STAR_COLOR


def test_run_demo_renders_then_closes_on_quit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    sequence = load_depth_csv(EXAMPLE_CSV)
    events = iter(([], [pygame.event.Event(pygame.QUIT)]))
    monkeypatch.setattr(pygame.event, "get", lambda: next(events))
    rendered_frames: list[int] = []
    render_frame = demo.render_frame

    def record_frame(
        surface: pygame.Surface,
        frame: DepthFrame,
        selection: demo.DepthSelection,
        stars: tuple[demo._Star, ...],
    ) -> None:
        render_frame(surface, frame, selection, stars)
        rendered_frames.append(frame.frame)

    monkeypatch.setattr(demo, "render_frame", record_frame)

    demo.run_demo(sequence)

    assert rendered_frames == [0]
    assert len(sequence.frames[0].depths) == 4
    assert len(sequence.frames[0].depths[0]) == 4
