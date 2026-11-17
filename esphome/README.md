# ESP32 #2 — FVE diverter (ESPHome)

ESP32, ktorý riadi elektrické špirály z prebytku FVE.
Config: [`fve-diverter.yaml`](fve-diverter.yaml). Schéma: [`../docs/schematics/fve_schema.svg`](../docs/schematics/fve_schema.svg).

**Stav (2026-11-17):** ostrá verzia v prevádzke od 2026-11-15 (regulácia Shelly + Solax cloud,
okno FVE podľa východu/západu slnka, energia, čerpadlá). Celý popis: [`../README.sk.md`](../README.sk.md).

## GPIO mapa

Aktualizované **2026-11-10** — nové rozloženie podľa
[`../docs/schematics/esp32_pinout_zapojenie.png`](../docs/schematics/esp32_pinout_zapojenie.png)
(ESP32-DevKitC 38-pin, pin po pine s popisom zapojenia).

| GPIO | Funkcia | Pozn. |
|---|---|---|
| 36 (VP) | rbdimmer1 TUV — TEMP | ADC1, input-only |
| 39 (VN) | rbdimmer1 TUV — CUR-S | ADC1, input-only |
| 34 | rbdimmer2 podlaha — TEMP | ADC1, input-only |
| 35 | rbdimmer2 podlaha — CUR-S | ADC1, input-only |
| 32 | rbdimmer2 podlaha — FAN | výstup; 34·35·32 = 3 susedné piny (1 konektor) |
| 33 | rbdimmer1 TUV — FAN | výstup (34–39 sú input-only) |
| 25 | Relé → čerpadlo podlaha | active-LOW |
| 26 | Relé → čerpadlo TUV | active-LOW (25+26 = jeden 2-kan. modul) |
| 27 | OPTO — Daikin žiada čerpadlo podlahy | AC 230 V opto modul (kanál 2), interný pull-up, debounce 500 ms; modul napájať z **3,3 V** |
| 14 | OPTO — Daikin žiada ohrev TUV (cievka stykača **K3M** A1/A2 v hydroboxe) | AC 230 V opto modul (kanál 1), interný pull-up, debounce 500 ms; modul napájať z **3,3 V** (nie 5 V); bez sériového rezistora (opto obmedzí prúd aj pri štartovacom signáli GPIO14) |
| 13 | *(rezerva)* záložné relé VCC ventilátora skrine | **zrušené 2026-11-10** — PWM 0 % fan zastaví; pin rezervovaný pre prípad výmeny fanu (YAML blok zakomentovaný) |
| 23 | PWM → pin 4 ventilátora skrine (25 kHz) | 4-vodičový PWM fan |
| 22 | Tacho ← pin 3 ventilátora skrine | `pulse_counter`, interný pull-up (len 3,3 V), ×0,5 |
| 21 | DS18B20 OneWire (×3, voliteľne 4. v skrini) | externý pull-up **4,7 kΩ** |
| 19 | Relé → cievka stykača podlaha (izolačný) | active-LOW |
| 18 | Relé → cievka BYPASS stykača podlaha | active-LOW |
| 17 | Relé → cievka stykača TUV (izolačný) | active-LOW |
| 16 | Relé → cievka BYPASS stykača TUV | active-LOW |
| 4 | Prietok studenej → TUV (odber) | interný pull-up |
| 2 | I2C SDA — DimmerLink TUV (0x54) + DimmerLink podlaha (0x53), 0x50 voľná | **POVINNÝ externý pull-up 4,7 kΩ → 3,3 V** |
| 15 | I2C SCL — DimmerLink1 + DimmerLink2 | **POVINNÝ externý pull-up 4,7 kΩ → 3,3 V** |

Voľné: **GPIO5** (zatiaľ neotestovaný). **GPIO12 nepoužívať** — strapping pin
(MTDI): ak ho relé modul pri štarte ťahá HIGH, ESP zvolí 1,8 V flash a
nenaštartuje. 2026-11-10 relé čerpadla pri VYP slabo svietilo, lebo vodič bol
ešte podľa starého zapojenia na GPIO12 (YAML ho nepoužíva). GPIO0/1/3 a
6–11 (flash) nepoužívať.

## DimmerLink — presné zapojenie (overené oproti rbdimmer.com/docs, 2026-11-06)

