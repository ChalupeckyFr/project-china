# Project China

Projekt vyvíjený agenty ve spolupráci s člověkem podle provozního řádu
v [`AGENTS.md`](AGENTS.md).

> Aktuální stav, fázi a bod pokračování najdeš vždy v [`PROJECT.md`](PROJECT.md).
> Tento soubor stav nekopíruje.

## Mapa dokumentace

| Dokument | Účel |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Provozní řád: proces, autonomie, schvalování, evidence, definice hotovo. |
| [`PROJECT.md`](PROJECT.md) | Aktuální fáze, aktivní přírůstek, otevřené otázky, bod pokračování. |
| [`SPEC.md`](SPEC.md) | Účel, rozsah, požadavky, omezení, akceptační kritéria. |
| [`TASKS.md`](TASKS.md) | Úkoly, závislosti, stav, ověření, důkazy. |
| [`DECISIONS.md`](DECISIONS.md) | Rozhodnutí, důvody, záznamy schválení. |
| [`docs/evidence`](docs/evidence) | Snímky obrazovky citované v důkazech úkolů; nepatří mezi soubory aplikace. |
| `IDEAS.md` | Nápady – vznikne až s prvním nápadem. |

## Jak začít

Postup zvol podle aktuální fáze a dalšího kroku v [`PROJECT.md`](PROJECT.md).
Discovery **zahajuje člověk**.

### Ve VS Code s GitHub Copilot

1. Otevři Copilot Chat v agentním režimu.
2. Spusť odpovídající příkaz z tabulky níže (nebo použij `Chat: Run Prompt...`).
3. Postupuj podle pokynů agenta a posuď případná schválení.

Další vstupní body:

| Příkaz | Použij když |
| --- | --- |
| `/discover-project` | Zahajuješ nebo obnovuješ specifikaci. |
| `/plan-increment` | Máš schválený rozsah a chceš návrh řešení a úkoly. |
| `/work-task T-xxx` | Chceš realizovat konkrétní úkol. |

### V jiném nástroji

Otevři odpovídající soubor v `.github/prompts/`, zkopíruj jeho tělo (část pod
frontmatterem) jako zadání agentovi a připoj pokyn, aby nejprve načetl
`AGENTS.md` a `PROJECT.md`.

## Příprava vývojového prostředí

Závislosti jsou uvedeny v [`requirements.txt`](requirements.txt) a
[`requirements-dev.txt`](requirements-dev.txt). V rámci T-002 bylo po
oprávněních DEC-007 a DEC-008 ověřeno prostředí CPython 3.13.17 a nainstalovány
deklarované závislosti. Původní neúspěšné prostředí Pythonu 3.14 zůstalo
zachováno jako `.venv-py314-failed`.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Ověřeno na Windows s CPythonem 3.13.17 x64. Před vytvořením prostředí
ověř, že `.venv` ještě neexistuje.

## Základní kontroly

