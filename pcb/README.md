# Základná doska FVE divertera (ESP32 + 2× DimmerLink)

> ⚠️ **Not tested yet / zatiaľ neoverené (2026-11-17):** doska rev B je objednaná, ale ešte nie je
> osadená ani oživená. Rozmery líšt ESP32 a DimmerLinku treba overiť na reálnych kusoch.
>
> ⚠️ **Rezistory pre CUR-S (R9–R12) ešte nie sú určené.** Napätie výstupu prúdového snímača
> CUR-S na doskách rbdimmer výrobca neuvádza a zatiaľ sme ho nezmerali. Kým nebude zmerané,
> **R9/R11 neosadzuj** (CUR-S je tak od ESP32 odpojený; firmvér ho aj tak len zobrazuje ako napätie, na reguláciu sa nepoužíva).
> Snímač na 3,3 V → R9/R11 = 0 Ω, R10/R12 neosadiť; na 5 V → delič (návrh R9/R11 10 kΩ +
> R10/R12 18 kΩ, ešte neoverený). Postup merania: [`../docs/MERANIE_rbdimmer.md`](../docs/MERANIE_rbdimmer.md).

KiCad 9 projekt: `fve_doska/fve_doska.kicad_pro`. Generuje ho `gen_doska.py`. Pri zmene
rozmerov alebo zapojenia upraviť generátor a spustiť znova. Ručné úpravy v KiCade sa
pri ďalšom generovaní prepíšu.

**Stav (rev B): OBJEDNANÁ 2026-11-16** — Gerbery `vyroba/fve_doska_gerber.zip` z commitu
`96e6954` (posun konektorov + prepojovacie priechody GND). Freerouting 2.5, 0 nespojených, DRC
bez chýb spojov aj medzier — zostali len kozmetické upozornenia potlače a 4× „starved thermal“
pri GND pinoch, ktoré sú pripojené aj trasou. Napájanie a GND 1 mm (pri pinoch min 0,4),
signály 0,4 mm, všetky medzery min 0,4 mm, GND vyliaty na oboch vrstvách + 114 prepojovacích
priechodov (prekryté maskou). Na spodnej potlači „rev B 2026-11“.

**rev B oproti rev A:** J15 I2C zmenený z XH-4 na **XH-5 s 5 V** + nový rovnaký **J18** pod ním
(2× rbAmp UI1 — TUV a podlaha, viď `../docs/rbAmp_meranie_vykonu.md`). Inak bez zmeny.
rev A (commit `5b418e1`) mal user prvú objednanú — ak by prišla rev A, J15 je len XH-4 bez 5 V
(5 V pre rbAmp potom priamo zo zdroja Mean Well).
Poradie pinov DimmerLinku 2CH overil user fyzicky (2026-11-15) — sedí.

⚠️ `gen_doska.py` dosku vygeneruje znova BEZ trás → po každej zmene spustiť aj `route.py`.

Náhľad: `fve_doska/nahlad_doska.png` · schéma: `fve_doska/fve_doska_schema.pdf` · nákup: [`NAKUP_TME.md`](NAKUP_TME.md)

## Zásady

- Na doske je **len 5 V a 3,3 V**. 230 V ostáva na relé moduloch, opto module a doskách
  rbdimmer.
- ESP32 a DimmerLinky sú zasunuté v dutinkových lištách, dajú sa vymeniť.
- Všetko s tenkými káblami (snímače, prietok, opto, relé moduly, rbdimmery) je na zacvakávacích
  **JST-XH so zámkom** (rozteč 2,5 mm). Krimpuje sa bežnými kliešťami pre JST-XH (XH-2…6). Na strane
  modulov (relé, opto, rbdimmer s kolíkmi 2,54 mm) je kábel ukončený DuPont puzdrom zo sady.
  Rbdimmer má 2 konektory XH-4 (riadenie a snímače), lebo sada má XH najviac 6-pin.
- Len napájanie 5 V je na bezskrutkovej svorke **WAGO 2601-3102** (push-in, vodič zhora,
  do 1,5 mm², každý pól 2 nožičky kvôli pevnosti).
- Rezistory sú priletované na doske. GND je vyliaty na oboch vrstvách. Pod anténou ESP32
  nie je meď.

## Svorky (poradie pinov = poradie na doske, popis na potlači)

