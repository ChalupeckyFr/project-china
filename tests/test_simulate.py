"""Levý klik kreslí, pravý maže, předloha je vždy snímek předtím."""

import json
from pathlib import Path

import numpy as np

import simulate as sim

sim.window.attributes("-alpha", 0.0)
sim.window.withdraw()


def fresh():
    sim.reset_frames()
    sim.brush_width = 1
    sim.interval_ms = sim.INTERVAL_START
    sim.near_mm = sim.NEAR_START
    sim.interval_var.set(str(sim.interval_ms))
    sim.distance_var.set(str(sim.near_mm))
    sim.sync_interval()
    sim.rebuild_strip()


def test_left_click_paints_and_right_click_erases():
    fresh()
    sim.paint_cell(4, 6, erase=False)
    assert sim.frames[0]["person"][6, 4]
    assert not sim.frames[0]["person"][6, 5]
    sim.paint_cell(4, 6, erase=True)
    assert not sim.frames[0]["person"][6, 4]


def test_guide_is_the_previous_frame_and_cannot_be_erased():
    fresh()
    sim.paint_cell(3, 3, erase=False)
    sim.add_frame()
    assert tuple(sim.cell_colors()[3, 3]) == sim.GUIDE_COLOR
    assert not sim.frames[1]["person"][3, 3]
    sim.paint_cell(3, 3, erase=True)
    assert sim.frames[0]["person"][3, 3]
    assert tuple(sim.cell_colors()[3, 3]) == sim.GUIDE_COLOR
    sim.paint_cell(8, 8, erase=False)
    colors = sim.cell_colors()
    assert tuple(colors[8, 8]) == sim.INK_COLOR
    assert tuple(colors[3, 3]) == sim.GUIDE_COLOR


def test_guide_stays_the_frame_before_after_a_delete_and_a_new_frame():
    fresh()
    sim.paint_cell(1, 1, erase=False)
    sim.add_frame()
    sim.paint_cell(4, 4, erase=False)
    sim.add_frame()
    sim.paint_cell(7, 7, erase=False)
    # Otevřený je třetí snímek. Smaže se první, nesouvisející.
    sim.remove_frame(0)
    assert tuple(sim.cell_colors()[4, 4]) == sim.GUIDE_COLOR
    sim.add_frame()
    # Nový snímek je prázdný. Předloha je všechno, co bylo vidět na tom před ním.
    assert not sim.frames[sim.index]["person"].any()
    assert tuple(sim.cell_colors()[7, 7]) == sim.GUIDE_COLOR
    assert tuple(sim.cell_colors()[4, 4]) == sim.FAR_COLOR
    assert tuple(sim.cell_colors()[1, 1]) == sim.FAR_COLOR


def test_guide_is_only_the_frame_immediately_before():
    fresh()
    sim.paint_cell(5, 5, erase=False)
    sim.add_frame()
    sim.add_frame()
    assert tuple(sim.cell_colors()[5, 5]) == sim.FAR_COLOR


def test_interval_is_typed_and_locked_for_a_single_picture():
    fresh()
    assert str(sim.interval_entry.cget("state")) == "disabled"
    sim.add_frame()
    assert str(sim.interval_entry.cget("state")) == "normal"
    sim.interval_var.set("250")
    sim.apply_interval()
    assert sim.interval_ms == 250
    sim.interval_var.set("abc")
    sim.apply_interval()
    assert sim.interval_ms == 250
    assert sim.interval_var.get() == "250"


def test_export_writes_the_typed_distance(tmp_path):
    fresh()
    sim.paint_cell(2, 5, erase=False)
    sim.add_frame()
    sim.interval_var.set("100")
    sim.distance_var.set("800")
    sim.EXPORT_DIR = tmp_path / "vstup"
    sim.export_frames()
    data = np.load(sim.EXPORT_DIR / "frames.npy")
    info = json.loads((sim.EXPORT_DIR / "info.json").read_text(encoding="utf-8"))
    assert data.shape == (2, sim.HEIGHT, sim.WIDTH)
    assert data.dtype == np.float32
    assert data[0, 5, 2] == 800
    assert data[1, 5, 2] == sim.FAR_MM
    assert data[0, 0, 0] == sim.FAR_MM
    assert info["interval_ms"] == 100
    assert info["near_mm"] == 800
    assert info["far_mm"] == sim.FAR_MM
    assert info["unit"] == "mm"


def test_right_click_removes_a_frame_but_keeps_one():
    fresh()
    sim.paint_cell(1, 1, erase=False)
    sim.add_frame()
    sim.paint_cell(2, 2, erase=False)
    sim.remove_frame(0)
    assert len(sim.frames) == 1
    assert sim.frames[0]["person"][2, 2]
    assert not sim.frames[0]["person"][1, 1]
    sim.remove_frame(0)
    assert len(sim.frames) == 1


def test_wheel_over_the_grid_changes_the_width():
    fresh()
    sim.set_width(5)
    sim.cursor_over_board = lambda: True
    sim.on_wheel(type("Wheel", (), {"delta": 120})())
    assert sim.brush_width == 6
    sim.on_wheel(type("Wheel", (), {"delta": -120})())
    assert sim.brush_width == 5
    away = sim.cursor_over_board
    sim.cursor_over_board = lambda: False
    sim.on_wheel(type("Wheel", (), {"delta": 120})())
    assert sim.brush_width == 5
    sim.cursor_over_board = away


def test_launcher_does_not_open_simulate():
    text = (Path(__file__).resolve().parents[1] / "spustit.py").read_text(encoding="utf-8")
    assert "simulate.py" not in text
