# Přiveze hotovou součást Pythonu, která umí nakreslit okno. Nemusí se instalovat zvlášť.
import tkinter as tk

# Nápis v liště okna.
TITLE = "Aurela"
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
# Okno opravdu otevře a nechá ho otevřené, dokud ho člověk nezavře křížkem.
# Bez tohoto řádku by program skončil dřív, než by bylo okno vidět.
window.mainloop()