| Svorka | Piny | Kam |
|---|---|---|
| J1 NAPÁJANIE 5V (WAGO) | 5V GND | Mean Well MDR-20-5 |
| J2 B1 BOJLER (XH-3) | 3V3 GND DQ (G21, R1) | DS18B20 |
| J3 B2 VRATNÁ (XH-3) | 3V3 GND DQ (G5, R7 — alebo G21 cez JP5) | DS18B20 |
| J4 B3 PODLAHA (XH-3) | 3V3 GND DQ (G13, R8 — alebo G21 cez JP6) | DS18B20 |
| J5 PRIETOK TUV (XH-3) | 3V3 GND SIG (G4, R6) | Hall prietokomer |
| J6 OPTO DAIKIN + 5V (XH-6) | 5V GND K3M (G14) ČERP (G27) GND 3V3 | AC opto modul (VCC = 3V3!) + napájanie ESPAltherma 5 V |
| J7 RELÉ TUV (XH-5) | GND IN1 (G17 stykač) IN2 (G16 bypass) 3V3 5V(JD-VCC) | 2-kan. relé |
| J8 RELÉ PODLAHA (XH-5) | GND IN1 (G19) IN2 (G18) 3V3 5V | 2-kan. relé |
| J9 RELÉ ČERPADLÁ (XH-5) | GND TUV (G26) POD (G25) 3V3 5V | 2-kan. relé |
| J10 RBDIMMER TUV riadenie (JST-XH 4) | 3V3 GND ZC DIM | doska D1 (ZC/DIM z DimmerLinku TUV, I2C 0x54) |
| J11 RBDIMMER TUV snímače (JST-XH 4) | TEMP CUR FAN 5V | doska D1 |
| J13 RBDIMMER POD riadenie (JST-XH 4) | 3V3 GND ZC DIM | doska D2 (ZC/DIM z DimmerLinku podlaha, I2C 0x53) |
| J14 RBDIMMER POD snímače (JST-XH 4) | TEMP CUR FAN 5V | doska D2 |
| J12 FAN SKRINE (XH-4) | GND 5V TACHO (G22) PWM (G23) | ventilátor skrine (pôvodný konektor fanu nahradený JST-XH) |
| J15 I2C (1) (XH-5) | 3V3 GND SDA (G2) SCL (G15) 5V | rbAmp TUV (GND SDA SCL 5V, 3V3 nezapájať) alebo SHT/BME/DS2482 (3V3) |
| J18 I2C (2) (XH-5) | 3V3 GND SDA (G2) SCL (G15) 5V | rbAmp podlaha — rovnaké ako J15, pod ním (rev B, 2026-11-16) |
| J16 ONEWIRE (1) (XH-3) | 3V3 GND DQ — cez JP7: 1-2 G5 (R7), 2-3 G21 | ďalšie DS18B20 |
| J17 ONEWIRE (2) (XH-3) | 3V3 GND DQ — cez JP8: 1-2 G13 (R8), 2-3 G21 | ďalšie DS18B20 |

**Prepojky OneWire JP5–JP8:** podrobný návod je nižšie v sekcii „Prepojky OneWire JP5–JP8 — návod“.

**TEMP** (NTC 10k proti GND, overené) ide priamo na ESP: TUV G36, podlaha G34, pull-up R4/R5 10 kΩ.
**CUR-S** ide na ESP cez R9/R11 (G39/G35). **R9/R11 osadiť až po zmeraní** napätia snímača
([`../docs/MERANIE_rbdimmer.md`](../docs/MERANIE_rbdimmer.md)): snímač na 3,3 V → R9/R11 = 0 Ω, R10/R12 neosadiť; na 5 V → delič.
Kým R9/R11 chýba, CUR-S je od ESP odpojený.

## Prepojky OneWire JP5–JP8 — návod

*(Napísané 2026-11-16, aby sa to dalo pochopiť aj o pár rokov.)*

### Prečo to tam je

Teplomery DS18B20 komunikujú cez OneWire: jeden dátový vodič (DQ, žltý), na ktorom môže byť
aj viac snímačov naraz (tzv. zbernica). **Lacné klony DS18B20, ktoré máme (2026-11-14), po dvoch
na jednej zbernici nefungujú** (ESP číta samé nuly). Preto má každý z nich vlastný pin ESP32:

| Pin ESP32 | Pull-up (4,7 kΩ na 3,3 V) | Názov vo firmvéri (`one_wire` id) | Pevne zapojený |
|---|---|---|---|
| **G21** | R1 | `ow_bus` | **B1 BOJLER (J2) — vždy, bez prepojky** |
| **G5** | R7 | `ow_vratna` | nie, cez JP5 alebo JP7 |
| **G13** | R8 | `ow_podlaha` | nie, cez JP6 alebo JP8 |

