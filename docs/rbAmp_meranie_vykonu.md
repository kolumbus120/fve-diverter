# rbAmp — meranie skutočného výkonu do špirál (PLÁN, 2026-11-16)

**Stav:** zámer usera, **nekúpené, nezapojené, nie je v YAML-e**. Doska rev B (objednaná
2026-11-16) má pre rbAmp pripravené 2× I2C konektory J15/J18 (XH-5 s 5 V), viď `../pcb/README.md`.

**Prečo:** dnes výkon do TUV/podlahy len **odhadujeme** (úroveň dimmera × výkon špirály z
kalibrácie). Návrh č. 2 z porovnania s YaSolR (`porovnanie_yasolr_fve_diverter.md`): merať
skutočný výkon → presná energia, zistenie, že špirála neberie (vypol mechanický termostat
bojlera → prebytok presunúť inam), automatická kontrola výkonu špirál (teraz TUV 3003 W,
podlaha 595 W z kalibrácie 2026-11-16). CUR-S na rbdimmeri (R9/R11) by potom netreba.

## Rozhodnutie (2026-11-16, po diskusii s userom)

User chce merať 3 veci. Výsledok:

| Čo | Prúd | Čím merať | Adresa I2C |
|---|---|---|---|
| Špirála TUV (L1) | ~13 A | **rbAmp Basic UI1 + SCT-013-020** (napätie z L1) | **0x52** |
| Špirála podlaha (L2) | ~2,8 A | **rbAmp Basic UI1 + SCT-013-005** (napätie z L2) | **0x51** |
| Skriňa: ESP, ventilátory, čerpadlá (zdroj Mean Well + čerpadlá) | ~0,05–0,5 A | **Shelly PM Mini Gen3** na prívode skrine (Wi-Fi, nie I2C) | — |

### Prečo takto

- **2× UI1, nie 1× UI3:** UI1/UI2/UI3 majú **jeden vstup napätia** pre všetky kanály. TUV je na
  L1, podlaha na L2 → kanál na inej fáze by počítal výkon s napätím posunutým o 120° (nezmysel;
  prúd by bol správny). Každý UI1 má svoje napätie zo svojej fázy → výkon správne.
  - Núdzové riešenie s 1× UI3: výkon podlahy počítať z prúdu, P = I² · R (podlaha ≈ 89 Ω) —
    platí pre odporovú špirálu aj pri fázovom riadení. Pre skriňu (nie je odporová záťaž) nie.
- **Kliešte podľa pravidla výrobcu:** najmenšie kliešte, ktorých rozsah pokryje špičkový prúd
  s rezervou ~30 % (väčšie = slabší signál voči šumu → horšia presnosť, hlavne pri malom výkone
  dimmera).
  - TUV: 13 A × 1,3 ≈ 17–18 A → **SCT-013-020** (~4,6 kW). (Staršia poznámka „-020/-030“ →
    upresnené na 020.)
  - Podlaha: 2,8 A × 1,3 ≈ 3,6 A → **SCT-013-005** (~1,15 kW). Pri 10–30 % (0,3–0,9 A) dáva
    najlepšie rozlíšenie. 5 A kliešte trochu posúvajú fázu (odporová záťaž ukáže účinník
    ~0,985–0,993) → chyba výkonu ~1 %, nevadí.
  - **Len verzie s napäťovým výstupom 1 V.** SCT-013-000 (prúdový výstup) NEFUNGUJE. Kliešte sa
    zasúvajú priamo do jacku na rbAmp, adaptér netreba.
- **Skriňa nie cez kliešte:** SCT-013 majú šum ~0,15–0,2 A (≈ 35–45 W) → ESP + ventilátory (pár W)
  by zanikli, čerpadlá na hranici. Shelly meria presne aj malé výkony a ide samo do HA (ako 3EM).
  - **PM Mini Gen3 (len meria, bez relé, 16 A)** — nie 1PM: 1PM má relé v sérii, omylom vypnuté
    (aplikácia, automatizácia, aktualizácia) = vypne celú skriňu vrátane ESP → dimmery/stykače
    bez kontroly. 16 A, nie 8 A (1PM Mini): prístroj má zniesť aspoň to, čo pustí istič prívodu.
  - 1PM Gen3/Gen4 (16 A, s relé) len ak by user chcel skriňu na diaľku reštartovať.
  - Zapojiť **len na prívod elektroniky** (zdroj Mean Well, ventilátory, čerpadlá) — **nie** na
    silové vedenia k špirálam.
  - Otvorené: na ktorej fáze / ktorom ističi sú skriňa a čerpadlá.

### Zvážená alternatíva: rbAmp STD-U3I3 (3-fázový)

