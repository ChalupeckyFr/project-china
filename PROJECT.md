# PROJECT.md – aktuální stav projektu Project China

Jediný zdroj pravdy pro **fázi, aktivní přírůstek, otevřené otázky a bod
pokračování**. Stavy úkolů, znění požadavků a rozhodnutí sem nekopíruj –
odkazuj na ně. Pravidla viz [`AGENTS.md`](AGENTS.md), sekce 3.

## Fáze

- Fáze: `planovani-prirustku`
- Od: 2026-11-06
- Poslední změna fáze: člověk schválil technická rozhodnutí DEC-002 až DEC-006

## Aktivní přírůstek

Demo hloubkové mapy – schválený rozsah viz `DECISIONS.md#dec-001`.

## Další krok

První připravený úkol: `T-001` (`/work-task T-001`).

## Bod pokračování

- Aktivní úkol: žádný
- Poslední dokončená činnost: záznam schválených technických rozhodnutí a plánu prvního přírůstku
- Neověřené změny ve worktree: toolchain, výkon a kompatibilita nebyly ověřeny; implementace dema nezačala
- Další bezpečný krok: spustit `/work-task T-001`; k instalaci v T-002 je nutný samostatný souhlas

## Otevřené otázky

Formát záznamu (vzor, není záznam):

```markdown
## Q-001

- Otázka: Konkrétní nejasnost.
- Blokuje: Co nelze bez odpovědi správně udělat (ID nebo „nic“).
- Rozhodne: Osoba nebo role, je-li známa.
- Stav: otevreno
- Výsledek: (po vyřešení odkaz na DEC/FR/…, ne kopie)
```

### Záznamy

## Q-001

- Otázka: V jakých jednotkách je hloubkový interval pro demo?
- Blokuje: FR-001
- Rozhodne: člověk
- Stav: vyreseno
- Výsledek: Demo nevyužívá fyzikální jednotky; používá pevný interval 750–1000 nad bezrozměrnými CSV hodnotami (příklad rozsahu dat 0–1500).

## Q-002

- Otázka: Jaká další nastavení mají mít objektové efekty kromě velikosti?
- Blokuje: nic
- Rozhodne: člověk
- Stav: otevreno
- Výsledek: člověk doplní později

## Q-003

- Otázka: Jaká pevná hodnota bezrozměrného koeficientu gravitační přitažlivosti se použije?
- Blokuje: nic
- Rozhodne: člověk
- Stav: vyreseno
- Výsledek: Koeficient je bezrozměrný; jeho pevná hodnota se určí při vizuálním ladění dema.

## Q-004

- Otázka: Načítá demo jeden pevný CSV vzorek, nebo umožňuje vybrat více souborů?
- Blokuje: nic
- Rozhodne: člověk
- Stav: otevreno
- Výsledek: zatím nerozhodnuto

## Q-005

- Otázka: Který konkrétní model ToF kamery bude použit v produkci?
- Blokuje: nic
- Rozhodne: člověk
- Stav: otevreno
- Výsledek: zatím není rozhodnuto

## Q-006

- Otázka: Jaký hloubkový interval vymezuje snímaný kruh v produkčním scénáři?
- Blokuje: nic
- Rozhodne: člověk
- Stav: otevreno
- Výsledek: zatím není rozhodnuto

## Q-007

- Otázka: Jsou parametry efektů pevně dané i v demu, nebo se tam dají měnit?
- Blokuje: FR-005, FR-006, FR-008
- Rozhodne: člověk
- Stav: vyreseno
- Výsledek: Parametry jsou pevně dané v demu i produkci; obsluha je nenastavuje. Návštěvník později tlačítkem přepíná mód nebo efekt.

## Provozní omezení

Pouze skutečně dohodnutá omezení provozu projektu (ne produktová omezení
`CON-*`, ta patří do `SPEC.md`).

_Žádná._
