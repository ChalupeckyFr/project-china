"""Komplexní testy aplikace AbstractView:
- Výchozí 'první hodnoty', ukládání a resetování nastavení
- Logika shuffle ('normal', 'random' bez opakování v cyklu, 'custom', Smooth přechod)
- Vykreslování tvarových efektů (gravitace 0 vs 20 vs 100)
- Vykreslování objektového efektu 'Prstence tvarů' (koule, jehlany, válce, kvádry, rychlost, velikost/počet, vzory, graffiti)
- Dynamické škálování UI okna, přepínání light/dark módu, dialogy a samostatné výstupní okno
- Měření spotřeby RAM, CPU a rychlosti renderu
"""

from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import psutil
import pygame

from abstractview_app.config import (
    ALL_EFFECT_KEYS,
    AppSettings,
    SettingsStore,
    ShuffleScheduler,
)
from abstractview_app.renderer import (
    AbstractViewEngine,
    extract_anatomical_rig,
)
from abstractview_app.samples import (
    SAMPLE_POSES,
    discover_camera_ports,
    export_sample_csv,
    get_sample_sequence,
    render_sample_thumbnail_ppm,
)
from abstractview_app.scene import (
    _FISTRON_SPRITE_CACHE,
    FistronCompanion,
    _draw_aa_projection_screen,
    _draw_desert_glass_panel,
    _render_dunes_base,
    render_fistron_sprite_rgba,
)
from abstractview_app.theme import (
    DARK_PALETTE,
    LIGHT_PALETTE,
    PRESET_COLORS,
    hex_to_rgb,
    interpolate_palette,
)
from abstractview_app.ui import AbstractViewApp
from project_china.selection import select_depth_regions


def test_first_values_and_persistence_and_reset(tmp_path: Path) -> None:
    """Ověří první hodnoty při prvním spuštění, uložení změn a následný reset."""
    cfg_file = tmp_path / "settings.json"
    store = SettingsStore(cfg_file)
    s = store.settings

    # Kontrola prvních hodnot dle zadání
    assert s.shuffle_interval_s == 60  # 1 min
    assert s.shuffle_transition_s == 1.0  # 1 s
    assert s.shuffle_order == "normal"
    assert s.gravity == 20
    assert s.orbit_speed == 0
    assert s.theme_mode == "dark"
    assert s.window_geometry == ""
    assert s.window_state == "normal"

    # Změna nastavení uživatelem a uložení
    s.theme_mode = "light"
    s.gravity = 85
    s.shuffle_interval_s = 120
    s.shuffle_order = "random"
    s.orbit_speed = 65
    s.shape_size = 75
    s.window_geometry = "1200x800+40+50"
    s.window_state = "zoomed"
    store.save()

    # Opětovné načtení zachovává hodnoty nastavené člověkem
    reloaded = SettingsStore(cfg_file).settings
    assert reloaded.theme_mode == "light"
    assert reloaded.gravity == 85
    assert reloaded.shuffle_interval_s == 120
    assert reloaded.shuffle_order == "random"
    assert reloaded.orbit_speed == 65
    assert reloaded.shape_size == 75
    assert reloaded.is_graffiti_unlocked is True
    assert reloaded.window_geometry == "1200x800+40+50"
    assert reloaded.window_state == "zoomed"

    # Reset vrátí vše na první hodnotu
    reset_s = store.reset_to_defaults()
    assert reset_s.theme_mode == "dark"
    assert reset_s.gravity == 20
    assert reset_s.shuffle_interval_s == 60
    assert reset_s.shuffle_transition_s == 1.0
    assert reset_s.shuffle_order == "normal"
    assert reset_s.orbit_speed == 0
    assert reset_s.window_geometry == ""
    assert reset_s.window_state == "normal"


