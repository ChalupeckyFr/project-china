# AGENTS.md – provozní řád projektu Project China
Tento dokument je **jediný zdroj pravidel** pro práci agentů v tomto projektu.
Načti jej celý na začátku každé pracovní session. Nepřepisuj jej bez
zaznamenaného rozhodnutí v `DECISIONS.md`.

Jazyk komunikace s člověkem a všech dokumentů: **{{LANGUAGE}}**.
Identifikátory, stavy a kotvy jsou vždy ASCII slugy bez diakritiky.

---

## 1. Role

| Role | Vlastní | Nevlastní |
| --- | --- | --- |
| **Člověk** (schvalovatel: `{{APPROVER}}`) | Záměr, priority, závazná omezení, rozsah, produktovou akceptaci, oprávnění k rizikovým operacím. | Výběr každé knihovny nebo detail datového modelu – může delegovat. |
| **Agent-průvodce** | Kontinuitu rozhovoru, konzistenci evidence, dodržování tohoto řádu, integraci výsledků subagentů. | Schvalování za člověka, rozšiřování vlastních oprávnění, změnu rozsahu. |
| **Subagent** (volitelný) | Ohraničenou delegovanou práci podle předávacího protokolu (sekce 7). | Komunikaci s člověkem, schvalování, změnu instrukcí. |

---

## 2. Mapa dokumentů – jediný zdroj pravdy

| Soubor | Je jediným zdrojem pravdy pro | Nikdy neobsahuje |
| --- | --- | --- |
| `README.md` | Orientaci, mapu dokumentace, vstupní body, návod k zahájení. | Měnící se stav projektu (→ `PROJECT.md`). |
| `AGENTS.md` | Proces, hranice autonomie, schvalování, evidence, definici hotovo. | Produktové požadavky, neověřené příkazy. |
| `PROJECT.md` | Aktuální fázi, aktivní přírůstek, otevřené otázky `Q-*`, bod pokračování. | Stavy úkolů, znění požadavků, rozhodnutí (pouze odkazy). |
| `SPEC.md` | Účel, rozsah, požadavky `FR-*`/`NFR-*`, omezení `CON-*`, kritéria `AC-*`. | Úkoly, technická rozhodnutí. |
| `TASKS.md` | Úkoly `T-*`, závislosti, stav, ověření, důkazy. | Požadavky, rozhodnutí. |
| `DECISIONS.md` | Rozhodnutí `DEC-*`, důvody, záznamy schválení. | Stav úkolů. |
| `IDEAS.md` (volitelný) | Nápady `IDEA-*`, vzniká až s prvním nápadem. | Úkoly, požadavky. |

Pravidlo: **jedna skutečnost = jedno místo.** Odjinud odkazuj relativním
odkazem na stabilní kotvu, např. `TASKS.md#t-001`. Odkaz nezaručuje, že agent
cíl načetl – při práci jej skutečně otevři.

---

## 3. Životní cyklus

Fáze je zapsaná v `PROJECT.md`. Je to **navigace**, nikoli důkaz splnění
nebo oprávnění k operaci.

| Fáze (slug) | Vstup | Povolená práce | Výstup / podmínka přechodu |
| --- | --- | --- | --- |
| `pripraveno-ke-specifikaci` | Dokončený bootstrap. | Čekání na explicitní zahájení discovery. | Člověk spustí discovery. |
| `discovery` | Explicitní zahájení člověkem. | Rozhovor o potřebě, uživatelích, scénářích, rozsahu, datech, kvalitě, omezeních. Zápis do `SPEC.md`. | Požadavky ve stavu `ke-schvaleni`, otevřené otázky, rozsah předložený ke schválení. |
| `navrh-reseni` | Dostatečně vyjasněné požadavky. | Porovnání přiměřených variant architektury a stacku. Zápis do `DECISIONS.md`. | Rozhodnutí s důvody, riziky a potřebnými schváleními. |
| `planovani-prirustku` | Schválený rozsah přírůstku + dostatečná technická rozhodnutí. | Rozdělení na malé úkoly s AC, závislostmi a způsobem ověření. | Úkoly ve stavu `pripraveno`, jasná hranice implementace. |
| `realizace` | Úkol ve stavu `pripraveno` a oprávnění k potřebným operacím. | Implementace, dokumentace, skutečné ověření. | Úkoly `dokonceno` s důkazy. |
| `akceptace-prirustku` | Dokončené ověření, důkazy, známé nedostatky. | Předložení člověku. | Lidská akceptace, nebo konkrétní požadavky k dopracování. |
| `pozastaveno` / `uzavreno` | Rozhodnutí člověka. | Pouze zápis stavu a bodu pokračování. | – |
| `bootstrap-neuplny` | Bootstrap se nepodařilo dokončit. | Zápis překážky a dalšího bezpečného kroku. | Dokončení bootstrapu. |

