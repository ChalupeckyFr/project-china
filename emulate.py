# Přiveze hotovou součást Pythonu, která umí nakreslit okno. Nemusí se instalovat zvlášť.
import json
import math
import time
import tkinter as tk
from pathlib import Path

import numpy as np

# Bez toho Windows okno roztáhne a písmo i kolečko jsou kostrbaté.
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Nápis v liště. U Aurely je na tom místě "Aurela".
TITLE = "emulate"
# Rozměr okna v pixelech, tedy v bodech na obrazovce.
# 960x600 znamená 960 bodů na šířku a 600 na výšku.
# Písmeno x uprostřed je součást zápisu, není to krát.
SIZE = "960x600"

# Vzhled tlačítek. Barva a písmo se mění jen v tomhle bloku.
FONT = ("Segoe UI", 36)
WINDOW_BG = "#101010"
LOOK = {
    "PWR": {"bg": "#3c2a22", "fg": "#f7efe8", "activebackground": "#5c4034"},
    "Mode": {"bg": "#262626", "fg": "#f4f4f4", "activebackground": "#3d3d3d"},
    "EFF": {"bg": "#1c2830", "fg": "#e7eef3", "activebackground": "#2d4250"},
}

# Okno vytvoří, ale ještě ho neukáže.
window = tk.Tk()
# Do lišty vloží název.
window.title(TITLE)
# Nastaví šířku a výšku.
window.geometry(SIZE)
# False a False: nejde měnit šířku ani výšku, okno zůstane pořád stejné.
window.resizable(False, False)
# Plocha okna je černá.
window.configure(bg=WINDOW_BG)

# Názvy, které tlačítka střídají. Po posledním se vrací na první.
MODES = ("mód 1", "mód 2", "mód 3")
EFFECTS = ("efekt 1", "efekt 2", "efekt 3")
powered = False
mode_index = 0
effect_index = 0
# Soubor vedle tohoto programu. Aurela si z něj čte stejné čtyři údaje.
STATE_PATH = Path(__file__).resolve().parent / "stav.json"

def write_state():
    # Čtyři údaje jdou rovnou do souboru. Když ho zrovna čte Aurela, zápis se zopakuje.
    payload = {
        "powered": powered,
        "mode": mode_index,
        "effect": effect_index,
        "value": level,
    }
    text = json.dumps(payload)
    for attempt in range(8):
        try:
            STATE_PATH.write_text(text, encoding="utf-8")
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.01)

def show_state():
    # Vypnuté okno nic nemění. Zapnuté jen odemkne Mode, EFF a kolečko.
    write_state()
    if powered:
        mode_button.config(state="normal")
        effect_button.config(state="normal")
    else:
        mode_button.config(state="disabled")
        effect_button.config(state="disabled")
    draw_knob()


def toggle_power():
    global powered, target_level
    powered = not powered
    if not powered:
        target_level = level
    show_state()


def next_mode():
    global mode_index
    if not powered:
        return
    mode_index = (mode_index + 1) % len(MODES)
    show_state()


def next_effect():
    global effect_index
    if not powered:
        return
    effect_index = (effect_index + 1) % len(EFFECTS)
    show_state()


def render_knob(value, is_on):
    # Jeden hotový obrázek kolečka. Hrana se kreslí větší a pak zmenší.
    size = 168
    scale = 4
    n = size * scale
    y, x = np.ogrid[0:n, 0:n]
    center = (n - 1) / 2
    dist = np.sqrt((x - center) ** 2 + (y - center) ** 2)
    radius = n * 0.36
    edge = scale * 1.4

    def cover(distance):
        return np.clip(0.5 + distance / edge, 0, 1)

    body = cover(radius - dist) * cover(dist - radius * 0.55)
    angle = math.radians(-140 + (value / 100) * 280)
    end_x = center + math.sin(angle) * radius * 0.72
    end_y = center - math.cos(angle) * radius * 0.72
    vx = end_x - center
    vy = end_y - center
    length = vx * vx + vy * vy
    along = np.clip(((x - center) * vx + (y - center) * vy) / length, 0, 1)
    line = np.sqrt((x - (center + along * vx)) ** 2 + (y - (center + along * vy)) ** 2)
    mark = cover(scale * 2.4 - line) * cover(radius * 0.85 - dist)
    ring = cover(radius - dist) * cover(dist - (radius - scale * 3))
    ink = np.array([247, 239, 232] if is_on else [110, 110, 110], dtype=np.float32)
    fill = np.array([34, 30, 28], dtype=np.float32)
    bg = np.array([16, 16, 16], dtype=np.float32)
    rgb = bg + (fill - bg) * body[..., None]
    rgb = rgb * (1 - ring)[..., None] + ink * ring[..., None]
    rgb = rgb * (1 - mark)[..., None] + ink * mark[..., None]
    small = rgb.reshape(size, scale, size, scale, 3).mean(axis=(1, 3))
    data = np.clip(small, 0, 255).astype(np.uint8)
    ppm = f"P6 {size} {size} 255\n".encode() + data.tobytes()
    return tk.PhotoImage(data=ppm, format="ppm")


