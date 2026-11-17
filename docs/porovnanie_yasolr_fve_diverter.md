# Porovnanie: YaSolR vs. náš FVE diverter (2026-11-15)

**O čo ide:** user chcel vedieť, v čom je náš diverter (`../esp32-fve-diverter/fve-diverter.yaml`,
ostrá verzia z 2026-11-15) lepší alebo horší než známy open-source solárny router **YaSolR**
(„Yet Another Solar Router“, autor Mathieu Carbou). Prešiel som web aj zdrojový kód. Tento súbor
je výsledok + návrhy, čo od neho prevziať. **Nič z návrhov zatiaľ nie je implementované.**

## Zdroje (čo sa čítalo)

- Web: <https://yasolr.carbou.me/> (hlavná), `/pro`, `/comparison`, `/manual`
- Kód: <https://github.com/mathieucarbou/YaSolR>, commit `7c6e8b8` (2026-11-14) —
  hlavne `src/yasolr_pid.cpp`, `src/yasolr_router.cpp`, `lib/MycilaRouter/`,
  `include/yasolr_macros.h`, `platformio.ini`
- Náš stav: `../esp32-fve-diverter/fve-diverter.yaml` (2026-11-15) a
  `TODO_fve_diverter.md`, sekcia „Ostrá verzia 2026-11-15“

## Čo je YaSolR

- Firmvér pre ESP32 (Arduino/PlatformIO, C++), licencia **GPL-3**. Vlastný kód ~8,4 tisíc riadkov
  plus knižnice Mycila (MycilaDimmer, MycilaJSY, MycilaPID…).
- **Univerzálny router:** 1–2 výstupy (špirály), **jeden** zdroj merania siete a reguluje tak,
  aby odber zo siete bol 0 (setpoint 0 W).
- Zdroje merania siete: JSY-MK-163/193/194/227/229/333 (lokálne, UART), MQTT (HA, Shelly EM…),
  Shelly LNM (UDP multicast, 1 správa/s, Gen2+, „preview“), Victron/Fronius Modbus TCP.
- Stmievače: zero-cross SSR, random SSR + ZCD, RobotDyn, regulátory napätia LSA/LCTC cez DAC.
  Vie **fázové riadenie** aj **vynechávanie celých periód** (cycle stealing, delta-sigma).
- Bypass relé (NO/NC), max. 2 relé s automatickým spínaním podľa prebytku, DS18B20, OLED,
  web UI, REST, MQTT + HA auto-discovery.
- **OSS vs. Pro:** firmvér je rovnaký, Pro pridáva komerčné knižnice (úplný dashboard,
  konfigurácia z dashboardu, ladenie PID s grafom, GPIO/HW health). Odomkne sa darom od 25 €.

### Predvolené hodnoty PID v YaSolR (z manuálu + kódu)

- P z merania („On Input“): `P += Kp·(last_measured − measured)`, alternatíva „On Error“.
- Kp 0,1 / **Ki 0,3** / Kd 0, výstup −800…4000 W, setpoint 0, spúšťanie pri každom novom meraní
  (max. každé 2 s).
- Obmedzenie integrátora (CLAMP), voliteľný EMA filter na vstupe (0/30/40/80 %).
- **Reset integrátora:** pri pretoku, keď sa nič neodbočuje (napr. limit výstupu), aby po
  uvoľnení nevznikol skok (`yasolr_pid.cpp`).
- Prevod výkonu na úroveň stmievača: tabuľka (`enablePowerLUT(true)`).
- Platnosť meraní z MQTT: `YASOLR_MQTT_MEASUREMENT_EXPIRATION 120000` (120 s; manuál uvádza 1 min).
  Keď meranie 2 s nepríde, PID zopakuje poslednú korekciu.

## Hlavný rozdiel v jednej vete

YaSolR je hotový univerzálny router, ktorý vidí iba sieť. Náš je diverter na mieru celému domu:
rieši batériu Solax, Daikin, čerpadlá a režimy kúrenia, ale meria pomalšie a regulátor je
ručne písaný.

## Kde je YaSolR lepší

| Oblasť | YaSolR | My (2026-11-15) |
|---|---|---|
| Rýchlosť regulácie | Lokálny JSY: niekoľko meraní/s, PID viac ako 3×/s | Shelly každých 5 s, Solax cez cloud raz za ~4 min |
| Regulátor | Riadny PID (P z merania, CLAMP, EMA filter, reset integrátora) | Vlastný krokový regulátor: ubratie 0,6·odber, pridanie 0,3·pretok + krok podľa Solaxu; ladený skúšaním |
| Meranie výstupu | JSY/PZEM: skutočný výkon do špirály, účinník, harmonické; odpor špirály sa kalibruje sám | Výkon iba odhad (úroveň × výkon špirály), výkon špirály zmeraný ručne cez Shelly |
| Nečinný výstup | Po 10 s bez odberu výstup dostane len 2 W, zvyšok ide na druhý výstup | Nevidíme. Ak vypne mechanický termostat bojlera skôr než náš strop 74 °C, prebytok ide do siete |
| Harmonické | Fázové riadenie + cycle stealing (oveľa menej harmonických), zobrazenie voči EN 61000-3-2 | Iba fázové riadenie (DimmerLink); proti rušeniu len EMI filter |
| Vyspelosť | Veľa používateľov, dokumentácia, safeboot, záloha konfigurácie; s lokálnym JSY beží úplne bez siete | 2100-riadkový YAML s lambdami, jedna inštalácia, vlastná opravená kópia komponentu DimmerLink |