<https://www.rbdimmer.com/shop/power-metering-13/energy-meter-3-phases-std-u3i3-89> — 59,90 $ bez DPH.

- Napätie zvlášť L1/L2/L3 + N (každá fáza istená, max. 0,1 A), 3 prúdové kanály → správny výkon
  na ľubovoľnej fáze; uhly a poradie fáz; energia počítaná v module (prežije reštart ESP).
- 3 snímače 60 A alebo 100 A v balení, **kalibrované s modulom, nedajú sa vymeniť** za menšie.
- DIN lišta, galvanicky oddelený výstup. Komponent `rbamp-esphome` podporuje rad STD cez I2C.
- **Neoverené:** stránka U3I3 uvádza len Modbus RTU (UART TTL); pri STD-UI1 píšu „I²C alebo Modbus
  RTU (prepínač)“. Presnosť pri 1–3 A ani napájacie napätie neuvedené.
- **Prečo nie:** podlaha (2,8 A) a hlavne skriňa sú na 60 A snímači na spodku rozsahu.
  Prípadne neskôr na TUV + podlahu, ak výrobca potvrdí I2C a presnosť pri ~3 A.

## Modul rbAmp Basic UI1

- **rbAmp Basic AC Power Wattmeter for SCT-013** (rbdimmer.com, ten istý výrobca ako DimmerLink),
  kliešte zvlášť. <https://www.rbdimmer.com/shop/power-metering-13/basic-ac-power-wattmeter-module-for-sct-013-clamp-74>
  (cena v e-shope 2026-11-16 uvedená 3,99 $, skôr 13,99 $ — overiť pri objednávke).
- Varianty UI1 / UI2 / UI3 / UI5 / UI7 = 1/2/3/5/7 vstupov pre kliešte, **jeden vstup napätia**
  (L + N, skrutkové svorky, galvanicky oddelené). Viackanálový modul má **jednu I2C adresu**,
  kanály sú v ESPHome senzory `current`, `current_1`, `current_2`…
- Meria: U RMS, I RMS na kanál, činný/jalový výkon, PF, frekvenciu. 12-bit ADC, 5 kHz, true RMS
  z okien 200 ms. Presnosť modul ~0,5 % + kliešte 1–3 %.
- **I2C**, z výroby adresa **0x50** (všetky moduly rbdimmer, aj DimmerLink), voliteľný pin DataReady (netreba).
- **Napájanie 5 V** (vlastný 3,3 V regulátor, < 20 mA), logika I2C 3,3 V → priamo na ESP32.
- **Vlastné pull-upy 4,7 kΩ na SDA/SCL** (overené v dokumentácii 2026-11-16). S našimi R2/R3 a
  2× rbAmp: 3 páry paralelne ≈ 1,6 kΩ → ~2 mA, ešte v norme ESP32 (≤ 3 mA). Výrobca: pri 2
  moduloch nechať jeden pár, pri 3+ odstrániť všetky a dať jeden spoločný. → Pri oživovaní
  zvážiť odstrániť pull-upy na jednom rbAmp (alebo nechať a overiť, že zbernica beží).
- ESPHome komponent: <https://github.com/rb-amp/rbamp-esphome> (min. ESPHome 2025.3.0):
  ```yaml
  external_components:
    - source: {type: git, url: https://github.com/rb-amp/rbamp-esphome, ref: v1.9.1}
      components: [rbamp]
  ```
  `rbamp:` (`address`, `ct_model` / `ct_models` per kanál, `new_address` = zmena adresy),
  `sensor: platform: rbamp` (voltage, current, power, power_factor, energy…; `update_interval`
  min. 1 s). Výrobca: I2C 100 kHz → občasné NACK, odporúča 50 kHz = default ESPHome; naša
  zbernica nemá `frequency` nastavenú → už beží na 50 kHz, netreba meniť.
- **Zmena adresy** (`new_address:`) na firmvéri modulu v1.3+ funguje bez špeciálneho režimu
  (dvojfázový zápis, modul sa reštartuje). Modul musí byť na 0x50 **jediný**.

## Adresy I2C — 0x50 voľná (user 2026-11-16)

Nápad usera: všetky moduly rbdimmer (DimmerLink, rbAmp) majú z výroby 0x50. Keď je 0x50 na
zbernici vždy voľná, nový modul sa dá pripojiť bez kolízie (nič nenaruší) a adresu mu zmeniť
priamo v skrini, bez odpájania ostatných. Potom je 0x50 zase voľná pre ďalší.