def test_shuffle_normal_random_no_repeat_and_custom() -> None:
    """Ověří, že random nikdy nezopakuje efekt dříve, než projdou všechny ostatní,
    ani nedá stejný efekt 2x po sobě na přechodu mezi koly."""
    scheduler = ShuffleScheduler(seed=123)
    settings = AppSettings(
        shape_shuffle=True,
        object_shuffle=True,
        shuffle_interval_s=30,
        shuffle_transition_s=2.0,
        shuffle_order="random",
    )
    pool = scheduler.active_pool(settings)
    assert set(pool) == set(ALL_EFFECT_KEYS)
    n = len(pool)

    # Nasbíráme sekvenci efektů přes 12 celých cyklů
    visited: list[str] = []
    for step in range(n * 12):
        eff, _, _ = scheduler.state_at(settings, step * 30.0 + 1.0)
        visited.append(eff)

    # 1. Každá n-tice (jeden cyklus) musí obsahovat všechny efekty právě jednou
    for cycle in range(12):
        chunk = visited[cycle * n : (cycle + 1) * n]
        assert set(chunk) == set(pool)

    # 2. Nikdy nesmí být stejný efekt 2x za sebou (ani mezi konci a začátky cyklů)
    for i in range(1, len(visited)):
        assert visited[i] != visited[i - 1]

    # 3. Ověření Smooth přechodu (na konci intervalu probíhá plynulý přechod 0 < alpha < 1)
    _, next_eff, alpha = scheduler.state_at(settings, 29.0)
    assert next_eff is not None
    assert 0.0 < alpha < 1.0

    # 4. Ověření custom filtru
    settings.shuffle_order = "custom"
    settings.custom_enabled_effects = ["stars", "rings"]
    custom_pool = scheduler.active_pool(settings)
    assert custom_pool == ["stars", "rings"]


def test_three_sample_poses_and_thumbnails(tmp_path: Path) -> None:
    """Ověří okamžité načtení všech 3 ukázkových póz člověka, jejich náhledy a CSV export."""
    assert len(SAMPLE_POSES) == 3
    for pose in SAMPLE_POSES:
        seq = get_sample_sequence(pose.sample_id)
        assert len(seq.frames) >= 12
        ppm = render_sample_thumbnail_ppm(pose.sample_id, 156, 116)
        assert ppm.startswith(b"P6 156 116 255\n")
        image = np.frombuffer(ppm.split(b"\n", 1)[1], dtype=np.uint8).reshape(116, 156, 3)
        assert len(np.unique(image.reshape(-1, 3), axis=0)) > 250

    csv_file = export_sample_csv("pose_spread", tmp_path / "sample.csv")
    assert csv_file.exists()


def test_object_color_controls_follow_pattern() -> None:
    settings = AppSettings()
    assert not settings.uses_secondary_color
    assert not settings.show_graffiti_editor
    settings.pattern_style = "spiral"
    assert settings.uses_secondary_color
    settings.shape_size = 65
    settings.pattern_style = "graffiti"
    assert settings.show_graffiti_editor
    assert not settings.uses_secondary_color
    settings.shape_size = 35
    settings.validate()
    assert settings.pattern_style == "solid"
    assert not settings.show_graffiti_editor


def test_scene_is_sharp_and_sprite_frames_are_reused() -> None:
    background = _render_dunes_base(960, 1100, 0.0, "stars", "light_blue", -1)
    assert background.shape == (1100, 960, 3)
    assert background[100, 100].tolist() != background[600, 100].tolist()
    assert background[1099, 100].sum() > 0
    assert _render_dunes_base(960, 1100, 0.0, "stars", "light_blue", -1) is background

    poses = ("sleep", "push", "walk", "hands_up", "focus", "exhausted")
    for pose in poses:
        sprite = render_fistron_sprite_rgba(pose)
        assert sprite.shape == (190, 200, 4)
        assert int(sprite[:, :, 3].max()) > 200
        assert render_fistron_sprite_rgba(pose) is sprite
        assert (pose, False) in _FISTRON_SPRITE_CACHE
    assert np.any(
        render_fistron_sprite_rgba("walk", facing_left=True)
        != render_fistron_sprite_rgba("walk")
    )
    glass = background[:700, :900].copy()
    outside = glass[50, 50].copy()
    desert_pixel = glass[300, 400].copy()
    _draw_desert_glass_panel(glass, (220, 195, 800, 565), 0.0)
    assert np.array_equal(glass[50, 50], outside)
    assert not np.array_equal(glass[300, 400], desert_pixel)
    assert int(glass[300, 400].max()) > 40