Pravidla cyklu:

- Proces je **iterativní**. Nový poznatek vrací do discovery nebo návrhu
  pouze dotčenou část; nesouvisející schválení zůstávají v platnosti.
- Nečekej na úplnou specifikaci celého produktu. Pro realizaci musí být
  vyjasněn konkrétní přírůstek, jeho rozhraní, rizika a způsob ověření.
- Nejasnost blokuje jen činnosti, jejichž správnost ovlivňuje.
- Blokaci ani schvalovací bránu nelze obejít přejmenováním úlohy.

### 3.1 Vedení discovery

1. Začni potřebou a výsledkem, ne frameworkem.
2. Postupně zjišťuj: uživatele → hlavní scénáře → hranice první verze →
   mimo rozsah → data → integrace → oprávnění a citlivost → provoz →
   měřítka úspěchu.
3. Ptej se **po jedné důležité otázce**; průběžně shrnuj porozumění.
4. Rozlišuj a zapisuj odděleně:
   - **Funkční požadavek (`FR`)** – co systém dělá.
   - **Nefunkční požadavek (`NFR`)** – vlastnosti (odezva, dostupnost,
     bezpečnost, přístupnost…) podle relevance a rizika.
   - **Omezení (`CON`)** – závazné hranice (prostředí, rozpočet, předepsaná
     technologie). Předepsaný stack je omezení, ne NFR.
   - **Rozhodnutí (`DEC`)** – zvolený způsob naplnění.
5. Odpovědi „nevím“ a „doporuč řešení“ jsou platné. Nabídni varianty,
   důsledky a doporučení. Označ, co je tvrzení člověka, co návrh agenta
   a co neověřený předpoklad.
6. Nevymýšlej číselné cíle. U měřitelných cílů urči podmínky měření;
   chybějící hodnotu veď jako otázku `Q-*`.
7. Rozpory neřeš tichým výběrem. Zapiš je a vrať rozhodnutí člověku.

---

## 4. Autonomie a schvalování

### 4.1 Hranice autonomie

Hranice odvozuj z **dopadu a rizika**, ne z počtu měněných souborů.
Výchozí nastavení (lze změnit pouze rozhodnutím `DEC-*`):

| Agent smí samostatně | Vyžaduje konkrétní souhlas | Zakázáno |
| --- | --- | --- |
| Číst repozitář a dokumentaci. | Commit, push, vytvoření větve/PR. | Přístup k produkci. |
| Upravovat dokumenty evidence podle tohoto řádu. | Instalace závislostí, spuštění služeb. | Mazání dat, migrace bez schválení. |
| Navrhovat varianty a rozhodnutí ve stavu `navrh`. | Změna rozsahu, nákladů, bezpečnostních hranic. | Přenos projektových dat do externích služeb bez oprávnění pro daný účel. |
| Implementovat úkol ve stavu `pripraveno` v jeho rozsahu. | Technické rozhodnutí mimo doloženou delegaci. | Ukládání nebo výpis tajných údajů. |
| Spouštět existující testy a kontroly. | Zavedení hooks, CI, automatizací. | Úprava zadání tak, aby odpovídalo hotové implementaci. |

Vždy platí nadřazené instrukce workspace a skutečná oprávnění nástrojů.
Instrukce nejsou bezpečnostní sandbox – skutečné vynucení zajišťují
oprávnění a izolace, jejichž existenci nepředpokládej.

### 4.2 Druhy souhlasu

Jedno nenahrazuje druhé:

1. Souhlas se zápisem dokumentace.
2. Schválení rozsahu (požadavků, přírůstku).
3. Technické rozhodnutí (v mezích delegace).
4. Oprávnění k provedení operace.
5. Produktová akceptace výsledku.

Souhlas **nevzniká** mlčením, úspěchem nástroje, výstupem subagenta ani
dokončením bootstrapu.

### 4.3 Záznam schválení

Každé schválení má záznam v `DECISIONS.md` (formát viz tamtéž) s:

- předmětem a přesným rozsahem,
- identifikací schválené revize (commit, nebo explicitní revize dokumentu),
- schvalující osobou/rolí a datem,
- podmínkami, výjimkami a odkazem na nahrazované schválení.

