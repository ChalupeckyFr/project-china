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
- Nahrazuje / Nahrazeno: – / kruhový prvek a samostatný průlet byly z následné revize odstraněny podle [DEC-012](DECISIONS.md#dec-012) a [DEC-013](DECISIONS.md#dec-013); počet částic pro detailního člověka změnilo [DEC-015](DECISIONS.md#dec-015); přitažení 0,08 nahradila pružina podle [DEC-018](DECISIONS.md#dec-018); akceptace zde uvedené revize zůstává historická.
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
- Nahrazuje / Nahrazeno: – / Částečně [DEC-016](DECISIONS.md#dec-016), pouze v okamžitém skoku mezi pozicemi.
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

## DEC-016

- Předmět: Plynulé morfování obrysu mezi snímky CSV
- Typ: schvaleni-rozsahu
- Kontext: Při přechodu mezi snímky se tvar obrysu měnil skokově a hvězdy ztrácely přiřazení k bodům obrysu, protože se počet a pořadí cílů měnily. Člověk zadal tři části řešení: interpolaci hloubky před prahováním, převzorkování a ukotvení obrysu s `smoothstep` interpolací a omezení rychlosti s vysouváním nových částí.
- Varianty: (A) jen morfování obrysu bez interpolace hloubky; (B) i interpolace hloubky před prahováním, která zužuje tvar na průnik snímků, takže objekt by uprostřed přechodu zmizel a prsty by blikaly. Časování: přechod přes celou délku snímku, nebo nejvýše 600 ms.
- Výsledek: Člověk zvolil variantu A („contour“) a přechod nejvýše 600 ms („capped“). Agent zvolil 1 024 bodů na konturu, pevné čtvrtiny bodů pro kvadranty, párování podle nejbližšího těžiště a strop rychlosti cílů 900 px/s.
- Důvod: Přímé volby člověka v rozhovoru. Pevné čtvrtiny drží indexy nezměněných kvadrantů a dávají každému snímku jednoznačnou reprezentaci, takže přechody na sebe navazují. Strop 900 px/s leží nad naměřeným běžným pohybem (555 a 840 px/s) a omezuje jen skutečné skoky.
- Důsledky: Ukázkový objekt nadále mění pozici každé 3 s podle [DEC-011](DECISIONS.md#dec-011), ale místo skoku 2,4 s stojí a 600 ms plynule pluje. Snímky kratší než 600 ms, například člověk po 50 ms, se interpolují přes celou délku. Hustota bodů se mezi kvadranty liší podle jejich délky. Změna počtu kontur přeskupí přiřazení hvězd; ty k novým cílům doletí plynule.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-011](DECISIONS.md#dec-011), pouze v okamžitém skoku mezi pozicemi / –.
- Schválení:
  - Rozsah: Morfování obrysu bez interpolace hloubky, přechod nejvýše 600 ms; číselné parametry jsou volbou agenta.
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-017

- Předmět: Realistický anatomický model syntetického člověka
- Typ: schvaleni-rozsahu
- Kontext: Postava z [T-013](TASKS.md#t-013) měla končetiny s konstantní šířkou, válcový trup, ostré zářezy v podpaží a u krku, výstupky na hlavě a strnulé prsty. Člověk zadal úpravu generátoru: zužované kapsle, trojdílný trup s pasem asi 75 % ramen, smin s k = 0,12–0,18, hladkou hlavu, krk 45–50 % hlavy, kompaktní dlaně, 2.5D hloubkový spád, easing `sin²` nebo kubický, zvedání pivotu ramene o 5–8 % výšky trupu nad horizontálou, ohyb lokte 10–20° a modulaci hrudníku. Formát dat a rozhraní se nemají měnit.
- Varianty: smin faktor v metrech (k = 0,15 m) nebo v jednotkách šířky hlavy; easing kubický nebo `sin²`.
- Výsledek: Agent zvolil `SMIN_K = 0.15` v jednotkách šířky hlavy (asi 2,5 cm), easing `sin²`, pas 0,75 × 0,41 m, krk 0,46 šířky hlavy, zvednutí ramene 6,5 % výšky trupu a posun ke krku 2 cm (obojí nastupuje plynule od horizontály), ohyb lokte 10 + 10·sin(π·zvednutí) a dýchání ±1,2 % s rozšířením hrudníku o 1,5 % při vzpažení.
- Důvod: k = 0,15 m by vyplnilo asi 6 cm širokou mezeru mezi visící paží a trupem a vznikla by blána. Kubický easing měl uprostřed pohybu dvojnásobnou rychlost oproti `sin²` a porušil test plynulosti obrysu mezi snímky (12 px > 10 px). Obě volby leží v rámci zadání.
- Důsledky: CSV i API zůstávají beze změny, ale `examples/human_motion.csv` bylo nutné přegenerovat. Model už nemá uši ani jednotlivé prsty. Hloubkový objem zatím renderer nevyužívá (doplněno v [DEC-018](#dec-018)). Požadavky na fyziku částic (pružina, odpuzování, částice uvnitř objemu) z předchozí zprávy člověka nahradilo toto zadání a nejsou realizovány (realizovány později v [DEC-018](#dec-018)).
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-014](DECISIONS.md#dec-014), pouze v modelované anatomii a pohybu / částečně [DEC-019](#dec-019) v hloubkovém profilu.
- Schválení:
  - Rozsah: Úprava generátoru syntetického člověka podle zadání člověka; číselné parametry v povolených rozmezích a jednotka faktoru smin jsou volbou agenta. Smazání a přegenerování `examples/human_motion.csv` člověk výslovně povolil.
  - Revize: Pracovní kopie nad HEAD `51c92cf`; SHA-256 `src/project_china/synthetic_human.py`: `1498246E0588AC6108D8526806D3BFF063D37745BB1127992E6DF2531F598DED`, `tests/test_synthetic_human.py`: `7CAB28A50CB454A9F7B4FB8B7402FB7D4797A3AD437B94FBDAB4634F590F6A57`.
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-018

- Předmět: 2.5D objem částic, pružinová fyzika a turbulence hvězd
- Typ: schvaleni-rozsahu
- Kontext: Člověk zadal úpravu rendereru: cílové body i uvnitř těla s hustotou podle gradientu hloubky, Z-hloubku na velikost (+30–50 %) a alfu (blízko 0,8–1,0, daleko 0,25–0,5), jitter ±1,5–2,5 px, pružinu se stiffness 0,12 a damping 0,85, odrážení volných hvězd rychlými končetinami v poloměru 20–35 px s turbulencí a tlumeným návratem, předalokovaná pole pro všechny částice a striktní oddělení datové vrstvy od vykreslování.
- Varianty: Objem pro všechna dema, nebo volitelně počtem částic; normalizace hloubky pevným rozsahem, nebo min/max na snímek; kreslení `draw.circle`, nebo aditivní gaussovské skvrny.
- Výsledek: Agent zvolil: geometrii objemu v samostatném modulu `volume.py` (paprsky dovnitř obrysu, 12 vrstev na kvantilech váhy `0,25 + gradient/medián`), který renderer dostává jen jako body obrazovky a hloubky (`BodyTargets`); objem volitelný přepínačem `--volume-particles` (výchozí 0, `runHuman.ps1` 1500); normalizaci hloubky min/max přes cíle snímku (plochá hloubka = blízko); velikost +40 %, alfu 0,30–1,00 se třpytem ±15 %; jitter po kružnici s poloměrem 1,5–2,5 px pomalu rotující 0,3–0,9 rad/s; pružinu na referenční tik 1/60 s s podkroky a stropem 40 px/tik; poloměr odpuzování 28 px, práh rychlé končetiny 150 px/s, kolmou turbulenci ±35 % a návrat hvězdy pružinou 2,5/s² s tlumením 3/s; kreslení částic aditivními gaussovskými skvrnami 4×4 do předalokovaného bufferu.
- Důvod: Objekt 4×4 objem nepotřebuje a s menším počtem částic zůstává jeho obrys čitelný. Min/max na snímek funguje pro libovolný rozsah hloubek bez ladění. Gaussovské skvrny umožní subpixelovou polohu a plynulou změnu velikosti; rotující jitter rozbije rastr bez blikání. Všechny číselné volby leží v zadaných rozmezích.
- Důsledky: Pružina nahrazuje lineární přitažení 0,08 z [DEC-009](#dec-009); náběh 180 ms a uvolnění 700 ms zůstávají. `StarEffect.update` přijímá `BodyTargets` i prostou posloupnost bodů. Nativní okno nebylo ověřeno.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-009](#dec-009), pouze v koeficientu přitažení částic / částečně [DEC-019](#dec-019) ve výběru vrstev objemu, koeficientech pružiny a jitteru objemových částic.
- Schválení:
  - Rozsah: Úprava rendereru a částicového systému podle zadání člověka; číselné parametry v povolených rozmezích, volitelnost objemu a normalizace hloubky jsou volbou agenta.
  - Revize: Pracovní kopie nad HEAD `51c92cf`; SHA-256 `src/project_china/volume.py`: `80E1D1E63AF89299743DE2FC52672F06A87AF6D1EB465E98D472227107D2F4E1`, `src/project_china/effects.py`: `D5CE08D90EFBD1AC36DDE60F3FF38FEC9945A1622766817694E8D1F9E00BDE14`, `src/project_china/demo.py`: `E5E97E77CBA8A46D84179F15C0A50428E2F9346B03EB3978284684B7697DB3ED`, `runHuman.ps1`: `2B34B1726A7478B31B23A2F887923BF6D9F3DF4CCD79873ACDE5C7A6453CE4CD`, `tests/test_volume.py`: `778E5FA1CC33312D65D03756693D26F94AD42026CD907D8F98C68E59E8712065`, `tests/test_effects.py`: `504F8EAAF71519FE61ACCC1712841D14F56829D3BD3A3417EEF597CD0A46E39E`, `tests/test_demo.py`: `F0E152DF02D811A51EC8D427D85BF18B2A6A6A696552207568894C0E0D98A93D`.
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-019

- Předmět: Plynulý hloubkový profil bez švů a stochastický objem částic
- Typ: schvaleni-rozsahu
- Kontext: Uvnitř postavy byly vidět ostré čáry, vrstevnice a obrysy segmentů. Člověk zadal: hloubku počítat až ze sloučeného SDF celé postavy (smin) jako hladký sférický nebo parabolický spád bez celočíselného zaokrouhlení; v rendereru odstranit prahování gradientu, vysokou hustotu jen na skutečné vnější hraně a vnitřek vzorkovat stochasticky s pravděpodobností `P = (1 − norm_dist_from_edge)^2,5`; jitter vnitřních částic ±2–4 px a pružinu stiffness 0,18, damping 0,80.
- Varianty: Profil z přímé vzdálenosti od okraje, nebo z lokální poloviční šířky; sférický, nebo superelipsový spád; stochastické body losované každý snímek znovu, nebo pevné náhodné souřadnice na paprscích.
- Výsledek: Agent zvolil: hloubku `rovina − 0,75 · R · sqrt(1 − (1 − t)²)`, kde `t` je vzdálenost od okraje ze sloučeného SDF (vyhlazená σ 2 px) dělená 85 % lokální poloviční šířky `R` (největší vepsaný kruh, vyhlazený σ 3 px); roviny segmentů vážené blízkostí a vyhlazené σ 4 px; nos jako gaussovský reliéf místo segmentu siluety; hrudník a hlava už nemají vlastní hloubkový poloměr. Objemové částice mají pevné náhodné spojité souřadnice `t = 1 − (1 − u)^(1/3,5)` (inverzní transformace hustoty `(1 − t)^2,5`) na paprscích dovnitř obrysu; 16 rovnoměrných bodů na paprsku slouží jen k interpolaci. Jitter objemu 2–4 px vzniká lineárním přemapováním losování obrysu (1,5–2,5 px), takže se nemění pořadí náhodných čísel.
- Důvod: Profil z přímé vzdálenosti od okraje tvořil hřbet podél os končetin a trupu; lokální šířka s plochým vrcholem jej odstraní a je spojitá přes klouby. Superelipsa zvýšila počet pixelů s |laplaciánem| nad 0,5. Nové losování každý snímek by posílalo částice přes celé tělo; pevné souřadnice na morfovaných paprscích zachovávají plynulý pohyb. Všechny číselné volby leží v zadaných rozmezích.
- Důsledky: `examples/human_motion.csv` bylo nutné přegenerovat. Pružina 0,18/0,80 přestřeluje skok o 100 px asi o 47 px; to plyne ze zadaných koeficientů. Funkce `depth_gradient` a parametr gradientu v `build_volume` byly odstraněny. Nativní okno nebylo ověřeno.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-017](#dec-017) v hloubkovém profilu a [DEC-018](#dec-018) ve vrstvách objemu, pružině a jitteru objemu / částečně [DEC-020](#dec-020) v plochém vrcholu profilu, hustotě objemu `(1 − t)^2,5` a pružině 0,18/0,80.
- Schválení:
  - Rozsah: Oprava generátoru a rendereru podle zadání člověka; číselné parametry v povolených rozmezích, tvar profilu a pevné náhodné souřadnice jsou volbou agenta. Smazání a přegenerování `examples/human_motion.csv` člověk výslovně povolil.
  - Revize: Pracovní kopie nad HEAD `35983a2`; SHA-256 `src/project_china/synthetic_human.py`: `0496BE035F81A05CE52A81BF6F67450B870D7C81C248965F8C2573294D531554`, `src/project_china/volume.py`: `4D909594E95EEF2C1462857FBF00FEF39E76CD32D59F9234C4A1444A2C6D2946`, `src/project_china/effects.py`: `EA5F6E1E392A7B1ABC4A863453B192218CF361401AAA606561DFADC462E3C862`, `tests/test_synthetic_human.py`: `9D9B8C98AF5E91C800761906E8C0A7866E70F70018C2128D3C0C338B9E484002`, `tests/test_volume.py`: `52E8C6B38BCDD92F1CB999824DFA4BAE0A881C60E8EE8076A2BC5D815A06B8E6`, `tests/test_effects.py`: `9F207373CB5836C52071A8A33B48DD921C1A9F5B6FF290DFA9370C9A131754C0`.
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-020

- Předmět: Stabilní cíle objemu, kriticky tlumená pružina, výplň bez děr a parabolický profil hloubky
- Typ: schvaleni-rozsahu
- Kontext: Po [DEC-019](#dec-019) člověk nahlásil tři chyby: cíle objemu mezi snímky skákaly až o 100 px a pružina přestřelovala asi o 47 px; hustota `(1 − t)^2,5` tvořila tlusté okraje a černé díry uprostřed těla; plochý vrchol hloubky dělal ostrý přechod. Zadal: párovat částice na blízké cíle nebo stabilně řadit body, kriticky tlumenou pružinu nebo limit rychlosti, rovnoměrnější výplň (např. exponent 0,5–0,8 nebo Halton/Poisson) s mírně hustším okrajem, Fresnel jen alfou a velikostí, obrys jen na vnější hranici siluety, hladký parabolický nebo kosinový profil přes celou šířku, přegenerovat CSV a upravit testy.
- Varianty: Párování na nejbližší cíl každý snímek, nebo pevné rozdělení částic mezi paprsky; exponent 0,5–0,8, nebo lineární hustota; parabolický, kosinový, nebo sférický profil; pružina odvozená z tuhosti 0,18, nebo se stejnou délkou kinetické stopy jako dřív.
- Výsledek: Agent zvolil: pevné váhy paprsků jako průměr délek paprsků přes všechny klíčové snímky (`reference_weights`, demo je počítá při startu), takže počet částic na paprsek se mezi snímky nemění; délku paprsku na hřebeni vzdálenostní mapy (konec před poklesem o 0,75 px), vyhlazenou gaussovsky podél obrysu (σ 4 body z 1 024), prodlouženou 1,3× za osu a omezenou výstupem z masky; tečny pro normály z okna ±8 bodů. Hustotu výplně `1 − 0,8 · t` (inverzní transformace CDF `(t − 0,4 t²)/0,6`). Parabolický profil `1 − (1 − t)²` přes celou lokální poloviční šířku. Kriticky tlumenou pružinu s přesným integrátorem a rychlostí 0,9 na tik 1/60 s, strop posunu 40 px na tik; uvolněné částice tlumí rychlost 0,80 na tik jako dřív.
- Důvod: Přeřazování na nejbližší cíl by u 3 000 částic stálo víc času a neřeší příčinu; skoky vznikaly přerozdělováním částic po obvodu podle délek paprsků aktuálního snímku a skokem délky paprsku v podpaží. Exponent 0,6 nechával u osy jen 23–37 % hustoty okraje (pruh podél středu); lineární hustota s koeficientem 0,5 dávala kvůli překryvu paprsků u osy okraj jen 1,0×, koeficient 0,8 dává mírně hustší okraj 1,15–1,33× a díry ≤ 6,7 px. Parabola měla nejmenší max |laplacián| mimo hlavu (1,01 proti 1,23 s plató, sféra 1,14, kosinus 1,38). Kritická pružina odvozená z tuhosti 0,18 (0,55/tik) zaostávala až o 23 px; 0,9/tik dává stejně dlouhou stopu jako stará pružina (16,4 proti 16,2 px) bez přestřelu.
- Důsledky: `examples/human_motion.csv` bylo nutné přegenerovat. Start dema s objemem trvá asi o 1,1 s déle. Koeficienty 0,18/0,80 z [DEC-019](#dec-019) už pro přitahované částice neplatí. Částice mohou být mimo aktuální siluetu jen o jitter a zpoždění za pohybující se končetinou (nejvýše 11 px), ne přestřelem. Nativní okno nebylo ověřeno.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-019](#dec-019) v plochém vrcholu profilu, hustotě objemu a pružině / částečně [DEC-021](#dec-021) v rozdělení objemu, pružině a jitteru objemu.
- Schválení:
  - Rozsah: Oprava generátoru, geometrie objemu, dema a rendereru podle zadání člověka; způsob stabilizace cílů, tvar hustoty, rychlost pružiny a profil jsou volbou agenta v mezích zadání. Smazání a přegenerování `examples/human_motion.csv` člověk výslovně zadal.
  - Revize: Pracovní kopie nad HEAD `b48774e`; SHA-256 `src/project_china/synthetic_human.py`: `020F8E64AA174DFEABBAB09899D412225EBF098310818CA0C41CE35064C84BEF`, `src/project_china/volume.py`: `1C98931CC78A067D73DA9D71E42CD7C0FB3E933F20514E670E433FB15248CB1D`, `src/project_china/effects.py`: `BE2B3ECC0EED9A420904B656DB4C2F48A1A8CB76A97409BD3504B51F3527522A`, `src/project_china/demo.py`: `039C83C908A7A674020574929E1A111210FED1C576C5045F0F10A0AFF3302FFE`, `tests/test_volume.py`: `3FBFCE39F4A3BC632191CB7ED15D3B4AD9EAC1889729BCB458925AD669C9B427`, `tests/test_effects.py`: `9366CF759A6C085AE7FB7033EC7D47634727905E550553EF129792B2AAFDDD73`.
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-021

- Předmět: Pevná mřížka výplně, párování podle ID a nejbližšího volného cíle, přetlumený pohyb s limitem
- Typ: schvaleni-rozsahu
- Kontext: Po [DEC-020](#dec-020) člověk nahlásil díry v podpaží a trupu, zpožděné plápolání a chaotické shluky. Zadal: párovat částice na nejbližší volný cíl (např. scipy cKDTree) nebo oddělené pooly, přebytečné částice vybledni na místě; kriticky tlumený nebo přetlumený pohyb (např. k = 0,25, d = 0,92, nebo `pos += (target − pos) · 0,25`) s limitem 8–12 px na snímek; uvnitř Poisson-disc nebo pravidelnou mřížku s jitterem ±1 px; zkontrolovat falešnou hranu v podpaží.
- Varianty: Paprsky s pevnými vahami (stav DEC-020), Poisson-disc vzorkování po snímcích, nebo jedna pevná mřížka; párování přes scipy, nebo vlastní v numpy; pružina, nebo exponenciální lerp.
- Výsledek: Agent zvolil: jednu pevnou šestiúhelníkovou mřížku přes celou matici se stálým posunem bodů v kruhu 0,5 grid px; rozestup se při startu nastaví tak, aby nejplnější klíčový snímek potřeboval nejvýš 97 % objemových částic. Cílem je bod mřížky, jehož prolnutá znaménková vzdálenost celé binární siluety je ≤ −0,5 px; ID cíle je index bodu. Hloubka cíle a obrysu se čte z mapy doplněné nejbližším pixelem siluety a lineárně prolíná. Renderer drží cíl, dokud jeho ID existuje; ostatní páruje v kolech, kde si každá volná částice vybere nejbližší volný cíl a cíl dostane nejbližší žadatel. Částice bez cíle stojí a vyblednou s časovou konstantou 120 ms; objemová částice dál než 8–20 px od cíle tmavne. Pohyb `pos += (cíl − pos) · (1 − (1 − 0,25 · síla)^tiky)`, posun nejvýš 10 px za tik 60 Hz. Jitter objemu 0,3–0,6 px. Ray kód (`VolumePicks`, `reference_weights`, `sample_volume`) a `limit_speed` pro objem byly odstraněny.
- Důvod: Statická mřížka je homogenní z definice (minimální vzdálenost ≥ rozestup − 1 px, žádná díra větší než buňka) a cíle se nehýbou, takže párování podle ID nemůže přehodit částici napříč tělem. Poisson-disc po snímcích by cíle přeskupoval. Prolínání SDF celé siluety odstraňuje vnitřní hrany v podpaží. Instalace scipy vyžaduje podle [AGENTS.md](AGENTS.md) souhlas; párování v numpy stačí (p95 vykreslení 8,6 ms). Lerp 0,25 je přetlumený, takže nepřestřelí; 10 px je ve středu zadaného rozsahu 8–12 px.
- Důsledky: Odchylka od navrženého cKDTree (vlastní numpy). Kriticky tlumená pružina 0,9/tik z [DEC-020](#dec-020) se nahrazuje lerpem 0,25/tik; ustálené zpoždění za paží asi 12 px. Při rychlém pohybu paže se hvězdy ze zadní hrany přesouvají na přední; po dobu přeletu jsou tmavé. Výplň má viditelnou pravidelnou strukturu mřížky. Asi 8–10 % objemových hvězd je vyblednutých. CSV se nemění. Nativní okno nebylo ověřeno.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-020](#dec-020) v rozdělení objemu, pružině a jitteru objemu / částečně [DEC-022](#dec-022) ve vzhledu částic a víření hvězd pozadí.
- Schválení:
  - Rozsah: Oprava geometrie objemu, dema a rendereru podle zadání člověka; mřížka, způsob párování, parametry pohybu a vyblednutí jsou volbou agenta v mezích zadání.
  - Revize: Pracovní kopie nad HEAD `492c9f8`; SHA-256 `src/project_china/volume.py`: `5222D4639CF22511F587AC58EF376EA6E3A49CF2793CCE557336F0465116AAE6`, `src/project_china/effects.py`: `C0262E945B0829EADE2599863B149B993197A58480B9C2AAF1E561E73CC32D36`, `src/project_china/demo.py`: `43B57DC506A3D136FD5E378EF725E7062C618B77814B70F4E1C5A24449EE854E`, `tests/test_volume.py`: `C3E179B759D9E3393C44FD0B796584A9D99DBB648A4940D1B0D67B2F3E34C20C`, `tests/test_effects.py`: `B9A36D68E3000B87B5E6AB27E631C845F247C2E93BBD019272DE06FFB1B4F00B`.
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.
## DEC-022

- Předmět: Stínování částic podle hloubky, dvousegmentová paže, dýchání a víření hvězd pozadí
- Typ: schvaleni-rozsahu
- Kontext: Po [DEC-021](#dec-021) člověk zadal: výraznější promítnutí hloubky do velikosti a alfy (blízko 3,5–4,5 px, alfa 0,9–1,0, teplejší odstín; středně 2,0–2,8 px, 0,45–0,65; daleko 1,2–1,8 px, 0,15–0,30); předloktí zaostávající o 0,15–0,2 rad a pokrčení lokte 15–20° při zvedání; dýchání s periodou asi 4 s a amplitudou 2–3 % šířky trupu, zvednutí hrudní kosti a pletence o 3–5 px nad horizontálou; víření hvězd pozadí rychlostí dlaní a předloktí v poloměru 25–40 px (kolmá odpudivá + tečná složka a turbulence) s tlumením 0,90–0,94 za snímek; zachovat předalokovaná pole.
- Varianty: Gaussovské skvrny s větší sigmou, nebo měkké kotouče s kompaktním nosičem; perioda dýchání 3 s v 6 s smyčce, 4 s se švem, 4 s ve 12 s smyčce s krokem 100 ms, nebo 4 s ve 12 s smyčce s krokem 50 ms; ohyb lokte jen jedním směrem, nebo podle zpoždění předloktí; dlaně v rovině předloktí, nebo předsunuté ke kameře; ruční smazání CSV, nebo přegenerování zastaralého CSV skriptem.
- Výsledek: Agent zvolil: každá částice je kotouč `w = alfa · (1 − (d/r)²)²` (váhy pod 0,05 tvaru se zahazují) v předalokovaném jádru 10×10; poloměr 1,5/2,4/4,0 px a alfa 0,22/0,55/0,95 pro blízkost 0/0,5/1, mezi nimi lineárně, s mrkáním 15 %; barva se prolíná z (170, 192, 255) do (255, 238, 210) podle blízkosti vážené jasem; akumulace přes `np.bincount`. Předloktí `REST + span · (1 − cos(2π·fáze − 0,175))/2 − 4°`, loket = nadloktí − předloktí. Dýchání `0,025 · šířka ramen` v šířce hrudníku i výšce ramen, perioda 80 snímků = 4 s ve smyčce 240 snímků po 50 ms (12 s), paže z `snímek % 120` (dva stejné cykly po 6 s); zápěstí předsunuto o 0,040 m a dlaň celkem o 0,075 m ke kameře; `runHuman.ps1` přegeneruje CSV, chybí-li nebo je starší než generátor, přes dočasný `human_motion.csv.new`; zvednutí hrudníku `0,018 m · elevace` (≈ 4,2 px obrazovky) posouvá elipsoid hrudníku, začátek pletence a z poloviny základ krku; lopatkový zdvih ramene z [DEC-017](#dec-017) zůstává. Víření: body obrysu rychlejší než 150 px/s, poloměr 32 px, tečna kosti z bodů obrysu ±3, tlak `0,6 · |v| · normála + 0,8 · v + turbulence ±0,35 napříč`; tlumení 0,92 za referenční krok 60 Hz, pružina návratu 6/s².
- Důvod: Kotouč s kompaktním nosičem drží zadaný poloměr přesně a nepřesytí trup jako široký gauss. Zadaná perioda ~4 s bez švu vyžaduje smyčku 12 s; krok 100 ms rozpadal prolnutí sousedních snímků až na 8 komponent, proto 240 snímků po 50 ms. Dlaně v rovině předloktí měly blízkost ≈ 0,4, zadání je řadí k nejbližším bodům; předsun 0,075 m dává 0,85–1,00 a nechá hrudník na 0,92–1,00 (0,090 m snižoval hrudník na 0,84). `examples/human_motion.csv` je neverzovaný výstup `runHuman.ps1`, který ho podle zadání člověka generuje; nahrazení zastaralé kopie novým výstupem téhož generátoru není mazání projektových dat a bez něj by skript nový pohyb neukázal. Ohyb na straně zaostávání vychází z fázového posunu fyzikálně (setrvačnost) a při zvedání dává 17°. Tuhost návratu 6 při tlumení 0,92/tik dává téměř kritický návrat, takže hvězdy se vrátí bez kmitání.
- Důsledky: CSV má 240 snímků a 608 466 502 B (dříve 296 MB), generování asi 32 s, načtení asi 22 s a ~2,7 GB paměti. Při spouštění paží se loket ohne opačně až o 9°. Vykreslení snímku medián 8,1–8,5 ms, p95 9,4–11,0 ms (T-020: 6,0 / 8,6 ms), pod 16,7 ms pro 60 FPS. Hvězdy pozadí se vychylují až o 56 px. Nativní okno nebylo ověřeno.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-021](#dec-021) ve vzhledu částic a víření hvězd pozadí; částečně [DEC-017](#dec-017) v ohybu lokte a dýchání / –.
- Schválení:
  - Rozsah: Úprava generátoru a rendereru podle zadání člověka; tvar kotouče, barvy, délka smyčky, předsun dlaní, přegenerování zastaralého CSV v `runHuman.ps1` a parametry víření jsou volbou agenta v mezích zadání.
  - Revize: Pracovní kopie nad HEAD `492c9f8` (včetně necommitnuté T-020); SHA-256 `src/project_china/synthetic_human.py`: `EFEF77C64E87713F263C746EECED79854B2FCCDAEAE73EAF29A409840AF4BE68`, `src/project_china/effects.py`: `0D5CD9354B91A19AA84E87350D155A867BDFC000F3683C816DEB5962D3FA08CE`, `tests/test_synthetic_human.py`: `B8580A5880138D959C25EE78CF805AEE1E9633E8A34C912696F8F91B57F3D0BA`, `tests/test_effects.py`: `7AFEE8EB712559A36874690943C3B10A594D7FAF21C7F7B6E215D0CCD6AB567D`, `runHuman.ps1`: `F1D47ED160B884B907E9D6C27433C90C53FF6442FAC09691A674F8223BA21670`; vygenerované `examples/human_motion.csv`: `7A0B05542699F9ED5C355F12F9C2632772B877645ABA83B76937D37D11A50D96`.
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-023

- Předmět: Plné paže, časově stabilní stínování, rovnoměrná hustota a omezení zrychlení částic
- Typ: schvaleni-rozsahu
- Kontext: Po [DEC-022](#dec-022) člověk zadal čtyři opravy:
  1. Paže: předloktí min. 14–18 px a zápěstí min. 10–12 px, vzorkování kolmo na osu kosti, rozptyl kolmo na kost ±2,0–3,5 px.
  2. Blikání: filtr `val = prev · 0,8 + target · 0,2` na poloměr a alfu, stálé souřadnice vnitřních částic trupu vůči tělu.
  3. Hustota: pokles k okrajům max. 25–30 %, hloubka jen jasem (střed 0,95, boky 0,35) a velikostí (3,5 / 1,5 px).
  4. Úvratě: tlumení 0,92–0,95 nebo omezení zrychlení.
- Varianty:
  - px jako body matice, nebo jako pixely obrazovky;
  - kotva trupu: těžiště a rozptyl jádra (2D UV), nebo jen vodorovné těžiště;
  - blízkost: normovaná po snímcích, nebo pevným rozsahem sekvence;
  - rozptyl napříč kostí: náhodný každý snímek, nebo stálý pro částici;
  - úvratě: pružina s tlumením, nebo omezení zrychlení;
  - nové okrajové cíle: nejbližší volná částice kdekoli, nebo jen do poloměru a jinak respawn neviditelné částice z poolu.
- Výsledek: Agent zvolil:
  - Poloměry „px“ jsou pixely obrazovky dema (1 px ≈ 4,24 mm). Nadloktí 0,072/0,064 m, předloktí 0,062/0,044 m (14,6 / 10,4 px), dlaň 0,050 × 0,096 m, předsun dlaně 0,070 m.
  - Mřížka výplně se posouvá jen vodorovně o vážené těžiště jádra (váha `max(vnitřní vzdálenost − 0,5 · max, 0)`), ID zůstávají.
  - Osa kosti: strukturní tenzor gradientu znaménkové vzdálenosti (Gauss σ = 3).
  - Váha končetiny: `1 − smoothstep` lokální poloviční šířky mezi 12 a 16 body.
  - Prostor k okraji: −znaménková vzdálenost × měřítko.
  - Blízkost: pevný rozsah hloubek siluet celé sekvence, oříznutý na 0..1.
  - Blízkost, poloměr i alfa: filtr 0,8/0,2 za referenční tik 60 Hz (`1 − 0,8^tiky`).
  - Pásma: 1,5 / 2,4 / 3,5 px, alfa 0,35 / 0,55 / 0,95; mrkání objemu 5 % (obrysu 15 %).
  - Stálý rozptyl napříč kostí: `u ∈ [−1, 1] · 3 px · váha končetiny`, oříznutý na prostor − 1 px.
  - Pohyb: chtěná rychlost 25 % zbývající vzdálenosti, nejvýše 10 px za tik; změna rychlosti nejvýše 2 px za tik; krok nikdy nepřesáhne zbývající vzdálenost.
  - Párování: uvolněná částice bere volný cíl jen do 12 px. Zbylé nové cíle převezmou částice s přítomností < 0,05, které se přesunou přímo na cíl s jeho stínováním a rozsvítí se. Dálkové párování jen bez neviditelných částic (start).
- Důvod:
  - Zadané poloměry odpovídají tomu, co uživatel vidí na obrazovce.
  - Svislý střed a rozptyl jádra skákaly o 2,8 bodu za snímek, když se visící paže v podpaží slévaly s trupem. 2D UV kotva by tak vnášela přeskakování, proti kterému je zadání. Vodorovné těžiště se mění plynule (krok ≤ 0,23 bodu) a sleduje přenos váhy.
  - Blikání způsobovala hlavně normalizace min/max po snímcích a přímé převzetí blízkosti. Simulace pak ukázala druhou příčinu: přelety částic na vzdálené okrajové cíle přes hrudník. Respawn v poolu je odstraňuje bez alokací.
  - Stálý rozptyl nemění rozložení mezi snímky, takže nevytváří nový šum.
  - Omezení zrychlení s ořezem kroku vylučuje překmit konstrukcí, nezávisle na volbě tlumení.
  - Pevná mřížka má rovnoměrnou hustotu; pokles u okraje je dán jen ořezem siluety (měřeno ≥ 0,7).
- Důsledky:
  - Silueta paží je širší (plocha masky asi 11 300 místo 10 400 bodů).
  - Zužování paže je mírnější (18 : 14 bodů).
  - Dlaně mají blízkost ≥ 0,83, hrudník ≥ 0,92.
  - Hvězda za paží nabírá rychlost nejvýše 2 px za tik², takže za rychlým pohybem zaostává o něco víc.
  - Vykreslení snímku zrychlilo na medián 3,5 ms.
  - CSV má 608 238 502 B.
  - Nativní okno nebylo ověřeno.
- Stav: prijato
- Nahrazuje / Nahrazeno: Částečně [DEC-022](#dec-022) (pásma stínování, normalizace hloubky, předsun dlaní) a [DEC-021](#dec-021) (nehybná mřížka výplně, párování na nejbližší volný cíl bez omezení) / –.
- Schválení:
  - Rozsah: Úprava generátoru, výplně a rendereru podle zadání člověka. Výklad px jako pixelů obrazovky, vodorovná kotva, respawn v poolu a konkrétní parametry jsou volbou agenta v mezích zadání.
  - Revize: Pracovní kopie nad HEAD `492c9f8` (včetně necommitnutých T-020 a T-021). SHA-256:
    - `src/project_china/synthetic_human.py`: `CE3562E13B35306702B5F8BE41AF88AA42D07E05B3F943C57D5CDD8E3196E8E3`
    - `src/project_china/effects.py`: `4ACDFA5421D1D5FFEBC0D21423A95C80F8C65DAD068580C3D685150F883A1383`
    - `src/project_china/volume.py`: `EFC9F7C8E1CA6AE60F17838852C28117B40F17D188EE1C938CC0075FF6F0AD36`
    - `src/project_china/demo.py`: `6C6CF4846E8FA1777FFB936C39D2197A49BFAD6D9514FCC0D16FE2F715BDFDD7`
    - `tests/test_synthetic_human.py`: `ED477276910DF66B2CDDE93DA8D9207C15729CE10E12835852C31A5DDE934A4C`
    - `tests/test_effects.py`: `8AE4555C1A103261596651A7E437E2E1D5502B63EC0C9290799792B6F124C80E`
    - `tests/test_volume.py`: `49747944B38F875E5051955DBE20D4700B8E331578F9433C1AAABC909CDB2C54`
    - vygenerované `examples/human_motion.csv`: `9CF201211C2F4FDBA4E495EC68C94900C82572B53E790F0D31A086A89FE08148`
  - Schválil: člověk
  - Datum: 2026-11-07
  - Podmínky / výjimky: Požadavek není produktovou akceptací nové vizuální revize.

## DEC-024

- Předmět: Rozsah úprav desktopové aplikace AbstractView
- Typ: schvaleni-rozsahu
- Kontext: Člověk 2026-11-08 zadal vizuální a výkonnostní úpravy s obrázky 1–6 a videem animace běhu Fištróna.
- Varianty: Jednotlivé detaily vzhledu a technologie byly výslovně delegovány agentovi; přepínač tématu, reset a výběr efektů mají zůstat v dosavadní podobě mimo konkrétně zadané opravy.
- Výsledek: Aktivní přírůstek obsahuje [FR-009](SPEC.md#fr-009), [NFR-002](SPEC.md#nfr-002), [AC-002](SPEC.md#ac-002) a [AC-003](SPEC.md#ac-003). Maximální počet 2 500 hvězd je součástí opravy. Produktovou podobu po provedení posoudí člověk.
- Důvod: Přímé zadání člověka.
- Důsledky: Nové úkoly T-023 až T-025; původní akceptace T-022 zůstává otevřená.
- Stav: prijato
- Nahrazuje / Nahrazeno: – / DEC-026 pouze v části podoby Fištróna a nastavení
- Schválení:
  - Rozsah: Přesně FR-009, NFR-002, AC-002 a AC-003 v uvedené revizi SPEC.md; volba konkrétní technologie v těchto mezích je delegována agentovi.
  - Revize: `SPEC.md` SHA-256 `A8806FF376A933540FD244FA6A81F5DA6A40043B1F1E6B7C8CB84C3C33977711` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-08
  - Podmínky / výjimky: Jde o oprávnění k úpravám a ověřování, nikoli o produktovou akceptaci výsledku.

## DEC-025

- Předmět: Způsob vykreslení a omezení práce v hlavním vlákně AbstractView
- Typ: technicke-rozhodnuti
- Kontext: Původní pozadí se zvětšovalo z polovičního rozlišení a zaoblené karty se počítaly pomocí velkých polí NumPy při každém snímku; při 2 500 hvězdách renderer indexoval mimo obrys.
- Varianty: Nový grafický framework; zachování Tk/Pygame s optimalizací; ukládání předem vykreslených celých videí. Zvolená druhá možnost v rámci delegace DEC-024.
- Výsledek: Pozadí a karty kreslí OpenCV v cílovém rozlišení, statické pozadí a pózy Fištróna se ukládají do omezených pamětí, kola běhu se otáčejí na hotovém spritu, scéna ovládacího panelu běží nejvýše 30 snímků za sekundu a při minimalizaci se nekreslí. Fyzické kamery se vyhledávají na vedlejším vlákně; nabídka virtuální kamery se ukáže ihned. Výběr cílů hvězd indexuje podle počtu dostupných bodů.
- Důvod: Měření celé scény bez Tk kleslo přibližně z 33 na 5 ms na snímek; samotné pozadí z 610 na 4 ms při 960×720. Není potřeba další runtime závislost pro renderer.
- Důsledky: Vzhled kresby je plošší a ostřejší; nativní rychlost na různých počítačích a subjektivní vzhled vyžadují lidské posouzení.
- Stav: prijato
- Nahrazuje / Nahrazeno: – / DEC-027 pouze v části Fištróna a panelu
- Schválení:
  - Rozsah: Technická volba pro FR-009 a NFR-002 v mezích delegace DEC-024.
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `abstractview_app/ui.py` `7A9EA56AE3B146A53FAC7CBF4CCD1757666C7675D08342672DA32121E9867815`, `abstractview_app/scene.py` `0719AB48BE0B8BF0E933EF2CB966C9C3D28AA8F262DE2AC765E03E3FEC0F4D33`, `abstractview_app/renderer.py` `F1E83C10CB616B2F59337A596868D8C0B817F5A9525DE0CF15EFC778A8F54943`, `abstractview_app/samples.py` `B9A686EBCA1D5EC8D2586352A5706735C908EAA2A0044D3D7BDF4DFF8359F989`, `abstractview_app/config.py` `16EBE2559F23C0CDC31A136ECF86AC816FB5DD92345D847DFA1E193D0C9D67F3`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-024)
  - Datum: 2026-11-08
  - Podmínky / výjimky: Bez závazného číselného cíle FPS; akceptaci vzhledu provede člověk. Podobu Fištróna a panelu v této historické revizi mění [DEC-027](#dec-027).

## DEC-026

- Předmět: Nová podoba Fištróna a skleněné nastavení AbstractView
- Typ: schvaleni-rozsahu
- Kontext: Člověk po náhledu z 2026-11-08 žádá dvourozměrný hologram podle neonové kočky z obrázku a chůze z videa, novou polohu podložky a širší prosklené nastavení.
- Varianty: Rozsah vyplývá z přímého zadání člověka; konkrétní kresba a způsob zobrazení skla jsou technickou volbou agenta.
- Výsledek: Schváleny [FR-010](SPEC.md#fr-010) a [AC-004](SPEC.md#ac-004). Mění se pouze dotčená část [FR-009](SPEC.md#fr-009); ostatní části [DEC-024](#dec-024) platí dál.
- Důvod: Konkrétní vizuální zpětná vazba člověka k dosavadnímu náhledu.
- Důsledky: Nový úkol [T-026](TASKS.md#t-026); předchozí akceptace [T-023](TASKS.md#t-023) a [T-024](TASKS.md#t-024) zůstává otevřená.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-024 pouze v části podoby Fištróna a nastavení / DEC-028 pouze v části podoby Fištróna a přechodu motivu
- Schválení:
  - Rozsah: FR-010 a AC-004 v uvedené revizi SPEC.md, technické provedení v mezích tohoto zadání.
  - Revize: `SPEC.md` SHA-256 `0FE3DEA22C64327AE0BB63DEBFFCB1A8B43929099CE33BF05E7833CE969E5F9B` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-08
  - Podmínky / výjimky: Produktová akceptace nové podoby proběhne až po jejím vyzkoušení.

## DEC-027

- Předmět: Vykreslení dvourozměrného hologramu a skleněného panelu
- Typ: technicke-rozhodnuti
- Kontext: Původní model používal prostorové stínování a pohyblivý květináč. Tk nepodporuje průhledné pozadí vnořených ovládacích prvků; první způsob skládání skla s NumPy zatěžoval hlavní vlákno.
- Varianty: Externí animované soubory; nový grafický framework; kreslené sprity v OpenCV a prosklený rám s barevně sladěnými ovládacími prvky. Zvolena třetí možnost bez nové závislosti.
- Výsledek: Starý prostorový model a květináč byly odstraněny. Fištrón je sada předkreslených plochých neonových póz s pevným projektorem vlevo dole; běh má osm fází a na širokém panelu se zastaví na průhledné části skla vedle ovládání. Skleněný rám ukazuje poušť za panelem, ovládací plocha má sladěný odstín a zůstává čitelná. Složení skla používá OpenCV masku bez pomalého indexování NumPy.
- Důvod: Měřená část scény s panelem a hologramem při 1100×730 klesla po opravě skla přibližně ze 17,0 na 4,9 ms na snímek; v nativním okně aplikace ukazovala přibližně 28 FPS při otevřeném nastavení.
- Důsledky: Sklo je v Tk vizuálně simulované; střed ovládací plochy má jednolitý podklad, poušť je přímo vidět v rámu a nad ovládáním. Vzhled a plynulost na zařízení člověka čekají na posouzení.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-025 pouze v části Fištróna a panelu / DEC-029 pouze v části Fištróna a přechodu motivu
- Schválení:
  - Rozsah: Technická volba k FR-010 a NFR-002 v mezích DEC-026.
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `abstractview_app/scene.py` `78724E18B5722DBAA950719FCC952231221EEAE12A755F309909EC5984C40DE0`, `abstractview_app/ui.py` `796B51166666B44D94ED0BFB011513F04D8C88663E43D169BA785863B494AB82`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-026)
  - Datum: 2026-11-08
  - Podmínky / výjimky: Bez garantovaného FPS na jiném zařízení; finální podobu potvrdí člověk.

## DEC-028

- Předmět: Nahrazení neonového Fištróna kreslenou postavou a oprava přepnutí motivu
- Typ: schvaleni-rozsahu
- Kontext: Člověk 2026-11-08 označil předchozí podobu za nevyhovující a zadal šest konkrétních póz, rychlejší běh, novou polohu plátna, odstranění textu a plynulé přepnutí motivu.
- Varianty: Konkrétní technologie kresby a animace byla ponechána agentovi; vzhled a pózy určil člověk.
- Výsledek: Schváleny [FR-011](SPEC.md#fr-011) a [AC-005](SPEC.md#ac-005). Neonová část FR-010 a AC-004 je nahrazena; dřívější nesouvisející části zadání zůstávají platné.
- Důvod: Přímá oprava od člověka podle vizuálního náhledu.
- Důsledky: Nový [T-027](TASKS.md#t-027), dřívější T-026 se neakceptuje v jeho původní podobě.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-026 pouze v části podoby Fištróna a přechodu motivu / –
- Schválení:
  - Rozsah: FR-011 a AC-005 v uvedené revizi SPEC.md; technické provedení v jejich mezích.
  - Revize: `SPEC.md` SHA-256 `3C9D4126F1F8E7B67DB85F8D4FF30D548273685E26B3BD526A4F42C8566B315B` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-08
  - Podmínky / výjimky: Zadání dovoluje implementaci a ověření; produktovou akceptaci nového vzhledu provede člověk po vyzkoušení.

## DEC-029

- Předmět: Šest 2D kreslených póz a omezení práce při změně motivu
- Typ: technicke-rozhodnuti
- Kontext: Opakované přebarvování všech Tk prvků trvalo v profilu přibližně 53–110 ms na krok. Předchozí procedurální neonový Fištrón neodpovídal zadanému stylu.
- Varianty: Nový grafický framework; ruční kresba v OpenCV; šest průhledných PNG póz a dosavadní OpenCV skládání. Zvolena třetí možnost v mezích DEC-028.
- Výsledek: Šest kreslených PNG je uloženo v `abstractview_app/assets`, za běhu se jednou načtou a zmenší do paměti. Chůze používá hotovou pózu s rychlým posunem a lehkým nadskakováním. Poušť se vykresluje průběžně; barvy ovládání se mění v deseti krocích střídavě s renderem scény. Skryté posuvníky svůj obrázek překreslí až při zobrazení. Fyzické kamery se při souběžném skenu serializují.
- Důvod: Původní paleta blokovala opakovaně na 53–110 ms. Nativní měření nové varianty ukázalo v obou směrech a s otevřeným i zavřeným nastavením jen 0–3 kroky nad 33 ms z 42 oproti 6–12 krokům při souběžném přebarvení a renderu. Obrázkové pózy splňují požadovaný vzhled bez výpočtu prostorového modelu.
- Důsledky: Výsledný vzhled a subjektivní plynulost ještě posoudí člověk. Barvy Tk ovládání se mění po desetinách přechodu, poušť má jemnější snímkování.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-027 pouze v části podoby Fištróna a přechodu motivu / –
- Schválení:
  - Rozsah: Technická volba pro FR-011 a NFR-002 v mezích delegace DEC-028.
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `abstractview_app/scene.py` `5CA969114E633B2783A81AB3A79CB106B0A1F413DBF30705E5F38EF7156014FD`, `abstractview_app/ui.py` `5D123CCECB9D48450AB282AB18245E810AC56CDDDC397BECAF3DFC8497065B5E`, `abstractview_app/samples.py` `8670DC611C192EC6203A5323B402475077C5477794D16EEA606838B85AE1F993`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-028)
  - Datum: 2026-11-08
  - Podmínky / výjimky: Bez garantovaného FPS na jiném zařízení a bez produktové akceptace.

## DEC-030

- Předmět: Samostatné přesouvatelné panely a nové reakce Fištróna
- Typ: schvaleni-rozsahu
- Kontext: Člověk 2026-11-08 ocenil kreslenou podobu, ale zadal změnu úderu, nové pózy u panelu, současně otevřená nastavení s uloženou polohou, opravu nočního vykreslení a oživení plátna.
- Varianty: Vzhled interakcí určil člověk; technické provedení bylo ponecháno agentovi.
- Výsledek: Schváleny [FR-012](SPEC.md#fr-012) a [AC-006](SPEC.md#ac-006) v návaznosti na FR-011 a NFR-002.
- Důvod: Přímé zadání člověka podle nového videa a obrázku.
- Důsledky: [T-028](TASKS.md#t-028); vizuální akceptace nové revize po vyzkoušení.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-028 pouze v části počtu póz a chování u nastavení a tlačítka / –
- Schválení:
  - Rozsah: FR-012 a AC-006 v uvedené revizi SPEC.md; technické detaily v jejich mezích.
  - Revize: `SPEC.md` SHA-256 `5887F2C9AAE42E3D87E0EFCA8DCD6AFE5C7F49AF20D3B36A206A882B1D48D6A5` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-08
  - Podmínky / výjimky: Nejde o akceptaci nové implementace ani oprávnění ke commitu či publikaci.

## DEC-031

- Předmět: Vnořené plovoucí panely a úspornější kreslení interakcí
- Typ: technicke-rozhodnuti
- Kontext: Tři souběžně otevřená nastavení potřebují spolehlivý fokus, uloženou polohu a rychlé vykreslení. Tk okna vložená přímo do canvasu se při překrytí nevrstvila podle aktivního panelu.
- Varianty: Samostatná systémová okna; položky `create_window` v canvasu; rámy uvnitř hlavní scény umístěné přes `place`. Zvolena třetí možnost.
- Výsledek: Každá skupina nastavení má jediný interní panel se společným záhlavím a obsahem. Pořadí aktivních panelů se ukládá spolu s polohou do JSON. Dvě nové kreslené PNG pózy ukazují záda při změně hodnot a tlak při přesouvání. Úder používá skutečný střed tlačítka; animace prachu předchází změně výstupu o 620 ms. Malé bitmapy posuvníků a tlačítek se kreslí přes OpenCV, během mezikroků motivu se část obrázků nepřepočítává. Poušť přechází plynule, hromadné přebarvení Tk ovladačů probíhá ve čtyřech krocích. Otevření panelu ihned vynutí vykreslení scény.
- Důvod: Aktivní panel se musí celý překrýt přes ostatní; zkouška v nativním okně potvrdila správné vrstvení. Pózy zůstávají 2D a nevyžadují výpočet 3D modelu. Kratší práce s grafikou snižuje dobu kroků přechodu motivu.
- Důsledky: Všechny tři panely mohou být otevřené současně, ale na menším monitoru se překrývají a obsah může vyžadovat posun. Při třech otevřených panelech zůstávají čtyři kroky motivu delší než 33 ms z 19 měřených kroků; viz [T-028](TASKS.md#t-028). Vzhled a subjektivní odezvu posoudí člověk.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-029 jen v části počtu póz a způsobu vykreslení malých ovladačů / –
- Schválení:
  - Rozsah: Technická volba pro FR-012, AC-006 a NFR-002 v mezích delegace DEC-030.
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `config.py` `5E5084FCB1EC92ED312D2C83B8038E366F45B775AD9187352091157489D25625`, `ui.py` `C636C918F50C1F5116E3CC7022696D4A5879B34FF2D16F7707F9FDDD0B9F8B11`, `scene.py` `84C53379EBD61B0D51C6950CAFACA388F15A7985EACA1AAAF81E73C0EABBA3D6`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-030)
  - Datum: 2026-11-08
  - Podmínky / výjimky: Produktová akceptace ani výkon na cílovém monitoru z technických testů neplynou.

## DEC-032

- Předmět: Nahrazení hlavního EXE a odstranění pomocných náhledů
- Typ: schvaleni-operace
- Kontext: Člověk požádal o jeden přehledný spustitelný soubor v kořeni projektu a odstranění nepotřebných pracovních souborů.
- Varianty: Další náhledový EXE; aktualizace `abstractview.exe`. Zvolena aktualizace hlavního souboru.
- Výsledek: Povoleno přepsat `abstractview.exe` ověřenou revizí T-028 a odstranit starší náhledové EXE a dočasné pracovní soubory. Projektová data a uživatelské nastavení zůstávají potřebné.
- Důvod: Přímé zadání člověka 2026-11-08; více náhledových EXE bylo nepřehledných.
- Důsledky: Jediným aktuálním spustitelným souborem je `abstractview.exe`; starší náhledy zůstávají popsány v historické evidenci, ale nejsou určeny ke spuštění.
- Stav: prijato
- Nahrazuje / Nahrazeno: – / –
- Schválení:
  - Rozsah: Přepsání hlavního EXE a odstranění nepotřebných pracovních a náhledových souborů v kořeni projektu; bez commitu a publikace.
  - Revize: Hlavní EXE SHA-256 `C116AD6170B9E38365C103CB30D5CF221453C896BBF5E9165DD55A1E79455952` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-08
  - Podmínky / výjimky: Zachovat soubory potřebné k běhu aplikace, uložené nastavení a zdrojové podklady.

## DEC-033

- Předmět: Zaoblené přesouvané panely, Fištrón u hrany, plátno a přepínač den/noc
- Typ: schvaleni-rozsahu
- Kontext: Člověk na videu z 2026-11-09 ukázal opožděný obrys při tažení panelu, požádal o skutečné zaoblení, bližší interakci Fištróna s obsahem, nové pózy na plátně a plynulý přepínač se sluncem a měsícem.
- Varianty: Vizuální výsledek určil člověk; provedení v rámci desktopové aplikace bylo ponecháno agentovi.
- Výsledek: Schváleny [FR-013](SPEC.md#fr-013) a [AC-007](SPEC.md#ac-007) v návaznosti na FR-012 a NFR-002.
- Důvod: Přímé zadání člověka k aktuálnímu EXE.
- Důsledky: [T-029](TASKS.md#t-029); vizuální akceptace až po vyzkoušení nové revize.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-030 pouze v dotčené vizuální části panelu, plátna a přepínače / –
- Schválení:
  - Rozsah: FR-013 a AC-007 v revizi SPEC.md níže; technické provedení v jejich mezích.
  - Revize: `SPEC.md` SHA-256 `DBE272F1190456D15B614E070B50EFD81C8D4D699B9667CCAEF609163485FC45` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-09
  - Podmínky / výjimky: Pokračuje předchozí oprávnění nahradit hlavní `abstractview.exe`; bez produktové akceptace a bez commitu.

## DEC-034

- Předmět: Jediný zaoblený panel, 2D překryv Fištróna a vektorový přepínač dne a noci
- Typ: technicke-rozhodnuti
- Kontext: Obrys kreslený do scény se při tažení zpožďoval za skutečným Tk panelem. Fištrón kreslený jen ve scéně zůstával schovaný za panelem. Dřívější obrázkový přepínač zatěžoval přechod motivu.
- Varianty: Souběžné vykreslování obrysu a panelu; jeden nativně zaoblený Tk rám. Pro Fištróna úplné překreslení scény; malý oříznutý překryv na panelu. Zvoleny druhé možnosti.
- Výsledek: Plovoucí rám se ve Windows ořezává nativní zaoblenou oblastí; jeho původní samostatný obrys ve scéně se nekreslí. Přes hranu panelu se skládá jen malý výřez 2D sprite, poloha zadní pózy sleduje kurzor. Plátno střídá dvě nové PNG pózy. Přepínač se kreslí jako malý vektorový ovladač se sluncem, měsícem a popisy day/night. Vestavěný `--self-test` používá dočasný soubor nastavení.
- Důvod: Rám a obsah se musí přesouvat společně; malý 2D výřez a vektorový ovladač nevyžadují další plnoobrazovkové bitmapy.
- Důsledky: Zaoblení rámu spoléhá na nativní Windows API, které odpovídá cílovému EXE; vzhled a odezvu na cílovém monitoru musí přijmout člověk. Úvodní smoke test před opravou `--self-test` mohl změnit aktivní efekt a otevřené panely v existujícím nastavení; finální self-test již soubor nemění.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-031 pouze v části vykreslení obrysu panelu a motivového přepínače / –
- Schválení:
  - Rozsah: Technické provedení [FR-013](SPEC.md#fr-013) a [AC-007](SPEC.md#ac-007) v mezích delegace [DEC-033](#dec-033).
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `ui.py` `5F523FB7224DDAB3A905FADEB5C27D101356FB35D531ED320E2488A4FDCD183A`, `scene.py` `860E36CE358444EC39AE59F55A4E67CBD0B2F83AFCC5E7C92FA54799BE83C788`, `main.py` `83BFEFF89BAF1AC6968A206BAF00EEDEFB96110123DDF4E99247E6425F72F637`; nové PNG `screen_wave` `4FA02BD39F36C62D8135802D4FB1B80F2404BABB2DC100768CFBDB16189C3210` a `screen_hop` `DDBFB27FBD00631B5FEF202D01B7123D4E4F0E21F3FE68D8BD5597480413A65B`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-033)
  - Datum: 2026-11-09
  - Podmínky / výjimky: Nejde o produktovou akceptaci ani souhlas ke commitu nebo publikaci.

## DEC-037

- Předmět: Odpočinek Fištróna mimo tažení, tabule s názvem efektu a úchop panelů
- Typ: schvaleni-rozsahu
- Kontext: Člověk na snímku ukázal částečné překrytí Fištróna panelem a odmítl jeho setrvávání u okna i nefunkční obrysy na tabuli. Požaduje také zřetelné záhlaví místo textu „přetáhni“.
- Varianty: Produktové chování určil člověk; provedení zůstává v delegaci agenta.
- Výsledek: Schváleny [FR-015](SPEC.md#fr-015) a [AC-009](SPEC.md#ac-009). Oprava funkce hvězd následuje samostatně po tomto vizuálním přírůstku.
- Důvod: Přímá produktová zpětná vazba k aktuálnímu hlavnímu EXE.
- Důsledky: [T-031](TASKS.md#t-031); nový výsledek vyžaduje vizuální posouzení člověka.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-035 pouze v klidové poloze Fištróna a obsahu tabule / –
- Schválení:
  - Rozsah: FR-015 a AC-009 v uvedené revizi SPEC.md; jediný hlavní `abstractview.exe`, bez změny funkční logiky hvězd.
  - Revize: `SPEC.md` SHA-256 `10C29DCE35E6A8C125FA8864577A22F94C39F4614A05ECC6F4E4C670DC0E661D` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-09
  - Podmínky / výjimky: Navazuje oprávnění k náhradě jediného hlavního EXE; bez commitu a bez předběžné produktové akceptace.

## DEC-038

- Předmět: Vyhrazený prostor pro odpočinek a jediný text na promítací tabuli
- Typ: technicke-rozhodnuti
- Kontext: Plovoucí Tk panel překrýval obrázek Fištróna vykreslený ve scéně. Dosavadní stav `near_panel` udržoval postavu u panelu i po puštění myši. Promítací tabule míchala efekt s animovanou postavou a obrysovými motivy.
- Varianty: Přeskládat nativní widgety s průhledným překryvem; ponechat Fištróna v klidu doma a panelům vyhradit prostor mimo jeho obrázek. Zvolena druhá možnost.
- Výsledek: Fištrón odpočívá doma, k panelu přiběhne pouze při tažení. Plovoucí panely začínají nejdříve na x=160 a v úzkém okně se přizpůsobí jejich šířka; kreslené pózy odpočinku a tlačení se do vyhrazeného prostoru vejdou. Tabule kreslí čistou plochu a Tk do ní vkládá aktuální název efektu; dvě staré projekční pózy byly odstraněny. Záhlaví panelu má kontrastní podklad, úchop `⋮⋮` a kurzor pro tažení.
- Důvod: Zabraňuje částečnému zakrytí postavy nativním widgetem v běžném i úzkém rozložení a odstraňuje nefunkční vizuální vrstvu tabule.
- Důsledky: Na minimální šířce má panel menší šířku a méně prostoru pro horizontální tažení. Funkční problém hvězd zůstává navazující prací.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-036 v poloze Fištróna u otevřeného panelu a DEC-031 v obsahu tabule / –
- Schválení:
  - Rozsah: Technické provedení [FR-015](SPEC.md#fr-015) a [AC-009](SPEC.md#ac-009) v mezích [DEC-037](#dec-037).
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `ui.py` `0D3646E551306AEF4BF1AF47B22111516A4733FF142E5477C8439442FC4301FB`, `scene.py` `5783C830C199CBC47F274815AF09D473008C77A9C824FA528DB85E96D866DBCE`, hlavní `abstractview.exe` `DCCC9814A7C965C52CBEADAD8B34113D3A1587756D6C4EC1C009405FC13C8FAF`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-037)
  - Datum: 2026-11-09
  - Podmínky / výjimky: Bez produktové akceptace a bez commitu.

## DEC-035

- Předmět: Oprava vizuálních regresí u Fištróna a přechodu motivu
- Typ: schvaleni-rozsahu
- Kontext: Člověk po vyzkoušení T-029 označil překryv Fištróna přes panel a přepínání jeho póz při pohybu myší za chybné. Videa z 2026-11-09 ukazují také skokové přebarvení karet a pixelové čáry přepínače.
- Varianty: Vizuální výsledek určil člověk; technické provedení zůstává v delegaci agenta.
- Výsledek: Schváleny [FR-014](SPEC.md#fr-014) a [AC-008](SPEC.md#ac-008). Dřívější požadavek na vykukování přes panel se ruší; ostatní funkce plovoucích panelů a plátna trvají.
- Důvod: Přímá produktová zpětná vazba člověka k aktuálnímu EXE.
- Důsledky: [T-030](TASKS.md#t-030); výsledek znovu vyžaduje vizuální posouzení člověka.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-033 a DEC-030 pouze v části překryvu a pózy Fištróna u panelu; DEC-034 v části překryvu Fištróna a vektorového přepínače / –
- Schválení:
  - Rozsah: FR-014 a AC-008 v revizi SPEC.md níže; průběžné přebarvení a vyhlazení prvků v rámci existující desktopové aplikace.
  - Revize: `SPEC.md` SHA-256 `97EFF67C26C6E6CAEDED299FC5A011218D6492816F25E053C678DBFF009A8488` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-09
  - Podmínky / výjimky: Pokračuje oprávnění nahradit jediný `abstractview.exe` podle DEC-032; bez commitu a bez produktové akceptace opravy před jejím vyzkoušením.

## DEC-036

- Předmět: Stabilní 2D postava mimo panel a společné přebarvení ovládání
- Typ: technicke-rozhodnuti
- Kontext: V T-029 se Fištrónův překryv vykresloval nad rámem panelu a při přejezdu myší měnil pózu i výšku. Čtyři barevné kroky panelů a odložené překreslení tlačítek způsobovaly viditelné skoky. Lineární prolnutí textu by uprostřed přechodu zhoršilo čitelnost.
- Varianty: Opravovat vrstvení překryvu a synchronizaci dvou póz; odstranit překryv a ponechat postavu stabilně vedle panelu. Průběžně vytvářet všechny bitmapy; oddělit časté přebarvení podkladů od méně častého překreslení průhledných prvků. Zvoleny druhé možnosti.
- Výsledek: Fištrón při otevřeném panelu používá celou přední kreslenou pózu mimo panel, bez reakce polohy či pózy na přejezd myší. Přetahování nadále používá tlačící pózu. Dvě nepoužívané PNG pózy vykukování byly odstraněny. Karty a panely přecházejí přes dvacet mezibarev; průhledná vyhlazená tlačítka a posuvníky obnovují detaily v osmi krocích a jejich podklad se přebarvuje současně s kartou. Dražší obnova detailů a kresba scény probíhají v sousedních snímcích. Text v mezistavech přepne na kontrastní barvu. Přepínač se kreslí ve čtyřnásobném rozlišení a zmenšuje s vyhlazením.
- Důvod: Jeden stabilní obraz postavy odstraňuje překrývání a blikání; průhledné podklady ruší obdélníkové záplaty bez drahého překreslování každého detailu v každém snímku.
- Důsledky: V přechodu je krátká změna barvy textu při překročení poloviny, aby zůstal čitelný. Jednotlivé kroky mohou na jiném monitoru trvat déle; produktovou plynulost musí posoudit člověk.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-034 v části překryvu Fištróna a kresby přepínače; DEC-031 v části řídkého přebarvení ovládacích prvků / –
- Schválení:
  - Rozsah: Technické provedení [FR-014](SPEC.md#fr-014) a [AC-008](SPEC.md#ac-008) v mezích delegace [DEC-035](#dec-035).
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `ui.py` `78A31F7CE1615434D77B00A203DBE707E7A6E2BBF54FEC931370D4485B800573`, `scene.py` `F4A36759455207F74D92A7A91374F0F9501CF7C01ABF83FA5C897D98FC9D89FF`, `theme.py` `CCA91CD87214BF7BFB09F3E408188F15284503FBC6007C0CFC97DDF5239622C3`, hlavní `abstractview.exe` `BEECA1CBE1D7236B62886F2E6AA35F56329323B7B31A4B48F58CA15E8B91D6BC`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-035)
  - Datum: 2026-11-09
  - Podmínky / výjimky: Nejde o produktovou akceptaci ani souhlas ke commitu nebo publikaci.

## DEC-039

- Předmět: Odstranění záhlaví a opravy odezvy a perzistence AbstractView
- Typ: schvaleni-rozsahu
- Kontext: Člověk na přiloženém obrázku odmítl přidané barevné záhlaví panelu a úchop `⋮⋮`. Současně popsal poskočení pozadí při otevření nastavení, ztrátu velikosti nebo maximalizace po restartu, dlouhou prodlevu Fištrónova spuštění a znovuotevření zavřeného panelu při vypnutí shuffle.
- Varianty: Produktové chování určil člověk; technické provedení zůstalo v delegaci agenta.
- Výsledek: Schváleny [FR-016](SPEC.md#fr-016) a [AC-010](SPEC.md#ac-010), včetně náhrady jediného hlavního `abstractview.exe`.
- Důvod: Přímá produktová zpětná vazba k aktuální revizi aplikace.
- Důsledky: [T-032](TASKS.md#t-032); výsledek znovu vyžaduje vizuální posouzení člověka.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-037 pouze v požadavku na zřetelné přidané záhlaví; DEC-038 pouze v technickém provedení záhlaví a úchopu / –
- Schválení:
  - Rozsah: FR-016 a AC-010 v uvedené revizi SPEC.md; aktualizace jediného hlavního `abstractview.exe`, bez změny logiky obrazových efektů.
  - Revize: `SPEC.md` SHA-256 `C2B84C6B73F99438898166521EEE5AAABAE3F49FC202BA2C95B0A744EA2D322C` nad HEAD `ebec925`.
  - Schválil: člověk
  - Datum: 2026-11-09
  - Podmínky / výjimky: Bez commitu, publikace a předběžné produktové akceptace.

## DEC-040

- Předmět: Vnitřní nadpis jako úchop, stabilní render pozadí a uložený stav okna
- Typ: technicke-rozhodnuti
- Kontext: Samostatná lišta zvětšovala panel a neodpovídala požadovanému vzhledu. Výška kreslené pouště se odvozovala od scrollregionu otevřených panelů, takže změna výšky přepočítala polohu dun. Shuffle bezpodmínečně otevíral svůj panel a spuštění výstupu čekalo 620 ms.
- Varianty: Ponechat neviditelnou úchopovou lištu; použít stávající vnitřní nadpis. Překreslovat proměnlivě vysoké pozadí; oddělit jeho výšku od panelového scrollregionu. Zvoleny druhé možnosti.
- Výsledek: Přidané záhlaví a `⋮⋮` byly odstraněny; běžný vnitřní nadpis táhne panel a samostatné `✕` jej zavírá. Pozadí se kreslí ve stabilní výšce nezávislé na otevření panelu. Nastavení ukládá normální geometrii a stav `normal`, `zoomed` nebo `fullscreen`. Vypnutí shuffle zavřený panel neotevře. Akce živého výstupu následuje 180 ms po kliknutí a efekt úderu začíná po 70 ms. Sestavovací specifikace výslovně přibaluje šest PNG póz.
- Důvod: Zachování ovladatelnosti bez odmítnuté vizuální vrstvy a odstranění přímých příčin všech čtyř funkčních regresí.
- Důsledky: Při velmi vysokém scrollování se kreslené pozadí rezervuje nejméně do výšky 1 100 px; produktovou odezvu a vzhled musí posoudit člověk.
- Stav: prijato
- Nahrazuje / Nahrazeno: DEC-038 pouze v provedení záhlaví a úchopu / –
- Schválení:
  - Rozsah: Technické provedení [FR-016](SPEC.md#fr-016) a [AC-010](SPEC.md#ac-010) v mezích [DEC-039](#dec-039).
  - Revize: Pracovní kopie nad HEAD `ebec925`; SHA-256 `ui.py` `6B0092ECC23DADB5E6D484152D4F0C4365CD6A6BED5D383DD8B16594C27FEAD3`, `config.py` `4C476B06F13AB50CAA5202A7BA00086A909C6B994E189B63335DACB97218F422`, `test_abstractview.py` `DA210B1120626D820ACC83E4EFDB9D33245F6AC1A2CCE50ABB6E247CB62D110F`, `abstractview.spec` `72D91ECC51B46517132D594362545F1872024F2F574E51155DF20869811EB61D`, hlavní `abstractview.exe` `4D53BCD039BA91F4C9E9B7E7E608034329F573E7524E0573B1EAB6B15391245D`.
  - Schválil: agent-pruvodce (technická volba delegovaná člověkem v DEC-039)
  - Datum: 2026-11-09
  - Podmínky / výjimky: Bez produktové akceptace a bez commitu.
