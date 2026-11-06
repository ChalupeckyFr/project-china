# SPEC.md – specifikace Project China

Jediný zdroj pravdy pro **účel, rozsah, požadavky, omezení a akceptační
kritéria**. Naplňuje se během discovery; viz
[`AGENTS.md`](AGENTS.md), sekce 3.1.

Hodnota `nezjištěno` znamená, že informace dosud nebyla získána od člověka.
Není to fakt ani rozhodnutí. Nevyplňuj ji odhadem.

## 1. Účel produktu

- Potřeba, kterou produkt řeší: Zpracovat hloubkovou mapu a vykreslit vizuální efekty navázané na obrys člověka nebo objektu v určené vzdálenosti od kamery.
- Hlavní uživatelé: Běžní návštěvníci akcí, například dne otevřených dveří nebo Noci vědců, a obsluha akce.
- Měřítka úspěchu: viz AC-001

## 2. Rozsah

### 2.1 V rozsahu první verze

Demo aplikace využívající posloupnost zjednodušených vymyšlených snímků hloubkové mapy v CSV, demonstrující efekt kolem člověka i libovolného objektu a zobrazující výsledek na monitoru.

### 2.2 Mimo rozsah

Fyzická tlačítka pro přepínání módů jsou zamýšlena až v pozdější fázi při nasazení na Raspberry Pi.

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

## FR-001

- Název: Výběr cíle podle vzdálenosti
- Popis: Zpracovat posloupnost snímků hloubkové mapy a vyseparovat cílový objekt podle hloubky; cílem může být člověk i libovolný jiný objekt. Demo bez kamery načítá z CSV posloupnost bezrozměrných hloubkových hodnot (například 0–1500) a používá pevně zadaný interval 750–1000. V produkčním scénáři ToF kamera snímá pouze prostor vyznačený kruhem na zemi a odpovídající cílové vzdálenosti; v kruhu je vždy jeden návštěvník.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Vazby: Q-001

## FR-002

- Název: Získání obrysu
- Popis: Získat obrys vybraného člověka nebo objektu.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Vazby: FR-001

## FR-003

- Název: Vykreslení efektů kolem obrysu
- Popis: Kolem obrysu vykreslovat tvary nebo shluky částic.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Vazby: FR-002

## FR-004

- Název: Chování efektu s hvězdami
- Popis: Hvězdy jsou po celé obrazovce, s výrazně vyšší hustotou přímo na obvodu obrysu. Občas mírně pohasínají a plynule následují obrys při pohybu nebo odchodu člověka. V demu se samostatná prolétající hvězda v pozadí nevykresluje; původní požadavek na průlety menších hvězd pro ostatní prostředí tím není změněn.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001; změna průletu v demu DEC-013
- Vazby: FR-002, FR-003

## FR-005

- Název: Parametry částicových efektů
- Popis: Částicový efekt používá bezrozměrný ladicí koeficient gravitační přitažlivosti k obrysu člověka, počet částic, sílu animací a barevné kombinace. Konkrétní hodnota koeficientu zatím není určena.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Vazby: Q-003

## FR-006

- Název: Parametry objektových efektů
- Popis: Objektové efekty mají nastavení velikosti; další parametry budou upřesněny později.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Vazby: Q-002

## FR-007

- Název: Přepínání módů fyzickými tlačítky
- Popis: V pozdější fázi při provozu na Raspberry Pi umožnit návštěvníkovi měnit mód nebo efekt stiskem fyzického tlačítka.
- Původ: člověk
- Stav: navrh
- Schválení: –
- Vazby: –

## FR-008

- Název: Pevné parametry efektů
- Popis: V demu i produkci jsou všechny parametry částicových a objektových efektů pevně dané; obsluha je nenastavuje.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Vazby: FR-005, FR-006

## 4. Nefunkční požadavky (`NFR-*`)

Pouze podle relevance a rizika; nevyplňuj preventivně všechny kategorie.
Stejný formát jako FR. Měřitelná hodnota bez podmínek měření je otázka `Q-*`,
ne požadavek.

### Záznamy

## NFR-001

- Název: Neukládání hloubkových dat
- Popis: Hloubková data pouze zpracovat a dále je neukládat.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Vazby: CON-001

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

## CON-001

- Název: Demo a produkční prostředí
- Omezení: Demo nepoužívá kameru; na počítači načítá z CSV posloupnost zjednodušených vymyšlených snímků bezrozměrných hloubkových hodnot a zobrazuje výsledek na monitoru. Produkční prostředí má používat reálný stream z ToF kamery a projektor; snímaná oblast odpovídá kruhu vyznačenému na zemi.
- Původ: člověk
- Stav: schvaleno
- Schválení: DEC-001
- Dopad: Vstupní a zobrazovací prostředí dema a zamýšleného produkčního prostředí.

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

## AC-001

- Požadavek: FR-001, FR-002, FR-004
- Podmínky: Demo přehraje posloupnost hloubkových snímků zachycující pohyb cíle; příkladem je člověk zvedající ruce.
- Očekávaný výsledek: Hvězdy jsou po celé obrazovce, výrazně hustší u obrysu a občas pohasínají; samostatná prolétající hvězda v pozadí se nevykresluje. Efekt plynule sleduje obrys a zřetelně ukazuje pohyb cíle, například zvednutí rukou.
- Způsob ověření: Návrh agenta: přehrát posloupnost a vizuálně zkontrolovat rozložení hvězd, jejich animace, nepřítomnost samostatného průletu a následování obrysu.
- Stav: schvaleno
- Schválení: DEC-001; změna průletu v demu DEC-013

## 7. Předpoklady

Neověřené vstupy, které agent nebo člověk zatím nepotvrdil. Nesmí se tvářit
jako požadavky.

_Žádné._
