# PROJECT.md – aktuální stav projektu Project China

Jediný zdroj pravdy pro **fázi, aktivní přírůstek, otevřené otázky a bod
pokračování**. Stavy úkolů, znění požadavků a rozhodnutí sem nekopíruj –
odkazuj na ně. Pravidla viz [`AGENTS.md`](AGENTS.md), sekce 3.

## Fáze

- Fáze: `realizace`
- Od: 2026-11-06
- Poslední změna fáze: zahájena práce na T-007

## Aktivní přírůstek

Demo hloubkové mapy – schválený rozsah viz `DECISIONS.md#dec-001`.

## Další krok

Následuje T-008: vizuální ověření dema a předložení výsledku člověku.

## Bod pokračování

- Aktivní úkol: T-008
- Poslední dokončená činnost: deterministické animace a pevný objektový obrys ověřené testy v T-007
- Neověřené změny ve worktree: vizuální výsledek T-007 nad syntetickou posloupností
- Další bezpečný krok: provést vizuální kontrolu v T-008; produktovou akceptaci ponechat člověku

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

## Q-008

- Otázka: Jak odblokovat T-002 po selhání sestavení Pygame 2.6.1 na dostupném CPythonu 3.14.7?
- Blokuje: T-002, DEC-002
- Rozhodne: člověk
- Stav: vyreseno
- Výsledek: Člověk zvolil zachování Pygame a povolil instalaci kompatibilního Pythonu; postup a oprávnění jsou zaznamenány v [DEC-008](DECISIONS.md#dec-008). CPython 3.13.17 umožnil úspěšně nainstalovat a ověřit závislosti.

## Provozní omezení

Pouze skutečně dohodnutá omezení provozu projektu (ne produktová omezení
`CON-*`, ta patří do `SPEC.md`).

_Žádná._
