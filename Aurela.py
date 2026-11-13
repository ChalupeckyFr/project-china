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
# Okno opravdu otevře a nechá ho otevřené, dokud ho člověk nezavře křížkem.
# Bez tohoto řádku by program skončil dřív, než by bylo okno vidět.
window.mainloop()