def prepare_knob():
    # 21 obrázků pro hodnoty 0, 5, 10, ... 100. Při točení se už jen vyměňují.
    global knob_on, knob_off
    knob_on = [render_knob(value, True) for value in range(0, 101, 5)]
    knob_off = [render_knob(value, False) for value in range(0, 101, 5)]


def draw_knob():
    pictures = knob_on if powered else knob_off
    picture = pictures[level // 5]
    knob.delete("all")
    knob.create_image(84, 84, image=picture)
    knob.image = picture


def remember_knob_hover(_event=None):
    # Najetí myší si pamatujeme. Kolečko pak samo převezme fokus.
    # Ve Windows jde kolečko myši do toho, co má fokus, ne pod kurzor.
    global hover_knob
    hover_knob = True
    knob.focus_set()


def forget_knob_hover(_event=None):
    global hover_knob
    hover_knob = False


def cursor_over_knob():
    # Pozice kurzoru vůči kolečku. Nezávisí na tom, které tlačítko má fokus.
    try:
        px, py = knob.winfo_pointerxy()
        x, y = knob.winfo_rootx(), knob.winfo_rooty()
        width, height = knob.winfo_width(), knob.winfo_height()
    except tk.TclError:
        return False
    return width > 1 and x <= px < x + width and y <= py < y + height


def on_wheel(event):
    # Kolečko myši jen posune cíl. Kreslení běží samo, po jednom kroku.
    global target_level, spin_job
    widget = getattr(event, "widget", None)
    over = hover_knob or widget is knob or cursor_over_knob()
    if not powered or getattr(event, "delta", 0) == 0 or not over:
        return
    step = 5 if event.delta > 0 else -5
    target_level = min(100, max(0, target_level + step))
    if spin_job is None:
        spin_job = window.after(16, spin_toward_target)


def spin_toward_target():
    # Jeden krok o 5 a pak krátká pauza. Rychlé točení se nesloží do jedné fronty.
    global level, spin_job
    spin_job = None
    if not powered or level == target_level:
        return
    level += 5 if target_level > level else -5
    try:
        show_state()
    finally:
        if powered and level != target_level:
            spin_job = window.after(16, spin_toward_target)


def make_button(name, command):
    # Vezme barvy z LOOK a přidá společné písmo. relief flat je jen plná barva, bez stínu.
    return tk.Button(
        window,
        text=name,
        command=command,
        font=FONT,
        relief="flat",
        borderwidth=0,
        highlightthickness=0,
        disabledforeground="#6e6e6e",
        **LOOK[name],
    )


# Tři tlačítka vyplní okno. Dole zůstane pruh na kolečko, jinak by na něj nešlo najet.
window.rowconfigure(0, weight=1)
window.rowconfigure(1, minsize=200)
window.columnconfigure(0, weight=1)
window.columnconfigure(1, weight=1)
window.columnconfigure(2, weight=1)

# PWR je zásuvka: jedno kliknutí zapne, druhé vypne.
pwr_button = make_button("PWR", toggle_power)
pwr_button.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
mode_button = make_button("Mode", next_mode)
mode_button.grid(row=0, column=1, sticky="nsew", padx=3)
effect_button = make_button("EFF", next_effect)
effect_button.grid(row=0, column=2, sticky="nsew", padx=(3, 0))

# Kulaté kolečko. Hodnota 0 až 100 se mění kolečkem myši, když je kurzor nad ním.
level = 50
target_level = 50
spin_job = None
prepare_knob()
knob_band = tk.Frame(window, bg=WINDOW_BG)
knob_band.grid(row=1, column=0, columnspan=3, sticky="nsew")
knob = tk.Canvas(knob_band, width=168, height=168, bg=WINDOW_BG, highlightthickness=0)
knob.place(relx=0.5, rely=0.5, anchor="center")
hover_knob = False
knob.bind("<Enter>", remember_knob_hover)
knob.bind("<Leave>", forget_knob_hover)
# Jedno poslouchání na celé okno. Po kliknutí na PWR, Mode i EFF kolečko myši pořád dojde sem.
window.bind_all("<MouseWheel>", on_wheel)
show_state()

# Okno opravdu otevře a nechá ho otevřené, dokud ho člověk nezavře křížkem.
# Bez tohoto řádku by program skončil dřív, než by bylo okno vidět.
if __name__ == "__main__":
    window.mainloop()