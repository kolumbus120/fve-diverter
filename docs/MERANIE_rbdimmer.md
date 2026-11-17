# Meranie rbdimmerov pred pripojením TEMP a CUR-S na ESP

> **Otázka výrobcovi (2026-11-14):** https://github.com/robotdyn-dimmer/rbdimmerESP32/issues/7
> (TEMP pull-up, CUR-S napätie/napájanie 3,3 vs 5 V, trimer, schéma). Kým neodpovie, platí meranie nižšie.

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
| 2. TEMP–GND odpor (kΩ), izbová teplota °C | ✅ 10,87 kΩ, ~23 °C (2026-11-13) | ✅ ~10,87 kΩ (2026-11-13, „to isté“) |
| 3. TEMP–GND napätie (V) | | |
| 4. CUR-S bez záťaže (V DC) | | |
| 5. CUR-S so záťažou (V DC / V AC) | | |

Hodnoty pošli Claudovi. Podľa nich upraví YAML (`ct_clamp`, kalibrácia
teploty) a schému (`schematics/esp32_schema_realny`: R4/R5, prípadne delič).

Až potom pripojiť: **TUV** TEMP → GPIO36, CUR-S → GPIO39 · **podlaha**
TEMP → GPIO34, CUR-S → GPIO35.

*Podrobnosti a zdroje: `TODO_fve_diverter.md`, sekcia „TEMP / CUR-S — ZMERAŤ“.*
