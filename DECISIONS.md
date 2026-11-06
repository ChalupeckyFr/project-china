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
- Nahrazuje / Nahrazeno: – / částečně v části samostatného průletu v demu ve FR-004 a AC-001 nahrazeno [DEC-013](DECISIONS.md#dec-013).
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
- Nahrazuje / Nahrazeno: – / částečně v části samostatného kruhového prvku pro demo nahrazeno [DEC-012](DECISIONS.md#dec-012) a v části samostatného průletu v demu [DEC-013](DECISIONS.md#dec-013).
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
- Nahrazuje / Nahrazeno: – / kruhový prvek a samostatný průlet byly z následné revize odstraněny podle [DEC-012](DECISIONS.md#dec-012) a [DEC-013](DECISIONS.md#dec-013); počet částic pro detailního člověka změnilo [DEC-015](DECISIONS.md#dec-015); akceptace zde uvedené revize zůstává historická.
- Schválení:
  - Rozsah: Vizuální výsledek T-008 a výše uvedené pevné parametry prvního dema.
  - Revize: Pracovní kopie nad HEAD `c07b45a`; SHA-256 `src/project_china/demo.py`: `913F16D250AB139D469A70929FC6C664A63E56A23841E2DDCA235FD322B23210`; `src/project_china/effects.py`: `A4C89CD7EC8F486E8737E63040D7831E5BB498E78C0D2DA7421FA3596FD9B511`; náhled `T-008-preview.png`: `FBD778F13FE005B9B0268B3F8F150A0721D8DD7B39ACE556095E239497B43FF0`; detail `T-008-raised-frame.png`: `FAEA35DC85AE9A3E9CEE7342F080E37C0001F94D720F7CCBBBC4397DDF4C3692`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Ověření bylo provedeno na syntetické postavě 24×32 vytvořené v paměti; skutečný záznam z kamery ani produkční zařízení nebyly součástí akceptace.

## DEC-010

- Předmět: Zobrazení postavy či objektu hvězdami bez kresleného obrysu
- Typ: schvaleni-rozsahu
- Kontext: Po přijetí předchozí revize v [DEC-009](DECISIONS.md#dec-009) člověk požádal o změnu její vizuální podoby.
- Varianty: Ponechat obrysovou čáru, nebo ji odstranit a tvar nadále zobrazovat hvězdami.
- Výsledek: Člověk zadal odstranění vykreslované obrysové čáry postavy či objektu, aby byl tvar vidět z hvězd.
- Důvod: Přímý požadavek člověka: „odstraň outlinu objektu/postavy, aby to bylo vidět z hvězd“.
- Důsledky: Obrys zůstává interním vstupem pro částice; samostatný kruhový objektový prvek a dosavadní pevné parametry se nemění. DEC-009 zůstává dokladem přijetí předchozí revize; nový vzhled tím není automaticky produktově přijat.
- Stav: prijato
- Nahrazuje / Nahrazeno: – / částečně v části zachování kruhového prvku nahrazeno [DEC-012](DECISIONS.md#dec-012) a v části zachování samostatného průletu [DEC-013](DECISIONS.md#dec-013).
- Schválení:
  - Rozsah: Odstranit přímou kresbu obrysu cíle a zachovat jeho zobrazení pomocí hvězd.
  - Revize: Výslovný požadavek člověka nad stavem projektu na HEAD `553cc19`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Požadavek není akceptací nového vizuálního výsledku; samostatný kruhový prvek nebyl součástí výslovného požadavku.

## DEC-011

- Předmět: Třísekundové kroky a opakování ukázky
- Typ: schvaleni-rozsahu
- Kontext: Člověk požádal o delší rozestup mezi skoky snímků při spuštění ukázkového CSV a o nepřetržité přehrávání.
- Varianty: Zachovat původní časování a zastavení na posledním snímku, nebo prodloužit kroky a opakovat posloupnost.
- Výsledek: Člověk zvolil 3 sekundy mezi skoky a opakování až do vypnutí dema.
- Důvod: Přímá odpověď člověka: „3 pro skoky a loopni to, aby to běželo dokud to nevypnu“.
- Důsledky: Ukázkový soubor má kroky po 3 sekundách; ostatní CSV zachovávají své časové značky podle [DEC-003](DECISIONS.md#dec-003). Pro dobu posledního snímku agent použil odstup posledních dvou snímků; jediný snímek zůstává zobrazený. Požadavek nepředstavuje produktovou akceptaci nové revize.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: Třísekundový odstup ukázkových snímků a opakování až do uživatelského ukončení.
  - Revize: Pracovní kopie nad HEAD `553cc19` včetně předchozí úpravy T-009; SHA-256 `src/project_china/demo.py`: `5634ABABF3A83D0B9DB57A6C765F313D50ACDC6744ECA2E4F36D0633D078B9F4`; `examples/moving_object.csv`: `5D0356DF8E18D263B49B23C007ED3A72046DD4308FCA9AFED130DB64874BDE72`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Třísekundový interval je nastaven v ukázkovém CSV, nikoli vnucen ostatním souborům; další vizuální akceptace zůstává samostatná.

## DEC-012

- Předmět: Odstranění kolečka uvnitř postavy či objektu
- Typ: schvaleni-rozsahu
- Kontext: V demu zůstal po úpravě T-009 samostatný kruhový prvek dříve přijatý v [DEC-009](DECISIONS.md#dec-009).
- Varianty: Kolečko zachovat, nebo odstranit a ponechat vykreslení cíle pomocí hvězd.
- Výsledek: Člověk zadal odstranění kolečka uvnitř objektu.
- Důvod: Přímý požadavek člověka: „odstraň to kolečko uvnitř objektu“.
- Důsledky: Samostatný kruhový prvek se v demu nevykresluje. Obrys zůstává interním vstupem částic; parametry hvězd a přehrávání se nemění. DEC-009 zůstává historickým dokladem přijetí své původní revize.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-005](DECISIONS.md#dec-005) a [DEC-010](DECISIONS.md#dec-010), pouze v části samostatného kruhového prvku pro toto demo / částečně v části zachování samostatného průletu nahrazeno [DEC-013](DECISIONS.md#dec-013).
- Schválení:
  - Rozsah: Odstranit samostatně kreslené kolečko uvnitř cíle; zachovat hvězdy a jejich chování.
  - Revize: Pracovní kopie nad HEAD `553cc19` včetně T-009 a T-010; SHA-256 `src/project_china/demo.py`: `669A8065A002A285ECD721304E2563250136AEDF2D82E5275F3746DC707B704E`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-013

- Předmět: Odstranění prolétající hvězdy v pozadí dema
- Typ: schvaleni-rozsahu
- Kontext: Demo obsahuje samostatný periodický průlet hvězdy v pozadí podle původního rozsahu [DEC-001](DECISIONS.md#dec-001) a technického rozhodnutí [DEC-005](DECISIONS.md#dec-005).
- Varianty: Průlet zachovat, nebo ho odstranit při zachování ostatních hvězd a jejich animace.
- Výsledek: Člověk zadal odstranění prolétající hvězdy v pozadí.
- Důvod: Přímý požadavek člověka: „odstraň létající hvězdu v pozadí“.
- Důsledky: Demo nevykresluje samostatnou prolétající hvězdu ani její stopu; ostatní hvězdy, částice a přehrávání zůstávají zachovány. [DEC-009](DECISIONS.md#dec-009) zůstává historickým dokladem přijetí své původní revize.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-001](DECISIONS.md#dec-001), [DEC-005](DECISIONS.md#dec-005), [DEC-010](DECISIONS.md#dec-010) a [DEC-012](DECISIONS.md#dec-012), pouze v části samostatného průletu v demu / –.
- Schválení:
  - Rozsah: Odstranit samostatnou prolétající hvězdu v pozadí dema; ostatní hvězdy a jejich chování zachovat.
  - Revize: Výslovný požadavek nad pracovní kopií na HEAD `553cc19` včetně T-009 až T-011.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize ani změnou požadavků pro ostatní prostředí.

## DEC-014

- Předmět: Detailní syntetická posloupnost člověka pro demo
- Typ: schvaleni-rozsahu
- Kontext: Člověk požádal o mimořádně detailní CSV simulující člověka pro výkonný počítač.
- Varianty: Statická postava, detailní pózy po třech sekundách, nebo plynulé zvedání a spouštění rukou.
- Výsledek: Člověk zvolil plynulé zvedání a spouštění obou rukou v opakující se sekvenci.
- Důvod: Výslovný požadavek na detailní CSV a odpověď „Plynulé zvedání a spouštění obou rukou v opakující se sekvenci“.
- Důsledky: Vznikne samostatný vymyšlený vstup a reprodukovatelný generátor; původní malé CSV ani renderer se nemění. Agent volí mřížku 256×384 a 120 snímků po 50 ms, tedy šestisekundový cyklus. Modelovaná anatomie není skutečný sken ani záruka přesnosti vůči konkrétnímu člověku.
- Stav: prijato
- Nahrazuje / Nahrazeno: –
- Schválení:
  - Rozsah: Mimořádně detailní syntetický člověk pro demo na výkonném počítači, plynulý pohyb obou rukou a opakování; konkrétní rozlišení a časování jsou volbou agenta.
  - Revize: Výslovný požadavek a upřesnění nad HEAD `d444dd5`.
  - Schválil: člověk
  - Datum: 2026-11-06
  - Podmínky / výjimky: Nejde o produktovou akceptaci výsledného vzhledu ani o změnu třísekundových kroků původního CSV.

## DEC-015

- Předmět: Hustší hvězdný obrys detailního člověka
- Typ: schvaleni-rozsahu
- Kontext: U detailního vstupu [T-013](TASKS.md#t-013) tvořilo obrys postavy jen 72 hvězd podle [DEC-009](DECISIONS.md#dec-009), tedy přibližně jedna hvězda na 33 px obvodu.
- Varianty: Zvýšit počet hvězd pro všechna dema, nebo jen pro detailního člověka a výchozí demo ponechat beze změny.
- Výsledek: Člověk zadal přidání hvězd tvořících obrys člověka. Agent zvolil 360 hvězd jen pro spuštění detailního člověka; výchozí hodnota 72 zůstává.
- Důvod: Přímý požadavek člověka: „u člověka přidej více hvězd, které tvoří jeho obrys“. Ve srovnání 72/240/360/480 hvězd byl obrys při 360 výrazný a stále složený z jednotlivých hvězd, při 480 začínal splývat v čáru.
- Důsledky: Demo přijímá vývojářský parametr `--particles` s výchozí hodnotou 72; skript `runHuman.ps1` pevně používá 360, obsluha hodnotu nenastavuje ([FR-008](SPEC.md#fr-008)). Ostatní parametry efektu se nemění.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-009](DECISIONS.md#dec-009), pouze v počtu částic pro detailního člověka / –.
- Schválení:
  - Rozsah: Více hvězd tvořících obrys člověka; konkrétní počet je volbou agenta.
  - Revize: Výslovný požadavek nad HEAD `3b766b5`; SHA-256 `src/project_china/effects.py`: `4DDC53F8E4D9BDC8A9932F33EAEE07D22E1A861A3907CC286E61A24CA6DC2F80`, `src/project_china/demo.py`: `96CE8A0DD62EF2AA0E3831DCD14CB9EE35801B7ACB542F6E301FFF11B1FDB311`, `runHuman.ps1`: `8200B3F1835B714A31D3E54AE2D8A94FC4812EF282F04E56277BCD9214381910`.
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.