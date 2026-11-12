# Project China

Výstavní stand. Návštěvník stoupne do vyznačeného místa, kamera vezme jeho tvar, Raspberry Pi kolem něj spočítá efekt a projektor ho ukáže na plátno.

Teď ten stand běží jako simulátor na notebooku. Krabice, kabely, LED, tlačítka i projektor jsou nakreslené v okně. Skutečné Raspberry Pi 4B (4 GB) přijde ve chvíli, kdy ho budeme mít v ruce. Složka `demo/` je dřívější ukázka a dál se nemění.

## Složky

```
project-china/
├── Spustit stand.bat     ← dvojklik spustí simulátor
├── PRUVODCE.md           ← tento soubor
├── demo/                 ← dřívější ukázka, neměníme ji
└── stand/
    ├── app/              ← okno: krabice, kabely, plátno, monitoring
    ├── core/             ← video, efekty, měření výkonu
    ├── hardware/         ← stavy krabičky (kabely, LED, tlačítka)
    ├── tests/            ← automatické kontroly
    └── logs/             ← vznikne po běhu, poslední kliky
```

`app` kreslí. `hardware` si pamatuje, co je zapojené. `core` později spočítá obraz. Díky tomu půjde myš v simulátoru vyměnit za skutečná tlačítka na Pinech Raspberry Pi a kreslení místnosti zůstane jen u notebooku.

## Pojmy

| Pojem | Význam |
| --- | --- |
| ToF kamera | U každého bodu obrazu řekne vzdálenost, ne jen barvu. |
| Hloubková mapa | Tabulka vzdáleností. V demu leží v souboru CSV. |
| Silueta | Místa, kde program vidí člověka. |
| Efekt | Kresba kolem člověka: hvězdy, mlha nebo prstence. |
| LED | Červená znamená, že zařízení chybí. Zelená, že je připojené. |
| Potenciometr | Kolečko, kterým se mění jedna hodnota, třeba počet hvězd. |
| Soft vypnutí | Raspberry Pi dostane pokyn „vypni se“ a teprve potom ztratí proud. |
| FPS | Kolik obrázků za sekundu program stíhá. |
| GPIO | Kontakty na Raspberry Pi pro tlačítka, LED a potenciometr. |

## Spuštění

V Průzkumníku otevři složku projektu a dvakrát klikni na `Spustit stand.vbs`. Otevře se jen oranžové okno, bez černé konzole. `Spustit stand.bat` udělá totéž, ale Windows u každého `.bat` na okamžik ukáže černé okno. Ani jeden soubor nespouštěj napsáním do PowerShellu.

Když se okno neobjeví, stejný Python vypíše důvod:

```powershell
.\.venv\Scripts\python.exe -m stand.app.main
```

## Jak se simulátor používá

1. Mezi zásuvkou a Pi leží srolovaný bílý kabel. Klik na **zásuvku** ho dá pod proud, na volném konci jsou jiskry. Klik na port **napájení** konektor zasune. Boot začne až ve chvíli, kdy konektor vizuálně sedí v portu.
2. Černý kabel kamery i projektoru je u zařízení pořád. Klik na port na Pi zasune druhý konec.
3. Najetím na kameru se objeví **Import**. Tlačítko zůstane, i když z kamery sjedeš přímo na něj.
4. **Mód +** a **Mód −** mění efekt. **Volba** vybere hodnotu. Kulatý potenciometr se otáčí podržením levého tlačítka: myš nahoru točí doprava, dolů doleva.
5. **Vypnout** je bezpečné vypnutí, kabely zůstanou. Vytažení napájení za běhu nechá na plátně ❌ a kamera s projektorem se samy neodpojí.
6. Dole je notebook. Monitoring na jeho displeji se ukáže po zapojení **debug** portu.

Plátno je schválně černé. Projektor při zapojení svítí kuželem na jeho horní hranu. Efekty v `stand/core/effects.py` už mají první výpočet, na plátno je pustíme, až budou vypadat dobře.