def test_rest_and_push_sprites_fit_beside_the_panel_lane() -> None:
    for pose, center_x in (("sleep", 82), ("push", 60)):
        alpha = render_fistron_sprite_rgba(pose)[:, :, 3]
        visible_x = np.nonzero(alpha > 24)[1]
        left = center_x - 95 + int(visible_x.min())
        right = center_x - 95 + int(visible_x.max())
        assert left >= 0
        assert right < 160

def test_theme_transition_keeps_text_readable_at_midpoint() -> None:
    for progress in (0.4, 0.45, 0.5, 0.55, 0.6):
        palette = interpolate_palette(progress)
        card = sum(hex_to_rgb(palette.bg_card)) / 3
        text = sum(hex_to_rgb(palette.text_primary)) / 3
        assert abs(card - text) > 95


def test_fistron_moves_only_during_panel_drag_and_changes_button_pose() -> None:
    fistron = FistronCompanion(x=120, y=500)
    common = {
        "light_progress": 1.0,
        "settings_open": True,
        "panel_rect": (620, 220, 1040, 660),
        "button_hovered": False,
        "button_center": (850, 680),
        "stage_center": (320, 500),
        "home_center": (120, 500),
    }
    fistron.update(0.05, **common)
    assert fistron.state == "resting"
    assert fistron.x == 120
    assert not fistron.is_dashing
    for _ in range(5):
        fistron.update(0.05, **{**common, "panel_dragging": True})
    assert fistron.state == "pushing_panel"
    assert fistron.x == 520
    assert not fistron.is_dashing
    back_home = {**common, "panel_dragging": False}
    for _ in range(4):
        fistron.update(0.05, **back_home)
    assert fistron.state == "resting"
    assert fistron.facing_left
    assert fistron.x == 120

    fistron.update(0.05, **{**common, "button_hovered": True})
    assert fistron.state == "button_ready"
    assert fistron.is_dashing
    fistron.trigger_button_smash(850, 680)
    assert fistron.state == "button_windup"
    assert fistron.x == 850
    assert fistron.y == 588


def test_fistron_stays_home_during_idle_in_light_mode() -> None:
    fistron = FistronCompanion(x=120, y=500)
    kwargs = {
        "light_progress": 1.0,
        "settings_open": False,
        "panel_rect": None,
        "button_hovered": False,
        "button_center": (850, 680),
        "stage_center": (320, 500),
        "home_center": (120, 500),
    }
    for _ in range(5):
        fistron.update(0.05, idle_time=3.5, **kwargs)
    assert fistron.state == "resting"
    assert fistron.target_x == 120
    fistron.update(0.05, idle_time=8.0, **kwargs)
    assert fistron.state == "resting"
    assert fistron.target_x == 120


def test_projection_screen_keeps_center_clear_for_effect_title() -> None:
    screen = np.zeros((400, 500, 3), dtype=np.uint8)
    _draw_aa_projection_screen(screen, (250, 270), 1.0)
    assert tuple(screen[190, 250]) == (8, 15, 32)
    assert np.all(screen[175:205, 220:280] == (8, 15, 32))


