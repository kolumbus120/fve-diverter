# Meranie rbdimmerov pred pripojením TEMP a CUR-S na ESP

> **Otázka výrobcovi (2026-11-14):** https://github.com/robotdyn-dimmer/rbdimmerESP32/issues/7
> (TEMP pull-up, CUR-S napätie/napájanie 3,3 vs 5 V, trimer, schéma). Kým neodpovie, platí meranie nižšie.
> Stav 2026-11-18: bez odpovede (0 komentárov).

> **Čip snímača identifikovaný (2026-11-18, nápis na náhradných moduloch):**
> `CC6920SO` / `ELC-50A` / `022308` = **CrossChip CC6920SO-50A** (Hall, SOP8).
> Datasheet rev2.5: https://cdn.icstop.com/upload/pdfs/1f/bf/1fbf80f94824e40bc43af1c7b92b249a.pdf
> - **5 V verzia** (VCC 4,5–5,5 V, abs. max 7 V). 3,3 V verzia by bola CC6920**B**SO (26,4 mV/A).
> - Nula = 0,5·VCC (2,5 V), **40 mV/A**, ±50 A, lineárny výstup 0,2–4,8 V → **môže ísť nad 3,3 V**.
> - Piny: 1–2 IP+, 3–4 IP−, 5 GND, 6 VZCR (referencia VCC/2), 7 OUT, 8 VCC. Výstup min. záťaž 1,5 kΩ.
> - „022308“ je asi dátum/šarža, „ELC-50A“ zrejme prevzaté z ACS712 značenia (datasheet nevysvetľuje).
> - TUV ~13 A ef. → špička 18,4 A → ±0,74 V okolo stredu.


**Prečo:** výrobca neuvádza, aké napätie je na pinoch TEMP a CUR-S. Ak by bolo
nad 3,3 V, ESP sa poškodí. Kým to nezmeriaš, **TEMP a CUR-S na ESP nepripájaj.**

**Treba:** multimeter. Merať len na nízkonapäťovej strane (konektor k MCU,
čipy), vždy proti **GND** dosky. Pri kroku 4 je na doske 230 V, silovej časti
sa nedotýkaj.

Urob to pre **obe dosky**: D1 (TUV) aj D2 (podlaha).

---

## Krok 1: Napätie prúdového snímača (najdôležitejšie)

Prúdový snímač je malý čip s 8 nožičkami (zoškrabaný nápis). Na jednej strane
idú 2 nožičky na AC IN a 2 do TRIAC-u, na druhej strane sú 4 nožičky do dosky.

- Dosku napájaj ako v prevádzke: **VCC 3,3 V** (z DimmerLinku) + **pin 5V**
  (z Mean Wellu). **230 V NEPRIPÁJAŤ.**
- Zmeraj napätie medzi **nožičkou 8 a nožičkou 5** snímača.
  - Nožička 1 má bodku. Nožička 8 je na druhej strane presne oproti nej.
    Nožička 5 je na tej istej strane ako 8, ale na opačnom konci.

| Výsledok | Čo to znamená |
|---|---|
| okolo **3,3 V** | OK, delič netreba |
| okolo **5 V** | pred ESP treba **delič** (navrhnem ho) |

## Krok 2: TEMP bez napájania

- Doska **odpojená** od všetkého.
- Zmeraj **odpor** medzi **TEMP a GND**.

| Výsledok | Čo to znamená |
|---|---|
| okolo **10 kΩ** (pri izbovej teplote) | holý teplomer, treba pridať rezistor 10 kΩ z TEMP na 3,3 V (R4/R5 v schéme) |
| iná hodnota | doska má vlastný delič, rezistor netreba |

> ✅ **Výsledok 2026-11-13:** 10,87 kΩ → holý teplomer, doska delič nemá.
> R4/R5 10 kΩ treba (už zakreslené v schéme). **Krok 3 netreba** (bez deliča
> na doske by bez R4/R5 nič neukázal).

## Krok 3: TEMP s napájaním (NETREBA — viď výsledok kroku 2)

