# Project China

Výstavní stand. Návštěvník stoupne do vyznačeného místa, kamera vezme jeho tvar a projektor kolem něj ukáže obraz. Tenhle soubor je příběh projektu: co už existuje a jak se to spouští. Po přečtení tohoto souboru by každý měl vědět jak vlastně software funguje a měl by mít dostatečné informace k popsání projektu vlastnímy slovy.

## Dva Python soubory

Celý projekt začínáme dvěma soubory, které jdou otevřít a přepisovat v editoru:

- `emulate.py` je okno pomocí kterého budeme simulovat inputy které budou přicházet do RPi.
- `Aurela.py` je okno samotné aplikace. Aurela je její název. Význam - světelný prstenec kolem člověka.

`Aurela.py` otevře prázdné okno. `emulate.py` má černou plochu, pevný rozměr, tlačítka PWR, Mode a EFF a kolečko hodnoty.

## Co v nich je

`Aurela.py` má jen nastavení obrazovky. Žádné tlačítko, žádný obraz, žádná kamera.

```python
# Přiveze hotovou součást Pythonu, která umí nakreslit okno. Nemusí se instalovat zvlášť.
import tkinter as tk

# Nápis v liště.
TITLE = "emulate"
# Rozměr okna v pixelech.
# Písmeno x je součást zápisu.
SIZE = "960x600"

# Okno vytvoří, ale ještě ho neukáže.
window = tk.Tk()
# Do lišty vloží název.
window.title(TITLE)
# Nastaví šířku a výšku.
window.geometry(SIZE)
# Okno otevře.
# Bez tohoto řádku by program skončil dřív, než by bylo okno vidět.
window.mainloop()
```

`emulate.py` začíná stejně a před otevřením okna přidá:

```python
# Nedá se měnit šířka ani výška.
window.resizable(False, False)
# Plocha okna je černá.
window.configure(bg="black")
# PWR zapne a vypne. Mode a EFF střídají název.
pwr_button = tk.Button(window, text="PWR", command=toggle_power)
mode_button = tk.Button(window, text="Mode", command=next_mode)
effect_button = tk.Button(window, text="EFF", command=next_effect)
# Kolečko. Kolečko myši nad ním mění číslo od 0 do 100.
knob = tk.Canvas(window, width=120, height=120)
```

## Jak to spustit

1. Otevři `emulate.py` nebo `Aurela.py`.
2. Vpravo nahoře klikni na trojúhelník **Run Python File**.
3. Otevře se okno. Zavře se křížkem.

Když šipka není vidět, stejnou věc udělá příkaz z kořene projektu. Pro emulační okno:

```powershell
.\.venv\Scripts\python.exe emulate.py
```

Pro aplikaci:

```powershell
.\.venv\Scripts\python.exe Aurela.py
```

`.venv` je připravený Python tohoto projektu. Má v sobě knihovnu pro okno, proto se používá tenhle, ne první Python, který Windows najde.
