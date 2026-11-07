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

import numpy as np
import psutil
import pygame

from abstractview_app.config import (
    ALL_EFFECT_KEYS,
    AppSettings,
    SettingsStore,
    ShuffleScheduler,
)
from abstractview_app.renderer import AbstractViewEngine
from abstractview_app.samples import (
    SAMPLE_POSES,
    discover_camera_ports,
    export_sample_csv,
    get_sample_sequence,
    render_sample_thumbnail_ppm,
)
from abstractview_app.theme import DARK_PALETTE, LIGHT_PALETTE, PRESET_COLORS
from abstractview_app.ui import AbstractViewApp


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

    # Změna nastavení uživatelem a uložení
    s.theme_mode = "light"
    s.gravity = 85
    s.shuffle_interval_s = 120
    s.shuffle_order = "random"
    s.orbit_speed = 65
    s.shape_size = 75
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

    # Reset vrátí vše na první hodnotu
    reset_s = store.reset_to_defaults()
    assert reset_s.theme_mode == "dark"
    assert reset_s.gravity == 20
    assert reset_s.shuffle_interval_s == 60
    assert reset_s.shuffle_transition_s == 1.0
    assert reset_s.shuffle_order == "normal"
    assert reset_s.orbit_speed == 0


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

    csv_file = export_sample_csv("pose_spread", tmp_path / "sample.csv")
    assert csv_file.exists()


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
    """Ověří objektový efekt 'Prstence tvarů', velikost vs počet, vzory a Graffiti."""
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
    """Ověří dynamickou responzivitu okna při zvětšení/zmenšení, přepínání light/dark
    témat, dialogy a samostatné okno výstupu s fullscreenem."""
    store = SettingsStore(tmp_path / "ui_settings.json")
    root = tk.Tk()
    app = AbstractViewApp(root=root, store=store)
    try:
        root.update_idletasks()
        root.update()

        # 1. Test přepínání témat (dark = tmavě modrá, light = béžová)
        assert app.settings.theme_mode == "dark"
        assert app.palette == DARK_PALETTE
        app.toggle_theme()
        root.update_idletasks()
        assert app.settings.theme_mode == "light"
        assert app.palette == LIGHT_PALETTE
        assert root.cget("bg") == LIGHT_PALETTE.bg_primary

        # 2. Test dynamického rozložení při různých velikostech okna
        for w, h, expected_cols in (
            (580, 480, 1),  # Zmenšené okno -> 1 sloupec + scrollování
            (1150, 820, 2),  # Standardní okno -> 2 sloupce
            (1500, 960, 2),  # Velké okno -> 2 sloupce
        ):
            root.geometry(f"{w}x{h}")
            app._relayout_cards(w)
            root.update_idletasks()
            root.update()
            assert app._current_columns == expected_cols
            bbox = app.scroll_canvas.bbox("all")
            assert bbox is not None
            assert bbox[2] > 200 and bbox[3] > 200

        # 3. Test dialogů (Nahrát CSV, Vybrat kameru, Resetovat možnosti)
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
        app.confirm_reset(reset_dlg)
        assert app.settings.theme_mode == "dark"

        # 4. Test samostatného okna výstupu a přepnutí na fullscreen bez horní lišty
        out_win = app.open_output_window()
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
        out_win.close()
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