| Adresa | Čo | Stav |
|---|---|---|
| 0x50 | **voľná** — „vstupná“ adresa pre nový modul rbdimmer | ✅ voľná od 2026-11-16 |
| 0x51 | rbAmp UI1 podlaha | plán (po kúpe) |
| 0x52 | rbAmp UI1 TUV | plán (po kúpe) |
| 0x53 | DimmerLink podlaha | ✅ presunuté z 0x51 (2026-11-16) |
| 0x54 | DimmerLink TUV | ✅ presunuté z 0x50 (2026-11-16) |

Poznámky:
- Výhoda platí len pre moduly rbdimmer. Bežné I2C veci majú iné adresy: SHT3x 0x44/0x45,
  BME280 0x76/0x77, DS2482 0x18–0x1B, OLED 0x3C.
- Rozsah 0x50–0x57 = pamäte EEPROM (napr. modul hodín DS3231 nesie EEPROM na **0x57**) →
  0x57 nepoužívať.
- Nový modul po pripojení nič nepokazí, ale funguje až po doplnení do YAML-u.
- **Presun DimmerLinkov urobený 2026-11-16** (pri nulovom výkone, dážď): jednorazový kód v
  `on_boot` zapísal register 0x30 (0x50→0x54, 0x51→0x53) ešte pred pripojením komponentu
  DimmerLink → firmvér hneď bežal na nových adresách. Overené: po ďalšom reštarte sken zbernice
  = len 0x53 + 0x54, oba moduly FW 1, 50 Hz. Detaily v `../esp32-fve-diverter/README.md`.

## ⚠️ Na čo dať pozor

1. **Adresa:** nový rbAmp má 0x50 (voľná) → pripojiť a `new_address:` zmeniť na 0x52 (TUV) /
   0x51 (podlaha). Vždy len jeden nový modul naraz.
2. **Na module je 230 V** (vstup napätia) → patrí do silovej časti skrine, nie na dosku
   divertera (tá je len 5 V / 3,3 V). Odbočku napätia istiť. Do dosky len 4-žilový kábel
   (GND, SDA, SCL, 5V) na J15 / J18.
3. Každý UI1 napätie **zo svojej fázy** (TUV L1, podlaha L2).

## Zapojenie na dosku rev B

J15 a J18 (JST-XH 5-pin, rovnaké): `3V3 GND SDA SCL 5V`. Pre rbAmp: GND, SDA, SCL, 5V
(3V3 nezapájať). Doska rev A (ak by sa vyrábala) má J15 len XH-4 bez 5 V → 5 V vtedy priamo
zo zdroja Mean Well MDR-20-5 (zdvojené výstupné svorky).

## Ďalšie kroky

- [x] Presunúť DimmerLinky na 0x54 / 0x53 (2026-11-16).
- [ ] Kúpiť 2× rbAmp Basic UI1 + SCT-013-020 (TUV) + SCT-013-005 (podlaha), verzie 1 V.
- [ ] Kúpiť Shelly PM Mini Gen3 na prívod skrine; zistiť fázu/istič skrine a čerpadiel.
- [ ] Nastaviť adresy rbAmp 0x52 (TUV) / 0x51 (podlaha) (`new_address:`, vždy len jeden nový na 0x50).
- [ ] Doplniť do `fve-diverter.yaml` (externý komponent + senzory), energiu do HA/Influxu.
- [ ] Porovnať s odhadom výkonu a kalibráciou (TUV 3003 W, podlaha 595 W).
- [ ] Využiť v regulácii: detekcia nečinnej špirály (výkon ≈ 0 pri úrovni > 0) → presun
      prebytku na druhú špirálu / do batérie.
- [ ] **Rozdeliť energiu do špirál na „zo slnka“ a „zo siete“** (user 2026-11-16) — z meraného
      výkonu rbAmp, nie z odhadu. Zo siete = aj ohrev na žiadosť Daikinu (K3M) a manuálny
      režim. Návrh: v každom kroku zo siete = min(výkon špirály, odber zo siete podľa Shelly,
      prípadne aj vybíjanie batérie zo Solaxu), zvyšok zo slnka. Dnes: manuálny ohrev sa
      započíta do „Energia do TUV/podlahy“ (FVE), ohrev cez Daikin K3M sa počíta zvlášť (odhad).
      **Čiastočne hotové 2026-11-16 (len K3M, len Shelly):** „Energia do TUV — K3M zo siete /
      zo slnka“ (dnes, celkom; týždeň/mesiac = UI helpery utility_meter). Zo siete = odber zo
      siete podľa Shelly (každé 2 s), najviac výkon špirály; výkon špirály stále odhad
      (menovitý). Batériu nevidíme → vybíjanie batérie do špirály padne do „zo slnka“.
      Po rbAmp: skutočný výkon, manuál a podlaha rovnako, prípadne „z batérie“ (dongl).