Spusť test importu a statickou kontrolu z kořene repozitáře:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check src tests
```

## Vstupní CSV

`project_china.frames.load_depth_csv(path)` načítá posloupnost se záhlavím
`frame,time_ms,x,y,depth`. Každý snímek musí mít jednotný čas a úplnou
obdélníkovou mřížku stejných rozměrů; hloubky se vracejí v paměti po řádcích
od `y=0`, bez ukládání zpracovaných dat. Neplatný vstup vyvolá
`DepthCsvError`.

`project_china.selection.select_depth_regions(frame)` vybírá hodnoty včetně
obou mezí 750–1000 a vrací binární masku i obrysy všech oddělených oblastí.
Prázdný výběr vrací prázdnou množinu obrysů, nikoli chybu.

Lokální demo spustíš s explicitní cestou k jednomu CSV souboru; jako příklad
slouží syntetická posloupnost `examples/moving_object.csv`:

```powershell
Push-Location src
try {
    ..\.venv\Scripts\python.exe -m project_china.demo ..\examples\moving_object.csv
}
finally {
    Pop-Location
}
```

Totéž z kořene repozitáře spustí `.\runObject.ps1`. Skript `.\runHuman.ps1`
spustí detailního člověka; pokud `examples/human_motion.csv` neexistuje nebo
je starší než generátor `src/project_china/synthetic_human.py`, nejprve ho
(pře)generuje do dočasného `human_motion.csv.new` a ten pak přesune na místo
CSV, jinak použije existující soubor. Pro člověka spouští
demo s 360 hvězdami na obrysu místo výchozích 72 a s 1 500 hvězdami
vyplňujícími objem těla; počty lze při ručním spuštění zadat parametry
`--particles` a `--volume-particles` (výchozí 0, tj. jen obrys). Při omezující
execution policy použij např.
`powershell -ExecutionPolicy Bypass -File .\runHuman.ps1`.

Ukázkový objekt na každé pozici stojí 2,4 s a během dalších 600 ms plynule
přepluje na novou, takže se posouvá každé 3 sekundy. Posloupnost se opakuje
až do zavření okna; u jiných CSV demo zachovává jejich časové značky. Poslední
snímek zobrazí stejně dlouho, jako trval odstup dvou posledních snímků, a pak
plynule přejde zpět na první. Pokud soubor obsahuje jediný snímek, zůstane
zobrazený.

### Detailní syntetický člověk

`examples/human_motion.csv` obsahuje 240 snímků 256×384 po 50 ms:
98 304 bodů na snímek a celkem 23 592 960 datových řádků. Samotné postavě
patří přes 10 000 bodů v každém snímku; ostatní body tvoří pozadí. Člověk
během dvanáctisekundové smyčky dvakrát plynule zvedne a spustí obě ruce
(cyklus paží 6 s) a třikrát se nadechne (perioda dechu 4 s).

Jde o procedurální čelní ortografický model, nikoli skutečný sken. Tělo je
složené ze vzdálenostních polí (SDF): trup tvoří hrudník, pas široký asi 75 %
šířky ramen a pánev, končetiny jsou zužované kapsle (rameno → loket → zápěstí,
stehno → koleno → kotník) a dlaně jsou zploštělé elipsoidy natočené podle
předloktí a předsunuté asi o 7 cm ke kameře, takže patří spolu se středem
hrudníku k nejbližším bodům. Paže jsou dost silné, aby ani svislé nesplynuly
do jedné řady hvězd: poloměr předloktí je asi 14,6 px obrazovky a zápěstí
asi 10,4 px ([T-022](TASKS.md#t-022)).
Hlava je hladký elipsoid bez uší, krk má asi 46 % šířky hlavy.
Spoje trupu, krku, ramen a končetin jsou slité polynomiálním smooth minimum
(`SMIN_K = 0.15` v jednotkách šířky hlavy, tj. asi 2,5 cm), takže v podpaží
ani u krku nevznikají ostré zářezy. Hloubka (2.5D) se nepočítá po segmentech:
nejdřív vznikne jedno sloučené SDF celé postavy a z něj hladký parabolický
profil přes celou lokální šířku těla (bez plochého vrcholu), takže uvnitř
nejsou švy mezi
hrudníkem, pasem, pánví a končetinami ani hřbety podél jejich os. Nos a očnice
jsou jemný reliéf obličeje. Hloubky se ukládají na tři desetinná místa
(viz [T-018](TASKS.md#t-018) a [T-019](TASKS.md#t-019)).

Paže se pohybují s easingem `sin²`, takže v dolní a horní úvrati zpomalí.
Nad horizontálou se ramenní kloub zvedá až o 6,5 % výšky trupu a mírně
přisouvá ke krku. Paže má dva segmenty: předloktí za nadloktím zaostává
o fázi 0,175 rad, takže se loket při zvedání pokrčí až o 17° a při spouštění
se mírně ohne na druhou stranu. Hrudník dýchá s periodou 4 s (amplituda 2,5 %
šířky trupu v šířce hrudníku i výšce ramen) a nad horizontálou
se hrudní kost s ramenním pletencem zvedne asi o 4 px obrazovky; kyčle jemně
přenášejí váhu. Anatomická přesnost vůči skutečnému člověku nebyla změřena;
parametry popisují [DEC-017](DECISIONS.md#dec-017),
[DEC-022](DECISIONS.md#dec-022) a [DEC-023](DECISIONS.md#dec-023).

Spuštění:

```powershell
Push-Location src
try {
    ..\.venv\Scripts\python.exe -m project_china.demo ..\examples\human_motion.csv --particles 360 --volume-particles 1500
}
finally {
    Pop-Location
}
```

Velké vygenerované CSV není verzované; lze ho reprodukovat tímto příkazem:

```powershell
Push-Location src
try {
    ..\.venv\Scripts\python.exe -m project_china.synthetic_human ..\examples\human_motion.csv
}
finally {
    Pop-Location
}
```

Generátor odmítne přepsat existující soubor. CSV má přibližně 608 MB (generování asi 32 s, načtení asi 22 s);
načítání potřebuje řádově gigabajty paměti a více času než původní příklad.
Naměřené nároky jsou v [T-013](TASKS.md#t-013).
U člověka tvoří obrys 360 hvězd a objem těla dalších 1 500 hvězd
(viz [T-017](TASKS.md#t-017)).

Příklad je vymyšlený testovací vstup, ne záznam z kamery. Demo žádná zpracovaná
hloubková data neukládá. Volba pevného vzorku nebo souborů přes uživatelské
rozhraní zůstává otevřená v Q-004. Okno lze zavřít klávesou `Esc` nebo `q`.

Hvězdné pozadí plynule pohasíná a při výskytu obrysu
k němu přitahuje částice rovnoměrně rozložené po obvodu (výchozí počet 72,
u člověka 360); po jeho zmizení se částice postupně uvolní.

Obrys se mezi snímky CSV plynule morfuje (modul `project_china.morph`):

- Každá kontura se převzorkuje na 1 024 bodů ve směru hodinových ručiček.
  Index 0 leží na nejvyšším bodě nad těžištěm a body vpravo, dole a vlevo
  od těžiště připadnou na indexy 256, 512 a 768. Změna jedné končetiny tak
  neposune body v ostatních kvadrantech. Když kvadranty nejsou spolehlivé
  (těžiště mimo tvar), obrys se převzorkuje rovnoměrně od horního bodu.
- Cíl je `lerp(předchozí, další, smoothstep(alpha))`. Přechod trvá délku
  snímku, nejvýše však 600 ms, a končí přesně v čase dalšího snímku.
- Kontury se párují podle nejbližšího těžiště. Nová kontura vyrůstá ze
  svého těžiště, mizející se do něj stáhne.
- Cílové body se na obrazovce posouvají nejvýše o 900 px/s.
- Hloubka se mezi snímky neinterpoluje; tvar každého snímku vychází z jeho
  vlastního prahování.

Obrysy a objemy klíčových snímků se počítají jen jednou a ukládají se do
mezipaměti. Pokud demo kreslí objem, spočítá je při startu všechny (u člověka
asi 1 s navíc), aby jedna pevná mřížka výplně platila pro celou sekvenci.
Obrys postavy či objektu se nevykresluje čarou, jeho tvar
naznačují hvězdy.
Samostatné kolečko uprostřed cíle se nevykresluje.
Samostatná prolétající hvězda v pozadí se nevykresluje.

Vykreslování (modul `project_china.effects`) dostává jen body na obrazovce
a jejich hloubky; CSV ani matice nečte. Geometrii objemu počítá z hloubkové
matice samostatný modul `project_china.volume`:

- 2.5D objem: vnitřek vyplňuje jedna pevná šestiúhelníková mřížka s malým
  stálým posunem bodů (do 0,5 bodu matice), takže hustota je homogenní bez
  shluků a děr. Rozestup se při startu nastaví tak, aby nejplnější snímek
  potřeboval nejvýše 97 % objemových hvězd. Cílem je každý bod mřížky
  uvnitř siluety; mezi snímky se prolínají znaménkové vzdálenostní pole
  celé binární siluety, takže tělo plynule roste a ubývá a v podpaží ani
  v kloubech nevzniká vnitřní hrana. Mřížka se jako celek posouvá do stran
  s váženým těžištěm silného jádra těla (přenos váhy), takže body trupu
  jedou s tělem a nepřeskakují. Hustota je všude stejná; u okraje klesá
  nejvýše o 30 %. Obrysové hvězdy vznikají jen na vnější hranici celé siluety.
- Párování: každý bod mřížky má stálé ID. Hvězda si drží svůj cíl, dokud
  jeho ID existuje; uvolněná hvězda si vezme nejbližší volný cíl do 12 px.
  Vzdálenější nový cíl převezme neviditelná hvězda z poolu, objeví se přímo
  na něm a rozsvítí se, takže přes tělo nepřelétají blikající hvězdy.
  Hvězdy bez cíle zůstanou na místě a vyblednou (asi 120 ms).
- Hloubka: každá hvězda je měkký kotouč, jehož poloměr a alfa plynou po
  částech lineárně z blízkosti. Blízkost je hloubka normalizovaná pevným
  rozsahem celé sekvence (ne extrémy jednotlivého snímku): boky a okraje
  1,5 px a alfa 0,35, střední 2,4 px a 0,55, nejbližší (střed hrudníku,
  dlaně) 3,5 px a 0,95 s teplejším odstínem. Blízkost, poloměr i alfa se
  vyhlazují exponenciálním filtrem `předchozí · 0,8 + cíl · 0,2` za krok
  60 Hz, takže hrudník nebliká. Objemový dojem vzniká jen velikostí,
  jasem a barvou, ne prázdnými místy.
- Každá hvězda obrysu má k cíli malý posun 1,5–2,5 px, objemová 0,3–0,6 px
  (mřížka už je rozházená); posun pomalu obíhá, takže nevzniká rastr ani
  zdvojené čáry. Hvězdy končetin mají navíc stálý posun kolmo na kost
  v rozsahu ±3 px, oříznutý tak, aby zůstaly 1 px uvnitř siluety. Svislá
  paže tak drží plný válcový objem. Směr kosti se bere ze strukturního
  tenzoru vzdálenostního pole, „končetinovost“ z lokální poloviční šířky.
- Hvězdy se k cíli blíží přetlumeně: za každý referenční krok 60 Hz chtějí
  urazit 25 % zbývající vzdálenosti, nejvýše 10 px. Rychlost se za krok
  změní nejvýše o 2 px a krok nikdy nepřesáhne zbývající vzdálenost. Za
  rychlou paží tak mírně zaostávají, v úvratích nepřekmitnou ani
  nekmitají a nevystřelí z těla. Náběh přitažlivosti trvá 180 ms
  a uvolnění má časovou konstantu 700 ms.
- Body obrysu rychlejší než 150 px/s (paže, předloktí, dlaně) víří hvězdy
  pozadí do 32 px: odpudivá složka kolmo na směr kosti, tečná ve směru
  švihu a mírná turbulence napříč. Hvězdy si pak každý krok 60 Hz ponechají
  92 % rychlosti a pružina je vrátí na místo.
- Stav všech hvězd je v polích alokovaných jednou při startu.

Parametry nemají nastavovací UI; popisují je
[`DEC-018`](DECISIONS.md#dec-018), [`DEC-019`](DECISIONS.md#dec-019),
[`DEC-020`](DECISIONS.md#dec-020), [`DEC-021`](DECISIONS.md#dec-021),
[`DEC-022`](DECISIONS.md#dec-022) a [`DEC-023`](DECISIONS.md#dec-023),
původní přijaté hodnoty
[`DEC-009`](DECISIONS.md#dec-009).

## Desktopová aplikace AbstractView

Vedle původního dema je v `abstractview_app/` ovládací panel AbstractView. Spustíš
jej z kořene repozitáře po přípravě prostředí:

```powershell
.\.venv\Scripts\python.exe -m abstractview_app.main
```

`ui.py` obsahuje ovládací panel Tk, přesouvatelná nastavení a samostatné okno výstupu, `scene.py`
vykresluje pozadí a Fištróna ze šesti obrázků v `abstractview_app/assets/`, `renderer.py` skládá efekty v Pygame, `samples.py`
připravuje ukázky, CSV a náhradní vstup kamery, `config.py` ukládá nastavení do
`abstractview_settings.json`. Běžná webkamera poskytuje jen obraz převedený na
přibližnou hloubku; virtuální ToF je simulace. Skutečný ToF senzor je budoucí
integrace. Testy panelu jsou v `abstractview_app/tests/` a spouštějí se explicitně
cestou k souboru; výchozí `pytest` zahrnuje pouze `tests/`.
Aktuální sestavená aplikace je `abstractview.exe` v kořeni projektu. Otevřené panely a jejich polohy se ukládají do `abstractview_settings.json`.

## Co tu (zatím) není

CI zatím není připravené.
Architekturu a základní závislosti stanovují
schválené záznamy v `DECISIONS.md`.
