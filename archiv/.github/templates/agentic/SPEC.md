# SPEC.md – specifikace Project China

Jediný zdroj pravdy pro **účel, rozsah, požadavky, omezení a akceptační
kritéria**. Naplňuje se během discovery; viz
[`AGENTS.md`](AGENTS.md), sekce 3.1.

Hodnota `nezjištěno` znamená, že informace dosud nebyla získána od člověka.
Není to fakt ani rozhodnutí. Nevyplňuj ji odhadem.

## 1. Účel produktu

- Potřeba, kterou produkt řeší: nezjištěno
- Hlavní uživatelé: nezjištěno
- Měřítka úspěchu: nezjištěno

## 2. Rozsah

### 2.1 V rozsahu první verze

nezjištěno

### 2.2 Mimo rozsah

nezjištěno

## 3. Funkční požadavky (`FR-*`)

Vzor (není záznam):

```markdown
## FR-001

- Název: Stručný název.
- Popis: Co systém dělá a jak se chová.
- Původ: Kdo/co požadavek vznesl (člověk, DEC-xxx, Q-xxx).
- Stav: navrh
- Schválení: (DEC-xxx při stavu schvaleno)
- Vazby: AC-xxx, CON-xxx
```

### Záznamy

_Žádné._

## 4. Nefunkční požadavky (`NFR-*`)

Pouze podle relevance a rizika; nevyplňuj preventivně všechny kategorie.
Stejný formát jako FR. Měřitelná hodnota bez podmínek měření je otázka `Q-*`,
ne požadavek.

### Záznamy

_Žádné._

## 5. Závazná omezení (`CON-*`)

Prostředí, rozpočet, předepsaná technologie, regulace. Předepsaný stack je
omezení, nikoli NFR.

Vzor (není záznam):

```markdown
## CON-001

- Název: Stručný název.
- Omezení: Přesné znění hranice.
- Původ: Kdo omezení stanovil.
- Stav: navrh
- Dopad: Na co má vliv.
```

### Záznamy

_Žádné._

## 6. Akceptační kritéria (`AC-*`)

Vzor (není záznam):

```markdown
## AC-001

- Požadavek: FR-xxx
- Podmínky: Výchozí stav / vstup.
- Očekávaný výsledek: Pozorovatelné chování.
- Způsob ověření: Test, manuální postup, měření – konkrétně.
- Stav: navrh
```

Vyhni se formulacím „rychlé“, „uživatelsky přívětivé“ bez vyjasněného významu.

### Záznamy

_Žádné._

## 7. Předpoklady

Neověřené vstupy, které agent nebo člověk zatím nepotvrdil. Nesmí se tvářit
jako požadavky.

_Žádné._
