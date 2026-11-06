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

## DEC-002

- Předmět: Prostředí a skladba dema
- Typ: technicke-rozhodnuti
- Kontext: [DEC-001](#dec-001), [FR-001](SPEC.md#fr-001), [FR-004](SPEC.md#fr-004), [NFR-001](SPEC.md#nfr-001) a [CON-001](SPEC.md#con-001). V repozitáři zatím není aplikační kód ani toolchain.
- Varianty:
  - A: Lokální desktopová aplikace v Pythonu s Pygame, NumPy a OpenCV. Nabízí přímou práci s maticemi a obrysy, ale vyžaduje závislosti včetně binární knihovny.
  - B: Lokální webová aplikace v JavaScriptu a Canvasu. Vykreslování běží v prohlížeči, ale práci s obrysy a budoucí připojení ToF by bylo nutné vyřešit samostatně.
- Výsledek: Návrh agenta je varianta A: oddělit zdroj snímků, výběr hloubky a obrysů, efekty a zobrazení v lokálním okně. Rozhraní zdroje předává matici a čas snímku; demo používá CSV, nikoli kameru. Bez databáze, síťové služby a ukládání zpracovaných hloubkových dat.
- Důvod: Návrh přímo podporuje zpracování matic i 2D animaci a ponechává prostor pro pozdější jiný zdroj snímků, aniž by jej nyní implementoval.
- Důsledky: Instalace závislostí vyžaduje samostatné oprávnění. Dostupnost toolchainu, výkon, licence závislostí a kompatibilita s budoucím Raspberry Pi nebo ToF hardwarem zatím nebyly ověřeny.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: DEC-002, doporučená varianta A a uvedená omezení.
  - Revize: `DECISIONS.md`, návrhy DEC-002 až DEC-006 před zapsáním souhlasu dne 2026-11-06; SHA-256 souboru `0d309f74e7ba5ce0d80138026ba92d51b5a86ce0fcfcde83342d369e823dbe40`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Souhlas nezahrnuje instalaci závislostí ani spuštění služeb.

## DEC-003

- Předmět: Formát a načítání časové posloupnosti CSV
- Typ: technicke-rozhodnuti
- Kontext: [FR-001](SPEC.md#fr-001), [CON-001](SPEC.md#con-001) a [Q-004](PROJECT.md#q-004). Přesná struktura vstupního CSV dosud nebyla stanovena.
- Varianty:
  - A: Jeden CSV soubor pro posloupnost, s jedním řádkem na bod snímku a sloupci `frame,time_ms,x,y,depth`.
  - B: Samostatná tabulka CSV pro každý snímek a zvláštní určení jejich pořadí a času. Tabulky jsou názornější, ale práce s posloupností vyžaduje více souborů.
- Výsledek: Návrh agenta je varianta A. `frame` označuje snímek, `time_ms` jeho čas, `x` a `y` souřadnice bodu a `depth` bezrozměrnou konečnou číselnou hodnotu. Body každého snímku tvoří úplnou obdélníkovou mřížku stejných rozměrů; souřadnice jsou nezáporná celá čísla od nuly, časy jsou v rámci snímku shodné a mezi snímky rostou. Duplicitní nebo chybějící body, neplatná čísla či rozporné časy se oznámí jako chyba, nikoli tiše opraví.
- Důvod: Jednoznačný návrh formátu dovoluje přehrát časovou posloupnost a ověřit vstup bez předpokladu skutečné ToF kamery.
- Důsledky: Hodnoty 0–1500 jsou pouze příklad, nikoli povinný limit vstupu. Čtení jednoho souboru v daném okamžiku nerozhoduje o pevné volbě vzorku ani o výběru více souborů; Q-004 zůstává otevřená. Chybová zpráva nemá ukládat ani vypisovat celé hloubkové mapy.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: DEC-003, doporučený CSV formát varianty A a uvedená validace.
  - Revize: `DECISIONS.md`, návrhy DEC-002 až DEC-006 před zapsáním souhlasu dne 2026-11-06; SHA-256 souboru `0d309f74e7ba5ce0d80138026ba92d51b5a86ce0fcfcde83342d369e823dbe40`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Q-004 zůstává otevřená.

## DEC-004

- Předmět: Výběr hloubky a získání obrysů
- Typ: technicke-rozhodnuti
- Kontext: [FR-001](SPEC.md#fr-001), [FR-002](SPEC.md#fr-002) a [AC-001](SPEC.md#ac-001).
- Varianty:
  - A: Práh nad maticí NumPy a získání hranic pomocí OpenCV. Zavádí závislost, ale využívá existující funkce pro obrysy.
  - B: Práh a vlastní výpočet hranic jen pomocí NumPy. Má méně závislostí, ale více vlastní logiky a případů k ověření.
- Výsledek: Návrh agenta je varianta A. Pro demo považovat za popředí hodnoty včetně obou mezí `750 <= depth <= 1000` a získat obrysy odpovídajících oblastí. Při více oddělených oblastech v intervalu zobrazit jejich obrysy; samotný hloubkový práh nerozpoznává identitu člověka. Snímek bez hodnot v intervalu je platný stav bez obrysu, nikoli chyba vstupu.
- Důvod: Tento postup vychází z požadovaného hloubkového výběru a pracuje stejně s člověkem i jiným objektem.
- Důsledky: Zahrnutí obou mezí a zpracování více oddělených oblastí jsou návrhy k výslovnému schválení. Šum nebo více objektů ve stejné hloubce může vytvářet další obrysy; jejich potlačení ani rozpoznávání osob není v tomto návrhu slíbeno. Produkční interval zůstává otevřený v [Q-006](PROJECT.md#q-006).
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: DEC-004, varianta A včetně obou mezí intervalu a obrysů všech oddělených oblastí.
  - Revize: `DECISIONS.md`, návrhy DEC-002 až DEC-006 před zapsáním souhlasu dne 2026-11-06; SHA-256 souboru `0d309f74e7ba5ce0d80138026ba92d51b5a86ce0fcfcde83342d369e823dbe40`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Produkční interval v Q-006 zůstává otevřený.

## DEC-005

- Předmět: Vykreslování a pohyb efektů
- Typ: technicke-rozhodnuti
- Kontext: [FR-003](SPEC.md#fr-003), [FR-004](SPEC.md#fr-004), [FR-005](SPEC.md#fr-005), [FR-006](SPEC.md#fr-006), [FR-008](SPEC.md#fr-008) a [AC-001](SPEC.md#ac-001).
- Varianty:
  - A: 2D vykreslování a pohyb částic na CPU v Pygame, s pevně danými parametry.
  - B: GPU shader nebo specializovaný grafický engine. Může lépe zvládat složitější efekty, ale přidává závislosti a požadavky na grafické prostředí, které zatím nejsou ověřeny.
- Výsledek: Návrh agenta je varianta A: hvězdy ponechat po celé obrazovce a zvýšit jejich hustotu u obrysu; částice plynule přitahovat k měnící se hranici, animovat pohasínání a občasný průlet menších hvězd. Při zmizení obrysu přitažlivost postupně uvolnit, aby zůstalo pozadí s hvězdami. Návrh počítá také s obrysovým objektovým prvkem s pevně danou velikostí, bez nastavovacího rozhraní.
- Důvod: Návrh pokrývá požadovaný hvězdný efekt a umožňuje vizuální ladění bez předčasného výběru grafického enginu.
- Důsledky: Koeficient přitažlivosti je bezrozměrný a jeho hodnotu lze určit při vizuálním ladění podle [Q-003](PROJECT.md#q-003). Konkrétní počty, barvy, tvar a velikost objektového prvku zatím nejsou stanoveny a vizuální výsledek bude předložen člověku; žádné číselné cíle se nepředpokládají. Výkon ani plynulost na konkrétním zařízení nebyly změřeny. Tlačítka a přepínání módů zůstávají mimo první přírůstek.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: DEC-005, doporučené CPU vykreslování a uvedené chování efektů.
  - Revize: `DECISIONS.md`, návrhy DEC-002 až DEC-006 před zapsáním souhlasu dne 2026-11-06; SHA-256 souboru `0d309f74e7ba5ce0d80138026ba92d51b5a86ce0fcfcde83342d369e823dbe40`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Konkrétní vizuální výsledek bude předložen člověku; tlačítka nejsou v prvním přírůstku.

## DEC-006

- Předmět: Toolchain a ověřování dema
- Typ: technicke-rozhodnuti
- Kontext: [AC-001](SPEC.md#ac-001), [NFR-001](SPEC.md#nfr-001) a návrhy DEC-002 až DEC-005. Zatím neexistují projektové testy ani konfigurace nástrojů.
- Varianty:
  - A: Projektová konfigurace Pythonu a izolované prostředí, testy v pytest a statická kontrola pomocí Ruff. Vyžaduje další vývojové závislosti.
  - B: Testy pouze pomocí standardní knihovny Pythonu a bez dalšího linteru. Má méně závislostí, ale samostatnou statickou kontrolu by bylo nutné vyřešit jinak.
- Výsledek: Návrh agenta je varianta A. Ověřit čtení a chyby CSV, časovou posloupnost, výběr hodnot 749, 750, 1000 a 1001, obrys na syntetických datech, platný stav bez obrysu a neukládání hloubkových dat. Logiku animace ověřovat s řízeným časem a náhodností; AC-001 doplnit skutečnou vizuální kontrolou pohybu, hustoty hvězd a animací.
- Důvod: Kombinace cílených automatických kontrol a lidského vizuálního ověření odpovídá datovým i vizuálním částem schváleného rozsahu.
- Důsledky: Závislosti, jejich verze a dostupnost prostředí je třeba ověřit při přípravě toolchainu. Schválení tohoto návrhu samo o sobě neopravňuje k instalaci závislostí ani spuštění služeb. Žádné testy ani měření zatím neproběhly.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: DEC-006, doporučený toolchain a uvedený způsob ověřování.
  - Revize: `DECISIONS.md`, návrhy DEC-002 až DEC-006 před zapsáním souhlasu dne 2026-11-06; SHA-256 souboru `0d309f74e7ba5ce0d80138026ba92d51b5a86ce0fcfcde83342d369e823dbe40`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Souhlas nezahrnuje instalaci závislostí ani spuštění služeb.

## DEC-007

- Předmět: Oprávnění k vytvoření izolovaného prostředí a instalaci závislostí
- Typ: opravneni-k-operaci
- Kontext: [T-002](TASKS.md#t-002) vyžaduje místní prostředí a instalaci balíků uvedených v `requirements-dev.txt`, včetně `requirements.txt`.
- Varianty: Udělit přesně toto oprávnění pro T-002, nebo úkol ponechat čekat.
- Výsledek: Člověk udělil výslovný souhlas k vytvoření `.venv` v kořeni repozitáře a instalaci pouze závislostí deklarovaných v `requirements-dev.txt` a zahrnutých přes `requirements.txt`.
- Důvod: Přímá odpověď člověka na žádost o oprávnění k T-002.
- Důsledky: Lze změnit pouze místní izolované prostředí a stáhnout schválené balíky. Oprávnění nepokrývá globální instalaci, další balíky, spouštění služeb ani rozšíření rozsahu.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: Vytvořit `.venv` a nainstalovat právě balíky z `requirements-dev.txt` včetně odkazovaných runtime závislostí.
  - Revize: T-002 v `TASKS.md` a manifests `requirements.txt` a `requirements-dev.txt` ve znění k 2026-11-06.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Při nedostupném Pythonu nebo chybě instalace nepokračovat obcházením problému; zaznamenat blokaci.

## DEC-008

- Předmět: Oprávnění k instalaci kompatibilního Pythonu pro T-002
- Typ: opravneni-k-operaci
- Kontext: [T-002](TASKS.md#t-002) zůstal blokovaný, protože pro Pygame 2.6.1 nebyl na dostupném CPythonu 3.14.7 zvolen binární balík a sestavení ze zdrojů selhalo.
- Varianty: Zachovat schválenou závislost Pygame a použít kompatibilní CPython, revidovat volbu závislosti, nebo T-002 ponechat blokovaný.
- Výsledek: Člověk zvolil zachování Pygame a povolil instalaci kompatibilního Pythonu. Ověření ukázalo CPython 3.13.17 od Python Software Foundation, dostupný jako uživatelská instalace přes winget, a wheel Pygame 2.6.1 `cp313-cp313-win_amd64`.
- Důvod: Zachová se schválený technický návrh a obejde se neúspěšné sestavení Pygame na Pythonu 3.14.
- Důsledky: Lze instalovat CPython 3.13.17 pouze pro uživatele a použít jej pro T-002; schválené závislosti se nemění. Neúspěšné prostředí Pythonu 3.14 bude zachováno pod jiným názvem, nikoli odstraněno.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: Zachovat Pygame a nainstalovat kompatibilní CPython pro pokračování v T-002.
  - Revize: Přímá volba člověka; winget uvádí Python.Python.3.13 verze 3.13.17, vydavatele Python Software Foundation a oficiální instalační URL `python.org`. Metadata PyPI Pygame 2.6.1 obsahují Windows wheel pro CPython 3.13 x64.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Instalace pouze v uživatelském rozsahu; žádné změny schválených závislostí ani globální instalace.

## DEC-009

- Předmět: Produktová akceptace vizuálního dema
- Typ: produktova-akceptace
- Kontext: [T-008](TASKS.md#t-008) předkládá výsledek vizuální kontroly [AC-001](SPEC.md#ac-001) a provizorní parametry efektů.
- Varianty: Přijmout předložený výsledek a parametry, nebo požadovat úpravy.
- Výsledek: Člověk výslovně přijal vizuální výsledek a provizorní parametry dema.
- Důvod: Přímá odpověď člověka: „Přijímám výsledek a provizorní parametry“ po předložení sekvence zvedání paží a snímků vykreslení.
- Důsledky: Pro první demo jsou přijaty pevné parametry: 72 částic, přitažlivost 0,08 na kroku 60 Hz, náběh 180 ms, uvolnění s časovou konstantou 700 ms, průlet každé 3 s po dobu 750 ms a kruhový obrys s poloměrem 12 px. Akceptace se vztahuje na syntetickou posloupnost, nikoli na kameru, produkční data nebo výkon na jiném zařízení.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: Vizuální výsledek T-008 a výše uvedené pevné parametry prvního dema.
  - Revize: Pracovní kopie nad HEAD `c07b45a`; SHA-256 `src/project_china/demo.py`: `913F16D250AB139D469A70929FC6C664A63E56A23841E2DDCA235FD322B23210`; `src/project_china/effects.py`: `A4C89CD7EC8F486E8737E63040D7831E5BB498E78C0D2DA7421FA3596FD9B511`; náhled `T-008-preview.png`: `FBD778F13FE005B9B0268B3F8F150A0721D8DD7B39ACE556095E239497B43FF0`; detail `T-008-raised-frame.png`: `FAEA35DC85AE9A3E9CEE7342F080E37C0001F94D720F7CCBBBC4397DDF4C3692`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Ověření bylo provedeno na syntetické postavě 24×32 vytvořené v paměti; skutečný záznam z kamery ani produkční zařízení nebyly součástí akceptace.
