# Nákup súčiastok — základná doska FVE divertera (rev B)

Zoznam na **1 dosku** (2026-11-15). Odkazy vedú na **vyhľadávanie v TME podľa typového čísla**.
Priame stránky produktov sa nedali overiť (TME blokuje automatický prístup), preto pred
objednaním skontroluj dostupnosť. Ak konkrétny typ nemajú, vyber iný s rovnakými parametrami.
Celý zoznam súčiastok dosky je v [`README.md`](README.md).

## Dokúpiť

| # | Súčiastka | Ks | Parametre / kde | Typ (príklad) | TME |
|---|---|---|---|---|---|
| 1 | Dutinková lišta 1×40, 2,54 mm, rovná | 2 | odrezať: 2× 19 (ESP32), 2× 4 + 2× 5 (DimmerLinky) | Connfly DS1023-1*40S21 | [hľadať](https://www.tme.eu/sk/katalog/?search=DS1023-1%2A40S21) |
| 2 | Svorka WAGO push-in, 2 póly, 3,5 mm, vodič zhora | 1 | napájanie 5 V (J1) | **WAGO 2601-3102** | [hľadať](https://www.tme.eu/sk/katalog/?search=2601-3102) |
| 3 | Rezistor 4,7 kΩ, 0,25 W, metalizovaný | 6 | R1–R3, R6–R8 | Yageo MFR-25FBF52-4K7 | [hľadať](https://www.tme.eu/sk/katalog/?search=MFR-25FBF52-4K7) |
| 4 | Rezistor 10 kΩ, 0,25 W | 2 (+2) | R4, R5; +2 na delič CUR-S (R9, R11), ak bude treba | Yageo MFR-25FBF52-10K | [hľadať](https://www.tme.eu/sk/katalog/?search=MFR-25FBF52-10K) |
| 5 | Rezistor 18 kΩ, 0,25 W | 2 | len ak CUR-S bude na 5 V (R10, R12) | Yageo MFR-25FBF52-18K | [hľadať](https://www.tme.eu/sk/katalog/?search=MFR-25FBF52-18K) |
| 6 | Keramický kondenzátor 100 nF, 50 V, rozteč 5 mm | 3 | C2, C3, C4 | KEMET C322C104K5R5TA | [hľadať](https://www.tme.eu/sk/katalog/?search=C322C104K5R5TA) |
| 7 | Elektrolyt 470 µF, 10 V (aj 16 V), Ø8 mm, rozteč 3,5 mm | 1 | C1 | Panasonic EEU-FR1A471 | [hľadať](https://www.tme.eu/sk/katalog/?search=EEU-FR1A471) |
| 8 | Elektrolyt 47 µF, 10 V (aj 16 V), Ø5 mm, rozteč 2 mm | 1 | C5 | Panasonic EEU-FR1A470 | [hľadať](https://www.tme.eu/sk/katalog/?search=EEU-FR1A470) |
| 9 | Prepojka (jumper) 2,54 mm | 4 (+2) | JP5–JP8 | ľubovoľná 2,54 mm | [hľadať](https://www.tme.eu/sk/katalog/?search=jumper%202.54) |
| 10 | Dištančný stĺpik M3, 10 mm (nylon alebo mosadz) | 6 | diery H1–H6 (Ø 3,2 mm) | M3×10 | [hľadať](https://www.tme.eu/sk/katalog/?search=distance%20M3%2010mm) |
| 11 | Skrutka M3×6 (+ podložka) | 6–12 | podľa typu stĺpika | DIN 7985 / ISO 7380 | [hľadať](https://www.tme.eu/sk/katalog/?search=M3x6%20skrutka) |

**Poznámky:**
- **Rezistory** sa na TME často predávajú po 10/100 ks. Sú lacné, kúp ich viac.
- **R9/R11 (CUR-S)** — pri snímači na 3,3 V stačí drôtová prepojka (odstrihnutá nožička
  rezistora), 0 Ω netreba kupovať. Pri 5 V delič 10 kΩ / 18 kΩ. Osadiť až po zmeraní
  (`../docs/MERANIE_rbdimmer.md`).
- **Dutinkové lišty** sa pri odrezávaní dajú len prerezať a stratí sa 1 pin. Preto 2× 1×40:
  19 + 19 + 4 + 4 + 5 + 5 = 56 pinov plus straty.

## Už je k dispozícii (sada PARKSIDE a iné)

- **JST-XH** zásuvky na dosku aj puzdrá: XH-3 ×6 (J2–J5, J16, J17), XH-4 ×5 (J10–J14),
  XH-5 ×5 (J7–J9, J15, J18), XH-6 ×1 (J6).
- **Kolíkové lišty 2,54 mm** na JP5–JP8 (4× 1×3 odlomiť z lišty zo sady).
- **DuPont puzdrá a kontakty** na strane modulov (relé, opto, rbdimmer).
- **RC snubbery** na cievky stykačov (A1–A2).

## Doska (výroba)

`vyroba/fve_doska_gerber.zip` — 2 vrstvy, 130 × 80 mm, 1,6 mm, 1 oz, HASL, 5 ks (parametre v
[`README.md`](README.md#objednanie-dosky)).

## Mimo TME — rbAmp (voliteľné, PLÁN 2026-11-16)

Meranie skutočného výkonu do špirál: **2× rbAmp UI1** (alebo 1× UI2) z rbdimmer.com + kliešte
SCT-013 s napäťovým výstupom (TUV -020/-030, podlaha -005/-010; NIE -000). Pripája sa na
J15 / J18 (doska rev B). Detaily: [`../docs/rbAmp_meranie_vykonu.md`](../docs/rbAmp_meranie_vykonu.md).
