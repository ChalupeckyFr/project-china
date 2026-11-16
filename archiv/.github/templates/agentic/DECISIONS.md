# DECISIONS.md – rozhodnutí a schválení Project China

Jediný zdroj pravdy pro **rozhodnutí, jejich důvody, historii a záznamy
skutečných schválení**. Pravidla viz
[`AGENTS.md`](AGENTS.md), sekce 4.

## Pravidla evidence

- Nadpis záznamu je pouze ID (`## DEC-001`); název je v poli `Předmět`.
- Nové ID = nejvyšší existující + 1. ID nepřečíslovávej a nepoužívej znovu.
- Staré rozhodnutí nikdy nepřepisuj tak, aby zmizel původní důvod nebo
  výsledek. Nahrazuj novým záznamem a propoj oba směry.
- Technické rozhodnutí přijaté agentem musí odkazovat na `DEC-*`, které
  delegaci stanovilo; nevydávej je za lidské schválení.
- Schválení nevzniká jako vedlejší efekt zápisu souboru, mlčením ani
  úspěchem nástroje.

## Vzor rozhodnutí (není záznam)

```markdown
## DEC-001

- Předmět: Co se rozhoduje.
- Typ: technicke-rozhodnuti | schvaleni-rozsahu | opravneni-k-operaci | produktova-akceptace | delegace
- Kontext: Proč je rozhodnutí potřeba; vazby na FR/NFR/CON/Q.
- Varianty: Přiměřené alternativy a jejich hlavní kompromisy.
- Výsledek: Zvolená varianta.
- Důvod: Proč.
- Důsledky: Co z toho plyne (úkoly, rizika, změny).
- Stav: navrh
- Nahrazuje / Nahrazeno: DEC-xxx, nebo –
- Schválení:
  - Rozsah: Přesně co je schváleno.
  - Revize: commit SHA nebo explicitní revize dokumentu (např. `SPEC.md` ve znění k {{DATE}}).
  - Schválil: Osoba nebo role.
  - Datum: RRRR-MM-DD
  - Podmínky / výjimky: (volitelné)
```

Pole `Schválení` vyplň **až po udělení** souhlasu člověkem. Do té doby je
stav `navrh` nebo `ke-schvaleni`.

## Záznamy

_Žádná rozhodnutí. Bootstrap prostředí není rozhodnutí o produktu._
