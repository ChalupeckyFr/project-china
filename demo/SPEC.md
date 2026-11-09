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

## FR-009

- Název: Vizuální úpravy ovládacího panelu AbstractView
- Popis: Zdroj v horní liště má čitelný zaoblený vzhled. Karty výběru efektů jsou zarovnané vlevo. U objektového efektu se zobrazují jen barvy potřebné pro zvolený vzor; v režimu čisté společné barvy stačí jedna volba. Graffiti editor je vidět pouze při zvoleném Graffiti a velikosti tvarů alespoň 60; pod touto mezí se zobrazí vysvětlení. Jeho plátno má zaoblené rohy a souvislou kreslenou čáru. Ukázkové postavy a pozadí jsou hladké a ostré v různých velikostech okna. Při změně dne a noci přicházející těleso vždy putuje zleva doprava. Výběr kamery se otevře bez čekání na fyzické porty a jeho volby mají jednotný vzhled. Tlačítko živého výstupu nemá světlý lesklý ovál. Fištrón je baculatější, usmívá se, dívá se na plátno a při rychlém přesunu má animaci roztočených nohou podle reference člověka.
- Původ: člověk, zadání z 2026-11-08 s obrázky 1–6 a videem 7
- Stav: schvaleno
- Schválení: DEC-024
- Vazby: AC-002; podobu Fištróna pro novou revizi mění [FR-010](#fr-010).

## FR-010

- Název: Plochý hologram Fištróna a prosklené nastavení
- Popis: Fištrón má novou podobu dvourozměrného svítícího králíka podle neonové kočky na předloze člověka; nepoužívá prostorově stínovaný model. Projektorová podložka stojí nízko vlevo s odstupem od rohu. Fištrón při přesunu k nastavení či tlačítku přebíhá rychleji podle video reference; na širokém otevřeném nastavení se objeví v průhledné části skla. Otevřené nastavení je širší a působí jako skleněné okno s viditelnou pouští za ním; ovládací prvky jsou čitelné na jeho ploše. Vzhled platí v obou tématech a při změně velikosti okna.
- Původ: člověk, zpětná vazba z 2026-11-08 s obrázkem pracovního stolu a videem `Záznam 2026-11-08 122152.mp4`
- Stav: schvaleno
- Schválení: DEC-026
- Vazby: AC-004; mění pouze dotčenou část FR-009. Podobu Fištróna a jeho chování následně nahrazuje [FR-011](#fr-011).

## FR-011

- Název: Kreslený Fištrón a plynulý přechod motivu
- Popis: Fištrón je nenéonový kreslený králík se dvěma očima podle stylové předlohy člověka. Používá šest připravených obrázků: spánek vleže v pelíšku, vykukování zpoza levé hrany nastavení se zbytkem těla za panelem, chůzi, radost se zvednutými tlapkami, soustředění nad tlačítkem se zvednutými tlapkami a únavu po úderu s tlapkami dole. Přesouvá se rychle. Promítací plátno je blízko pelíšku. V rozhraní není text „pohled do pouště“. Přechod mezi světlým a tmavým motivem v obou směrech působí plynule a při změně neblokuje ovládání.
- Původ: Člověk, oprava vzhledu z 2026-11-08 s obrázky kreslené postavy a vykukování a videem `Záznam 2026-11-08 164650.mp4`.
- Stav: schvaleno
- Schválení: DEC-028
- Vazby: AC-005, NFR-002; nahrazuje dotčenou část FR-010.

## FR-012

- Název: Plovoucí nastavení a kontextové animace Fištróna
- Popis: Nastavení shuffle, tvarového a objektového efektu se otevírají jako samostatné přesouvatelné panely uvnitř hlavního okna; lze je používat současně, stejný panel nejde otevřít dvakrát, aktivní panel je viditelně označen a jeho poloha i otevření se po opětovném spuštění obnoví. Fištrón přebíhá k aktivnímu panelu, při běžném zaměření se dívá k uživateli, při přímé úpravě hodnot se otáčí k panelu zády k uživateli a při přesouvání panel tlačí. Tlapky při vykukování lícují s hranou. Úder do tlačítka míří na jeho skutečný střed; změnu pózy zakrývá krátký kreslený oblak prachu a doprovázejí ji výraznější efekty. Při nečinnosti ve světlém režimu a bez otevřeného nastavení Fištrón pracuje s plátnem; plátno ukazuje právě aktivní efekt. Otevření panelů v tmavém režimu nemá viditelné postupné dokreslování.
- Původ: Člověk, zpětná vazba z 2026-11-08 s videem `Záznam 2026-11-08 181159.mp4` a obrázkem vykukování.
- Stav: schvaleno
- Schválení: DEC-030
- Vazby: AC-006, NFR-002; rozšiřuje FR-011 o nové pózy a interakce.
- Nahrazeno: [FR-014](#fr-014) pouze v části vykukování a střídání póz při úpravě hodnot.

## FR-013

- Název: Zaoblené panely, čitelné plátno a nový přepínač dne a noci
- Popis: Přesouvaný panel nastavení má skutečně zaoblené rohy a jeho vzhled se pohybuje společně s obsahem bez opožděného obrysu. Fištrónova hlava či packa mírně přesahuje do aktivního panelu a při práci s myší sleduje jeho obsah. Plátno zobrazuje rozpoznatelnou podobu Fištróna v aktivním efektu a občas střídá nově nakreslené pózy. Přepínač motivu obsahuje označení dne a noci a plynulou proměnu slunce v měsíc v obou směrech.
- Původ: Člověk, zpětná vazba z 2026-11-09 s videem `Záznam 2026-11-09 080434.mp4` a obrázkem přepínače.
- Stav: schvaleno
- Schválení: DEC-033
- Vazby: AC-007, NFR-002; upravuje dotčené vizuální chování FR-012.
- Nahrazeno: [FR-014](#fr-014) pouze v části překryvu Fištróna přes panel a způsobu přebarvování při přechodu motivu.

## FR-014

- Název: Klidný Fištrón vedle panelu a plynule přebarvovaný motiv
- Popis: Fištrón při otevřeném nastavení stojí celý vedle panelu; jeho obrázek se nevkládá přes obsah ani se při pohybu myší nad panelem nepřepíná mezi přední a zadní pózou. Přesun panelu může dál doprovázet tlačící pózou. Přepínač dne a noci, posuvníky a obrysy tlačítek mají vyhlazené hrany bez viditelných pixelových čar. Při změně motivu se karty, panel, ovládací prvky a jejich podklady postupně přebarvují společně; text zůstává čitelný i uprostřed přechodu. Dosavadní zaoblené panely a nové pózy na plátně zůstávají součástí výsledku.
- Původ: Člověk, oprava po videích `Záznam 2026-11-09 092637.mp4` a `Záznam 2026-11-09 092853.mp4`.
- Stav: schvaleno
- Schválení: DEC-035
- Vazby: AC-008, NFR-002; nahrazuje dotčenou část FR-012 a FR-013.
- Nahrazeno: [FR-015](#fr-015) v klidové poloze Fištróna u otevřeného panelu a v obsahu promítací tabule.

## FR-015

- Název: Fištrón doma mimo tažení a přehledná tabule efektu
- Popis: Fištrón při otevřeném nastavení zůstává na svém místě v odpočinkové póze. K panelu se přesouvá jen během jeho tažení a jeho obrázek nesmí být částečně překrytý panelem. Promítací tabule ukazuje pouze název právě aktivního efektu bez animovaných obrysů a postavy. Každý panel má zřetelné záhlaví použitelné jako úchop pro tažení; text „přetáhni“ se nezobrazuje. Funkční závada hvězd je samostatná navazující práce.
- Původ: Člověk, přímá zpětná vazba z 2026-11-09 s obrázkem překrytého Fištróna.
- Stav: schvaleno
- Schválení: DEC-037
- Vazby: AC-009; nahrazuje dotčenou část FR-014.
- Nahrazeno: [FR-016](#fr-016) pouze v podobě záhlaví a úchopu panelu.

## FR-016

- Název: Čisté panely, stabilní okno a rychlá odezva ovládání
- Popis: Plovoucí nastavení nemají přidané barevné záhlaví ani úchop `⋮⋮`; panel zůstává přesunutelný přes svůj běžný vnitřní nadpis a zachovává samostatné zavření. Otevření nastavení neposune pozadí. Hlavní okno po restartu obnoví svou poslední běžnou velikost a polohu i stav maximalizace nebo celé obrazovky. Kliknutí na Fištrónovo spouštěcí tlačítko otevře živý výstup s kratší prodlevou. Vypnutí aktivního shuffle po ručním zavření jeho nastavení toto nastavení znovu neotevře.
- Původ: Člověk, přímá zpětná vazba z 2026-11-09 s obrázkem záhlaví panelu.
- Stav: schvaleno
- Schválení: DEC-039
- Vazby: AC-010, NFR-002; nahrazuje dotčenou část FR-015.

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

## NFR-002

- Název: Plynulé ovládání AbstractView
- Popis: Při běhu efektů, změně velikosti okna, změně vzhledu a přesunu Fištróna má ovládací panel reagovat bez znatelných záseků. Maximální volba 2 500 hvězd nesmí vyvolat chybu. Konkrétní mez odezvy zatím člověk nestanovil.
- Původ: člověk, zadání z 2026-11-08
- Stav: schvaleno
- Schválení: DEC-024

- Vazby: AC-003

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

## AC-002

- Požadavek: FR-009
- Podmínky: Otevřený AbstractView v tmavém i světlém režimu, malé a velké okno, objektový efekt ve vzorech čistá barva, spirála a Graffiti, dialogy zdroje a kamery.
- Očekávaný výsledek: Vzhled a podmíněné ovládání odpovídají FR-009 a obrázkům či videu přiloženým k zadání člověka; Fištrón i scéna mají plynulý pohyb a jsou čitelní.
- Způsob ověření: Automatické testy zobrazení ovládacích prvků a čistého renderování; člověk vizuálně posoudí okno a náhledový exe.
- Stav: schvaleno
- Schválení: DEC-024

## AC-003

- Požadavek: NFR-002
- Podmínky: Ukázková postava, 2 500 hvězd, aktivní výstup a změna vzhledu či velikosti okna.
- Očekávaný výsledek: Vykreslování nepadá kvůli počtu cílů, ovládání zůstává použitelné bez znatelných záseků.
- Způsob ověření: Test mezního počtu hvězd, časové měření vytvoření scény a efektu, test Tk okna a smoke test sestaveného exe; subjektivní plynulost posoudí člověk.
- Stav: schvaleno
- Schválení: DEC-024

## AC-004

- Požadavek: FR-010, NFR-002
- Podmínky: Otevřený AbstractView v tmavém i světlém tématu, zavřené a otevřené nastavení, menší okno, přesun Fištróna k panelu a tlačítku.
- Očekávaný výsledek: Fištrón je čitelný dvourozměrný hologram bez starého 3D modelu, podložka zůstává nízko vlevo a v malém okně je viditelná. Na širokém panelu se hologram dívá z průhledné části skla směrem k nastavení. Nastavení má širší skleněný rám s pouští za ním a čitelnými prvky; přechody neblokují ovládání.
- Způsob ověření: Testy vykreslení a Tk rozložení, lokální vizuální kontrola okna, smoke test exe a lidské posouzení výsledku.
- Stav: nahrazeno
- Schválení: DEC-026
- Nahrazeno: [AC-005](#ac-005) pro novou podobu Fištróna a přechod motivu.

## AC-005

- Požadavek: FR-011, NFR-002
- Podmínky: Otevřený AbstractView v obou motivech, otevřené i zavřené nastavení, malé i velké okno, přejetí k tlačítku a jeho stisk.
- Očekávaný výsledek: Přepnutí motivu plynule mění scénu a přepínač bez opakovaných dlouhých záseků. Fištrón má přesně šest uvedených kreslených póz, dvě oči a žádné neonové záření; rychle doběhne k nastavení či tlačítku, vykukuje z levé hrany panelu a plátno je u pelíšku. Text „pohled do pouště“ se nezobrazuje.
- Způsob ověření: Automatické testy všech póz, stavů, změny motivu a rozložení, měření kroků v nativním Tk okně, kontrola lokálních snímků a lidské vizuální posouzení sestaveného EXE.
- Stav: schvaleno
- Schválení: DEC-028

## AC-006

- Požadavek: FR-012, NFR-002
- Podmínky: Otevření tří nastavení, jejich přesun, výběr aktivního panelu, změna posuvníku, restart aplikace, přepnutí světlého a tmavého režimu, nečinnost bez panelů a kliknutí na živý výstup.
- Očekávaný výsledek: Tři panely lze nezávisle přesouvat na stejné ploše a po restartu se obnoví bez duplicit. Aktivní panel má zřetelný stav a Fištrón u něj předvede odpovídající přední, zadní či tlačící pózu. Při úderu je zarovnán se skutečným středem tlačítka a prach překryje výměnu póz. Plátno v klidu ukazuje aktivní efekt a reaguje na Fištróna. Tmavé panely se otevřou bez postupného načítání jednotlivých prvků.
- Způsob ověření: Test perzistence a neduplicitních panelů, GUI test přesunu, zaměření a přepnutí motivu, kontrola animace v nativním okně, časové měření a smoke test sestaveného EXE; vzhled posoudí člověk.
- Stav: schvaleno
- Schválení: DEC-030
- Nahrazeno: [AC-008](#ac-008) pouze v části pózy Fištróna u panelu; ostatní podmínky zůstávají v platnosti.

## AC-007

- Požadavek: FR-013, NFR-002
- Podmínky: Tažení panelu v obou motivech, práce myší nad jeho obsahem, světelný přechod v obou směrech a nečinnost bez otevřeného nastavení.
- Očekávaný výsledek: Panel nemá oddělený opožděný obrys a jeho rohy jsou zaoblené; Fištrón viditelně přesahuje přes hranu směrem k obsahu; plátno promítá jeho rozpoznatelnou postavu v nejméně dvou nových pózách a stále ukazuje aktivní efekt; přepínač zřetelně ukazuje den/noc a plynule mění slunce v měsíc bez zadrhávání ovládání.
- Způsob ověření: Nativní GUI kontrola tažení, póz a přepínače, cílené testy polohy a stavu, měření přechodu motivu a smoke test hlavního EXE; výsledek vzhledu posoudí člověk.
- Stav: nahrazeno
- Schválení: DEC-033
- Nahrazeno: [AC-008](#ac-008) podle nové vizuální zpětné vazby člověka.

## AC-008

- Požadavek: FR-014, NFR-002
- Podmínky: Otevřený a přesouvaný panel, opakovaný přejezd myší přes jeho obsah, změna motivu tam a zpět, světlý i tmavý konečný stav a nečinnost u plátna.
- Očekávaný výsledek: Fištrón nezasahuje do panelu ani při přejezdu myší nepřeskakuje mezi pózami. Zaoblené okno se přesouvá bez odděleného obrysu, plátno ukazuje rozpoznatelné nové pózy. Přepínač a posuvníky mají hladké čáry; karty, panel a ovládací prvky mění barvu průběžně bez konečného skoku nebo obdélníkových záplat. Text je čitelný v mezistavech. Ovládání zůstává použitelné.
- Způsob ověření: Srovnání videí s nativním snímkem mezistavu, test stabilní polohy a pózy Fištróna při práci s panelem, test počtu mezibarev a čitelnosti, měření obou přechodů, regresní testy a smoke test jediného hlavního EXE; výsledný vzhled posoudí člověk.
- Stav: schvaleno
- Schválení: DEC-035
- Nahrazeno: [AC-009](#ac-009) v poloze Fištróna mimo tažení a v obsahu tabule; plynulé přebarvení zůstává v platnosti.

## AC-009

- Požadavek: FR-015
- Podmínky: Otevření jednoho i více panelů, práce uvnitř panelu bez tažení, tažení panelu a jeho puštění, světlý i tmavý motiv, přepnutí aktivního efektu.
- Očekávaný výsledek: Fištrón v klidu odpočívá u svého místa, během tažení může pomáhat s panelem a po puštění se vrátí. V běžném rozložení není za panelem vidět jen kus postavy. Tabule obsahuje jediný aktuální název efektu bez siluety a obrysových animací. Barevně odlišené záhlaví lze uchopit a žádný panel neobsahuje text „přetáhni“.
- Způsob ověření: Cílené stavové testy, nativní GUI test s panelovým tažením, kontrola tabule a záhlaví, smoke test jediného hlavního EXE; vizuální výsledek posoudí člověk.
- Stav: schvaleno
- Schválení: DEC-037
- Nahrazeno: [AC-010](#ac-010) pouze v podobě záhlaví a úchopu panelu.

## AC-010

- Požadavek: FR-016, NFR-002
- Podmínky: Otevření a zavření nastavení, tažení panelu, zapnutí shuffle a zavření jeho panelu, vypnutí shuffle, kliknutí na spuštění živého výstupu, ukončení aplikace v běžném i maximalizovaném stavu a následný restart.
- Očekávaný výsledek: Panel nemá samostatné barevné záhlaví ani `⋮⋮`, ale lze jej přesunout a zavřít. Pozadí při otevření panelu zůstane ve stejné poloze. Vypnutí shuffle neotevře zavřený panel. Živý výstup začne podstatně dříve než v předchozí revizi. Restart obnoví velikost, polohu a maximalizovaný nebo celoobrazovkový stav hlavního okna.
- Způsob ověření: Stavové a nativní GUI testy panelu, shuffle, stabilní výšky kresleného pozadí a restartu maximalizovaného okna; kontrola technické prodlevy spuštění, statická kontrola a smoke test jediného hlavního EXE. Vzhled a vnímanou odezvu posoudí člověk.
- Stav: schvaleno
- Schválení: DEC-039

## 7. Předpoklady

Neověřené vstupy, které agent nebo člověk zatím nepotvrdil. Nesmí se tvářit
jako požadavky.

_Žádné._
