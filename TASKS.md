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
  - Výsledek: dosud neprovedeno
- Stav: nezahajeno
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
  - Výsledek: dosud neprovedeno
- Stav: nezahajeno
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
  - Výsledek: dosud neprovedeno
- Stav: nezahajeno
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
  - Výsledek: dosud neprovedeno
- Stav: nezahajeno
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
  - Výsledek: dosud neprovedeno
- Stav: nezahajeno
- Poznámky: Koeficient přitažlivosti se určí při vizuálním ladění podle Q-003.

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
  - Výsledek: dosud neprovedeno
- Stav: nezahajeno
- Poznámky: Bez lidské akceptace nelze výsledek vydávat za produktově přijatý.
