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
  - Revize: commit SHA nebo explicitní revize dokumentu (např. `SPEC.md` ve znění k 2026-11-06).
  - Schválil: Osoba nebo role.
  - Datum: RRRR-MM-DD
  - Podmínky / výjimky: (volitelné)
```

Pole `Schválení` vyplň **až po udělení** souhlasu člověkem. Do té doby je
stav `navrh` nebo `ke-schvaleni`.

## Záznamy

## DEC-001

- Předmět: Schválení rozsahu prvního přírůstku – demo hloubkové mapy
- Typ: schvaleni-rozsahu
- Kontext: Rozsah dema a související požadavky jsou zapsány v `SPEC.md`.
- Varianty: Schválit přesně uvedený seznam ID, nebo pokračovat v discovery.
- Výsledek: Schválen přesně tento rozsah: CON-001, FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-008, NFR-001 a AC-001.
- Důvod: Člověk výslovně schválil uvedený seznam ID.
- Důsledky: Schválené záznamy v `SPEC.md` odkazují na DEC-001. FR-007, tlačítkové přepínání módů na Raspberry Pi, není součástí tohoto přírůstku. Otevřené otázky Q-002, Q-004, Q-005 a Q-006 neblokují schválené demo.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: CON-001, FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-008, NFR-001 a AC-001.
  - Revize: `SPEC.md` a `CON-001` ve znění schváleném dne 2026-11-06, identifikované výše uvedenými ID.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: FR-007 je mimo schválený rozsah prvního přírůstku.