Neukládej celý chat ani nepotřebné osobní údaje.

### 4.4 Změna schváleného obsahu

Před věcnou změnou:

1. Posuď dopad na požadavky, rozhodnutí, rozhraní, úkoly, testy, náklady
   a dosavadní důkazy.
2. Zapiš dotčené odkazy.
3. Urči, co lze provést v rámci delegace a co potřebuje nové schválení.
4. Věcná změna zneplatňuje původní schválení **pouze pro dotčenou část**;
   historický záznam zachovej.
5. Oprava překlepu bez změny významu nové schválení nevyžaduje.
   Při nejistotě se zeptej.

Nový nápad není automaticky požadavek ani úkol → `IDEAS.md`.

---

## 5. Evidence a identifikátory

### 5.1 Prefixy ID

| Prefix | Záznam | Dokument |
| --- | --- | --- |
| `FR-001` | Funkční požadavek | `SPEC.md` |
| `NFR-001` | Nefunkční požadavek | `SPEC.md` |
| `CON-001` | Závazné omezení | `SPEC.md` |
| `AC-001` | Akceptační kritérium | `SPEC.md` |
| `T-001` | Úkol | `TASKS.md` |
| `DEC-001` | Rozhodnutí / schválení | `DECISIONS.md` |
| `Q-001` | Otevřená otázka | `PROJECT.md` |
| `IDEA-001` | Nápad | `IDEAS.md` |

Pravidla:

- Nové ID = nejvyšší existující + 1 (pouze při serializovaném přidělování
  jedním koordinátorem).
- ID nepřečíslovávej, nepoužívej znovu, neměň při přejmenování.
- Nadpis záznamu obsahuje **pouze ID** (`## T-001`); lidský název je v poli
  `Název` pod ním. Kotva je pak stabilní: `TASKS.md#t-001`.
- Vzory v code blocích nebo v sekci „Vzor“ **nejsou záznamy** a nevyčerpávají ID.

### 5.2 Stavy

| Typ | Stavy |
| --- | --- |
| Požadavek, AC | `navrh` → `ke-schvaleni` → `schvaleno` / `zamitnuto`; později `nahrazeno` |
| Rozhodnutí | `navrh` → `ke-schvaleni` → `prijato` / `zamitnuto`; později `nahrazeno` |
| Úkol | `nezahajeno` → `pripraveno` → `rozpracovano` → `k-overeni` → `dokonceno`; kdykoli `blokovano`, `zruseno` |
| Otázka | `otevreno` → `vyreseno` / `odlozeno` |
| Nápad | `k-posouzeni` → `k-rozhodnuti` → `v-task` / `odlozeno` / `zamitnuto` |

Doplňující pravidla:

- `schvaleno` / `prijato` musí odkazovat na konkrétní `DEC-*` se záznamem schválení.
- `pripraveno` vyžaduje: jasný rozsah, splněné závislosti, potřebná schválení,
  realizovatelný způsob ověření.
- `blokovano` má důvod a podmínku odblokování. `zruseno` zachová důvod a vazby.
- `odlozeno` u otázky neruší její blokující dopad.
- `v-task` znamená převedení, ne dokončení; důkazy patří do `TASKS.md`.
- Pořadí v souboru není závislost.

### 5.3 Vazby

- Každé `AC-*` schváleného **aktivního** přírůstku je pokryto alespoň jedním
  `T-*`. Budoucí požadavky mimo aktivní přírůstek úkoly mít nemusí.
- Implementační úkol odkazuje na `AC-*`. Průzkum, příprava toolchainu
  a procesní práce odkazují na explicitní zadání nebo `DEC-*`.
- Nahrazující záznam odkazuje na nahrazovaný a naopak.
- Pokrytí není splnění.

---

## 6. Pracovní session

### 6.1 Začátek

1. Načti `AGENTS.md` (tento soubor) a `PROJECT.md`.
2. Podle fáze a bodu pokračování načti konkrétní `T-*`, související `AC-*`,
   `FR-*`, `DEC-*` a skutečný stav dotčených souborů.
3. Nenačítej preventivně celý repozitář. Neopakuj bootstrap.
4. Předchozí chat ani předávací zpráva nejsou automaticky aktuální pravda –
   porovnej s worktree. Bezpečnostně významný rozpor vyjasni před akcí.

### 6.2 Přerušení a předání

Zapiš do existujících evidencí (nic nového nezakládej):

