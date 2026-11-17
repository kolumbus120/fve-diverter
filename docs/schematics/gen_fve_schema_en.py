#!/usr/bin/env python3
# English version of the main schematic: reads fve_schema.svg (made by gen_fve_schema.py),
# translates every <text> by the dictionary below and writes fve_schema_en.svg + .png.
# Layout stays identical. Run after gen_fve_schema.py:  python3 gen_fve_schema_en.py
# Facts that are outdated in the Slovak drawing are updated here (2026-11-17): DimmerLink
# I2C addresses 0x54/0x53, PV window + "sunny day" instead of day/night, 15 s watchdog,
# Shelly read every 2 s. Untranslated Slovak text is reported (exit code 1).
import html
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fve_schema.svg")
DST = os.path.join(HERE, "fve_schema_en.svg")

TR = {
    "FVE automatizácia prebytkov — ESP32 #2  (TUV 3 kW → L1 · PODLAHA 600 W → L2)":
        "PV surplus diverter — ESP32 #2  (DHW 3 kW → L1 · FLOOR 600 W → L2)",
    "Revízia · 2026-09-13 · TRIAC fázovka (2× DimmerLink, I2C) + PI · 2 izolačné + 2 bypass stykače · EMI filtre":
        "Revision · 2026-11-17 · TRIAC phase control (2× DimmerLink, I2C) · 2 isolation + 2 bypass contactors · EMI filters",
    "SILNOPRÚD": "POWER",
    "HLAVNÝ 3F ISTIČ": "MAIN 3-PHASE BREAKER",
    "RCD 4-pól · 25 A · 30 mA · TYP A": "RCD 4-pole · 25 A · 30 mA · TYPE A",
    "(TRIAC fázovka → jednosmerné zložky → TYP A povinný; L1+L2 zdieľajú N)":
        "(TRIAC phase control → DC components → TYPE A required; L1+L2 share N)",
    "TUV / L1": "DHW / L1",
    "podlaha / L2": "floor / L2",
    "logika + čerpadlá": "logic + pumps",
    "STYKAČ 25 A (2×NO)": "CONTACTOR 25 A (2×NO)",
    "cievka 230 V ◄ relé GPIO17": "coil 230 V ◄ relay GPIO17",
    "cievka 230 V ◄ relé GPIO19": "coil 230 V ◄ relay GPIO19",
    "LINE-L/LINE-N ↑ sieť · LOAD-L/LOAD-N ↓ dimmer · kovové telo → PE":
        "LINE-L/LINE-N ↑ grid · LOAD-L/LOAD-N ↓ dimmer · metal case → PE",
    "40A TUV 3kW": "40A DHW 3kW",
    "I2C 0x50 · Z-C←L1": "I2C 0x54 · Z-C←L1",
    "40A podl.600W": "40A floor 600W",
    "I2C 0x51 · Z-C←L2": "I2C 0x53 · Z-C←L2",
    "obchádza celú vetvu": "bypasses the whole branch",
    "TUV špirála": "DHW heater",
    "Podlaha špirála": "Floor heater",
    "Čerpadlo TUV": "DHW pump",
    "◄ relé GPIO26": "◄ relay GPIO26",
    "Čerpadlo podlaha": "Floor pump",
    "◄ relé GPIO25": "◄ relay GPIO25",
    "N — spoločná zbernica (vedená cez RCD)": "N — common bus (through the RCD)",
    "RIADENIE — ESP32 DevKit  (TUV: nahrádza TechController ECO · podlaha: nová funkcia, Daikin OPTO)":
        "CONTROL — ESP32 DevKit  (DHW pump: replaces TechController ECO · floor pump: new, Daikin OPTO)",
    "DevKitC 38-pin · piny: esp32_pinout_zapojenie": "DevKitC 38-pin · pins: esp32_pinout_zapojenie",
    "DS18B20 B1 — TUV bojler": "DS18B20 B1 — DHW tank",
    "+3,3V": "+3.3V",
    "R1 4,7kΩ": "R1 4.7kΩ",
    "DS18B20 B2 — vratná voda TUV": "DS18B20 B2 — DHW return water",
    "R7 4,7kΩ": "R7 4.7kΩ",
    "DS18B20 B3 — voda podlaha": "DS18B20 B3 — floor water",
    "R8 4,7kΩ": "R8 4.7kΩ",
    "Prietok studenej → TUV (odber TÚV)": "Cold water flow → DHW (tap use)",
    "R6 4,7kΩ": "R6 4.7kΩ",
    "OPTO — Daikin žiada čerp. podlahy": "OPTO — Daikin wants floor pump",
    "OPTO — Daikin ohrev TUV (K3M)": "OPTO — Daikin DHW heating (K3M)",
    "DS18B20 × 3 — KAŽDÝ na vlastnom pine (klony nejdú po dvoch na zbernici)":
        "DS18B20 × 3 — EACH on its own pin (clones fail when two share a bus)",
    "Každý DATA vodič vlastný pull-up 4,7 kΩ na 3,3 V: R1 G21 · R7 G5 · R8 G13":
        "Each DATA wire has its own 4.7 kΩ pull-up to 3.3 V: R1 G21 · R7 G5 · R8 G13",
    "Každý DS18B20: červený VDD → 3,3 V · čierny → GND · žltý DATA → svoj GPIO":
        "Each DS18B20: red VDD → 3.3 V · black → GND · yellow DATA → its own GPIO",
    "I2C → DimmerLink1 (0x50) + DimmerLink2 (0x51)": "I2C → DimmerLink 0x54 + 0x53",
    "Relé → cievka stykača TUV (izolačný)": "Relay → DHW contactor coil (isolation)",
    "Relé → cievka BYPASS stykača TUV": "Relay → DHW BYPASS contactor coil",
    "Relé → cievka stykača podlaha (izolačný)": "Relay → floor contactor coil (isolation)",
    "Relé → cievka BYPASS stykača podlaha": "Relay → floor BYPASS contactor coil",
    "Relé → čerpadlo TUV": "Relay → DHW pump",
    "Relé → čerpadlo podlaha": "Relay → floor pump",
    "PWM priamo → pin 4 ventilátora (4-vodič.)": "PWM direct → fan pin 4 (4-wire)",
    "pull-up 4,7kΩ→3,3V POVINNÝ (1× SDA + 1× SCL, spoločné pre celú zbernicu)":
        "4.7kΩ pull-up→3.3V REQUIRED (1× SDA + 1× SCL, whole bus)",
    "2× 4,7kΩ": "2× 4.7kΩ",
    "2-kan. modul": "2-ch module",
    "L,N z B6  →  5V / GND do ESP32": "L,N from B6  →  5V / GND to ESP32",
    "Ventilátor skrine 5 V — 4-vodič. PWM": "Cabinet fan 5 V — 4-wire PWM",
    "chladenie dimmerov · floor 35% + dobeh 60s": "cools the dimmers · min 35% + 60 s run-on",
    "ZRUŠENÉ: relé cutoff VCC": "REMOVED: VCC cutoff relay",
    "nezapojené (GPIO13 = DS18B20 B3)": "not connected (GPIO13 = DS18B20 B3)",
    "Relé ZRUŠENÉ 2026-11-10 (PWM 0 % fan zastaví) — VCC priamo 5 V; GPIO13 teraz DS18B20 B3.":
        "Relay REMOVED (PWM 0 % stops fan) — VCC = 5 V; GPIO13 = B3.",
    "PWM na GPIO23, priamo do pinu 4 fanu. Tacho (pin3) → GPIO22 (vedľa PWM, od 2026-11-10).":
        "PWM GPIO23 → fan pin 4 directly. Tacho (pin3) → GPIO22.",
    "Farby vodičov (štandard, OVERIŤ multimetrom!)": "Wire colours (standard, CHECK with a multimeter!)",
    "pin1 GND — čierna": "pin1 GND — black",
    "pin2 VCC — žltá": "pin2 VCC — yellow",
    "pin3 Tacho — zelená": "pin3 Tacho — green",
    "pin4 PWM — modrá": "pin4 PWM — blue",
    "Intel/Noctua konvencia — iný výrobca môže mať iné farby,":
        "Intel/Noctua convention — other makers may use other colours,",
    "rozhoduje poloha pinu (zárez/šípka na konektore fanu), nie farba.":
        "the pin position (notch/arrow on the fan connector) decides, not the colour.",
    "Kľúčové poznámky": "Key notes",
    "• PI regulácia beží NA ESP32 — číta Shelly 3EM (súčet fáz!) priamo.":
        "• Regulation runs ON THE ESP32 — reads the Shelly 3EM (sum of phases!) directly, every 2 s.",
    "• EMI filter: LINE→sieť, LOAD→dimmer, kovové telo POVINNE na PE.":
        "• EMI filter: LINE→grid, LOAD→dimmer, metal case MUST be connected to PE.",
    "• Sériová tlmivka 200 µH/25 A LEN ak meranie (AM/DAB/WiFi/Zigbee) ukáže rušenie.":
        "• Series choke 200 µH/25 A ONLY if a measurement (AM/DAB/WiFi/Zigbee) shows interference.",
    "• 600 W filter: Schurter 5500.2623.01 (10A, máme) — montáž až po EMI meraní.":
        "• 600 W filter: Schurter 5500.2623.01 (10 A) — install only after an EMI measurement.",
    "• ⚠️ TOPOLÓGIA 2026-09-14: BYPASS je paralelne k CELEJ vetve (izolačný stykač":
        "• ⚠️ TOPOLOGY 2026-09-14: the BYPASS is parallel to the WHOLE branch (isolation contactor",
    "• + EMI filter + TRIAC/DimmerLink), NIE len k TRIAC-u. Dve nezávislé paralelné":
        "• + EMI filter + TRIAC/DimmerLink), NOT just to the TRIAC. Two independent parallel",
    "• cesty od ističa k špirále — bypass obchádza úplne všetko vrátane EMI filtra":
        "• paths from the breaker to the heater — the bypass skips everything incl. the EMI filter",
    "• (keď TRIAC nevedie, niet čo filtrovať). Stykače sa navzájom NIKDY neovplyvňujú.":
        "• (when the TRIAC does not conduct, there is nothing to filter). Contactors NEVER interact.",
    "• Izolačný stykač (TRIAC vetva) = mechanické odpojenie pri poruche TRIAC-u,":
        "• Isolation contactor (TRIAC branch) = mechanical disconnect if the TRIAC fails;",
    "• spína čisto DEŇ/NOC (SNTP + hodiny laditeľné z HA), NIE hysteréza na duty":
        "• closes only on a SUNNY DAY in the PV window (sunrise + 2 h … sunset − 2 h, first",
    "• (inak by sa spínal stovky-krát denne). Nezávislý od bypassu. Jediná výnimka:":
        "• surplus ≥ 100 W for 5 min) and stays closed until the window ends — no duty hysteresis.",
    "• manuálne vynútenie výkonu (nižšie) prebíja deň/noc, keď je aktívne.":
        "• Independent of the bypass. Only exception: manual power (below) overrides the window.",
    "• MANUÁLNE VYNÚTENIE výkonu (2026-09-14, laditeľné z HA, TUV aj podlaha":
        "• MANUAL POWER (adjustable from HA, DHW and floor separately, time limit default 5 h):",
    "• samostatne): 0=auto, 10-100%=vynúť túto hodnotu bez ohľadu na FVE prebytok":
        "• 0 = auto, 10–100 % = force this power regardless of the PV surplus",
    "• aj watchdog (napr. výpadok siete + generátor → nastav 100% → ide cez bypass).":
        "• and the watchdog (e.g. grid outage + generator → set 100 % → runs via the bypass).",
    "• Bypass stykač: FVE cesta má ZOP ≥97 % / ROZ ≤95 % (hysteréza + TRIAC-preload/":
        "• Bypass contactor: the PV path CLOSES at ≥97 % / OPENS at ≤95 % (hysteresis + TRIAC preload/",
    "• armed, aby TRIAC prevzal prúd predtým) — rieši časté prepínanie bez opotrebenia.":
        "• armed, so the TRIAC carries the current first) — no wear from frequent switching.",
    "• Daikin cesta (viď nižšie) je NEZÁVISLÁ od FVE hysterézy — priamo, bez preloadu.":
        "• The Daikin path (see below) is INDEPENDENT of the PV hysteresis — direct, no preload.",
    "• PODLAHA má IDENTICKÚ topológiu aj logiku ako TUV vyššie (bypass paralelne":
        "• The FLOOR has the IDENTICAL topology and logic as DHW above (bypass parallel",
    "• k celej vetve, izolačný stykač čisto deň/noc, FVE ZOP/ROZ hysteréza) — jediný":
        "• to the whole branch, isolation contactor by PV window, PV CLOSE/OPEN hysteresis) — the only",
    "• rozdiel je, že podlaha NEMÁ Daikin backup cestu (tá je výhradne pre TUV).":
        "• difference: the floor has NO Daikin backup path (that one is for DHW only).",
    "• ⚠️ TechController ECO ↔ Daikin/podlaha: NESÚVISIA. TechController = LEN čerpadlo":
        "• ⚠️ TechController ECO ↔ Daikin/floor: UNRELATED. TechController = ONLY the DHW",
    "• TUV (teplota/prietok). Podlaha+OPTO Daikin = NOVÁ funkcia, nie náhrada TechControlleru.":
        "• pump (temperature/flow). Floor + Daikin OPTO = NEW function, not a TechController replacement.",
    "• OPTO vstup z Daikinu izoluje jeho signál → čerpadlo beží aj keď Daikin OFF.":
        "• The OPTO input isolates the Daikin signal → the pump also runs when the Daikin is OFF.",
    "• Daikin ohrev TUV (GPIO14) = AC 230 V OPTO paralelne na cievku stykača K3M":
        "• Daikin DHW heating (GPIO14) = AC 230 V OPTO in parallel with the K3M contactor coil",
    "• (A1/A2, hydrobox EHBH08DA9W7) — NIE suchý kontakt (silové kontakty K3M pri":
        "• (A1/A2, hydrobox EHBH08DA9W7) — NOT a dry contact (the K3M power contacts are",
    "• 3,3 V nespoľahlivé). 2-kan. AC opto modul: K3M → GPIO14, čerpadlo podl. → GPIO27.":
        "• unreliable at 3.3 V). 2-ch AC opto module: K3M → GPIO14, floor pump → GPIO27.",
    "• Daikin GPIO14 ZAP → zopne LEN bypass stykač TUV, priamo, okamžite (bez FVE":
        "• Daikin GPIO14 ON → closes ONLY the DHW bypass contactor, directly, at once (no PV",
    "• hysterézy) — bez ohľadu na FVE prebytok aj watchdog. Izolačný stykač/EMI/TRIAC":
        "• hysteresis) — regardless of PV surplus and the watchdog. Isolation contactor/EMI/TRIAC",
    "• sa vôbec nedotýka, beží ďalej nezávisle podľa deň/noc. Limit: len max_t_tuv.":
        "• are not touched, they keep following the PV window. Only limit: max_t_tuv.",
    "• Čerpadlo TUV (2026-09-13/14, vzor TECH EU-11 Eco Circulation — nahrádzaný":
        "• DHW pump (modelled on TECH EU-11 Eco Circulation — the controller it replaces),",
    "• regulátor), 2 dôvody navyše k FVE/Daikin: ODBER — prietok A rozdiel bojler−":
        "• 2 reasons besides PV/Daikin: USE — flow AND tank − return",
    "• vratná > 5°C → beh na pevný čas (5 min). ÚDRŽBA — rozdiel > 3°C bez ohľadu":
        "• difference > 5 °C → runs for a fixed time (5 min). MAINTENANCE — difference > 3 °C regardless",
    "• na odber → beh KONTINUÁLNE kým rozdiel neklesne (udrží teplú vodu v systéme).":
        "• of use → runs CONTINUOUSLY until the difference drops (keeps hot water in the pipes).",
    "• Oba zdieľajú časové okno (deň/víkend, na minúty, laditeľné z HA).":
        "• Both share a time window (weekday/weekend, in minutes, adjustable from HA).",
    "• Pull-up: OPTO 27 + 14 = interný (pullup:true), debounce delayed_on/off 500 ms.":
        "• Pull-up: OPTO 27 + 14 = internal (pullup: true), debounce delayed_on/off 500 ms.",
    "• OPTO modul napájať z 3,3 V (nie 5 V); GPIO14 bez sériového rezistora (opto obmedzí prúd).":
        "• Power the OPTO module from 3.3 V (not 5 V); GPIO14 without a series resistor (the opto limits it).",
    "• TRIAC firing: DimmerLink modul (hardvérový Z-C/firing, I2C) — NIE natívny ac_dimmer.":
        "• TRIAC firing: DimmerLink module (hardware Z-C/firing, I2C) — NOT the native ac_dimmer.",
    "• 2× DimmerLink 1CH, vlastná fáza/adresa (0x50 TUV, 0x51 podlaha) — 2. kus nastaviť":
        "• 2× DimmerLink, own phase/address (0x54 DHW, 0x53 floor) — every new module is 0x50:",
    "• na 0x51 RAZ vopred (sám na zbernici), potom spojiť na spoločnú I2C.":
        "• connect it ALONE on the bus, change its address, then join the shared I2C.",
    "• Relé: 3× 2-kanál TUV(17+16), podlaha(19+18), čerpadlá(26+25), ALWAYS_OFF+inverted.":
        "• Relays: 3× 2-channel DHW (17+16), floor (19+18), pumps (26+25), ALWAYS_OFF + inverted.",
    "• Watchdog: Shelly/meranie nedostupné > 60 s → dimmery OKAMŽITE na 0 %, bypass":
        "• Watchdog: Shelly data older than 15 s → dimmers IMMEDIATELY at 0 %, the bypass",
    "• rozopne cez bežnú ROZ sekvenciu (TRIAC-preload, nie narovinu). Daikin cesta nezávislá.":
        "• opens via the normal OPEN sequence (TRIAC preload, not hard). Daikin path independent.",
    "• Ventilátor skrine: 4-vodičový PWM fan, rýchlosť rieši fan sám (GPIO23) — f(výkon dimmerov).":
        "• Cabinet fan: 4-wire PWM fan, it sets its own speed (GPIO23) — f(dimmer power).",
    "• Záložné relé VCC fanu ZRUŠENÉ (PWM 0 % fan zastaví) — GPIO13 použitý pre DS18B20 B3.":
        "• Backup VCC relay of the fan REMOVED (PWM 0 % stops the fan) — GPIO13 used for DS18B20 B3.",
    "• Tacho ventilátora (pin3) na GPIO22 (pulse_counter, ×0,5 pre 2 pulzy/otáčku) —":
        "• Fan tacho (pin3) on GPIO22 (pulse_counter, ×0.5 for 2 pulses/rev) —",
    "• presunuté 2026-11-10 z GPIO4 (vedľa PWM GPIO23); prietok TUV teraz na GPIO4.":
        "• moved 2026-11-10 from GPIO4 (next to PWM GPIO23); DHW flow is now on GPIO4.",
    "• Fyzicky GPIO2/15: rezistor → pin header; oba DimmerLink vodiče (skrútené) → svorka.":
        "• Physically on GPIO2/15: resistor → pin header; both DimmerLink wires (twisted) → terminal.",
    "Legenda": "Legend",
    "Silnoprúd / spínanie": "Power / switching",
    "Záťaž (špirály, čerpadlá)": "Load (heaters, pumps)",
    "Riadenie / ESP32": "Control / ESP32",
    "Senzory": "Sensors",
    "Suchý kontakt (bez opto)": "Dry contact (no opto)",
    "Ochrana (RCD)": "Protection (RCD)",
    "Napájanie / istenie": "Power supply / fusing",
    "ZÁLOHA (spare, nezapojené)": "SPARE (not connected)",
    "DimmerLink 2CH — náhradný diel": "DimmerLink 2CH — spare part",
    "Máme aj 1× DimmerLink 2CH (kúpený skôr,": "We also have 1× DimmerLink 2CH (bought earlier,",
    "PRED rozhodnutím o 2× 1CH vyššie).": "BEFORE deciding on the 2× 1CH above).",
    "NEPOUŽÍVA sa v zapojení — 1 zdieľaný Z-C": "NOT USED in the wiring — 1 shared Z-C",
    "pre oba kanály (predpokladá spoločnú fázu),": "for both channels (assumes a common phase),",
    "nehodí sa pre TUV/L1 + podlaha/L2 naraz.": "unsuitable for DHW/L1 + floor/L2 at once.",
    "Odložený ako náhradný diel — ak by jeden": "Kept as a spare part — if one",
    "z 2× DimmerLink 1CH zlyhal, dá sa dočasne": "of the 2× DimmerLink 1CH fails, it can be",
    "nasadiť (1 kanál, druhý ostane nevyužitý).": "used temporarily (1 channel, the other unused).",
    "DETAIL — vetva TUV: rbdimmer1 40A-CS ↔ DimmerLink1 ↔ ESP32":
        "DETAIL — DHW branch: rbdimmer1 40A-CS ↔ DimmerLink1 ↔ ESP32",
    "TUV 3 kW @ L1 · I2C adresa 0x50 · Z-C snímaný z L1": "DHW 3 kW @ L1 · I2C address 0x54 · Z-C sensed from L1",
    "Napájanie + I2C → DimmerLink:": "Power + I2C → DimmerLink:",
    "(pull-up 4,7kΩ→3,3V: 1× SDA + 1× SCL pre celú zbernicu)": "(4.7kΩ pull-ups→3.3V, one pair per bus)",
    "ADC priamo (obchádza DimmerLink):": "ADC directly (bypasses DimmerLink):",
    "(ADC1, attenuation 12dB — WiFi-safe)": "(ADC1, 12 dB attenuation — WiFi-safe)",
    "FAN riadenie priamo (bez MOSFETu):": "FAN control directly (no MOSFET):",
    "GPIO33 → FAN pin (on/off, nie PWM)": "GPIO33 → FAN pin (on/off, not PWM)",
    "(doska má vlastný tranzistor — pozri": "(the board has its own transistor — see",
    "poznámku dole, over pri oživení)": "the note below, verify at bring-up)",
    "I2C 0x50 · Z-C ← L1": "I2C 0x54 · Z-C ← L1",
    "4,7kΩ": "4.7kΩ",
    "(spoločné s": "(shared with",
    "druhou vetvou)": "the other branch)",
    "rbdimmer1 40A-CS — konektor k MCU": "rbdimmer1 40A-CS — MCU connector",
    "TEMP   → ESP32 GPIO36 priamo": "TEMP   → ESP32 GPIO36 directly",
    "CUR-S   → ESP32 GPIO39 priamo": "CUR-S   → ESP32 GPIO39 directly",
    "FAN   ← ESP32 GPIO33 priamo": "FAN   ← ESP32 GPIO33 directly",
    "5V   → vlastný fan (+), zdroj TODO": "5V   → own fan (+), supply TODO",
    "4 vodiče: VCC/GND/Z-C/DIM": "4 wires: VCC/GND/Z-C/DIM",
    "priamo, MIMO DimmerLinku!": "directly, NOT via DimmerLink!",
    "Vlastný fan chladiča": "Heatsink fan",
    "chladí TRIAC tuv vetvy": "cools the DHW branch TRIAC",
    "2-vodičový, spína ho ESP32:": "2-wire, switched by the ESP32:",
    "+ (červený) → 5V pin": "+ (red) → 5V pin",
    "− (čierny) → FAN pin (GPIO33)": "− (black) → FAN pin (GPIO33)",
    "⚠️ 2026-09-13 OPRAVA: doska FAN nerieši autonómne (zdroj:":
        "⚠️ 2026-09-13 FIX: the board does NOT run the fan by itself (source:",
    "GitHub robotdyn-dimmer/rbdimmerThermalESP32 API) — treba":
        "GitHub robotdyn-dimmer/rbdimmerThermalESP32 API) — the logic",
    "logiku z ESP32. Doska má vlastný tranzistor → MOSFET netreba,":
        "must come from the ESP32. The board has its own transistor → no MOSFET,",
    "len digitálny signál. Fan len on/off (2 vodiče, žiadny PWM vstup).":
        "just a digital signal. Fan on/off only (2 wires, no PWM input).",
    "DETAIL — vetva PODLAHA: rbdimmer2 40A-CS ↔ DimmerLink2 ↔ ESP32":
        "DETAIL — FLOOR branch: rbdimmer2 40A-CS ↔ DimmerLink2 ↔ ESP32",
    "podlaha 600 W @ L2 · I2C adresa 0x51 · Z-C snímaný z L2":
        "floor 600 W @ L2 · I2C address 0x53 · Z-C sensed from L2",
    "GPIO32 → FAN pin (on/off, nie PWM)": "GPIO32 → FAN pin (on/off, not PWM)",
    "I2C 0x51 · Z-C ← L2": "I2C 0x53 · Z-C ← L2",
    "rbdimmer2 40A-CS — konektor k MCU": "rbdimmer2 40A-CS — MCU connector",
    "TEMP   → ESP32 GPIO34 priamo": "TEMP   → ESP32 GPIO34 directly",
    "CUR-S   → ESP32 GPIO35 priamo": "CUR-S   → ESP32 GPIO35 directly",
    "FAN   ← ESP32 GPIO32 priamo": "FAN   ← ESP32 GPIO32 directly",
    "chladí TRIAC podlaha vetvy": "cools the floor branch TRIAC",
    "− (čierny) → FAN pin (GPIO32)": "− (black) → FAN pin (GPIO32)",
    "Skriňový ventilátor (GPIO23, sekcia vyššie) je výhradne pre CELÚ skrinku — nezávislý":
        "The cabinet fan (GPIO23, section above) is only for the WHOLE cabinet — independent",
    "od týchto dvoch fanov na jednotlivých doskách (tri nezávislé chladenia spolu). Oba typy":
        "of these two fans on the boards (three independent cooling systems). Both types",
    "idú teraz priamo z GPIO, bez MOSFETu — rozdiel je, že skriňový fan je 4-vodičový PWM":
        "now run directly from a GPIO, no MOSFET — the difference: the cabinet fan is 4-wire PWM",
    "(GPIO23 nesie 25kHz priamo do PWM pinu fanu, ten si rýchlosť rieši sám), kým fany na":
        "(GPIO23 sends 25 kHz straight to the fan's PWM pin, the fan sets its speed), while the",
    "doskách sú jednoduché 2-vodičové ZAP/VYP (doska má vlastný tranzistor, žiadna PWM).":
        "board fans are simple 2-wire ON/OFF (the board has its own transistor, no PWM).",
    "GPIO34/35/36/39 (TEMP/CUR-S vyššie) sú HW input-only (žiadny výstupný driver) — FAN":
        "GPIO34/35/36/39 (TEMP/CUR-S above) are input-only in hardware (no output driver) — the FAN",
    "preto musí na výstupovo schopný pin (GPIO33 TUV / GPIO32 podlaha).":
        "therefore needs an output-capable pin (GPIO33 DHW / GPIO32 floor).",
}

SK = re.compile(r"[áäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ]")


def main():
    svg = open(SRC, encoding="utf-8").read()
    missing = set()

    def sub(m):
        raw = html.unescape(m.group(2))
        key = raw.strip()
        if key in TR:
            new = raw.replace(key, TR[key])
        else:
            new = raw
            if SK.search(key):
                missing.add(key)
        return m.group(1) + html.escape(new, quote=False) + m.group(3)

    out = re.sub(r"(<text\b[^>]*>)(.*?)(</text>)", sub, svg, flags=re.S)
    out = out.replace('lang="sk"', 'lang="en"')
    with open(DST, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote", DST)
    if shutil.which("rsvg-convert"):
        png = DST[:-4] + ".png"
        subprocess.run(["rsvg-convert", "-o", png, DST], check=True)
        print("wrote", png)
    else:
        print("rsvg-convert not found — PNG must be rendered manually")
    if missing:
        print("UNTRANSLATED:", *sorted(missing), sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main()
