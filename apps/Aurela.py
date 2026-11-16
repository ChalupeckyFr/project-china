# Přiveze hotovou součást Pythonu, která umí nakreslit okno. Nemusí se instalovat zvlášť.
import json
import time
import tkinter as tk
from pathlib import Path

# Písmo rohu. Zúžené písmo, které umí háčky a čárky.
# Soubor je ve složce fonts, Windows ho dostane jen pro tento program.
FONT_FILE = Path(__file__).resolve().parent / "fonts" / "Oswald-Bold.ttf"
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    if FONT_FILE.exists():
        ctypes.windll.gdi32.AddFontResourceExW(str(FONT_FILE), 0x10, 0)
except Exception:
    pass

# Nápis v liště okna.
TITLE = "Aurela"
# Názvy podle pořadí ve stav.json. Co tu není, ukáže se jako unknown.
MODE_NAMES = (
    "Hvězdná obloha",
    "Vesmírná mlhovina",
)
EFFECT_NAMES = (
    "Síla gravitace",
    "Počet objektů",
    "Rychlost pohybu",
)
# Jak dlouho nápis zůstane v rohu, v sekundách.
SHOW_FOR = 2.5
STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "stav.json"
# Rozměr okna v pixelech, tedy v bodech na obrazovce.
# 960x600 znamená 960 bodů na šířku a 600 na výšku.
# Písmeno x uprostřed je součást zápisu, není to krát.
SIZE = "960x600"

# Okno vytvoří, ale ještě ho neukáže.
window = tk.Tk()
# Do lišty vloží název.
window.title(TITLE)
# Nastaví šířku a výšku.
window.geometry(SIZE)
# Plocha okna je černá. Alpha 1 znamená, že nikde neprosvítá plocha za oknem.
window.configure(bg="black")
window.attributes("-alpha", 1.0)
# True a True: šířku i výšku jde táhnout myší.
window.resizable(True, True)


def toggle_fullscreen(_event=None):
    # F11 schová lištu a roztáhne černou plochu na celou obrazovku. Druhé F11 vrátí okno.
    full = not window.attributes("-fullscreen")
    window.attributes("-fullscreen", full)
    window.configure(bg="black")


window.bind("<F11>", toggle_fullscreen)

def named(names, index):
    if isinstance(index, int) and 0 <= index < len(names):
        return names[index]
    return "unknown"


def read_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# Řádek v levém dolním rohu. Po zmizení módu se efekt sám posune doleva.
corner = tk.Frame(window, bg="black")
corner.place(relx=0, rely=1, x=18, y=-16, anchor="sw")
quiet = {"fg": "#c4c4c4", "bg": "black", "font": ("Oswald", 18, "bold")}
mode_label = tk.Label(corner, **quiet)
effect_label = tk.Label(corner, **quiet)
value_label = tk.Label(corner, **quiet)
mode_until = 0
effect_until = 0
last_state = None


def arrange_corner():
    now = time.monotonic()
    show_mode = now < mode_until
    show_effect = now < effect_until
    for label in (mode_label, effect_label, value_label):
        label.pack_forget()
    if show_mode:
        mode_label.pack(side="left", padx=(0, 16))
    if show_effect:
        effect_label.pack(side="left", padx=(0, 16))
    if show_mode or show_effect:
        value_label.pack(side="left")


def watch_state():
    # První přečtení si jen pamatuje. Nápis se objeví až při změně.
    global last_state, mode_until, effect_until
    state = read_state()
    now = time.monotonic()
    if state and state.get("powered"):
        mode = state.get("mode")
        effect = state.get("effect")
        value = state.get("value")
        if last_state is None:
            last_state = (mode, effect, value)
        elif (mode, effect, value) != last_state:
            mode_label.config(text=named(MODE_NAMES, mode))
            effect_label.config(text=named(EFFECT_NAMES, effect))
            value_label.config(text=str(value))
            if mode != last_state[0]:
                mode_until = now + SHOW_FOR
            if effect != last_state[1] or value != last_state[2]:
                effect_until = now + SHOW_FOR
            last_state = (mode, effect, value)
    else:
        mode_until = 0
        effect_until = 0
        if state:
            last_state = (state.get("mode"), state.get("effect"), state.get("value"))
    arrange_corner()
    window.after(50, watch_state)


watch_state()
# Okno opravdu otevře a nechá ho otevřené, dokud ho člověk nezavře křížkem.
# Bez tohoto řádku by program skončil dřív, než by bylo okno vidět.
if __name__ == "__main__":
    window.mainloop()