Prepojky rozhodujú, ktorý konektor dostane ktorý pin. Keď raz kúpiš originálne (alebo
overené) snímače, ktoré zvládnu spoločnú zbernicu, dajú sa B2 a B3 presunúť na G21 a uvoľnené
piny G5 / G13 použiť pre nové konektory ONEWIRE (1) J16 a ONEWIRE (2) J17.

### Ako vyzerá prepojka

Každá JP je 3-pinová lišta s jedným jumperom. **Prostredný pin (2) = DQ konektora.** Jumper ho
spojí buď s pinom 1 (vlastný pin), alebo s pinom 3 (spoločná zbernica G21):

```
          pin 1 ── G5 / G13  (vlastný pin, vlastný pull-up R7 / R8)
JP  ──┤   pin 2 ── DQ konektora (B2, B3, J16 alebo J17)
          pin 3 ── G21       (zbernica bojlera, pull-up R1)

jumper na 1-2 → konektor je na vlastnom pine
jumper na 2-3 → konektor je na spoločnej zbernici G21 (spolu s bojlerom B1)
bez jumpera   → konektor je odpojený (nič sa nepokazí)
```

| Prepojka | Pre konektor | 1-2 | 2-3 | Kde na doske | Pin 1 (štvorcová ploška) |
|---|---|---|---|---|---|
| **JP5** | B2 VRATNÁ (J3) | G5 | G21 | vľavo dole, nad J3, vedľa R7 | **hore** |
| **JP6** | B3 PODLAHA (J4) | G13 | G21 | vľavo dole, nad J4, vedľa R8 | **hore** |
| **JP7** | ONEWIRE (1) (J16) | G5 | G21 | vpravo v strede, pod J16 | **vľavo** |
| **JP8** | ONEWIRE (2) (J17) | G13 | G21 | vpravo v strede, pod J17 | **vľavo** |

Popis „1-2 G5 / 2-3 G21“ (resp. G13) je pri každej prepojke na potlači.

### Pravidlá

1. **G5 smie dostať len jeden konektor:** buď JP5 (B2), alebo JP7 (J16) v polohe 1-2, nie obe.
   **G13 rovnako:** buď JP6 (B3), alebo JP8 (J17). Na doske je to pripomenuté nápisom
   „JP5+JP7 / JP6+JP8 nie naraz 1-2!“. Elektricky sa nič nepokazí, ale dva snímače na jednom
   pine = zbernica a klony na zbernici nefungujú.
2. **Na G21 (poloha 2-3) dávaj len snímače, ktoré na zbernici preukázateľne fungujú.** Na G21
   je vždy aj bojler B1 — chybný alebo nevhodný snímač môže zablokovať celú zbernicu a bojler
   potom ukazuje nezmysel / „unknown“. Regulácia TUV pri neplatnej teplote bojlera nehreje.
3. **Na vlastnom pine (1-2) môže byť aj viac snímačov** (napr. na J16 rozdvojený kábel), ale
   platí to isté: zbernicu zvládnu len dobré snímače. Jeden klon = vždy sám na pine.
4. **Po každej zmene prepojok treba upraviť aj firmvér** (nižšie) — ESP nevie, kde je jumper.
5. Prepojky prestavovať **bez napätia** (vypnúť 5 V zdroj).
6. G5 je „strapping“ pin ESP32 (pri štarte má byť v log. 1, R7 to zaručí). Ak by ESP po
   pripojení snímača na G5 nenaštartovalo, vytiahni jumper JP5 / JP7 a skús znova.

### Platné nastavenia

| Situácia | JP5 | JP6 | JP7 | JP8 | Firmvér |
|---|---|---|---|---|---|
| **A — teraz (stav 2026-11): klony, každý sám** | 1-2 | 1-2 | bez jumpera alebo 2-3 * | bez jumpera alebo 2-3 * | `ow_b2: ow_vratna`, `ow_b3: ow_podlaha` (tak je to teraz) |
| **B — B2 a B3 originálne na G21, J16/J17 na vlastných pinoch** | 2-3 | 2-3 | 1-2 | 1-2 | `ow_b2: ow_bus`, `ow_b3: ow_bus`; snímač J16 na `ow_vratna`, J17 na `ow_podlaha` |
| **C — iba B2 na G21, B3 ostáva sám** | 2-3 | 1-2 | 1-2 | 2-3 alebo bez | `ow_b2: ow_bus`; snímač J16 na `ow_vratna`, J17 (ak je) na `ow_bus` |
| **D — iba B3 na G21, B2 ostáva sám** | 1-2 | 2-3 | 2-3 alebo bez | 1-2 | `ow_b3: ow_bus`; snímač J17 na `ow_podlaha`, J16 (ak je) na `ow_bus` |