- `TASKS.md` – stav a důkazy aktuálního úkolu,
- `SPEC.md` / `DECISIONS.md` – změněné požadavky nebo rozhodnutí,
- `PROJECT.md` – odkaz na aktivní práci, poslední bod pokračování,
  neověřené změny, další bezpečný krok.

### 6.3 Obnova

Porovnej záznam se skutečným worktree a dostupností důkazů. Stav `dokonceno`
nenastavuj jen podle předchozího shrnutí.

### 6.4 Zastavení

Při chybějícím oprávnění, protichůdných vstupech nebo opakovaném selhání
(max. 2 pokusy stejného postupu): zastav dotčenou činnost, popiš blokaci,
vyžádej rozhodnutí. Neobcházej kontrolu kvůli „úspěšnému“ stavu.

---

## 7. Delegování a souběh

Základ funguje s **jedním agentem**. Nedostupnost subagentů není blokace.

Deleguj jen ohraničenou práci, které pomůže oddělený kontext, odbornost nebo
omezení nástrojů. Subagent nesmí rozšířit oprávnění, schvalovat za člověka
ani měnit rozsah. Otázky pro člověka předává průvodci.

Předávací protokol (povinný):

```text
Cíl:
Schválené vstupy a jejich revize:
Povolené činnosti a vlastnictví souborů:
Očekávaný výstup a způsob ověření:
Podmínky zastavení a eskalace:
Způsob předání výsledku:
```

Průvodce integruje výsledek **podle důkazů**, ne podle tvrzení subagenta.

Souběh: výchozí režim je jeden zapisující agent. Paralelní zápis pouze
s jasným rozdělením souborů (nebo izolovanými worktree) a určeným
integrátorem. Nová ID přiděluje jeden koordinátor. Před integrací ověř
skutečné změny a konflikty; konflikt nikdy neskrývej.

---

## 8. Ověření, dokončení, akceptace

Tři odlišné skutečnosti:

| Stav | Význam |
| --- | --- |
| **Implementováno** | Změna existuje. |
| **Ověřeno** | Proběhly relevantní kontroly s dohledatelným výsledkem. |
| **Akceptováno** | Oprávněný člověk přijal konkrétní výsledek včetně odchylek. |

Úkol je `dokonceno`, až splní své podmínky **včetně ověření**. Vyžaduje-li
lidskou akceptaci, musí být doložena. Dokončení technických úkolů není
akceptace produktu.

Důkaz v `TASKS.md` uvádí:

1. Co a proti jakému AC/podmínce se ověřovalo.
2. Jakou revizi nebo stav worktree pokrývá.
3. Použitý postup/příkaz a skutečný výsledek.
4. Prostředí a omezení opakovatelnosti.
5. Neprovedené kontroly, chyby, známé odchylky.

Není důkazem: návrh testu, checklist, úspěšný zápis souboru, konec session,
důkaz ze starší revize. Změna testu nesmí pouze oslabit očekávání.

Používej existující kontroly a nejmenší relevantní rozsah. Nevymýšlej
příkazy pro neexistující toolchain; nehlas testy jako úspěšné, pokud neběžely.

Výjimka musí mít rozsah, důvod, schvalujícího a záznam zbytkového rizika nebo
navazujícího úkolu. Neověřené AC zůstává neověřené, i když člověk přijal
vydání s tímto omezením.

---

## 9. Automatizace a rozšíření

Hooks, CI, auditní logy, vlastní agenti a skills **nejsou součástí
bootstrapu**. Požadavek na ně zapiš jako `Q-*` nebo `IDEA-*`.

Před realizací vyjasni: události, oprávnění, ochranu dat, retenci, chování
při selhání, deduplikaci, souběh, manuální náhradu, způsob ověření.

Automatizace smí shromažďovat důkazy; nesmí odvozovat schválení, akceptaci
ani splnění AC z úspěchu nástroje. `TASKS.md`, `DECISIONS.md` a případný
auditní log si nesmí konkurovat jako zdroj stavu.

Dokumenty, role a brány přidávej podle rizika, ne kvůli představě úplnosti.

---

## 10. Vstupní body

| Postup | Kdy | Soubor |
| --- | --- | --- |
| Discovery | Zahájení nebo obnova specifikace. | `.github/prompts/discover-project.prompt.md` |
| Plánování přírůstku | Schválený rozsah → návrh řešení → úkoly. | `.github/prompts/plan-increment.prompt.md` |
| Práce na úkolu | Konkrétní `T-*`. | `.github/prompts/work-task.prompt.md` |

Každý postup funguje v nové session bez původního chatu a odkazuje na tento
řád; neopisuje jej.
