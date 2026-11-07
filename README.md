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
spustí detailního člověka; pokud `examples/human_motion.csv` neexistuje,
nejprve ho vygeneruje, jinak použije existující soubor. Pro člověka spouští
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

`examples/human_motion.csv` obsahuje 120 snímků 256×384 po 50 ms:
98 304 bodů na snímek a celkem 11 796 480 datových řádků. Samotné postavě
patří přes 10 000 bodů v každém snímku; ostatní body tvoří pozadí. Člověk
během šestisekundové smyčky plynule zvedá a spouští obě ruce.

Jde o procedurální čelní ortografický model, nikoli skutečný sken. Tělo je
složené ze vzdálenostních polí (SDF): trup tvoří hrudník, pas široký asi 75 %
šířky ramen a pánev, končetiny jsou zužované kapsle (rameno → loket → zápěstí,
stehno → koleno → kotník) a dlaně jsou zploštělé elipsoidy natočené podle
předloktí. Hlava je hladký elipsoid bez uší, krk má asi 46 % šířky hlavy.
Spoje trupu, krku, ramen a končetin jsou slité polynomiálním smooth minimum
(`SMIN_K = 0.15` v jednotkách šířky hlavy, tj. asi 2,5 cm), takže v podpaží
ani u krku nevznikají ostré zářezy. Hloubka (2.5D) klesá od středu hrudníku,
hlavy a os končetin plynule k okrajům siluety.

Paže se pohybují s easingem `sin²`, takže v dolní a horní úvrati zpomalí.
Nad horizontálou se ramenní kloub zvedá až o 6,5 % výšky trupu a mírně
přisouvá ke krku, loket se ohýbá o 10–20° podle fáze pohybu a hrudník jemně
dýchá spolu s přenosem váhy v kyčlích. Anatomická přesnost vůči skutečnému
člověku nebyla změřena; parametry popisuje [DEC-017](DECISIONS.md#dec-017).

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

Generátor odmítne přepsat existující soubor. CSV má přibližně 296 MB;
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
mezipaměti. Obrys postavy či objektu se nevykresluje čarou, jeho tvar
naznačují hvězdy.
Samostatné kolečko uprostřed cíle se nevykresluje.
Samostatná prolétající hvězda v pozadí se nevykresluje.

Vykreslování (modul `project_china.effects`) dostává jen body na obrazovce
a jejich hloubky; CSV ani matice nečte. Geometrii objemu počítá z hloubkové
matice samostatný modul `project_china.volume`:

- 2.5D objem: z každého bodu obrysu vede paprsek dovnitř do poloviny těla
  a vrstvy na něm houstnou podle gradientu hloubky, takže objemové hvězdy
  jsou nejhustší u okrajů a směrem ke středu hrudníku, hlavy a končetin
  řídnou. Objem se morfuje mezi snímky stejně jako obrys.
- Hloubka: blízké hvězdy jsou o 40 % větší s alfou až 1,0, vzdálené menší
  a tlumené (alfa od 0,30); hloubka se normalizuje min/max v rámci snímku.
- Každá hvězda má k cíli malý posun 1,5–2,5 px, který pomalu obíhá, takže
  nevzniká rastr ani zdvojené čáry.
- Hvězdy se k cíli táhnou tlumenou pružinou (tuhost 0,12, tlumení 0,85 na
  referenčním kroku 60 Hz), takže za rychlou paží mírně zaostávají
  a dobíhají s malým přestřelem. Náběh přitažlivosti trvá 180 ms
  a uvolnění má časovou konstantu 700 ms.
- Body obrysu rychlejší než 150 px/s odhrnou hvězdy pozadí do 28 px ve
  směru pohybu s mírnou turbulencí; hvězdy se pak tlumeně vrátí na místo.
- Stav všech hvězd je v polích alokovaných jednou při startu.

Parametry nemají nastavovací UI; popisuje je
[`DEC-018`](DECISIONS.md#dec-018), původní přijaté hodnoty
[`DEC-009`](DECISIONS.md#dec-009).

## Co tu (zatím) není

CI a licence zatím nejsou připravené.
Architekturu a základní závislosti stanovují
schválené záznamy v `DECISIONS.md`.