\* Kým na J16/J17 nič nie je, na polohe nezáleží. Odporúčam jumper odložiť nasadený len na
jeden pin (aby sa nestratil) — konektor je potom odpojený.

**Zakázané:** JP5 a JP7 obe v 1-2 (dva konektory na G5), JP6 a JP8 obe v 1-2 (dva na G13).

### Firmvér (`../esp32-fve-diverter/fve-diverter.yaml`)

Tri zbernice sú vo firmvéri definované vždy rovnako (sekcia `one_wire:`), menia sa len
priradenia snímačov. Pozor: názvy `ow_vratna` / `ow_podlaha` znamenajú **pin G5 / G13**, nie
konkrétny snímač — keď sa B2 presunie na G21, `ow_vratna` (G5) potom slúži pre J16.

- **B2 a B3** sa prepínajú substitúciami na začiatku súboru:
  ```yaml
  substitutions:
    ow_b2: ow_vratna    # JP5 1-2 (G5);  pri JP5 2-3 → ow_bus
    ow_b3: ow_podlaha   # JP6 1-2 (G13); pri JP6 2-3 → ow_bus
  ```
- **J16 / J17** (zatiaľ vo firmvéri nie sú) — doplniť snímač do sekcie `sensor:`:
  ```yaml
    - platform: dallas_temp
      one_wire_id: ow_vratna        # J16: JP7 1-2 → ow_vratna (G5), JP7 2-3 → ow_bus (G21)
      address: 0x...                # adresu zistiť z logov (nižšie)
      name: "Teplota ..."
      update_interval: 30s
  ```
  (J17: JP8 1-2 → `ow_podlaha` (G13), JP8 2-3 → `ow_bus`.)
- **Vždy s adresou** (`address:`). Bez nej ESPHome berie snímače podľa poradia a po reštarte by
  si mohli vymeniť miesta (napr. TUV by ukazovala podlahu).
- **Zistenie adresy nového snímača:** pripojiť ho samotný, nahrať firmvér, v logoch ESPHome
  hľadať „Found sensors: 0x…“ (postup je aj v komentári nad `one_wire:` v YAML-e). Adresu zapísať
  do YAML-u a kábel snímača oštítkovať.

### Postup pri zmene (krok za krokom)

1. Vypnúť napájanie 5 V.
2. Prestaviť prepojky podľa tabuľky „Platné nastavenia“ (skontrolovať pravidlo č. 1).
3. Pripojiť snímače.
4. Upraviť `fve-diverter.yaml` (substitúcie / nové snímače s adresami), nahrať (OTA).
5. Zapnúť, v logoch skontrolovať „Found sensors“ na každej zbernici a v HA všetky teploty —
   **hlavne bojler B1**, od ktorého závisí regulácia TUV.

### Keď niečo nejde

- **Bojler B1 po pridaní snímača na G21 ukazuje nezmysel / „unknown“:** nový snímač zbernicu
  nezvláda → daj ho na vlastný pin (prepojka 1-2), alebo vytiahni jeho jumper.
- **Snímač nie je vidieť vôbec:** je jumper nasadený? Sedí `one_wire_id` vo firmvéri s polohou
  jumpera? Sedí adresa?
- **Teplota 85 °C:** typická hodnota DS18B20 po zapnutí / pri zlom napájaní — skontrolovať
  kábel (3V3, GND).

## Zoznam súčiastok

| Ks | Súčiastka | Pozn. |
|---|---|---|
| 2 | dutinková lišta 1x19, 2,54 mm | pätica ESP32 (U1) |
| 2 + 2 | dutinková lišta 1x4 + 1x5, 2,54 mm | pätice DimmerLinkov (U2, U3), overiť |
| 1 | WAGO 2601-3102 | J1 |
| 6 | JST-XH 3-pin (XH-3A na dosku + XH-3Y puzdro) | J2–J5, J16, J17 (zo sady) |
| 5 | JST-XH 4-pin (XH-4A + XH-4Y) | J10–J14 (zo sady) |
| 5 | JST-XH 5-pin (XH-5A + XH-5Y) | J7–J9, J15, J18 (zo sady) |
| 1 | JST-XH 6-pin (XH-6A + XH-6Y) | J6 (zo sady) |
| 4 | kolíková lišta 1x3 + jumper | JP5–JP8 (OneWire) |
| — | kontakty JST-XH + DuPont puzdrá 1x3/1x4/1x5/1x8 na strane modulov | zo sady |
| 6 | rezistor 4,7 kΩ 0,25 W | R1–R3, R6–R8 |
| 2 | rezistor 10 kΩ 0,25 W | R4, R5 |
| 2 | 0 Ω alebo delič — až po zmeraní CUR-S | R9, R11 (R10, R12 len pri 5 V) |
| 3 | kondenzátor 100 nF, keramický, rozteč 5 mm | C2–C4 |
| 1 | elektrolyt 470 µF / 10 V, Ø8 mm | C1 |
| 1 | elektrolyt 47 µF / 10 V, Ø5 mm | C5 |