Konektor na DimmerLinku smerom k ESP32 má 4 piny, dátové piny majú na doske
**dvojaký popis** (UART aj I2C pre ten istý fyzický pin — modul si protokol
prepína sám, netreba iné zapojenie pre I2C než pre UART):

| Pin na DimmerLinku | → ESP32 | Pozn. |
|---|---|---|
| VCC | 3,3V | |
| GND | GND | |
| **TX/SDA** | GPIO2 | I2C SDA |
| **RX/SCL** | GPIO15 | I2C SCL |

**Externý pull-up rezistor je POVINNÝ** — 4,7 kΩ na SDA aj na SCL smerom k
3,3V, **jeden spoločný set pre celú zbernicu** (obe DimmerLink dosky), nie
samostatne pre každú. Interné pull-upy ESP32 sú na I2C príliš slabé (platí
pre ESP32/ESP8266 podľa dokumentácie). Bez neho hrozí presne to, čo je
vidieť v logu pri nezapojených moduloch (`Communication failed!` pri I2C
scane). Odporúčané aj: káble pod 30 cm, 100 nF kondenzátor VCC-GND tesne pri
každom DimmerLinku.

**Fyzicky na ESP32 doštičke** (pasívny pin-header + skrutková svorkovnica na
rovnakom GPIO nete): na GPIO2 aj GPIO15 sa stretávajú 3 vodiče (2×
DimmerLink + 1× nožička rezistora) — pod jednu skrutku to rozumne nejde,
takže:
- **rezistor** (tuhá nožička) → zasúvací pin header
- **oba DimmerLink vodiče** (SDA spolu, SCL spolu) → skrutková svorkovnica,
  najprv skrútiť spolu (alebo dutinka/ferrule), nie len voľne vedľa seba
  pod jednou skrutkou

Výstupný konektor DimmerLink → rbdimmer doska je **samostatný pre každý
modul** (nezdieľa sa): VCC, GND, Z-C, Dim → rbdimmer piny Z-C a DIM/Gate.

**Adresy I2C (od 2026-11-16):** DimmerLink TUV **0x54**, podlaha **0x53** (pôvodne 0x50/0x51).
**0x50 je zámerne VOĽNÁ** — všetky moduly rbdimmer (DimmerLink, rbAmp) majú z výroby 0x50, nový
modul sa tak pripojí bez kolízie a adresa sa mu zmení priamo v skrini (DimmerLink: register 0x30,
zmena okamžitá, ukladá sa do EEPROM — tlačidlá „nový modul 0x50 → 0x54 / 0x53“ v testovacej
verzii; rbAmp: `new_address:`). Na 0x50 vždy len jeden nový modul naraz. Plán: rbAmp TUV 0x52,
podlaha 0x51; 0x57 nepoužívať (EEPROM, napr. modul hodín DS3231).

Presun 2026-11-16 (pri nulovom výkone): jednorazový kód v `on_boot` (priorita 800, pred
pripojením komponentu DimmerLink) zapísal 0x50→0x54 a 0x51→0x53, firmvér hneď bežal na nových
adresách; potom kód odstránený a po ďalšom reštarte sken zbernice = len 0x53 + 0x54.

## rbAmp — meranie výkonu do špirál (PLÁN 2026-11-16)

Zatiaľ nekúpené ani v YAML-e. Plán: 2× rbAmp UI1 (TUV 0x52, podlaha 0x51) + Shelly PM Mini
Gen3 na skriňu. DimmerLinky už sú na 0x54 / 0x53, 0x50 voľná (viď vyššie).
Detaily, postup, fázy a kliešte: [`../docs/rbAmp_meranie_vykonu.md`](../docs/rbAmp_meranie_vykonu.md).

## Prvé oživenie

1. `cp secrets.yaml.example secrets.yaml` a doplň heslá a v `fve-diverter.yaml` substitúcie `shelly_ip`, `latitude`, `longitude`.
2. **Prvý flash cez USB** (`esphome run fve-diverter.yaml`), potom už OTA.
3. **Zisti adresy DS18B20** z logu a doplň ich do `fve-diverter.yaml` (postup je v komentári v configu). Kábel každého senzoru oštítkuj.
4. Over polarity: `inverted:` na prietoku, opte a ZC hrany.
5. Doplň a otestuj **Shelly čítanie + PI slučku** (zakomentované bloky v configu).

## Testovacia (servisná) verzia — `fve-diverter-test.yaml` (2026-11-09)

