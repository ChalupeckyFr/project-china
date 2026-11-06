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

Projekt je po bootstrapu ve fázi `pripraveno-ke-specifikaci`. Specifikace
aplikace zatím neexistuje – vzniká v discovery, které **zahajuje člověk**.

### Ve VS Code s GitHub Copilot

1. Otevři Copilot Chat v agentním režimu.
2. Spusť `/discover-project` (nebo `Chat: Run Prompt...` → `discover-project`).
3. Postupuj podle otázek agenta; rozsah ke schválení ti předloží explicitně.

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

## Co tu (zatím) není

Instalace, spouštění, CI, licence a architektura aplikace budou doplněny až
po příslušných rozhodnutích v `DECISIONS.md`. Nehledej je zde dříve.