C3, C4 (100 nF pri DimmerLinkoch) odporúča výrobca DimmerLinku na odfiltrovanie rušenia
na 3,3 V. Bez nich to funguje, na doske sú ako poistka.

## Otvorené

- [x] ESP32: rozteč radov ~25,5 mm (user) → 25,4 mm (1").
- [x] DimmerLink: vzdialenosť líšt ~12,5 mm (user) → 12,7 mm.
- [x] DimmerLink 2CH: vstup 1x4 VCC GND SDA SCL, výstup 1x5 VCC GND ZC DIM0 DIM1 — overené.
- [x] Doska 130 × 80 mm na šírku (kvôli cene), relé v jednom rade vedľa seba, 6× M3 pre dištančné stĺpiky (4 rohy, medzi ESP a relé, stred dolnej strany).
      ESP32 naležato vľavo, anténa k ľavému okraju (pod ňou bez medi).
- [x] Natrasované (`route.py` = Freerouting 2.5 + OpenJDK 25), DRC OK.
- [x] Gerber + vŕtanie: `vyroba/fve_doska_gerber.zip` (rev A 2026-11-15, **rev B 2026-11-16**).
- [x] rev B: J15 + J18 I2C XH-5 s 5 V (rbAmp).
- [x] rev B (2026-11-16, úprava): OneWire J16 +2 mm a J17 +1 mm doprava, I2C J15/J18 a relé J7/J8/J9 o 1 mm dole; znova natrasované.
- [x] rev B: 114 prepojovacích priechodov GND (vrch ↔ spodok), `prechodky.py`.
- [x] **rev B objednaná 2026-11-16** (Gerbery z commitu `96e6954`).
- [ ] Po príchode: osadiť, oživiť, overiť rozmery líšt ESP32 / DimmerLink.

## Generovanie

```
python3 gen_doska.py                       # schéma + doska (rozmiestnenie)
python3 route.py <freerouting-2.5.0.jar>   # autorouter (Java 25: /usr/lib/jvm/java-25-openjdk-amd64)
#   na konci spustí prechodky.py: vyliatie GND + prepojovacie priechody GND (mriežka 5 mm, 0,8/0,4 mm)
#   dá sa spustiť aj samostatne na natrasovanej doske: python3 prechodky.py
#   route.py: trasuje s medzerou 0,42 mm (rezerva na rozšírenie zúžení), uloží s pravidlom 0,4 mm;
#   zúžené trasy rozširuje textovo a GND vylieva v novom procese (KiCad 9.0.2: po importe SES
#   je väzba pcbnew v Pythone pokazená — GetTracks/LoadBoard vracajú SwigPyObject)
kicad-cli sch erc fve_doska/fve_doska.kicad_sch
kicad-cli pcb drc fve_doska/fve_doska.kicad_pcb
```

## Objednanie dosky

Súbor na nahratie: **`vyroba/fve_doska_gerber.zip`** (Gerber + vŕtanie, KiCad 9).
Pri zmene dosky: `gen_doska.py` → `route.py` → znova exportovať (príkazy nižšie).

Parametre (napr. JLCPCB / PCBWay):

| Parameter | Hodnota |
|---|---|
| Vrstvy | 2 |
| Rozmer | 130 × 80 mm |
| Hrúbka | 1,6 mm |
| Meď | 1 oz (35 µm) |
| Povrch | HASL (bezolovnatý podľa chuti) |
| Min. trasa / medzera | 0,4 / 0,4 mm (bežné, bez príplatku) |
| Min. vŕtanie | 0,4 mm (via) |
| Počet | 5 ks (minimum); user plánuje 10 ks (pre známych, +~5 €) |
| Osadenie | nie — súčiastky s vývodmi osádza user |

```
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts \
  --subtract-soldermask --no-x2 -o vyroba/gerber/ fve_doska/fve_doska.kicad_pcb
kicad-cli pcb export drill --format excellon --excellon-separate-th -o vyroba/gerber/ fve_doska/fve_doska.kicad_pcb
```

