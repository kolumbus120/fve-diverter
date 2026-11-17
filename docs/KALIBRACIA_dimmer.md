# Kalibrácia dimmerov — výkon podľa Shelly (HOTOVÉ 2026-11-15 22:25–22:50)

**Prečo:** prepočet výkon → úroveň dimmera (krivka DimmerLinku LINEAR) je zatiaľ podľa teórie
fázového riadenia `P/Pmax = L − sin(2πL)/(2π)`. Prvé meranie 2026-11-15 popoludní teóriu
potvrdilo, ale rušila ho iná spotreba na tej istej fáze (Daikin). Kliešte usera nemusia merať
presne → presný činný výkon zo Shelly 3EM.

## Podmienky

- **Čas 21:30–00:30** — o 21:00 nočná automatizácia vypne kúrenie Daikinu (kompresor = najväčšie
  kolísanie), o 01:00 sa zapína znova.
- **Batéria na min SoC** (Solax cloud `battery_soc` ≤ min, `battery_power` ≈ 0) — inak menič
  časť výkonu dorovná z batérie a Shelly ukáže menej. Pred testom overiť.
- V dome nezapínať veľké spotrebiče (kanvica, rúra, práčka).
- TUV pod max teplotou (74 °C), stykač TUV / podlaha zopnutý (deň do 20:00 → po 20:00 ho drží
  manuálny výkon). Podlaha: čerpadlo podlahy nie VYP, voda pod 35 °C.

## Postup

Cez `number.fve_diverter_tuv_manualny_vykon_0_auto` (a `…podlaha_manualny_vykon_0_auto`) — ESP
požadovaný výkon prepočíta na úroveň. Skript v scratchpade (`curve_test.py`) — Shelly
`http://<IP Shelly>/rpc/EM.GetStatus?id=0`, TUV je na fáze **C** (`c_act_power`), podlaha
overiť (L2 → pravdepodobne fáza B).

1. **TUV:** 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100 %, každý 2×.
   Krok: základ (4 čítania / 6 s) → nastav → 14 s (100 %: 20 s, zopne bypass) → meranie
   (4 čítania) → 0 → 8 s → základ po. **Ak sa základ pred/po líši o viac ako 50 W, krok zopakovať.**
2. **Podlaha (640 W):** to isté.
3. Na konci manuálny výkon späť na 0, skontrolovať dimmer VYP a bypass VYP.

Trvanie ~20 min, zo siete ~0,7 kWh (ide do bojlera / podlahy).

## Vyhodnotenie

- Výkon oboch špirál pri 100 % (Shelly) → nastaviť `number.fve_diverter_vykon_spiraly_tuv` /
  `…_podlaha` (zatiaľ TUV 2850 W podľa 1 merania, podlaha 640 W podľa klieští).
- Nameraný výkon vs. požadovaný. Ak sa líši viac ako ~5 %, nahradiť vzorec v `set_dimmer`
  (`fve-diverter.yaml`, regulácia) tabuľkou z merania (lineárna interpolácia).
- Výsledky dopísať sem a do `TODO_fve_diverter.md` (sekcia Ostrá verzia).

## Doterajšie merania (2026-11-15 popoludní, batéria 19 %)

| Úroveň | LINEAR | RMS | Teória |
|---|---|---|---|
| 10 % | 41 W | rušené | 19 W |
| 25 % | 317 W | 0 W (2×) | 265 W |
| 50 % | 1439 W | ~320 W (2×) | 1475 W |
| 75 % | 2696 W | ~1910 W | 2680 W |
| 100 % (bypass) | 2824 W | | |

Po zavedení prepočtu (požadovaný výkon): 50 % → 1572 W, 75 % → 2259 W (cieľ 1475 / 2210 W);
10 a 25 % rušené.

## ✅ Výsledok kalibrácie 2026-11-15 večer

Podmienky: 22:25–22:50, kúrenie Daikinu VYP, batéria 19 % (min SoC), dom ~370 W. TUV na fáze
**C**, podlaha na fáze **B**. Každý krok 2×, základ pred/po. Surové dáta:
[`kalibracia_dimmer_2026-11-15.csv`](kalibracia_dimmer_2026-11-15.csv) (stĺpce dA/dB/dC = prírastok
na fáze). Podlaha 70 % krok 1 vyradený (iná záťaž ~2 kW na fáze B).

**Plný výkon (100 %, bypass):** TUV **3003 W**, podlaha **595 W** → v HA nastavené 3000 / 595 W.

**Krivka (úroveň DimmerLinku LINEAR → % plného výkonu, priemer TUV a podlahy):**

| Úroveň | 20 | 26 | 30 | 34 | 37 | 40 | 45 | 50 | 55 | 60 | 66 | 74 | 100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TUV % | 6,2 | 12,2 | 17,4 | 23,7 | 28,9 | 34,6 | 43,9 | 53,6 | 63,6 | 73,2 | 82,2 | 91,8 | 100 |
| podlaha % | 5,3 | 12,4 | 18,2 | 24,4 | 29,9 | 36,0 | 45,3 | 55,5 | 64,6 | 71,3 | 80,6 | 89,6 | 100 |
| teória % | 4,9 | 10,1 | 14,9 | 20,6 | 25,4 | 30,6 | 40,1 | 50,0 | 59,9 | 69,4 | 79,4 | 89,9 | 100 |

Oba dimmery dávajú v strede o 3–5 bodov viac než teória (vlastnosť DimmerLinku, nie špirál) →
vo firmvéri (`set_dimmer`) teória nahradená **tabuľkou z merania** (priemer), pod 20 % úrovne body
z teórie.

**Overenie po zmene (TUV, požadovaný výkon):** 25 % → 767 W (cieľ 750), 50 % → 1519 W (1500),
75 % → 2290 W (2250) — odchýlka do ~1,5 %.
