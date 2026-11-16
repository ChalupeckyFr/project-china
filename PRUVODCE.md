# Project China

Tento projekt je primárně určen pro školní výstavní stánek na různých akcích. Návštěvník stoupne do vyznačeného místa, kamera vezme jeho tvar a projektor kolem něj ukáže obraz. Tenhle soubor je průvodce projektu: co už existuje a jak se co spouští.

## HW

Hardware použitý v tomto projektu:
 - Kamera:
 - RPi:
 - Output:

## Dva Python soubory

Celý projekt začínáme dvěma soubory, které jdou otevřít a přepisovat v editoru:

- `apps/emulate.py` je okno pomocí kterého budeme simulovat inputy které budou přicházet do RPi.
- `apps/Aurela.py` je okno samotné aplikace. Aurela je její název. Význam - světelný prstenec kolem člověka.

`apps/Aurela.py` otevře černé okno. V levém dolním rohu na chvíli ukáže název módu, efektu a hodnotu ze `data/stav.json`. `apps/emulate.py` má černou plochu, pevný rozměr, tlačítka PWR, Mode a EFF a kolečko hodnoty. Zůstane nad ostatními okny, i když se klikne jinam.

## Jak to spustit

1. Otevři `spustit.py`.
2. Vpravo nahoře klikni na trojúhelník **Run Python File**.
3. Otevřou se obě okna.

Stejnou věc udělá příkaz z kořene projektu.

```powershell
.\.venv\Scripts\python.exe spustit.py
```
