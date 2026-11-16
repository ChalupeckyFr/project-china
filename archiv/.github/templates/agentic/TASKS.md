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

_Žádné úkoly. Vznikají až v plánování přírůstku (`/plan-increment`)._
