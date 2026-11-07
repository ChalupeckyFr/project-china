# TASKS.md – úkoly projektu Project China

Jediný zdroj pravdy pro **úkoly, jejich závislosti, stav, ověření a důkazy**.
Pravidla stavů a vazeb viz [`AGENTS.md`](AGENTS.md), sekce 5,
pravidla důkazů viz [`AGENTS.md`](AGENTS.md), sekce 8.

## Pravidla evidence

- Nadpis záznamu je pouze ID (`## T-001`); název je v poli `Název`.
- Nové ID = nejvyšší existující + 1. ID nepřečíslovávej a nepoužívej znovu.
- Implementační úkol má vazbu na `AC-*`. Ostatní úkoly (průzkum, toolchain,
  proces) mají vazbu na `DEC-*` nebo explicitní zadání.
- Pořadí v souboru není závislost; závislosti jsou pouze v poli `Závislosti`.
- `dokonceno` vyžaduje vyplněné pole `Ověření` se skutečným výsledkem.
- Blokovaný úkol má důvod a podmínku odblokování; zrušený zachová důvod.

## Vzor záznamu (není úkol, nevyčerpává ID)

```markdown
## T-001

- Název: Stručný lidský název.
- Cíl: Pozorovatelný výsledek.
- Vazby: AC-xxx | DEC-xxx | explicitní zadání (odkaz).
- Rozsah: Co se mění; co je výslovně mimo úkol.
- Závislosti: T-xxx, nebo žádné.
- Riziko: Hlavní relevantní riziko.
- Hotovo když: Konkrétní podmínky dokončení.
- Ověření:
  - Plán: Jaké kontroly se provedou a jak.
  - Výsledek: (vyplnit po provedení) revize, příkaz/postup, výstup,
    prostředí, neprovedené kontroly, odchylky.
- Stav: nezahajeno
- Poznámky: (volitelné) důvod blokace/zrušení, odkaz na akceptaci.
```

## Záznamy

## T-001