def test_floating_panels_persist_and_fistron_reacts(tmp_path: Path) -> None:
    settings_path = tmp_path / "floating_panels.json"
    root = tk.Tk()
    root.geometry("1280x850+90+90")
    app = AbstractViewApp(root=root, store=SettingsStore(settings_path))
    try:
        root.update()
        assert app._scene_photo is not None
        stable_background_height = app._scene_photo.height()
        stable_scroll_top = app.scroll_canvas.canvasy(0)
        app.on_effect_button_clicked("stars")
        app.on_effect_button_clicked("rings")
        app._toggle_shape_shuffle()
        app.on_effect_button_clicked("stars")
        assert set(app.open_panels) == {"shape", "object", "shuffle"}
        assert len(app.open_panels) == 3
        assert app.active_panel == "shape"
        assert app.open_panels[-1] == "shape"
        assert len(app._panel_rects) == 3
        assert app._scene_photo is not None
        app._step_scene_and_fistron(0.0, True)
        assert app._scene_photo.height() == stable_background_height
        assert app.scroll_canvas.canvasy(0) == stable_scroll_top
        root.update_idletasks()

        assert app._panel_shells["shape"].winfo_manager() == "place"

        before = app._panel_rects["shape"]
        assert app._panel_shells["shape"]._region_size == (
            before[2] - before[0], before[3] - before[1]
        )
        assert before not in app._visible_card_rects
        press = SimpleNamespace(
            x_root=root.winfo_rootx() + before[0] + 30,
            y_root=root.winfo_rooty() + app.scroll_canvas.winfo_y() + before[1] + 20,
        )
        app._start_panel_drag("shape", press)
        app._drag_panel(SimpleNamespace(x_root=press.x_root + 45, y_root=press.y_root + 35))
        moved = app._panel_rects["shape"]
        assert moved[0] > before[0]
        assert moved[1] > before[1]
        app._step_scene_and_fistron(0.1)
        assert app.fistron.state == "pushing_panel"
        app._finish_panel_drag(press)
        app._mark_panel_editing("shape")
        for _ in range(6):
            app._step_scene_and_fistron(0.05)
        assert app.fistron.state == "sleeping"
        assert app.fistron.x < moved[0]
        stable_position = (app.fistron.x, app.fistron.y)
        app._step_scene_and_fistron(0.05)
        assert app.fistron.state == "sleeping"
        assert (app.fistron.x, app.fistron.y) == stable_position
        assert not hasattr(app, "_panel_headers")
        assert not hasattr(app, "_panel_grip_labels")
        assert app.card_shape_settings.title_label.cget("cursor") == "fleur"
        assert app._panel_close_labels["shape"].winfo_ismapped()
        assert app.OUTPUT_ACTION_DELAY_MS <= 200
        saved_position = app.settings.panel_positions["shape"]
        root.state("zoomed")
        root.update()
    finally:
        app.shutdown()

    second_root = tk.Tk()
    second = AbstractViewApp(root=second_root, store=SettingsStore(settings_path))
    try:
        second_root.update()
        assert second_root.state() == "zoomed"
        assert set(second.open_panels) == {"shape", "object", "shuffle"}
        assert len(second._panel_rects) == 3
        assert second.settings.panel_positions["shape"] == saved_position
        second.on_effect_button_clicked("stars")
        assert second.open_panels.count("shape") == 1
    finally:
        second.shutdown()


def test_maximum_star_count_has_valid_targets() -> None:
    engine = AbstractViewEngine((960, 720))
    try:
        for count in (1, 600, 2500):
            settings = AppSettings(active_effect="stars", star_count=count)
            surface, effect = engine.render_step(settings, count, 16.0)
            assert effect == "stars"
            assert surface.get_size() == (960, 720)
    finally:
        engine.close()


def test_shape_effect_gravity_extremes() -> None:
    """Ověří chování gravitace: 0 = hvězdné nebe, 100 = pouze obrys těla na černé obrazovce."""
    engine = AbstractViewEngine((480, 360))
    try:
        # Gravitace = 100: rohy obrazovky mimo postavu musí být čistě černé (0, 0, 0)
        s_100 = AppSettings(
            active_effect="stars",
            gravity=100,
            star_count=800,
            shooting_stars_freq=0,
        )
        for step in range(8):
            surf, _ = engine.render_step(s_100, step * 50.0, 50.0)
        arr_100 = pygame.surfarray.array3d(surf)
        # Levý horní roh (0..40, 0..40) je mimo tělo -> musí být černý
        corner_100 = arr_100[:40, :40]
        assert int(corner_100.max()) == 0
        # Střed obrazovky obsahuje postavu tvořenou z hvězd
        center_100 = arr_100[160:320, 80:280]
        assert int(center_100.max()) > 180

        # Gravitace = 0: hvězdné nebe po celé obrazovce (i v okrajových pásmech)
        s_0 = AppSettings(
            active_effect="stars",
            gravity=0,
            star_count=1200,
            shooting_stars_freq=0,
        )
        for step in range(8):
            surf_0, _ = engine.render_step(s_0, step * 50.0, 50.0)
        arr_0 = pygame.surfarray.array3d(surf_0)
        outer_band = arr_0[:90, :]
        assert int(outer_band.max()) > 100
    finally:
        engine.close()