- Napájanie ako v kroku 1 (bez 230 V), **ESP odpojené**.
- Zmeraj **napätie** medzi **TEMP a GND**.
- Okolo 1,6 V znamená, že doska má delič. Napätie **nesmie byť nad 3,3 V.**

## Krok 4: CUR-S bez záťaže

- Napájanie ako v kroku 1 (bez 230 V).
- Zmeraj **napätie** medzi **CUR-S a GND** (jednosmerný rozsah, DC).

| Výsledok | Čo to znamená |
|---|---|
| okolo **0 V** | jednosmerný výstup, bežné meranie |
| okolo **1,65 V** | snímač na 3,3 V, OK bez deliča |
| okolo **2,5 V** | snímač na 5 V, **treba delič** |

## Krok 5: CUR-S so záťažou (230 V!)

- Špirála zapojená, dimmer na 100 %, **bypass VYPNUTÝ** (prúd musí ísť cez dimmer).
- Zmeraj CUR-S proti GND: raz v **DC** rozsahu, raz v **AC** rozsahu.
- Zapíš obe hodnoty. Ak by DC išlo nad 3,0 V, skús trimrom
  „CURRENT SENSOR ADJUSTMENT“ znížiť a zapíš, čo trimer robí.

---

## Namerané hodnoty (sem dopíš)

| Meranie | D1 TUV | D2 podlaha |
|---|---|---|
| 1. snímač nožička 8–5 (V) | | |
| 1b. snímač nožička 7–5 = OUT pred trimrom (V) | | |
| 2. TEMP–GND odpor (kΩ), izbová teplota °C | ✅ 10,87 kΩ, ~23 °C (2026-11-13) | ✅ ~10,87 kΩ (2026-11-13, „to isté“) |
| 3. TEMP–GND napätie (V) | | |
| 4. CUR-S bez záťaže (V DC) | | |
| 5. CUR-S so záťažou (V DC / V AC) | | |

### Meranie 2026-11-18 (bez 230 V, doska pod nízkym napätím — **doska D1/D2 nezapísaná, doplniť**)

- **TEMP–GND = 1,79 V** → pod 3,3 V, OK. Zodpovedá NTC ~11,9 kΩ s pull-upom 10 kΩ na 3,3 V.
  ❓ Ak R4/R5 ešte **nie sú** osadené, má pull-up samotná doska → R4/R5 **nepridávať**.
- **CUR-S–GND = 1,83 V** → nesedí ani na 2,5 V (priamy 5 V výstup), ani na 1,65 V.
  Hypotéza: snímač na 5 V (OUT 2,5 V) a trimer „CURRENT SENSOR ADJUSTMENT“ funguje ako
  delič ~0,73. Potom TUV 13 A → CUR-S ~1,29–2,37 V (v presnom rozsahu ADC do ~2,45 V),
  nad 3,3 V až pri > ~30 A → **ďalší delič netreba, stačí sériový ~1 kΩ**. Trimrom nehýbať.
- **Ďalej:** zmerať nožičku 8–5 (čakám ~5 V) a 7–5 (čakám ~2,5 V) → potvrdí hypotézu;
  zmerať druhú dosku; zapísať, či sú R4/R5 osadené.
- Krok 5 (so záťažou) netreba cez nový switch: „TUV/Podlaha — manuálny výkon (0=auto)“ =
  **90 %** (nie 100 % — pri 100 % prevezme bypass a prúd snímačom nejde). Alebo vynechať
  a kalibrovať CUR-S z ESP oproti Shelly.

Hodnoty pošli Claudovi. Podľa nich upraví YAML (`ct_clamp`, kalibrácia
teploty) a schému (`schematics/esp32_schema_realny`: R4/R5, prípadne delič).

Až potom pripojiť: **TUV** TEMP → GPIO36, CUR-S → GPIO39 · **podlaha**
TEMP → GPIO34, CUR-S → GPIO35.

*Podrobnosti a zdroje: `TODO_fve_diverter.md`, sekcia „TEMP / CUR-S — ZMERAŤ“.*
