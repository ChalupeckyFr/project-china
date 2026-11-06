# Project China

Projekt vyvíjený agenty ve spolupráci s člověkem podle provozního řádu
v [`AGENTS.md`](AGENTS.md).

> Aktuální stav, fázi a bod pokračování najdeš vždy v [`PROJECT.md`](PROJECT.md).
> Tento soubor stav nekopíruje.

## Mapa dokumentace

| Dokument | Účel |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Provozní řád: proces, autonomie, schvalování, evidence, definice hotovo. |
| [`PROJECT.md`](PROJECT.md) | Aktuální fáze, aktivní přírůstek, otevřené otázky, bod pokračování. |
| [`SPEC.md`](SPEC.md) | Účel, rozsah, požadavky, omezení, akceptační kritéria. |
| [`TASKS.md`](TASKS.md) | Úkoly, závislosti, stav, ověření, důkazy. |
| [`DECISIONS.md`](DECISIONS.md) | Rozhodnutí, důvody, záznamy schválení. |
| `IDEAS.md` | Nápady – vznikne až s prvním nápadem. |

## Jak začít

Postup zvol podle aktuální fáze a dalšího kroku v [`PROJECT.md`](PROJECT.md).
Discovery **zahajuje člověk**.

### Ve VS Code s GitHub Copilot

1. Otevři Copilot Chat v agentním režimu.
2. Spusť odpovídající příkaz z tabulky níže (nebo použij `Chat: Run Prompt...`).
3. Postupuj podle pokynů agenta a posuď případná schválení.

Další vstupní body:

| Příkaz | Použij když |
| --- | --- |
| `/discover-project` | Zahajuješ nebo obnovuješ specifikaci. |
| `/plan-increment` | Máš schválený rozsah a chceš návrh řešení a úkoly. |
| `/work-task T-xxx` | Chceš realizovat konkrétní úkol. |

### V jiném nástroji

Otevři odpovídající soubor v `.github/prompts/`, zkopíruj jeho tělo (část pod
frontmatterem) jako zadání agentovi a připoj pokyn, aby nejprve načetl
`AGENTS.md` a `PROJECT.md`.

## Příprava vývojového prostředí

Závislosti jsou uvedeny v [`requirements.txt`](requirements.txt) a
[`requirements-dev.txt`](requirements-dev.txt). V rámci T-002 bylo po
oprávněních DEC-007 a DEC-008 ověřeno prostředí CPython 3.13.17 a nainstalovány
deklarované závislosti. Původní neúspěšné prostředí Pythonu 3.14 zůstalo
zachováno jako `.venv-py314-failed`.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Ověřeno na Windows s CPythonem 3.13.17 x64. Před vytvořením prostředí
ověř, že `.venv` ještě neexistuje.

## Základní kontroly

Spusť test importu a statickou kontrolu z kořene repozitáře:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check src tests
```

## Vstupní CSV

`project_china.frames.load_depth_csv(path)` načítá posloupnost se záhlavím
`frame,time_ms,x,y,depth`. Každý snímek musí mít jednotný čas a úplnou
obdélníkovou mřížku stejných rozměrů; hloubky se vracejí v paměti po řádcích
od `y=0`, bez ukládání zpracovaných dat. Neplatný vstup vyvolá
`DepthCsvError`.

`project_china.selection.select_depth_regions(frame)` vybírá hodnoty včetně
obou mezí 750–1000 a vrací binární masku i obrysy všech oddělených oblastí.
Prázdný výběr vrací prázdnou množinu obrysů, nikoli chybu.

Lokální demo spustíš s explicitní cestou k jednomu CSV souboru; jako příklad
slouží syntetická posloupnost `examples/moving_object.csv`:

```powershell
Push-Location src
try {
    ..\.venv\Scripts\python.exe -m project_china.demo ..\examples\moving_object.csv
}
finally {
    Pop-Location
}
```

Příklad je vymyšlený testovací vstup, ne záznam z kamery. Demo žádná zpracovaná
hloubková data neukládá. Volba pevného vzorku nebo souborů přes uživatelské
rozhraní zůstává otevřená v Q-004. Okno lze zavřít klávesou `Esc` nebo `q`.

Hvězdné pozadí plynule pohasíná, obsahuje občasné průlety a při výskytu obrysu
k němu přitahuje 72 částic; po jeho zmizení se částice postupně uvolní.
Provizorní pevné parametry jsou přitažlivost 0,08 na referenčním kroku 60 Hz,
náběh přitažlivosti 180 ms, uvolnění s časovou konstantou 700 ms, průlet každé
3 sekundy po dobu 750 ms a kruhový objektový obrys s poloměrem 12 px. Parametry
nemají nastavovací UI a čekají na vizuální posouzení v T-008.

## Co tu (zatím) není

CI a licence zatím nejsou připravené.
Architekturu a základní závislosti stanovují
schválené záznamy v `DECISIONS.md`.
