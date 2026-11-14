"""Každé pořadí klikání na PWR, Mode, EFF a kolečko nechá kolečko dál fungovat."""

import itertools
import tempfile
from pathlib import Path

import emulate as app

app.STATE_PATH = Path(tempfile.gettempdir()) / "emulate-test-stav.json"
# Okno musí být nakreslené, jinak Tk událost kolečka myši zahodí. Na obrazovce není vidět.
app.window.attributes("-alpha", 0.0)
app.window.geometry("960x600+-3200+-3200")
app.window.update()


def cancel_spin():
    if app.spin_job is not None:
        app.window.after_cancel(app.spin_job)
        app.spin_job = None


def flush():
    cancel_spin()
    for _ in range(40):
        if app.level == app.target_level:
            break
        app.spin_toward_target()
        cancel_spin()


def reset():
    cancel_spin()
    app.powered = False
    app.mode_index = 0
    app.effect_index = 0
    app.level = 50
    app.target_level = 50
    app.hover_knob = False
    app.show_state()


def wheel(delta, over=True):
    # over říká, jestli kurzor leží na kolečku. Skutečnou myš test neposouvá.
    app.hover_knob = over
    original = app.cursor_over_knob
    app.cursor_over_knob = lambda: over
    try:
        widget = app.window.focus_get() or app.window
        widget.event_generate("<MouseWheel>", delta=delta, when="now")
    finally:
        app.cursor_over_knob = original


def click(name):
    button = {"pwr": app.pwr_button, "mode": app.mode_button, "eff": app.effect_button}[name]
    if str(button.cget("state")) != "disabled":
        button.focus_set()
    button.invoke()


def test_font_stays_on_aurela_not_emulate():
    aurela = Path("Aurela.py").read_text(encoding="utf-8")
    emulator = Path("emulate.py").read_text(encoding="utf-8")
    assert '("Oswald", 18, "bold")' in aurela
    assert "BBH Bogle" not in aurela
    assert "BBH Bogle" not in emulator
    assert app.pwr_button.cget("font") == "{Segoe UI} 36"


def test_wheel_reaches_the_handler_from_every_focused_widget():
    reset()
    click("pwr")
    assert "<MouseWheel>" in app.window.bind_all()
    for widget in (app.pwr_button, app.mode_button, app.effect_button, app.knob, app.window):
        widget.focus_set()
        before = app.target_level
        wheel(120, over=True)
        assert app.target_level == min(100, before + 5)
        flush()
    # Vypnutí a znovu zapnutí nesmí kolečko umlčet, ani když fokus zůstal na Mode.
    click("mode")
    click("pwr")
    click("pwr")
    app.mode_button.focus_set()
    before = app.target_level
    wheel(120, over=True)
    assert app.target_level == min(100, before + 5)
    flush()


def test_entering_the_knob_after_a_button_makes_the_wheel_work():
    # Kurzor v testu na kolečku neleží. Stačí najetí, stejně jako když člověk přejede myší.
    reset()
    click("pwr")
    buttons = {"pwr": app.pwr_button, "mode": app.mode_button, "eff": app.effect_button}
    for name in ("pwr", "mode", "eff"):
        click(name)
        if not app.powered:
            click("pwr")
        button = buttons[name]
        button.focus_set()
        before = app.target_level
        app.remember_knob_hover()
        button.event_generate("<MouseWheel>", delta=120, when="now")
        assert app.target_level == min(100, before + 5)
        flush()
        app.forget_knob_hover()
        before = app.target_level
        app.knob.focus_set()
        app.knob.event_generate("<MouseWheel>", delta=120, when="now")
        assert app.target_level == min(100, before + 5)
        flush()


def test_every_short_click_order_keeps_the_knob_working():
    actions = ("pwr", "mode", "eff", "up", "down")
    for sequence in itertools.product(actions, repeat=3):
        reset()
        for action in sequence:
            if action == "pwr":
                click("pwr")
            elif action == "mode":
                before = app.mode_index
                was_on = app.powered
                click("mode")
                expected = (before + 1) % len(app.MODES) if was_on else before
                assert app.mode_index == expected
            elif action == "eff":
                before = app.effect_index
                was_on = app.powered
                click("eff")
                expected = (before + 1) % len(app.EFFECTS) if was_on else before
                assert app.effect_index == expected
            else:
                app.hover_knob = True
                before = app.target_level
                wheel(120 if action == "up" else -120)
                if app.powered:
                    assert app.target_level == min(100, max(0, before + (5 if action == "up" else -5)))
                else:
                    assert app.target_level == before
        flush()
        app.hover_knob = True
        if app.powered:
            start = app.level
            wheel(120)
            flush()
            assert app.level == min(100, start + 5)
        else:
            frozen = app.level
            wheel(120)
            flush()
            assert app.level == frozen
        frozen = app.level
        wheel(120, over=False)
        flush()
        assert app.level == frozen
        assert app.mode_button.cget("state") == ("normal" if app.powered else "disabled")
        assert app.effect_button.cget("state") == ("normal" if app.powered else "disabled")