def test_object_effect_rings_patterns_and_graffiti() -> None:
    """Ověří objektový efekt 'Prstence tvarů', stabilitu hlavy při vzpažení,
    plynulý pohyb rukou, oddělené prstence pro každou nohu, vzory a Graffiti."""
    # 1. Kontrola anatomie na Ukázce 3 (Vzpažení): hlava se nesmí zvětšovat a ruce jdou plynule nahoru
    seq_raise = get_sample_sequence("pose_raise")
    rigs = [
        extract_anatomical_rig(
            select_depth_regions(frame).mask, (960, 720)
        )
        for frame in seq_raise.frames[:13]
    ]
    head_radii = [r.head_radius for r in rigs]
    assert max(head_radii) - min(head_radii) < 1e-4

    # Ruce ve snímku 0 (dole) -> snímek 6 (uprostřed) -> snímek 12 (nahoře nad hlavou)
    hand_y_down = rigs[0].right_arm_points[-1][1]
    hand_y_mid = rigs[6].right_arm_points[-1][1]
    hand_y_up = rigs[12].right_arm_points[-1][1]
    assert hand_y_down > hand_y_mid > hand_y_up

    # Levá a pravá noha mají oddělené osy s jasným rozestupem
    left_leg_x = rigs[0].left_leg_points[0][0]
    right_leg_x = rigs[0].right_leg_points[0][0]
    assert (right_leg_x - left_leg_x) > 45.0

    engine = AbstractViewEngine((480, 360))
    try:
        # Ověření, že zvětšování tvarů snižuje jejich počet a od 60 odemyká Graffiti
        s_small = AppSettings(active_effect="rings", shape_size=15, orbit_speed=0)
        s_large = AppSettings(active_effect="rings", shape_size=80, orbit_speed=0)
        assert s_small.computed_shape_count > s_large.computed_shape_count
        assert s_small.is_graffiti_unlocked is False
        assert s_large.is_graffiti_unlocked is True

        # Při rychlosti 0 jsou tvary v klidu na stejném místě
        surf_a, _ = engine.render_step(s_small, 200.0, 16.0)
        arr_a = pygame.surfarray.array3d(surf_a).copy()
        surf_b, _ = engine.render_step(s_small, 200.0, 16.0)
        arr_b = pygame.surfarray.array3d(surf_b).copy()
        assert np.array_equal(arr_a, arr_b)

        # Při rychlosti 95 tvary obíhají (snímek se změní)
        s_fast = AppSettings(active_effect="rings", shape_size=35, orbit_speed=95)
        engine.render_step(s_fast, 200.0, 50.0)
        surf_fast, _ = engine.render_step(s_fast, 250.0, 50.0)
        arr_fast = pygame.surfarray.array3d(surf_fast)
        assert not np.array_equal(arr_a, arr_fast)

        # Všechny vzory (solid, brush, spiral, dots, graffiti) i pokročilé barvy částí těla
        for pattern in ("solid", "brush", "spiral", "dots", "graffiti"):
            s_pat = AppSettings(
                active_effect="rings",
                shape_size=75,
                color_mode="per_part",
                pattern_style=pattern,
                graffiti_strokes=[
                    {
                        "color": "yellow",
                        "eraser": False,
                        "size": 10,
                        "points": [[0.2, 0.2], [0.8, 0.8]],
                    }
                ],
            )
            engine.notify_graffiti_changed()
            surf_p, eff = engine.render_step(s_pat, 400.0, 16.0)
            assert eff == "rings"
            arr_p = pygame.surfarray.array3d(surf_p)
            assert int(arr_p.max()) > 100
    finally:
        engine.close()