## Funkce v kódu

### Krabice si pamatuje kabely a LED

`BoxState` v `stand/hardware/state.py` je celá krabice v paměti. Po změně kabelu se LED přepočítají:

```python
if self.boot in (BootPhase.BOOTING, BootPhase.RUNNING):
    self.camera_led = (
        LedState.READY if self.camera_cable else LedState.WAITING
    )
    self.projector_led = (
        LedState.READY if self.projector_cable else LedState.WAITING
    )
```

`WAITING` je červená, `READY` zelená. Stejná funkce poběží i na Raspberry Pi, jen místo myši přijde signál z pinu.

Tlačítko **Volba** posune, který parametr potenciometr mění, a na tři a půl sekundy ukáže nápis:

```python
def cycle_param(self, now_ms: int, show_ms: int = 3500) -> str:
    self.param_index = (self.param_index + 1) % len(ADJUSTABLE_PARAMS)
    self.show_param_label = True
    self.param_label_until_ms = now_ms + show_ms
    return self.current_param_key
```

Parametry jsou `gravitace_obrysu`, `pocet_hvezd`, `rychlost_hvezd` a `jas_efektu`. Hodnota je vždy číslo od 0 do 1.

### Klikací zóna kamery nesmí ztratit Import

V `stand/app/scene.py` je kamera i tlačítko Import jeden obdélník. Kurzor může sjet z kamery na tlačítko a tlačítko nezmizí:

```python
def pointer_over_camera(self, pos: tuple[int, int]) -> bool:
    return self.camera.union(self.import_btn).inflate(8, 10).collidepoint(pos)
```

Kabely se skládají z hladké křivky a na plátno nesmí vstoupit. `curve` body spojí, `trim` z nich nechá jen tolik, kolik kabelu už „přijelo“:

```python
shown = drawkit.trim(paths[key], amount)
drawkit.cable(surface, shown, color, width=16)
```

`drawkit.cable` nakreslí tři čáry přes sebe: tmavou, barevnou a tenký světlý pruh. Tím kabel vypadá kulatě, ale zůstává to obyčejná čára.

### Video se načte a ověří

`VideoInputSource.read` v `stand/core/input_source.py` vezme další snímek. Když video skončí, vrátí se na začátek. Z rozdílu proti pozadí vznikne maska člověka:

```python
diff = cv2.absdiff(gray, cv2.convertScaleAbs(self._bg))
_, mask = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)
```

`mask` je černobílý obrázek. Bílá místa bereme jako postavu. Simulátor snímek přečte, aby šlo video zkontrolovat, a výsledek zatím nepošle na plátno.

### Měření výkonu

`PerfMonitor.tick` v `stand/core/perf.py` po každém snímku spočítá FPS a přečte CPU a RAM. `SessionLog.add` si pamatuje větu o kliku, třeba `Kamera připojena`. Po zavření okna se log uloží do `stand/logs/last_session.txt`.

## Kamera

Na Raspberry Pi počítáme s hloubkovou ToF kamerou. Z tipů, které máme, tomu odpovídá Arducam ToF: malý obraz 240×180 a vzdálenost v milimetrech. Arducam 5MP PTZ je běžná barevná kamera. MaixCAM2 je kamera s rozpoznáváním obrazu. V simulátoru se místo kamery vybírá obyčejné video.

## Na Raspberry Pi

Po zapojení proudu se systém sám spustí, otevře celou obrazovku a podle posledního nastavení začne kreslit. Dvě tlačítka, nebo jeden potenciometr, přepnou mód. Další tlačítko ukáže název nastavované hodnoty a potenciometr změní číslo. Dvě LED hlídají kameru a projektor. Poslední tlačítko Raspberry Pi bezpečně vypne. Krabička bude mít napájení, HDMI, konektor kamery a debug výstup pro připojení z notebooku.
