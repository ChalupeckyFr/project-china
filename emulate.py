# Přiveze hotovou součást Pythonu, která umí nakreslit okno. Nemusí se instalovat zvlášť.
import math
import tkinter as tk

# Nápis v liště. U Aurely je na tom místě "Aurela".
TITLE = "emulate"
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
# False a False: nejde měnit šířku ani výšku, okno zůstane pořád stejné.
window.resizable(False, False)
# Plocha okna je černá.
window.configure(bg="black")

# Názvy, které tlačítka střídají. Po posledním se vrací na první.
MODES = ("mód 1", "mód 2", "mód 3")
EFFECTS = ("efekt 1", "efekt 2", "efekt 3")
powered = False
mode_index = 0
effect_index = 0

# Bílý text uprostřed. Ukazuje, jestli je zapnuto a co je vybrané.
status = tk.Label(window, text="vypnuto", fg="white", bg="black", font=("Segoe UI", 18))
status.place(relx=0.5, rely=0.32, anchor="center")


def show_state():
    # Vypnuté okno nic nemění. Zapnuté ukáže mód, efekt a hodnotu kolečka.
    if powered:
        status.config(text=f"{MODES[mode_index]}    {EFFECTS[effect_index]}    {level}")
        mode_button.config(state="normal")
        effect_button.config(state="normal")
    else:
        status.config(text="vypnuto")
        mode_button.config(state="disabled")
        effect_button.config(state="disabled")
    draw_knob()


def toggle_power():
    global powered
    powered = not powered
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


def draw_knob():
    # Čárka na obvodu ukazuje, jak je kolečko otočené.
    knob.delete("all")
    color = "white" if powered else "#666666"
    knob.create_oval(16, 16, 104, 104, fill="#222222", outline=color, width=3)
    angle = math.radians(-140 + (level / 100) * 280)
    knob.create_line(
        60,
        60,
        60 + 36 * math.sin(angle),
        60 - 36 * math.cos(angle),
        fill=color,
        width=4,
    )


def on_wheel(event):
    # Kolečko myši platí jen nad tímto kolečkem a jen když je zapnuto.
    global level
    if not powered or event.delta == 0:
        return
    step = 5 if event.delta > 0 else -5
    level = min(100, max(0, level + step))
    show_state()


# PWR je zásuvka: jedno kliknutí zapne, druhé vypne.
pwr_button = tk.Button(window, text="PWR", width=10, command=toggle_power)
pwr_button.place(relx=0.28, rely=0.52, anchor="center")
mode_button = tk.Button(window, text="Mode", width=10, command=next_mode)
mode_button.place(relx=0.5, rely=0.52, anchor="center")
effect_button = tk.Button(window, text="EFF", width=10, command=next_effect)
effect_button.place(relx=0.72, rely=0.52, anchor="center")

# Kulaté kolečko. Hodnota 0 až 100 se mění kolečkem myši, když je kurzor nad ním.
level = 50
knob = tk.Canvas(window, width=120, height=120, bg="black", highlightthickness=0)
knob.place(relx=0.5, rely=0.74, anchor="center")
knob.bind("<MouseWheel>", on_wheel)
show_state()

# Okno opravdu otevře a nechá ho otevřené, dokud ho člověk nezavře křížkem.
# Bez tohoto řádku by program skončil dřív, než by bylo okno vidět.
window.mainloop()