**Zaujímavosť:** naše `D += 0,3·pretok` je v podstate čistý I-regulátor s Ki = 0,3, a to je presne
predvolená hodnota Ki v YaSolR. Rozdiel nie je v zosilnení, ale v tom, ako často sa meria. Oni
ten istý pretok dorovnajú zhruba 15× rýchlejšie (krok ~0,3 s oproti našim 5 s).

**Rovnocenné:** prevod výkonu na úroveň stmievača. Oni majú tabuľku, my vzorec
`P/Pmax = L − sin(2πL)/2π`. Je to tá istá fyzika. Zero-cross: oni majú vlastné prerušenia
a analýzu impulzov, my to necháme na hardvér DimmerLinku.

## Kde je náš lepší

1. **Batéria.** YaSolR vidí iba sieť a nevie nič o batérii ani SoC. S hybridným meničom buď
   batéria zoberie všetko, kým sa nenabije, alebo menič vybíja batériu do špirály a sieť ukazuje
   0, takže to nezistí. My prebytok delíme zámerne: rezerva 300 W pre batériu, nad podlahou TUV a
   batéria v pomere ¾ : ¼, pri SoC ≥ 97 % všetko do TUV. Slabinu s vybíjaním pri mraku máme tiež,
   ale zachytíme ju pri ďalšom údaji zo Solaxu (max. ~5 min, po donglu ~3 s).
2. **Daikin a celý dom.** Bypass TUV na žiadosť K3M, čerpadlo podlahy podľa opto vstupu, režimy
   kúrenia, čerpadlo TUV podľa prietokomera, stratégia v HA (`packages/fve_strategia.yaml`).
   YaSolR má iba 2 relé spínané podľa prebytku.
3. **Prísnejší výpadok merania.** U nás je údaj zo Shelly starší ako 15 s neplatný a výkon ide
   na 0, pri výpadku nad 60 s vypnú aj stykače. YaSolR berie MQTT hodnoty ako platné až 120 s.
4. **Stykače.** Izolačný stykač pred TRIAC-om (TRIAC pri poruche zvyčajne zostane zopnutý),
   bypass so zopnutím pri ≥ 97 %, časové okno 6–20 h, teplotné stropy s hysteréziou, NaN →
   nehreje, počítadlá zopnutí.
5. **Diagnostika a HA.** Do Influxu ukladáme, prečo regulácia spravila každý krok. Ventilátor
   skrine riadime PWM podľa výkonu, s tachometrom. Všetko natívne v HA cez ESPHome, bez Pro.

## Návrhy, čo prevziať (poradie = prínos)

1. **Rýchlejšie meranie siete.** Najväčší prínos.
   - Dongl Solax s údajom každé 3 s je už v pláne (TODO_fve_diverter.md).
   - Shelly je **3EM-63 Gen3** (`<IP Shelly>`, `rpc/EM.GetStatus`), teda nie Gen1. Skúsiť
     čítať každú 1–2 s namiesto 5 s, prípadne Shelly LNM (UDP push 1×/s, v YaSolR „preview“,
     na našom kuse neoverené).
   - **2026-11-16:** ESP číta Shelly každé 2 s (1 s fungovala bez problémov, user zvolil 2 s
     pre rezervu; http request blokuje slučku, timeout 800 ms, pri výpadku skúša len každých
     5 s). Regulácia zatiaľ beží každých 5 s s nezmenenými ziskami.
   - Alternatíva: JSY-MK-333 (3-fázový, UART) priamo na ESP. Stojí to však voľné GPIO
     (aktuálne voľný je iba GPIO5).
2. **Meranie výkonu do špirál.** Napríklad CUR-S na rbdimmeri (postup v `MERANIE_rbdimmer.md`)
   alebo PZEM. Dá to skutočnú energiu namiesto odhadu a zistenie nečinného výstupu (vypnutý
   termostat bojlera). Potom by sa prebytok presunul na druhý výstup.
   → **Kandidát (2026-11-16): rbAmp od rbdimmer.com**, viď [`rbAmp_meranie_vykonu.md`](rbAmp_meranie_vykonu.md).
3. **Po donglu prejsť na štandardný PI:** P z merania, EMA filter, obmedzenie integrátora,
   reset integrátora pri pretoku bez odbočovania. Ki začať okolo 0,3 pri rýchlom meraní.
   Pri rýchlom meraní to bude stabilnejšie a ľahšie sa to ladí než pravidlá brzda/plyn.
4. **Časový limit pre ručný režim.** V ostrej verzii `number` „TUV/Podlaha — manuálny výkon
   (0=auto)“ **nemá časový limit a prebíja reguláciu aj watchdog** (komentár v
   `fve-diverter.yaml`, „MANUÁLNE VYNÚTENIE“). Auto-vypnutie po 30 min má iba testovacia verzia.
   YaSolR má pre ručný bypass časový limit + keep-alive. Zvážiť to isté (napr. 2–4 h,
   0 = bez limitu).
   → **✅ Implementované 2026-11-16:** „Manuálny výkon — časový limit“ (default 5 h, 1–72 h),
   po vypršaní manuál → 0 (automatika) + upozornenie do telefónu (HA automatizácia
   `fve_diverter_manual_vyprsal`); po reštarte ESP je manuál vždy 0. Senzory „TUV/Podlaha —
   manuál zostáva“ (min).
5. *(Voliteľné)* **Cycle stealing pre podlahu (~640 W)**, ak by sa ukázali problémy
   s harmonickými alebo blikaním. Neoverené, či to DimmerLink podporuje.

## Záver / odporúčanie

**Na YaSolR neprechádzať.** Nevie batériu ani Daikin, a práve to je jadro nášho riešenia.
Prevziať body 1–3 (hlavne rýchlejšie meranie) a doplniť bod 4 (bezpečnosť ručného režimu).