Na oživenie HW **pred** ostrou verziou. Načíta celý `fve-diverter.yaml` (cez
`packages:`) a pridá servisné veci; nič nebeží automaticky, všetko sa ovláda
ručne z HA dashboardu `../home-assistant/dashboards/fve_diverter_test.yaml`.
Rovnaké meno zariadenia → rovnaká IP (<IP ESP>), OTA aj entity v HA.

- **Navyše oproti ostrej:** I2C scan (text senzor + tlačidlo), tlačidlo na zmenu
  adresy DimmerLinku 0x50 → 0x51 (len 1 modul na zbernici!), zoznam nájdených
  adries DS18B20, DimmerLink diagnostika (frekvencia, perióda, úroveň, FW,
  ready/chyba/kalibrácia, krivka LINEAR/RMS/LOG, reset/rekalibrácia), Shelly
  (<IP Shelly>) čítané priamo z ESP, ventilátor skrine ako PWM fan, WiFi/uptime/
  SNTP diagnostika, reštart.
- **Bezpečnosť:** auto-vypnutie stykačov/bypassov/dimmerov po 30 min (laditeľné,
  0 = nikdy), tepelná poistka TUV/podlaha (len pri platnom meraní).
- **Postup:** 1) bez záťaže — adresy DimmerLink + DS18B20, pomocné relé →
  správne veľké stykače; 2) až potom špirály (dimmer 100 % → bypass).
- **Flash:** `esphome run fve-diverter-test.yaml --device <IP ESP>` (v
  adresári s reálnym `secrets.yaml`). Overené 2026-11-09 `esphome compile`
  (ESPHome 2026.10.2): RAM 30,6 %, Flash 59,5 %.
- Po teste nahrať ostrú `fve-diverter.yaml` — testovacie entity v HA ostanú
  „unavailable“, dajú sa zmazať.

## Bezpečnostné zásady (zapracované)

- Relé `restore_mode: ALWAYS_OFF` + `inverted` → po boote/výpadku všetko VYP.
- Watchdog: Shelly/meranie nedostupné > 60 s → dimmery 0 %, stykače OFF.
- Štart na duty 0 (`grid_power` sa neukladá do flash).
- HW poistky mimo ESP: stykač pred dimmerom, RCD 4P typ A, tepelná poistka telies.
- EMI filtre: TUV/L1 (30A, istý) — Schaffner FN2030-30-08 / RS PRO 237-8717
  (skrutkový M4). Podlaha/L2 (10A, voliteľný — len ak EMI meranie po zapojení
  ukáže rušenie) — Schurter 5500.2623.01 (Design F, faston 6,3×0,8mm).
- Ventilátor skrine: **4-vodičový PWM fan** (GND/VCC/Tacho/PWM) — rýchlosť rieši
  fan sám podľa PWM na GPIO23, netreba MOSFET ani iný driver na napájaciu vetvu.
  Rýchlosť = f(výkon dimmerov) (`max(duty_tuv, duty_podlaha)`), floor 35 % + dobeh
  60 s. Záložné relé na VCC **zrušené** (test 2026-11-10: PWM 0 % fan zastaví); ak by
  nový fan pri 0 % nezastal → relé IN na GPIO13, odkomentovať blok `fan_power_cutoff`.

### Ventilátor skrine — farby vodičov

⚠️ **Toto je všeobecný PC/Noctua 4-pin PWM štandard (Intel spec), NIE overené
pre konkrétny kus, čo máme** — značka/model fanu nie je nikde v projekte
zaznamenaná. Pred zapojením **over multimetrom** (kontinuita pin↔vodič), až
potom spájkuj/skrutkuj natrvalo:

| Pin | Štandardná farba | Funkcia | Kam |
|---|---|---|---|
| 1 | čierna | GND | spoločná GND |
| 2 | žltá | VCC | 5V (Mean Well MDR-20-5) priamo (záložné relé zrušené) |
| 3 | zelená | Tacho | GPIO22 (pulse_counter) |
| 4 | modrá | PWM | GPIO23 (ledc, 25 kHz) |

Ak fan po pripojení nereaguje na PWM alebo tacho nič neráta, najpravdepodobnejšia
príčina je práve odlišné farebné značenie u iného výrobcu — over podľa
skutočného poradia pinov na konektore (pin 1 je zvyčajne označený na fanu
samotnom zárezom/šípkou), nie len podľa farby.