- Název: Příprava projektové konfigurace
- Cíl: Připravit základ Python projektu podle schváleného návrhu bez instalace.
- Vazby: [DEC-002](DECISIONS.md#dec-002), [DEC-006](DECISIONS.md#dec-006).
- Rozsah: Založit minimální strukturu projektu a deklaraci schválených aplikačních a vývojových závislostí; popsat přípravu prostředí. Neinstalovat balíky ani nespouštět služby.
- Závislosti: žádné
- Riziko: Dostupnost a kompatibilita Pythonu i konkrétních verzí balíků nejsou zatím ověřeny.
- Hotovo když: Konfigurace odpovídá DEC-002 a DEC-006, neobsahuje tvrzení o neověřené instalaci a dokumentuje další bezpečný krok.
- Ověření:
  - Plán: Staticky projít vytvořenou konfiguraci a dokumentaci proti uvedeným rozhodnutím; dostupnost příkazů a případné neověřené části výslovně zaznamenat.
  - Výsledek: Proti revizi worktree `7d71824`: PowerShell statická kontrola potvrdila existenci `.gitignore`, `requirements.txt`, `requirements-dev.txt` a `src/project_china/__init__.py`, schválené názvy závislostí a upozornění na neprovedenou instalaci v README. `Get-Command` nalezl příkazy `python` a `py`; jejich verze, běh a dostupnost balíků nebyly ověřeny. Instalace ani testy neproběhly.
- Stav: dokonceno
- Poznámky: Tento úkol neuděluje oprávnění k instalaci.

## T-002

- Název: Příprava izolovaného prostředí
- Cíl: Po samostatném souhlasu připravit prostředí se schválenými závislostmi.
- Vazby: [DEC-002](DECISIONS.md#dec-002), [DEC-006](DECISIONS.md#dec-006).
- Rozsah: Ověřit dostupný Python a po výslovném oprávnění vytvořit izolované prostředí a nainstalovat deklarované závislosti. Neměnit globální prostředí ani neinstalovat další nástroje bez souhlasu.
- Závislosti: T-001
- Riziko: Chybějící Python, nekompatibilní balíky nebo nedostupná instalace.
- Hotovo když: Oprávnění je doloženo, prostředí obsahuje potřebné závislosti a jejich skutečná dostupnost byla ověřena.
- Ověření:
  - Plán: Po získání oprávnění ověřit importy a zaznamenat skutečné verze, prostředí, výstup i případná selhání.
  - Výsledek: Na Windows byl nejprve dostupný pouze CPython 3.14.7; instalace příkazem `$venvPython = (Resolve-Path '.venv\Scripts\python.exe').Path; & $venvPython -m pip install -r requirements-dev.txt` selhala při sestavování Pygame 2.6.1 chybou `ModuleNotFoundError: setuptools._distutils.msvccompiler`. Po výslovném souhlasu DEC-008 byl příkazem `winget install --id Python.Python.3.13 --exact --source winget --scope user --silent --accept-package-agreements --accept-source-agreements` nainstalován CPython 3.13.17 x64 od Python Software Foundation. Původní prostředí bylo zachováno jako `.venv-py314-failed`; nové `.venv` vytvořeno příkazem `py -3.13 -m venv .venv`. Instalace příkazem `$venvPython = (Resolve-Path '.venv\Scripts\python.exe').Path; & $venvPython -m pip install -r requirements-dev.txt` proběhla úspěšně. Importy `numpy`, `cv2`, `pygame` a `pytest` prošly; `.\.venv\Scripts\ruff.exe --version` potvrdil běh Ruff. Ověřené verze: Python 3.13.17, pip 26.2.2, numpy 2.5.4, opencv-python 5.0.0.93 (cv2 5.0.0), pygame 2.6.1, pytest 9.2.0 a ruff 0.17.4. Testy neběžely, jejich příprava je T-003.
- Stav: dokonceno
- Poznámky: Instalace byla provedena pouze v uživatelském rozsahu; závislosti ani jejich deklarace se neměnily.

## T-003

- Název: První testy a statická kontrola
- Cíl: Připravit spustitelné základní kontroly projektu bez CI a hooks.
- Vazby: [DEC-006](DECISIONS.md#dec-006).
- Rozsah: Nastavit pytest a Ruff a přidat smysluplnou základní kontrolu importu projektového balíčku.
- Závislosti: T-001, T-002
- Riziko: Nefunkční konfigurace nebo kontrola, která neověřuje žádný skutečný projektový kód.
- Hotovo když: Základní test i statická kontrola běží v připraveném prostředí a jejich výsledky jsou doloženy.
- Ověření:
  - Plán: Skutečně spustit nejmenší relevantní test a statickou kontrolu; zaznamenat příkazy, výstupy a prostředí.
  - Výsledek: V CPythonu 3.13.17 z `.venv` vytvořen `pyproject.toml` s konfigurací pytest (`testpaths = ["tests"]`, `pythonpath = ["src"]`) a Ruff (`target-version = "py313"`, délka řádku 88). Přidán test ověřující, že se balíček `project_china` importuje ze zdrojového stromu. Příkaz `& '.venv\Scripts\python.exe' -m pytest -q` skončil výstupem `1 passed in 0.01s`; `& '.venv\Scripts\ruff.exe' check src tests` skončil `All checks passed!`. CI ani hooks nebyly přidány.
- Stav: dokonceno
- Poznámky: Závisí na připraveném prostředí; CI ani hooks nejsou součástí úkolu.

## T-004

- Název: Časová posloupnost ze syntetického CSV
- Cíl: Načítat a ověřovat hloubkové snímky v dohodnutém formátu.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-001](SPEC.md#fr-001), [NFR-001](SPEC.md#nfr-001), [DEC-003](DECISIONS.md#dec-003).
- Rozsah: Implementovat zdroj snímků a validaci `frame,time_ms,x,y,depth`; připravit syntetický vstup ukazující pohyb. Nepřipojovat kameru ani nerozhodovat o uživatelském výběru souborů v Q-004.
- Závislosti: T-002, T-003
- Riziko: Chybné pořadí snímků, neúplná mřížka nebo tiché přijetí neplatných hodnot.
- Hotovo když: Platná posloupnost je dostupná v paměti ve správném čase a chybné řádky, duplicity, chybějící body a rozporné časy jsou výslovně oznámeny. Příklad 0–1500 není vynucen jako limit.
- Ověření:
  - Plán: Spustit cílené testy platných i neplatných CSV, časů a rozměrů; použít pouze syntetický vstup a ověřit, že se neukládají zpracovaná hloubková data.
  - Výsledek: V CPythonu 3.13.17 implementován `load_depth_csv` s návratem neměnné časové posloupnosti v paměti. Testy ověřují 2×2 pohybující se syntetickou mřížku včetně hodnoty 1750 (bez pevného limitu 0–1500), nezměněný vstup bez dalších výstupních souborů, záhlaví, neplatná čísla, rozměry, duplicity, chybějící body a rozporné či neklesající časy. `& '.venv\Scripts\python.exe' -m pytest -q` skončil `15 passed in 0.06s`; `& '.venv\Scripts\ruff.exe' check src tests` skončil `All checks passed!`. Vstup vzniká v dočasném adresáři testu; kamera, ukládání zpracovaných dat ani výběr souborů nebyly přidány.
- Stav: dokonceno
- Poznámky: Syntetické CSV je vstupní vzorek, nikoli uložený výstup nebo záznam kamery.

## T-005

- Název: Hloubková maska a obrysy
- Cíl: Z každého platného snímku získat obrysy oblastí v cílovém intervalu.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-001](SPEC.md#fr-001), [FR-002](SPEC.md#fr-002), [DEC-004](DECISIONS.md#dec-004).
- Rozsah: Implementovat práh 750–1000 včetně obou mezí a obrysy všech oddělených oblastí; snímek bez cíle je platný stav.
- Závislosti: T-002, T-003, T-004
- Riziko: Chyba na mezích intervalu, nesprávné souřadnice obrysu nebo ztráta oddělené oblasti.
- Hotovo když: Výběr i obrysy odpovídají DEC-004 a prázdný výběr není vydáván za chybný vstup.
- Ověření:
  - Plán: Spustit cílené testy hodnot 749, 750, 1000 a 1001, známých syntetických tvarů, více oblastí a prázdné masky.
  - Výsledek: V CPythonu 3.13.17 vytvořeno `select_depth_regions` nad NumPy/OpenCV; maska zahrnuje meze 750 i 1000 a obrysy zahrnují všechny oddělené popřední oblasti, včetně oblasti vnořené do díry. Testy pokrývají 749/750/1000/1001, čtyři oddělené oblasti a prázdný výběr. `& '.venv\Scripts\python.exe' -m pytest -q` skončil `19 passed in 0.16s`; `& '.venv\Scripts\ruff.exe' check src tests` skončil `All checks passed!`.
- Stav: dokonceno
- Poznámky: Rozpoznávání identity osoby ani produkční ToF vstup nejsou součástí úkolu.

## T-006

- Název: Minimální průchod demem
- Cíl: Propojit CSV, obrys a základní hvězdný výstup v lokálním okně.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-003](SPEC.md#fr-003), [FR-004](SPEC.md#fr-004), [DEC-002](DECISIONS.md#dec-002), [DEC-005](DECISIONS.md#dec-005).
- Rozsah: Přehrát syntetickou posloupnost v čase, promítnout obrys do okna a vykreslit základní hvězdné pozadí s hustší oblastí u obrysu. Chybný vstup oznámit; neukládat hloubkové výstupy.
- Závislosti: T-003, T-004, T-005
- Riziko: Nesoulad času, souřadnic CSV a vykreslení nebo skryté chyby při načítání.
- Hotovo když: Minimální propojený průchod funguje nad syntetickým vstupem a poskytuje pozorovatelný výstup. Úplné splnění AC-001 se v tomto úkolu nepředpokládá.
- Ověření:
  - Plán: Spustit cílenou integrační kontrolu a ověřit průchod jednou posloupností v lokálním okně; doložit prostředí, výstupy a neprovedené vizuální kontroly.
  - Výsledek: V CPythonu 3.13.17 propojeno načtení ukázkového CSV, časování snímků, výběr obrysů a kreslení hvězd do okna 960×720; cesta k CSV je povinný argument, bez výchozí volby souboru (Q-004 zůstává otevřená). Testy ověřují časový průchod, vykreslení pixelů, hlášení chybného CSV a běh s SDL dummy oknem; `& '.venv\Scripts\python.exe' -m pytest -q` skončil `23 passed in 0.62s`, Ruff `All checks passed!`. Nativní Pygame okno bylo spuštěno nad `examples/moving_object.csv`, mělo titulek `Project China - depth demo` a zavřelo se událostí QUIT. Testy neběží nad kamerou; úplná vizuální akceptace AC-001 zůstává neprovedená.
- Stav: dokonceno
- Poznámky: Kamera, síťová služba a tlačítkové přepínání nejsou součástí řezu.

## T-007

- Název: Dokončení animací a objektového prvku
- Cíl: Doplnit požadované chování hvězd a obrysový prvek s pevnou velikostí.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-005](SPEC.md#fr-005), [FR-006](SPEC.md#fr-006), [FR-008](SPEC.md#fr-008), [DEC-005](DECISIONS.md#dec-005).
- Rozsah: Doplnit plynulé následování a uvolnění obrysu, pohasínání a průlety hvězd i objektový prvek. Parametry zůstanou pevné; konkrétní vizuální hodnoty a výsledek se předloží člověku.
- Závislosti: T-003, T-005, T-006
- Riziko: Nevyhovující vizuální výsledek nebo výkon; konkrétní zařízení ani číselné cíle nebyly stanoveny.
- Hotovo když: Funkce odpovídají DEC-005, neexistuje nastavovací rozhraní a technické kontroly jsou doloženy; lidská produktová akceptace zůstává samostatná.
- Ověření:
  - Plán: Ověřit logiku s řízeným časem a náhodností, včetně pohybu a zmizení obrysu; zaznamenat provizorní hodnoty a omezení vizuálního hodnocení.
  - Výsledek: `StarEffect` používá pevné seedování 42 a řízené `delta_ms`; testy ověřují deterministické přitahování k pohyblivému cíli, postupné uvolnění po jeho zmizení, pohasínání a časování průletů. Pevné hodnoty: 72 částic, koeficient 0,08 na kroku 60 Hz, náběh 180 ms, uvolnění s časovou konstantou 700 ms, průlet každé 3 s po dobu 750 ms a poloměr objektového obrysu 12 px. Bez nastavovacího UI. `& '.venv\Scripts\python.exe' -m pytest -q` skončil `26 passed in 0.66s`; `& '.venv\Scripts\ruff.exe' check src tests` skončil `All checks passed!`. Vizuální kontrola v T-008 doplnila rovnoměrné vzorkování obvodu; lidské přijetí je zaznamenáno v [DEC-009](DECISIONS.md#dec-009).
- Stav: dokonceno
- Poznámky: Koeficient 0,08 a poloměr 12 px byly vizuálně přijaty v [DEC-009](DECISIONS.md#dec-009); kolečko a samostatný průlet byly později v demu odstraněny podle [DEC-012](DECISIONS.md#dec-012) a [DEC-013](DECISIONS.md#dec-013).

## T-008

- Název: Vizuální ověření a předání dema
- Cíl: Doložit AC-001 a předložit skutečný výsledek člověku.
- Vazby: [AC-001](SPEC.md#ac-001), [NFR-001](SPEC.md#nfr-001), [DEC-006](DECISIONS.md#dec-006).
- Rozsah: Ověřit hotový průchod nad syntetickou posloupností včetně pohybu cíle, vzhledu hvězd a neukládání hloubkových dat; předat výsledek k lidské akceptaci.
- Závislosti: T-006, T-007
- Riziko: Nedostupné zobrazovací prostředí nebo nevyhovující či dosud neodsouhlasený vizuální výsledek.
- Hotovo když: Existují skutečné důkazy o ověření, známé odchylky jsou zaznamenány a potřebná lidská akceptace je doložena.
- Ověření:
  - Plán: Spustit relevantní automatické kontroly a provést vizuální kontrolu AC-001 včetně příkladu zvedání rukou; zaznamenat revizi, prostředí, výsledky a odpověď člověka.
  - Výsledek: 6. 11. 2026 proběhlo přehrání v nativním okně Pygame 960×720 na CPythonu 3.13.17 a Pygame 2.6.1. Posloupnost tří syntetických snímků 24×32 (ruce dole, zvedání, ruce nahoře; časy 0/1800/3600 ms) byla vytvořena pouze v paměti. První kontrola ukázala shlukování částic na zjednodušených vrcholech obrysu; opraveno interpolací cílů po nejvýše 6 px a rovnoměrným rozdělením částic po obvodu. Opakované přehrání zachytilo stavy v 510/2306/4316 ms a okno se automaticky zavřelo. Náhled byl předložen jako artefakt `T-008-preview.png` a detail `T-008-raised-frame.png`. `& '.venv\Scripts\python.exe' -m pytest -q`: `28 passed in 0.64s`; `& '.venv\Scripts\ruff.exe' check src tests`: `All checks passed!`; `git diff --check` bez chyb. Ověření pokrývá syntetický tvar, nikoli kameru ani skutečný záznam člověka. Hloubková data nebyla zapsána. Člověk přijal vizuální výsledek a provizorní parametry dne 2026-11-06; schválení a otisky přesné pracovní revize jsou v [DEC-009](DECISIONS.md#dec-009).
- Stav: dokonceno
- Poznámky: Akceptace se vztahuje pouze na syntetické demo, ne na produkční kameru nebo hardware.

## T-009

- Název: Zobrazení cíle hvězdami bez obrysové čáry
- Cíl: Odstranit kreslený obrys postavy či objektu tak, aby jeho tvar naznačovaly hvězdy.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-004](SPEC.md#fr-004), [DEC-010](DECISIONS.md#dec-010).
- Rozsah: Obrys zachovat jako vstup pro cíle částic, ale nekreslit jeho čáru ani bod. Samostatný kruhový objektový prvek a parametry hvězd zůstávají beze změny.
- Závislosti: T-005, T-007, T-008
- Riziko: Tvar po odstranění čáry nemusí být dostatečně čitelný; nový vzhled vyžaduje lidské posouzení.
- Hotovo když: Obrys není přímo vykreslován, hvězdy se nadále přitahují k jeho bodům a technické kontroly projdou. Produktová akceptace změněného vzhledu je samostatná.
- Ověření:
  - Plán: Ověřit vícebodový i jednobodový obrys, skutečné vykreslení částic a zkontrolovat syntetický pohyb v obrazu.
  - Výsledek: Testy ověřují nepřítomnost přímé kresby obrysu při zachování kruhového prvku, předání bodů částicím a jejich vykreslení u obvodu. Snímky syntetické postavy 24×32 byly vykresleny mimo okno v časech 512/2304/4320 ms; náhled posloupnosti je `T-009-motion-preview.png` a detail `T-009-stars-only.png`. Ověřena pracovní kopie nad HEAD `553cc19` v CPythonu 3.13.17 a Pygame 2.6.1: `& '.venv\Scripts\python.exe' -m pytest -q` skončil `30 passed in 0.72s`, `& '.venv\Scripts\ruff.exe' check src tests` skončil `All checks passed!` a `git diff --check` bez chyb. Hloubková data zůstala v paměti. Nová vizuální podoba dosud nebyla člověkem přijata.
- Stav: dokonceno
- Poznámky: Samostatný kruhový prvek v této revizi zůstal zachován; později byl odstraněn v T-011. Rozhodnutí DEC-009 se týká předchozí revize.

## T-010

- Název: Třísekundové kroky a opakované přehrávání
- Cíl: Zpomalit kroky ukázkového objektu na 3 sekundy a opakovat posloupnost až do zavření dema.
- Vazby: [AC-001](SPEC.md#ac-001), [DEC-003](DECISIONS.md#dec-003), [DEC-011](DECISIONS.md#dec-011).
- Rozsah: Nastavit časy ukázkového CSV na 0/3000/6000 ms a přehrávat posloupnost ve smyčce. U jiných CSV zachovat jejich časy; poslední snímek podržet po dobu posledního časového odstupu. Jediný snímek zůstává zobrazený.
- Závislosti: T-004, T-006
- Riziko: Nesprávný interval při návratu na začátek, přerušení animací nebo nemožnost demo zavřít.
- Hotovo když: Ukázka mění snímky po 3 sekundách včetně návratu na začátek, smyčka pokračuje do uživatelského ukončení a testy pokrývají časové hranice i další typy posloupností.
- Ověření:
  - Plán: Ověřit hranice několika cyklů, nepravidelné a jednosnímkové CSV, nepřerušený čas animací, zavření okna a průchod skutečným časem s SDL dummy.
  - Výsledek: Automatické testy pokrývají kroky v časech 0/3000/6000/9000 ms, více cyklů, nepravidelné i desetinné časy, jediný snímek a ukončení událostí QUIT, klávesami Esc a q. Čas animací se při návratu na začátek nenuluje. V CPythonu 3.13.17 s Pygame 2.6.1 skončil `& '.venv\Scripts\python.exe' -m pytest -q` výsledkem `36 passed in 2.08s` a `& '.venv\Scripts\ruff.exe' check src tests` výsledkem `All checks passed!`. Reálný průchod s SDL dummy zaznamenal snímky 0/1/2/0 v časech 1/3012/6007/9009 ms a poté skončil událostí QUIT. Ověřena pracovní kopie nad HEAD `553cc19` včetně předchozí úpravy T-009; přesné otisky upraveného dema a ukázky jsou v [DEC-011](DECISIONS.md#dec-011). Nativní okno ani nová produktová akceptace nebyly součástí tohoto ověření.
- Stav: dokonceno
- Poznámky: Snímky mimo ukázkový soubor nadále používají časy ze svého CSV.

## T-011

- Název: Odstranění kolečka uvnitř cíle
- Cíl: Odstranit samostatně vykreslovaný kruh uvnitř postavy či objektu a zachovat hvězdný efekt.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-004](SPEC.md#fr-004), [DEC-012](DECISIONS.md#dec-012).
- Rozsah: Odstranit kresbu kruhu a jeho parametry; interní obrysy, hvězdy a opakované přehrávání ponechat beze změny.
- Závislosti: T-007, T-009
- Riziko: Při odstranění kruhu by se mohlo přerušit předávání obrysu částicím.
- Hotovo když: Uvnitř cíle se samostatné kolečko nevykresluje, hvězdy nadále vykreslují jeho tvar a související testy projdou.
- Ověření:
  - Plán: Ověřit jednobodový i vícebodový obrys bez přímé geometrie, skutečné částice a časování dema.
  - Výsledek: Testy kontrolují předání obrysových bodů částicím a při vypnuté kresbě hvězd čisté pozadí bez čáry i kruhu pro oba typy obrysu; samostatný test ověřuje hvězdy u obvodu. Související testy přehrávání a efektů prošly: `& '.venv\Scripts\python.exe' -m pytest -q tests\test_demo.py tests\test_effects.py` skončil `17 passed in 2.11s`, `& '.venv\Scripts\ruff.exe' check src tests` skončil `All checks passed!` a `git diff --check` bez chyb. Ověřena pracovní kopie nad HEAD `553cc19` včetně T-009 a T-010; otisk dema je uveden v [DEC-012](DECISIONS.md#dec-012). Nativní okno ani nová produktová akceptace nebyly součástí tohoto ověření.
- Stav: dokonceno
- Poznámky: Jednotlivé hvězdy a jejich pohyb zůstávají zachovány.

## T-012

- Název: Odstranění prolétající hvězdy v pozadí
- Cíl: Odstranit samostatný průlet hvězdy a jeho stopu při zachování ostatních hvězd.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-004](SPEC.md#fr-004), [DEC-013](DECISIONS.md#dec-013).
- Rozsah: Odstranit vykreslování a časování samostatného průletu; pohasínání pozadí, pohyb částic, sledování obrysu a přehrávání ponechat beze změny.
- Závislosti: T-007
- Riziko: Při odstraňování průletu by mohlo přestat fungovat pohasínání pozadí nebo zobrazování částic u obrysu.
- Hotovo když: Samostatná prolétající hvězda ani její stopa se nevykreslují a ostatní hvězdy a částice nadále fungují.
- Ověření:
  - Plán: Porovnat vykreslené pixely bez aktualizace částic v několika časech dřívějších průletů a ověřit pohasínání, přitažlivost částic i vykreslení dema.
  - Výsledek: Test porovnává polohy vykreslených pixelů v časech 350/600/1000/3350/3600 ms bez aktualizace částic; před odstraněním průletu selhal ve čtyřech časech s průletem. Další test ověřuje pohasínání samotného pozadí; testy částic a dema kontrolují jejich přitažlivost, uvolnění, zobrazení u obrysu a přehrávání. V CPythonu 3.13.17 s Pygame 2.6.1 skončil `& '.venv\Scripts\python.exe' -m pytest -q tests\test_effects.py tests\test_demo.py` výsledkem `22 passed in 1.99s`, `& '.venv\Scripts\ruff.exe' check src tests` výsledkem `All checks passed!` a `git diff --check` bez chyb. Ověřena pracovní kopie nad HEAD `553cc19` včetně T-009 až T-011; SHA-256 `src/project_china/effects.py`: `73F404A37378330202FAC4F22ADBA28A420A044EF8901B0B03D8F7376D2993B0`. Nativní okno ani nová produktová akceptace nebyly součástí tohoto ověření.
- Stav: dokonceno
- Poznámky: Nová vizuální revize nebyla člověkem produktově přijata.

## T-013

- Název: Generování detailní syntetické postavy
- Cíl: Dodat použitelné CSV s anatomicky modelovanou postavou a plynulým zvedáním a spouštěním rukou.
- Vazby: [AC-001](SPEC.md#ac-001), [CON-001](SPEC.md#con-001), [DEC-014](DECISIONS.md#dec-014).
- Rozsah: Samostatné CSV 256×384, 120 snímků po 50 ms; reprodukovatelný generátor a ověření v existujícím načítání a vykreslování. Původní příklad a efekty se nemění.
- Závislosti: T-004, T-005, T-006
- Riziko: Velikost CSV a paměť při načítání; syntetická geometrie nemusí odpovídat skutečnému člověku a renderer využívá pouze obrys.
- Hotovo když: CSV existuje, má úplné validní mřížky a souvislou neoříznutou postavu, ruce se plynule zvedají i vracejí a celý soubor lze načíst v demu.
- Ověření:
  - Plán: Testovat geometrii, spojitost pohybu včetně smyčky a CSV round-trip; ověřit celý vygenerovaný soubor, časování a výstup renderu.
  - Výsledek: Vytvořeno `examples/human_motion.csv`, 295 760 680 bajtů a 11 796 480 datových řádků. Všech 120 snímků má úplnou mřížku, jediný souvislý neoříznutý obrys a 10 118–10 237 bodů těla s hloubkou 862,751–903,477; maximální posun mezi sousedními obrysy je 7,211 px, na hraně smyčky 1 px. Původní kontrola odhalila oříznuté prsty v některých krajních pózách; záběr a proporce paží byly opraveny a kontrola rozšířena na všechny pózy. V CPythonu 3.13.17 s Pygame 2.6.1 skončil `& '.venv\Scripts\python.exe' -m pytest -q tests\test_synthetic_human.py tests\test_frames.py tests\test_selection.py tests\test_demo.py` výsledkem `158 passed in 10.26s`, Ruff `All checks passed!` a `git diff --check` bez chyb. Celé CSV bylo ověřeno přes `load_depth_csv` za 13,49 s a následně přehráno přes `run_demo` s SDL dummy a automatickou událostí QUIT: 379 vykreslených snímků, návštěva všech 120 póz a návrat na začátek v 6011 ms. Špička working set procesu byla 1948,3 MiB a špička commitované paměti 2420,1 MiB; výkon závisí na zařízení. Prohlédnuty diagnostické hloubkové mapy i hvězdné vykreslení. Ověřena pracovní kopie nad HEAD `d444dd5`; SHA-256 CSV `70061DEAD81F1C3F7CED0896398CE638611733A5F16472B0E53BBD0160DF23DB`, generátoru `74611703F17EAD2DDDBBD20B502B04BD809CEBA372B0C75218A208A603129410`. CSV není verzované a lze ho znovu vygenerovat. Nativní okno, skutečná kamera ani lidská produktová akceptace nebyly součástí ověření.
- Stav: dokonceno
- Poznámky: Všechny vstupní body jsou vymyšlené, ne záznam z kamery.

## T-014

- Název: Hustší hvězdný obrys člověka
- Cíl: Zvýšit počet hvězd tvořících obrys detailního člověka.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-004](SPEC.md#fr-004), [FR-008](SPEC.md#fr-008), [DEC-015](DECISIONS.md#dec-015).
- Rozsah: Volitelný počet částic v `StarEffect` a parametr `--particles` dema s výchozí hodnotou 72; `runHuman.ps1` používá 360. Ukázka objektu a ostatní parametry se nemění.
- Závislosti: T-007, T-013
- Riziko: Příliš mnoho hvězd by splynulo v souvislou čáru; vyšší výpočetní náročnost.
- Hotovo když: Obrys člověka je výrazně hustší, ale stále tvořený hvězdami; výchozí demo zůstává na 72 a testy projdou.
- Ověření:
  - Plán: Porovnat vykreslení s 72/240/360/480 hvězdami, změřit pokrytí obrysu a čas vykreslení, otestovat předání parametru a spustit skript.
  - Výsledek: Obvod postavy na obrazovce měří 2 305–2 397 px. Po 240 krocích je největší vzdálenost bodu obrysu od nejbližší hvězdy u snímků 0/30/60 při 72 hvězdách 23,2–25,5 px a při 360 hvězdách 7,0–7,1 px; všech 360 hvězd leží do 3 px od obrysu. Vykreslení snímku 960×720 trvalo 0,80 ms při 72 a 1,11 ms při 360 hvězdách. Vizuální srovnání je v `human-density.png` (session artefakt). Testy pokrývají výchozí počet, předání a odmítnutí neplatného `--particles`, počet hvězd v `run_demo` a pokrytí obrysu člověka. V CPythonu 3.13.17 s Pygame 2.6.1 skončil `& '.venv\Scripts\python.exe' -m pytest -q` výsledkem `177 passed in 12.23s` a `& '.venv\Scripts\ruff.exe' check src tests` výsledkem `All checks passed!`. `runHuman.ps1` s SDL dummy spustil demo s `--particles 360` a po 35 s stále běžel bez chyb. Ověřena pracovní kopie nad HEAD `3b766b5`; otisky jsou v [DEC-015](DECISIONS.md#dec-015). Nativní okno ani produktová akceptace nebyly součástí ověření.
- Stav: dokonceno
- Poznámky: Ukázka objektu (`runObject.ps1`) nadále používá 72 hvězd.

## T-015

- Název: Plynulé morfování obrysu mezi snímky
- Cíl: Odstranit skokové objevování a mizení končetin a obrysu při přechodu mezi snímky CSV.
- Vazby: [AC-001](SPEC.md#ac-001), [FR-004](SPEC.md#fr-004), [DEC-016](DECISIONS.md#dec-016).
- Rozsah: Nový modul `src/project_china/morph.py`: převzorkování kontur na 1 024 bodů, sjednocený směr obcházení, kotvy ve 4 kvadrantech od těžiště (záložně horní bod), párování kontur podle těžiště, vyrůstání a zanikání kontur v těžišti, `smoothstep` interpolace a strop rychlosti cílů. Napojení do render smyčky v `demo.py` s mezipamětí klíčových snímků. Hloubka se neinterpoluje.
- Závislosti: T-007, T-013, T-014
- Riziko: Nerovnoměrná hustota bodů mezi kvadranty; změna počtu kontur přeskupí přiřazení hvězd; delší první průchod smyčkou kvůli výpočtu klíčových snímků.
- Hotovo když: Cílové body obrysu se mezi render kroky posouvají plynule bez skoků v klíčových snímcích, ukázkový objekt stojí a pak plynule přepluje a testy i Ruff projdou.
- Ověření:
  - Plán: Jednotkové testy morfování, integrační testy render smyčky, měření plynulosti na celé smyčce syntetického člověka a objektu, měření pokrytí a času vykreslení, náhledy bez okna a spuštění obou skriptů.
  - Výsledek: Všech 120 snímků člověka má jednu konturu se spolehlivými kvadranty (podíl kvadrantů 19–31 %). Při kroku 1/60 s je přes celou smyčku největší posun cílového bodu 9,3 px (asi 555 px/s), medián 0,2 px; bez morfování přeskakovaly body v klíčovém snímku až o 21 px. Přechod objektu má nejvýše 14 px na krok (asi 840 px/s), strop 900 px/s běžný pohyb neomezuje. Konec jednoho přechodu a začátek dalšího se shodují (test s tolerancí 1e-9). Po 240 krocích je u snímků 0/30/60 největší vzdálenost bodu obrysu od nejbližší hvězdy 4,8–4,9 px při 360 hvězdách a 19,1–20,5 px při 72. Medián vykreslení snímku 960×720 je 0,76 ms u člověka s 360 hvězdami a 0,45 ms u objektu. Příprava jednoho klíčového snímku člověka trvá asi 62 ms, a to jen jednou díky mezipaměti. Náhledy `T-015-human-1700.png` a `T-015-object-2700.png` (session artefakty) ukazují souvislý obrys a objekt uprostřed přeplutí. V CPythonu 3.13.17 s Pygame 2.6.1 skončil `& '.venv\Scripts\python.exe' -m pytest -q` výsledkem `192 passed in 15.74s` a `& '.venv\Scripts\ruff.exe' check src tests` výsledkem `All checks passed!`. `runObject.ps1` (8 s) i `runHuman.ps1` (35 s) s SDL dummy běžely bez chybového výstupu. Ověřena pracovní kopie nad HEAD `88207f6`; otisky jsou v [DEC-016](DECISIONS.md#dec-016). Nativní okno, reálná kamera ani produktová akceptace nebyly součástí ověření.
- Stav: dokonceno
- Poznámky: Testy převodu indexu snímku přešly z odstraněné funkce `_frame_index_for_elapsed` na `transition_for_elapsed`; očekávané hodnoty se nezměnily. Test cíle v rohu obrysu nyní porovnává vzdálenost (< 0,5 px) místo přesné shody celočíselného bodu, protože cíle jsou převzorkované body s desetinnými souřadnicemi.