def test_ui_dynamic_resizing_themes_and_windows(tmp_path: Path) -> None:
    """Ověří dynamickou responzivitu okna, přepínání light/dark s animací měsíce/slunce,
    rozbalování/skrývání nastavení, králíčka Fištróna, 3D tlačítko a vycentrovaný reset."""
    store = SettingsStore(tmp_path / "ui_settings.json")
    root = tk.Tk()
    app = AbstractViewApp(root=root, store=store)
    try:
        root.update_idletasks()
        root.update()
        app.btn_play_output._on_leave(None)  # type: ignore[arg-type]
        for _ in range(15):
            app._step_scene_and_fistron(0.016)
        assert app.lbl_source_badge.variant == "inspect"
        assert app.shape_effect_buttons["stars"]._pill_photo.transparency_get(0, 0)

        # 1. Výchozí stav: žádné menu nastavení efektu není rozbalené, Fištrón spí v dark módu
        assert app.open_effect_settings is None
        assert (
            app.scroll_canvas.itemcget(app._win_shuffle_card, "state")
            == "hidden"
        )
        assert (
            app.scroll_canvas.itemcget(app._win_shape_settings, "state")
            == "hidden"
        )
        assert (
            app.scroll_canvas.itemcget(app._win_object_settings, "state")
            == "hidden"
        )
        assert app.fistron.state == "sleeping"
        assert app.fistron.x < app.scroll_canvas.winfo_width() * 0.3
        assert app.fistron.screen_x > app.fistron.x
        assert app.fistron.screen_x - app.fistron.x < 240

        # 2. Nastavení různých skupin zůstávají otevřená současně.
        app.on_effect_button_clicked("stars")
        root.update_idletasks()
        assert app.slider_gravity._slider_photo.transparency_get(0, 0)
        assert app.open_effect_settings == "stars"
        assert (
            app.scroll_canvas.itemcget(app._win_shape_settings, "state")
            == "normal"
        )
        assert (
            app.scroll_canvas.itemcget(app._win_object_settings, "state")
            == "hidden"
        )
        for _ in range(12):
            app._step_scene_and_fistron(0.05)
        assert app.fistron.state == "sleeping"
        assert app.scroll_canvas.itemcget(app._projection_effect_title, "text") == "Hvězdný obrys"
        panel_rect = app._get_open_settings_panel_rect()
        assert panel_rect is not None
        assert panel_rect in app._glass_rects
        assert app._panel_shells["shape"].winfo_manager() == "place"
        assert app.open_panels[-1] == app.active_panel
        assert panel_rect[2] - panel_rect[0] >= 500
        # Fištrón se bez tažení vrací domů a není částí panelu.
        assert app.fistron.x + 75 < panel_rect[0]

        # Přehození rovnou na objektový efekt bez vypnutí prvního
        app.on_effect_button_clicked("rings")
        root.update_idletasks()
        app._step_scene_and_fistron(0.05)
        assert app.scroll_canvas.itemcget(app._projection_effect_title, "text") == "Prstence tvarů"
        assert app.open_effect_settings == "rings"
        assert app.scroll_canvas.itemcget(app._win_shape_settings, "state") == "normal"
        assert (
            app.scroll_canvas.itemcget(app._win_object_settings, "state")
            == "normal"
        )
        assert not app.secondary_swatch_block.winfo_ismapped()
        assert not app.graffiti_section.winfo_ismapped()
        app._select_pattern("spiral")
        assert app.secondary_swatch_block.winfo_ismapped()
        app._on_shape_size_change(70)
        app._select_pattern("graffiti")
        assert app.graffiti_section.winfo_ismapped()
        assert not app.swatches_container.winfo_ismapped()
        app._on_shape_size_change(35)
        assert not app.graffiti_section.winfo_ismapped()

        # Opětovné kliknutí jen zaměří existující panel, nevytvoří kopii.
        app.on_effect_button_clicked("rings")
        root.update_idletasks()
        assert app.open_panels.count("object") == 1
        app._close_panel("object")
        assert app.scroll_canvas.itemcget(app._win_object_settings, "state") == "hidden"

        # 3. Shuffle je třetí samostatný panel.
        app.on_effect_button_clicked("stars")
        assert app.open_effect_settings == "stars"
        app._toggle_shape_shuffle()
        root.update_idletasks()
        assert app.settings.shape_shuffle is True
        assert "shape" in app.open_panels
        assert (
            app.scroll_canvas.itemcget(app._win_shuffle_card, "state")
            == "normal"
        )
        assert app.btn_shape_shuffle.variant == "shuffle"
        assert app.shape_effect_buttons["stars"].variant == "inspect"

        # Při běžícím shuffle zůstane tvarový panel otevřený a dá se zaměřit.
        app.on_effect_button_clicked("stars")
        root.update_idletasks()
        assert app.open_effect_settings == "stars"
        assert app.shape_effect_buttons["stars"].variant == "inspect"
        shuffle_y = app._panel_rects["shuffle"][1]
        shape_y = app._panel_rects["shape"][1]
        assert shape_y != shuffle_y

        # Zavřený panel se při vypnutí shuffle nesmí znovu otevřít.
        app._close_panel("shuffle")
        assert "shuffle" not in app.open_panels
        app._toggle_shape_shuffle()
        assert app.settings.shape_shuffle is False
        assert "shuffle" not in app.open_panels
        app._close_panel("shape")

        # 4. Přepnutí tématu dark -> light (plynulý přechod Měsíce a Slunce + Fištrón ožije)
        assert app.settings.theme_mode == "dark"
        assert app.palette == DARK_PALETTE
        app.toggle_theme()
        previous = app._light_progress
        previous_palette_step = app._last_palette_step
        card_colors = []
        for _ in range(10):
            app._step_scene_and_fistron(0.04)
            assert app._light_progress >= previous
            previous = app._light_progress
            assert app._last_palette_step >= previous_palette_step
            previous_palette_step = app._last_palette_step
            card_colors.append(app.card_shape_effects.cget("bg"))
        assert len(set(card_colors)) >= 7
        assert app.btn_theme._photo is not None
        assert not any(app.btn_theme.type(item) == "line" for item in app.btn_theme.find_all())
        assert app.palette != DARK_PALETTE
        for _ in range(35):
            app._step_scene_and_fistron(0.04)
        root.update_idletasks()
        assert app.settings.theme_mode == "light"
        assert app.palette == LIGHT_PALETTE
        assert app.fistron.state == "resting"
        app.toggle_theme()
        for _ in range(35):
            app._step_scene_and_fistron(0.04)
        assert app.settings.theme_mode == "dark"
        assert app.palette == DARK_PALETTE

        # V úzkém okně zůstane projektor i Fištrón uvnitř viditelné plochy.
        root.geometry("580x480")
        root.update()
        app.on_effect_button_clicked("stars")
        root.update_idletasks()
        app._step_scene_and_fistron(0.05)
        assert app.fistron.x >= 80.0
        assert app.fistron.y < app.scroll_canvas.winfo_height()
        assert app.fistron.screen_x < app.scroll_canvas.winfo_width()
        assert min(rect[0] for rect in app._glass_rects) >= 160
        assert app.fistron.x + 75 < min(rect[0] for rect in app._glass_rects)
        app._close_panel("shape")

        # 5. Test dynamického rozložení při různých velikostech okna
        for w, h, expected_cols in (
            (580, 480, 1),
            (1150, 820, 2),
            (1500, 960, 2),
        ):
            root.geometry(f"{w}x{h}")
            app._relayout_cards(w)
            root.update_idletasks()
            root.update()
            assert app._current_columns == expected_cols
            bbox = app.scroll_canvas.bbox("all")
            assert bbox is not None
            assert bbox[2] > 200 and bbox[3] > 200
            assert app.scroll_canvas.coords(app._win_shape_effects)[0] < 100
            assert app._scene_height >= max(rect[3] for rect in app._visible_card_rects)

        # 6. Test dialogů a vycentrování Reset okna uprostřed obrazovky
        csv_dlg = app.open_csv_dialog()
        root.update_idletasks()
        assert csv_dlg.winfo_exists()
        app.activate_sample_pose("pose_calm")
        assert app.settings.sample_id == "pose_calm"
        csv_dlg.destroy()

        cam_dlg = app.open_camera_dialog()
        root.update_idletasks()
        assert cam_dlg.winfo_exists()
        cam_dlg.destroy()

        reset_dlg = app.open_reset_dialog()
        root.update_idletasks()
        assert reset_dlg.winfo_exists()
        # Ověření, že dialog není vlevo nahoře (0, 0), ale uprostřed obrazovky
        assert reset_dlg.winfo_x() > 100
        assert reset_dlg.winfo_y() > 80
        app.confirm_reset(reset_dlg)
        assert app.settings.theme_mode == "dark"

        # 7. Test 3D tlačítka výstupu (hover po spuštění = '■  UKONČIT VÝSTUP', Fištrón praští do tlačítka)
        assert app.btn_play_output.current_label == "▶  SPUSTIT ŽIVÝ VÝSTUP"
        app.btn_play_output._on_enter(None)  # type: ignore[arg-type]
        app._step_scene_and_fistron(0.05)
        assert app.fistron.state == "button_ready"

        assert app.on_smash_play_button() is None
        assert app.output_window is None
        assert app.fistron.state == "button_windup"
        assert app.fistron.x == app._button_center_on_scene()[0]
        app._step_scene_and_fistron(0.40)
        assert app.fistron.state == "button_smash"
        assert any(p.kind == "dust" for p in app.fistron.particles)
        assert len(app.fistron.particles) > 5
        deadline = time.perf_counter() + 1.0
        while app.output_window is None and time.perf_counter() < deadline:
            root.update()
            time.sleep(0.01)
        out_win = app.output_window
        assert out_win is not None

        # Když je výstup spuštěný a myš je nad tlačítkem, nápis je '■  UKONČIT VÝSTUP'
        assert app.btn_play_output.current_label == "■  UKONČIT VÝSTUP"
        app.btn_play_output._on_leave(None)  # type: ignore[arg-type]
        assert app.btn_play_output.current_label == "●  ŽIVÝ VÝSTUP AKTIVNÍ"

        root.update_idletasks()
        root.update()
        out_win.render_tick(100.0, 16.0)
        assert out_win.window.winfo_exists()
        assert out_win.is_fullscreen is False

        out_win.enter_fullscreen()
        root.update_idletasks()
        assert out_win.is_fullscreen is True
        assert bool(out_win.window.overrideredirect()) is True

        out_win.exit_fullscreen()
        root.update_idletasks()
        assert out_win.is_fullscreen is False
        assert bool(out_win.window.overrideredirect()) is False

        # Opětovné kliknutí na 3D tlačítko výstup ukončí
        res = app.on_smash_play_button()
        assert res is None
        assert app.output_window is not None
        deadline = time.perf_counter() + 1.0
        while app.output_window is not None and time.perf_counter() < deadline:
            root.update()
            time.sleep(0.01)
        assert app.output_window is None
    finally:
        app.shutdown()


def test_performance_ram_and_frame_time() -> None:
    """Změří spotřebu RAM a rychlost vykreslování snímků pro zajištění plynulého chodu."""
    proc = psutil.Process()
    engine = AbstractViewEngine((960, 720))
    try:
        settings = AppSettings(
            active_effect="rings",
            shape_size=40,
            orbit_speed=60,
            pattern_style="spiral",
        )
        # Zahřátí cache
        engine.render_step(settings, 0.0, 16.0)

        t0 = time.perf_counter()
        frames = 30
        for i in range(frames):
            engine.render_step(settings, i * 16.6, 16.6)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        avg_frame_ms = elapsed_ms / frames
        ram_mb = proc.memory_info().rss / (1024 * 1024)

        assert len(PRESET_COLORS) >= 10
        assert len(discover_camera_ports(max_ports=1)) >= 1
        # Průměrná doba vykreslení snímku musí být hluboko pod 25 ms a RAM pod 600 MB
        assert avg_frame_ms < 25.0
        assert ram_mb < 600.0
    finally:
        engine.close()
