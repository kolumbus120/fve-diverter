#!/usr/bin/env python3
# =============================================================================
# FVE diverter — základná doska (carrier board) pre ESP32 + 2× DimmerLink
# Generátor KiCad 9 projektu: schéma (.kicad_sch), doska (.kicad_pcb),
# vlastné symboly (fve.kicad_sym) a footprinty (fve.pretty/).
#
# Spustenie:  python3 gen_doska.py          (potom route.sh = autorouter)
# Výstup:     fve_doska/  (otvoriť fve_doska/fve_doska.kicad_pro v KiCade)
#
# Návrh 2026-11-15 (Claude + user). Rozmery ESP32 a DimmerLinku sú ZATIAĽ
# PREDPOKLAD — user ich zmeria, potom sa upraví ROZMERY nižšie a vygeneruje znova.
# Len nízke napätie (5 V / 3,3 V). 230 V na dosku NEPATRÍ.
# Zdroj zapojenia: ../docs/schematics/esp32_schema_realny.svg, ../esphome/fve-diverter.yaml
# =============================================================================
import json
import os
import uuid as _uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fve_doska")
PROJ = "fve_doska"

# ----------------------------------------------------------------------------
# ROZMERY (mm) — upraviť podľa merania usera
# ----------------------------------------------------------------------------
ESP_ROZTEC_RADOV = 25.4        # ESP32 DevKitC 38-pin: rozteč radov (user zmeral ~25,5 mm → 1" = 25,4)
ESP_PINOV_V_RADE = 19
DL_IN_PINOV = 4                # DimmerLink vstup: VCC GND SDA SCL
DL_OUT_PINOV = 5               # DimmerLink 2CH výstup: VCC GND ZC DIM0 DIM1 (PREDPOKLAD)
DL_ROZTEC_RADOV = 12.7         # vzdialenosť vstupnej a výstupnej lišty (user zmeral ~12,5 mm → 5 × 2,54)
DOSKA_W, DOSKA_H = 130.0, 80.0      # na šírku (user 2026-11-15: menšia kvôli cene), dištančné stĺpiky

# WAGO 2601-31xx: push-in, rozteč 3,5 mm, vodič ZHORA (kolmo na dosku), do 1,5 mm²
FP_WAGO = "TerminalBlock_WAGO:TerminalBlock_WAGO_2601-31{n:02d}_1x{n:02d}_P3.50mm_Vertical"
# JST-XH (zacvakávací so zámkom, sada usera: XH-2…XH-6) — snímače, opto, relé, rbdimmery
# (tenké káble). Na WAGO ostáva len napájanie 5V (J1).
FP_XH = "Connector_JST:JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical"
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_C = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FP_CP = "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
FP_JP = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_JP3 = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"
FP_FAN = "Connector:FanPinHeader_1x04_P2.54mm_Vertical"
FP_HOLE = "MountingHole:MountingHole_3.2mm_M3"
FP_ESP = "fve:ESP32_DevKitC_38_Socket"
FP_DL = "fve:DimmerLink_2CH_Socket"

# ----------------------------------------------------------------------------
# ESP32 DevKitC 38-pin — poradie pinov (anténa hore), ľavý rad 1–19, pravý 20–38
# ----------------------------------------------------------------------------
ESP_L = ["3V3", "EN", "IO36", "IO39", "IO34", "IO35", "IO32", "IO33", "IO25", "IO26",
         "IO27", "IO14", "IO12", "GND", "IO13", "SD2", "SD3", "CMD", "5V"]
ESP_R = ["GND", "IO23", "IO22", "TX0", "RX0", "IO21", "GND", "IO19", "IO18", "IO5",
         "IO17", "IO16", "IO4", "IO0", "IO2", "IO15", "SD1", "SD0", "CLK"]

# ESP pin → sieť
ESP_NET = {
    "3V3": "+3V3", "5V": "+5V", "GND": "GND",
    "IO36": "TEMP_TUV", "IO39": "CURS_TUV_D", "IO34": "TEMP_POD", "IO35": "CURS_POD_D",
    "IO32": "FAN_POD", "IO33": "FAN_TUV", "IO25": "REL_CERP_POD", "IO26": "REL_CERP_TUV",
    "IO27": "OPTO_CERP_POD", "IO14": "OPTO_K3M", "IO13": "OW_G13",
    "IO23": "FAN_PWM", "IO22": "FAN_TACHO", "IO21": "OW_BOJLER", "IO19": "REL_STYK_POD",
    "IO18": "REL_BYP_POD", "IO5": "OW_G5", "IO17": "REL_STYK_TUV", "IO16": "REL_BYP_TUV",
    "IO4": "PRIETOK", "IO2": "SDA", "IO15": "SCL",
}

# ----------------------------------------------------------------------------
# SÚČIASTKY: ref, symbol, hodnota, footprint, {pin: sieť}, popis
# ----------------------------------------------------------------------------
KRATKE = {"+5V": "5V", "+3V3": "3V3", "GND": "GND", "OW_BOJLER": "DQ", "OW_VRATNA": "DQ",
          "OW_PODLAHA": "DQ", "PRIETOK": "SIG", "OPTO_K3M": "K3M", "OPTO_CERP_POD": "ČERP",
          "REL_STYK_TUV": "IN1", "REL_BYP_TUV": "IN2", "REL_STYK_POD": "IN1", "REL_BYP_POD": "IN2",
          "REL_CERP_TUV": "TUV", "REL_CERP_POD": "POD", "OPTO_K3M": "K3M", "SDA": "SDA", "SCL": "SCL", "OW_J16": "DQ", "OW_J17": "DQ", "FAN_TACHO": "TACHO", "FAN_PWM": "PWM", "ZC_TUV": "ZC", "DIM_TUV": "DIM",
          "TEMP_TUV": "TEMP", "CURS_TUV": "CUR", "FAN_TUV": "FAN", "ZC_POD": "ZC", "DIM_POD": "DIM",
          "TEMP_POD": "TEMP", "CURS_POD": "CUR", "FAN_POD": "FAN"}


def term(ref, nets, popis, fp=FP_WAGO):
    n = len(nets)
    return dict(ref=ref, sym=f"term{n}", val=popis, fp=fp.format(n=n),
                pins={str(i + 1): net for i, net in enumerate(nets)},
                pinnames=[KRATKE.get(x, x) for x in nets], popis=popis)

C = []
C.append(dict(ref="U1", sym="esp", val="ESP32-DevKitC-38", fp=FP_ESP,
              pins={str(i + 1): ESP_NET.get(p, "") for i, p in enumerate(ESP_L + ESP_R)},
              popis="ESP32 DevKitC 38-pin (pätica 2× 1x19)"))
for ref, adr, sfx in (("U2", "0x50 TUV", "TUV"), ("U3", "0x51 podlaha", "POD")):
    C.append(dict(ref=ref, sym="dl", val=f"DimmerLink {adr}", fp=FP_DL,
                  pins={"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL",
                        "5": "+3V3", "6": "GND", "7": f"ZC_{sfx}", "8": f"DIM_{sfx}", "9": ""},
                  popis=f"DimmerLink 2CH {adr} (pätica)"))
# svorkovnice (poradie pinov = poradie na doske)
C.append(term("J1", ["+5V", "GND"], "NAPÁJANIE 5V (Mean Well)"))
C.append(term("J2", ["+3V3", "GND", "OW_BOJLER"], "DS18B20 B1 BOJLER", FP_XH))
C.append(term("J3", ["+3V3", "GND", "OW_VRATNA"], "DS18B20 B2 VRATNÁ", FP_XH))
C.append(term("J4", ["+3V3", "GND", "OW_PODLAHA"], "DS18B20 B3 PODLAHA", FP_XH))
C.append(term("J5", ["+3V3", "GND", "PRIETOK"], "PRIETOK TUV", FP_XH))
# opto Daikin + 5 V pre ESPAltherma (user 2026-11-15): napájanie na krajoch, signály v strede
C.append(term("J6", ["+5V", "GND", "OPTO_K3M", "OPTO_CERP_POD", "GND", "+3V3"], "OPTO DAIKIN + 5V ESPALTHERMA", FP_XH))
C.append(term("J7", ["GND", "REL_STYK_TUV", "REL_BYP_TUV", "+3V3", "+5V"], "RELÉ TUV", FP_XH))
C.append(term("J8", ["GND", "REL_STYK_POD", "REL_BYP_POD", "+3V3", "+5V"], "RELÉ PODLAHA", FP_XH))
C.append(term("J9", ["GND", "REL_CERP_TUV", "REL_CERP_POD", "+3V3", "+5V"], "RELÉ ČERPADLÁ", FP_XH))
# rbdimmery: 2× JST-XH 4-pin na dosku dimmera (riadenie z DimmerLinku + snímače/fan)
C.append(term("J10", ["+3V3", "GND", "ZC_TUV", "DIM_TUV"], "RBD TUV riadenie", FP_XH))
C.append(term("J11", ["TEMP_TUV", "CURS_TUV", "FAN_TUV", "+5V"], "RBD TUV snímače", FP_XH))
C.append(term("J13", ["+3V3", "GND", "ZC_POD", "DIM_POD"], "RBD POD riadenie", FP_XH))
C.append(term("J14", ["TEMP_POD", "CURS_POD", "FAN_POD", "+5V"], "RBD POD snímače", FP_XH))
# I2C rozšírenie (user 2026-11-15): napr. teplomer skrine (SHT/BME) alebo DS2482 pre ďalšie
# OneWire snímače — tá istá zbernica ako DimmerLinky (0x50/0x51), pull-upy R2/R3 už sú.
# rev B (user 2026-11-16): 2× XH-5 s 5 V pod sebou — napr. 2× rbAmp UI1 (napájanie 5 V,
# 3V3 nezapájať), alebo SHT/BME/DS2482 (3V3). Viď ../docs/rbAmp_meranie_vykonu.md.
C.append(term("J15", ["+3V3", "GND", "SDA", "SCL", "+5V"], "I2C (1)", FP_XH))
C.append(term("J18", ["+3V3", "GND", "SDA", "SCL", "+5V"], "I2C (2)", FP_XH))
# OneWire rozšírenie (user 2026-11-15): 2× ďalšie snímače na zbernici G21 (spolu s B1 bojler,
# pull-up R1). Pozor: nefunkčný klon na zbernici zablokuje aj B1 → FVE ohrev TUV sa zastaví.
# JP7/JP8: 1-2 = voľný pin G5 / G13 (keď sú B2/B3 cez JP5/JP6 na G21), 2-3 = zbernica G21.
# NIKDY JP5+JP7 (ani JP6+JP8) naraz v 1-2 — dva snímače na jednom pine.
C.append(term("J16", ["+3V3", "GND", "OW_J16"], "ONEWIRE (1) G5/G21", FP_XH))
C.append(term("J17", ["+3V3", "GND", "OW_J17"], "ONEWIRE (2) G13/G21", FP_XH))
C.append(dict(ref="JP7", sym="JP3", val="J16: 1-2 G5 | 2-3 G21", fp=FP_JP3,
              pins={"1": "OW_G5", "2": "OW_J16", "3": "OW_BOJLER"}, popis="OneWire (1): voľný G5 / zbernica G21"))
C.append(dict(ref="JP8", sym="JP3", val="J17: 1-2 G13 | 2-3 G21", fp=FP_JP3,
              pins={"1": "OW_G13", "2": "OW_J17", "3": "OW_BOJLER"}, popis="OneWire (2): voľný G13 / zbernica G21"))
# ventilátor skrine: JST-XH 4-pin ako rbdimmery (user 2026-11-15: pôvodný konektor fanu odstrihnutý)
C.append(term("J12", ["GND", "+5V", "FAN_TACHO", "FAN_PWM"], "FAN SKRINE", FP_XH))


def R(ref, val, a, b, popis):
    C.append(dict(ref=ref, sym="R", val=val, fp=FP_R, pins={"1": a, "2": b}, popis=popis))


R("R1", "4k7", "+3V3", "OW_BOJLER", "pull-up DS18B20 bojler")
R("R7", "4k7", "+3V3", "OW_G5", "pull-up DS18B20 vratná (vlastný pin G5)")
R("R8", "4k7", "+3V3", "OW_G13", "pull-up DS18B20 podlaha (vlastný pin G13)")
# OneWire prepínanie (user 2026-11-15, nové snímače): prepojka 1-2 = vlastný pin (G5 / G13),
# 2-3 = spoločná zbernica G21 s B1 (pull-up len R1). Pri zmene prepnúť aj firmvér!
C.append(dict(ref="JP5", sym="JP3", val="B2: 1-2 G5 | 2-3 G21", fp=FP_JP3,
              pins={"1": "OW_G5", "2": "OW_VRATNA", "3": "OW_BOJLER"}, popis="DS18B20 B2 vratná: vlastný pin / zbernica"))
C.append(dict(ref="JP6", sym="JP3", val="B3: 1-2 G13 | 2-3 G21", fp=FP_JP3,
              pins={"1": "OW_G13", "2": "OW_PODLAHA", "3": "OW_BOJLER"}, popis="DS18B20 B3 podlaha: vlastný pin / zbernica"))
R("R6", "4k7", "+3V3", "PRIETOK", "pull-up prietokomer")
R("R2", "4k7", "+3V3", "SDA", "pull-up I2C SDA")
R("R3", "4k7", "+3V3", "SCL", "pull-up I2C SCL")
R("R4", "10k", "+3V3", "TEMP_TUV", "TEMP TUV (NTC) → 3V3")
R("R5", "10k", "+3V3", "TEMP_POD", "TEMP podlaha (NTC) → 3V3")
# TEMP (NTC 10k proti GND na doske dimmera, overené 2026-11-13) ide priamo na ESP (G36/G34).
# CUR-S: delič R9 (horný) / R10 (dolný) — R9/R11 OSADIŤ AŽ PO ZMERANÍ napätia snímača
# (3,3 V → 0 Ω, R10/R12 neosadiť; 5 V → delič). Kým R9/R11 chýba, CUR-S je od ESP odpojený.
R("R9", "0R*", "CURS_TUV", "CURS_TUV_D", "CUR-S TUV → G39: osadiť až po zmeraní (0 Ω alebo horný delič)")
R("R10", "DNP", "CURS_TUV_D", "GND", "CUR-S TUV — dolný delič (len pri snímači na 5 V)")
R("R11", "0R*", "CURS_POD", "CURS_POD_D", "CUR-S podlaha → G35: osadiť až po zmeraní")
R("R12", "DNP", "CURS_POD_D", "GND", "CUR-S podlaha — dolný delič (len pri 5 V)")
C.append(dict(ref="C1", sym="CP", val="470u/10V", fp=FP_CP, pins={"1": "+5V", "2": "GND"}, popis="5V vstup"))
C.append(dict(ref="C2", sym="C", val="100n", fp=FP_C, pins={"1": "+5V", "2": "GND"}, popis="5V"))
C.append(dict(ref="C3", sym="C", val="100n", fp=FP_C, pins={"1": "+3V3", "2": "GND"}, popis="DimmerLink TUV VCC"))
C.append(dict(ref="C4", sym="C", val="100n", fp=FP_C, pins={"1": "+3V3", "2": "GND"}, popis="DimmerLink podlaha VCC"))
C.append(dict(ref="C5", sym="CP", val="47u/10V", fp="Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
              pins={"1": "+3V3", "2": "GND"}, popis="3V3 rezerva"))
for i in range(6):     # 4 rohy + stred dosky + stred dolnej strany
    C.append(dict(ref=f"H{i + 1}", sym="hole", val="M3", fp=FP_HOLE, pins={}, popis="diera pre dištančný stĺpik M3"))

NETS = sorted({n for c in C for n in c["pins"].values() if n})


def uid():
    return str(_uuid.uuid4())


# =============================================================================
# 1) FOOTPRINTY (vlastné): pätica ESP32 a DimmerLink
# =============================================================================
def fp_socket(name, rows, descr):
    """rows = [(x0, y0, dx, dy, n, first_pin)] — pady 1,7 mm, vŕtanie 1,0 mm"""
    o = [f'(footprint "{name}" (version 20241229) (generator "gen_doska") (layer "F.Cu")',
         f'  (descr "{descr}")', '  (attr through_hole)']
    pads = []
    for x0, y0, dx, dy, n, first in rows:
        for i in range(n):
            pads.append((first + i, x0 + dx * i, y0 + dy * i))
    xs = [p[1] for p in pads]
    ys = [p[2] for p in pads]
    x1, x2, y1, y2 = min(xs) - 1.6, max(xs) + 1.6, min(ys) - 1.6, max(ys) + 1.6
    o.append(f'  (property "Reference" "REF**" (at {x1} {y1 - 1.5} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)) (justify left)))')
    o.append(f'  (property "Value" "{name}" (at {x1} {y2 + 1.5} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15)) (justify left)))')
    for (a, b, c, d) in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)):
        o.append(f'  (fp_line (start {a:.3f} {b:.3f}) (end {c:.3f} {d:.3f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    for num, x, y in pads:
        shp = "rect" if num == 1 else "circle"
        o.append(f'  (pad "{num}" thru_hole {shp} (at {x:.3f} {y:.3f}) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))')
    return o, (x1, y1, x2, y2), pads


def write_footprints():
    d = os.path.join(OUT, "fve.pretty")
    os.makedirs(d, exist_ok=True)
    # ESP: ľavý rad x=0, pravý x=ROZTEC; pin 1 hore vľavo, 20 hore vpravo
    o, bb, _ = fp_socket("ESP32_DevKitC_38_Socket",
                         [(0, 0, 0, 2.54, ESP_PINOV_V_RADE, 1),
                          (ESP_ROZTEC_RADOV, 0, 0, 2.54, ESP_PINOV_V_RADE, 20)],
                         f"Pätica ESP32-DevKitC 38-pin, 2x 1x19 dutinková lišta 2.54, rozteč radov {ESP_ROZTEC_RADOV} mm (overiť meraním!)")
    x1, y1, x2, y2 = bb
    # obrys modulu (doska 28 x 55 mm, anténa hore ~7 mm nad 1. pinom) na F.SilkS + F.Fab
    mx1, mx2 = -1.25, ESP_ROZTEC_RADOV + 1.25
    my1, my2 = -7.5, (ESP_PINOV_V_RADE - 1) * 2.54 + 1.8
    for lay in ("F.SilkS", "F.Fab"):
        for (a, b, c, e) in ((mx1, my1, mx2, my1), (mx2, my1, mx2, my2), (mx2, my2, mx1, my2), (mx1, my2, mx1, my1)):
            o.append(f'  (fp_line (start {a:.3f} {b:.3f}) (end {c:.3f} {e:.3f}) (stroke (width 0.15) (type solid)) (layer "{lay}"))')
    o.append(f'  (fp_text user "ANTÉNA hore" (at {ESP_ROZTEC_RADOV / 2:.2f} -5 0) (layer "F.SilkS") (effects (font (size 1.2 1.2) (thickness 0.18))))')
    o.append(f'  (fp_text user "ESP32 DevKitC" (at {ESP_ROZTEC_RADOV / 2:.2f} 20 90) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))')
    for i, n in enumerate(ESP_L):
        o.append(f'  (fp_text user "{n}" (at 2.4 {i * 2.54:.2f} 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify left)))')
    for i, n in enumerate(ESP_R):
        o.append(f'  (fp_text user "{n}" (at {ESP_ROZTEC_RADOV - 2.4:.2f} {i * 2.54:.2f} 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify right)))')
    o.append(")")
    open(os.path.join(d, "ESP32_DevKitC_38_Socket.kicad_mod"), "w").write("\n".join(o) + "\n")
    # DimmerLink: vstup (1-4) vľavo zvislo, výstup (5-9) vpravo zvislo
    o, bb, _ = fp_socket("DimmerLink_2CH_Socket",
                         [(0, 0, 0, 2.54, DL_IN_PINOV, 1),
                          (DL_ROZTEC_RADOV, 0, 0, 2.54, DL_OUT_PINOV, 5)],
                         "Pätica DimmerLink 2CH: vstup VCC GND SDA SCL, výstup VCC GND ZC DIM0 DIM1 — rozmery a poradie PREDPOKLAD, overiť!")
    for i, n in enumerate(["VCC", "GND", "SDA", "SCL"]):
        o.insert(-1, f'  (fp_text user "{n}" (at 1.6 {i * 2.54:.2f} 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify left)))')
    for i, n in enumerate(["VCC", "GND", "ZC", "DIM0", "DIM1"]):
        o.insert(-1, f'  (fp_text user "{n}" (at {DL_ROZTEC_RADOV - 1.6:.2f} {i * 2.54:.2f} 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify right)))')
    o.append(")")
    open(os.path.join(d, "DimmerLink_2CH_Socket.kicad_mod"), "w").write("\n".join(o) + "\n")


# =============================================================================
# 2) SYMBOLY (vlastná knižnica fve.kicad_sym, vložená aj do schémy)
# =============================================================================
def _pin(num, name, x, y, ang, length=2.54, typ="passive"):
    return (f'(pin {typ} line (at {x:.2f} {y:.2f} {ang}) (length {length}) '
            f'(name "{name}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')


def sym_box(name, left, right, w=15.24, ref="U"):
    """left/right = [(num, name)], piny po 2,54. Vracia (sexpr, {num: (dx, dy, strana)})"""
    n = max(len(left), len(right))
    h = n * 2.54
    top = h / 2
    pins, pos = [], {}
    for i, (num, nm) in enumerate(left):
        y = top - 1.27 - i * 2.54
        pins.append(_pin(num, nm, -w / 2 - 2.54, y, 0))
        pos[num] = (-w / 2 - 2.54, y, "L")
    for i, (num, nm) in enumerate(right):
        y = top - 1.27 - i * 2.54
        pins.append(_pin(num, nm, w / 2 + 2.54, y, 180))
        pos[num] = (w / 2 + 2.54, y, "R")
    s = (f'(symbol "fve:{name}" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
         f'  (property "Reference" "{ref}" (at 0 {top + 2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
         f'  (property "Value" "{name}" (at 0 {-top - 2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
         f'  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
         f'  (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
         f'  (symbol "{name}_0_1" (rectangle (start {-w / 2:.2f} {top:.2f}) (end {w / 2:.2f} {-top:.2f}) '
         f'(stroke (width 0.254) (type default)) (fill (type background))))\n'
         f'  (symbol "{name}_1_1" ' + " ".join(pins) + "))")
    return s, pos


def sym_2pin(name, body, ref):
    """2-pinová súčiastka vodorovne: pin1 vľavo, pin2 vpravo"""
    pos = {"1": (-3.81, 0, "L"), "2": (3.81, 0, "R")}
    pins = [_pin("1", "~", -3.81, 0, 0, 1.27), _pin("2", "~", 3.81, 0, 180, 1.27)]
    s = (f'(symbol "fve:{name}" (pin_names (offset 0) hide) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
         f'  (property "Reference" "{ref}" (at 0 2.54 0) (effects (font (size 1.27 1.27))))\n'
         f'  (property "Value" "{name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))\n'
         f'  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
         f'  (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
         f'  (symbol "{name}_0_1" {body})\n'
         f'  (symbol "{name}_1_1" ' + " ".join(pins) + "))")
    return s, pos


SYMS = {}


def build_symbols():
    SYMS["esp"] = sym_box("ESP32_DevKitC_38", [(str(i + 1), n) for i, n in enumerate(ESP_L)],
                          [(str(i + 20), n) for i, n in enumerate(ESP_R)], w=20.32, ref="U")
    SYMS["dl"] = sym_box("DimmerLink_2CH", [("1", "VCC"), ("2", "GND"), ("3", "SDA"), ("4", "SCL")],
                         [("5", "VCC"), ("6", "GND"), ("7", "ZC"), ("8", "DIM0"), ("9", "DIM1")], w=12.7, ref="U")
    SYMS["JP3"] = sym_box("Prepojka_1x03", [("1", "1"), ("2", "2"), ("3", "3")], [], w=5.08, ref="JP")
    for n in (2, 3, 4, 5, 6, 8):
        SYMS[f"term{n}"] = sym_box(f"Svorka_1x{n:02d}", [(str(i + 1), str(i + 1)) for i in range(n)], [],
                                   w=5.08, ref="J")
    SYMS["fan"] = sym_box("Fan_4pin", [("1", "GND"), ("2", "+5V"), ("3", "TACHO"), ("4", "PWM")], [], w=7.62, ref="J")
    SYMS["R"] = sym_2pin("R", '(rectangle (start -2.54 1.016) (end 2.54 -1.016) (stroke (width 0.254) (type default)) (fill (type none)))', "R")
    SYMS["C"] = sym_2pin("C", '(polyline (pts (xy -0.508 1.524) (xy -0.508 -1.524)) (stroke (width 0.3) (type default)) (fill (type none))) '
                              '(polyline (pts (xy 0.508 1.524) (xy 0.508 -1.524)) (stroke (width 0.3) (type default)) (fill (type none))) '
                              '(polyline (pts (xy -2.54 0) (xy -0.508 0)) (stroke (width 0) (type default)) (fill (type none))) '
                              '(polyline (pts (xy 0.508 0) (xy 2.54 0)) (stroke (width 0) (type default)) (fill (type none)))', "C")
    SYMS["CP"] = sym_2pin("CP", '(rectangle (start -0.762 1.524) (end -0.254 -1.524) (stroke (width 0.254) (type default)) (fill (type none))) '
                                '(polyline (pts (xy 0.508 1.524) (xy 0.508 -1.524)) (stroke (width 0.3) (type default)) (fill (type none))) '
                                '(polyline (pts (xy -2.54 0) (xy -0.762 0)) (stroke (width 0) (type default)) (fill (type none))) '
                                '(polyline (pts (xy 0.508 0) (xy 2.54 0)) (stroke (width 0) (type default)) (fill (type none))) '
                                '(text "+" (at -1.778 1.27 0) (effects (font (size 1.27 1.27))))', "C")
    SYMS["JP"] = sym_2pin("Jumper", '(circle (center -1.016 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none))) '
                                    '(circle (center 1.016 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none))) '
                                    '(arc (start -1.016 1.016) (mid 0 1.524) (end 1.016 1.016) (stroke (width 0) (type default)) (fill (type none)))', "JP")
    SYMS["hole"] = ('(symbol "fve:MountingHole" (pin_names (offset 1.016)) (exclude_from_sim yes) (in_bom no) (on_board yes)\n'
                    '  (property "Reference" "H" (at 0 2.54 0) (effects (font (size 1.27 1.27))))\n'
                    '  (property "Value" "MountingHole" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))\n'
                    '  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                    '  (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                    '  (symbol "MountingHole_0_1" (circle (center 0 0) (radius 1.27) (stroke (width 0.254) (type default)) (fill (type none)))))', {})


def sym_name(key):
    s = SYMS[key][0]
    return s.split('"')[1]


# =============================================================================
# 3) SCHÉMA — symboly v mriežke, na každom pine menovka siete (label)
# =============================================================================
def write_schematic():
    sheet_uuid = uid()
    out = [f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid "{sheet_uuid}") (paper "A3")',
           '  (title_block (title "FVE diverter — základná doska ESP32 + DimmerLink") (date "2026-11-16") (rev "B — 2× I2C XH-5 s 5 V (rbAmp)")'
           ' (comment 1 "Len 5 V / 3,3 V. Rozmery ESP32 a DimmerLink overiť.")'
           ' (comment 2 "R9/R11 osadiť až po zmeraní CUR-S (0 Ω / delič), R10/R12 len pri 5 V."))',
           "  (lib_symbols"]
    used = []
    for c in C:
        if c["sym"] not in used:
            used.append(c["sym"])
    for k in used:
        out.append("    " + SYMS[k][0].replace("\n", "\n    "))
    out.append("  )")
    # rozloženie: stĺpce
    G = 2.54

    def snap(v):
        return round(v / G) * G

    place = {}
    x, y = 40.64, 40.64
    col_w = 76.2
    order = (["U1", "U2", "U3"] + [c["ref"] for c in C if c["ref"].startswith("J")]
             + [c["ref"] for c in C if c["ref"][0] in "RC" or c["ref"].startswith("JP")]
             + [c["ref"] for c in C if c["ref"].startswith("H")])
    seen = set()
    order = [r for r in order if not (r in seen or seen.add(r))]
    cols = [["U1"], ["U2", "U3", "J12"], [r for r in order if r.startswith("J") and r != "J12" and not r.startswith("JP")],
            [r for r in order if r[0] in "RC" or r.startswith("JP") or r.startswith("H")]]
    xs = [45.72, 116.84, 177.8, 287.02]
    for ci, col in enumerate(cols):
        yy = 38.1
        for r in col:
            c = next(c for c in C if c["ref"] == r)
            pos = SYMS[c["sym"]][1]
            ys = [p[1] for p in pos.values()] or [0]
            hgt = (max(ys) - min(ys)) if pos else 2.54
            yy += hgt / 2 + 7.62
            place[r] = (snap(xs[ci]), snap(yy))
            yy += hgt / 2 + 7.62
            if yy > 235:
                xs[ci] += 40.64
                yy = 38.1
    for c in C:
        X, Y = place[c["ref"]]
        su = uid()
        c["uuid"] = su
        props = [("Reference", c["ref"], 0, -1), ("Value", c["val"], 0, 1)]
        pos = SYMS[c["sym"]][1]
        ys = [p[1] for p in pos.values()] or [0]
        top = max(ys) + 3.81 if pos else 3.81
        bot = min(ys) - 3.81 if pos else -3.81
        s = [f'  (symbol (lib_id "{sym_name(c["sym"])}") (at {X:.2f} {Y:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom {"no" if c["sym"] == "hole" else "yes"}) (on_board yes) (dnp {"yes" if c["val"] == "DNP" else "no"}) (uuid "{su}")',
             f'    (property "Reference" "{c["ref"]}" (at {X:.2f} {Y - top:.2f} 0) (effects (font (size 1.27 1.27))))',
             f'    (property "Value" "{c["val"]}" (at {X:.2f} {Y - bot:.2f} 0) (effects (font (size 1.27 1.27))))',
             f'    (property "Footprint" "{c["fp"]}" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))',
             f'    (property "Datasheet" "" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))',
             f'    (property "Description" "{c["popis"]}" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))']
        if c["ref"].startswith("J") and not c["ref"].startswith("JP"):
            s.append(f'    (property "Popis" "{c["popis"]}" (at {X:.2f} {Y - top - 2.54:.2f} 0) (effects (font (size 1.27 1.27) (bold yes))))')
        for num in pos:
            s.append(f'    (pin "{num}" (uuid "{uid()}"))')
        s.append(f'    (instances (project "{PROJ}" (path "/{sheet_uuid}" (reference "{c["ref"]}") (unit 1))))')
        s.append("  )")
        out += s
        # menovky na pinoch (Y v symbole hore = mínus na hárku)
        for num, (dx, dy, side) in pos.items():
            net = c["pins"].get(num, "")
            px, py = X + dx, Y - dy
            if not net:
                out.append(f'  (no_connect (at {px:.2f} {py:.2f}) (uuid "{uid()}"))')
                continue
            ang, just = (180, "right") if side == "L" else (0, "left")
            out.append(f'  (label "{net}" (at {px:.2f} {py:.2f} {ang}) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{uid()}"))')
    out.append(f'  (sheet_instances (path "/" (page "1")))')
    out.append(")")
    open(os.path.join(OUT, f"{PROJ}.kicad_sch"), "w").write("\n".join(out) + "\n")
    return sheet_uuid


def write_symlib():
    o = ['(kicad_symbol_lib (version 20241209) (generator "gen_doska") (generator_version "9.0")']
    for k, (s, _) in SYMS.items():
        o.append("  " + s.replace("fve:", "", 1).replace("\n", "\n  "))
    o.append(")")
    open(os.path.join(OUT, "fve.kicad_sym"), "w").write("\n".join(o) + "\n")
    open(os.path.join(OUT, "sym-lib-table"), "w").write(
        '(sym_lib_table (version 7)\n  (lib (name "fve")(type "KiCad")(uri "${KIPRJMOD}/fve.kicad_sym")(options "")(descr "FVE diverter doska"))\n)\n')
    open(os.path.join(OUT, "fp-lib-table"), "w").write(
        '(fp_lib_table (version 7)\n  (lib (name "fve")(type "KiCad")(uri "${KIPRJMOD}/fve.pretty")(options "")(descr "FVE diverter doska"))\n)\n')


def write_project():
    pro = {
        "board": {"design_settings": {"defaults": {"board_outline_line_width": 0.1},
                                       "rules": {"min_clearance": 0.2, "min_track_width": 0.25,
                                                 "min_via_diameter": 0.6, "min_through_hole_diameter": 0.3}}},
        "meta": {"filename": f"{PROJ}.kicad_pro", "version": 3},
        "net_settings": {
            "classes": [
                {"name": "Default", "clearance": 0.25, "track_width": 0.4, "via_diameter": 0.8, "via_drill": 0.4,
                 "wire_width": 6, "bus_width": 12, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "diff_pair_via_gap": 0.25, "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647},
                {"name": "Napajanie", "clearance": 0.3, "track_width": 1.0, "via_diameter": 1.0, "via_drill": 0.5,
                 "wire_width": 6, "bus_width": 12, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "diff_pair_via_gap": 0.25, "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 0}],
            "meta": {"version": 4},
            "netclass_patterns": [{"netclass": "Napajanie", "pattern": "+5V"},
                                  {"netclass": "Napajanie", "pattern": "+3V3"},
                                  {"netclass": "Napajanie", "pattern": "GND"}]},
        "sheets": [], "text_variables": {},
    }
    open(os.path.join(OUT, f"{PROJ}.kicad_pro"), "w").write(json.dumps(pro, indent=2))


# =============================================================================
# 4) DOSKA — rozmiestnenie (pcbnew API)
# =============================================================================
# (x, y, rotácia): x, y = ĽAVÝ HORNÝ ROH obalu (courtyard) súčiastky po otočení,
# v mm od ľavého horného rohu dosky. Svorky WAGO 2601-31xx = vodič zhora → otočenie
# len kvôli poradiu pinov (rot 0: pin 1 vľavo; rot 90: pin 1 dole).
PLACE = {
    # HORE zľava: napájanie 5V (WAGO), ventilátor skrine, rbdimmer TUV (2× XH-4), rbdimmer podlaha
    "J1": (9, 1.5, 0), "J12": (36, 2, 0),
    "J10": (58, 2, 0), "J11": (73, 2, 0), "J13": (90, 2, 0), "J14": (105, 2, 0),
    # pod nimi bloky DimmerLink + TEMP pull-up + delič CUR-S
    "U2": (58, 14, 0), "R4": (75, 14, 90), "R9": (78.5, 14, 90), "R10": (82, 14, 90), "C3": (85.5, 14, 90),
    "U3": (90, 14, 0), "R5": (107, 14, 90), "R11": (110.5, 14, 90), "R12": (114, 14, 90), "C4": (117.5, 14, 90),
    # VPRAVO v strede: relé moduly v jednom rade za sebou (XH-5, pin 1 vľavo)
    "J7": (76, 58, 0), "J8": (93, 58, 0), "J9": (110, 58, 0),   # user 2026-11-16: o 1 mm dole
    # I2C rozšírenie + 2× OneWire (G21) nad relé
    "J15": (76, 30, 0), "J18": (76, 42, 0), "J16": (95, 32.5, 0), "J17": (112, 32.5, 0),   # user 2026-11-16: posuny
    "JP7": (94, 43.5, 90), "JP8": (112, 43.5, 90),
    # DOLE: teplomery, prietok, opto (XH)
    "J2": (10, 71.6, 0), "J3": (25, 71.6, 0), "J4": (40, 71.6, 0), "J5": (55, 71.6, 0), "J6": (95, 71.6, 0),
    # pull-upy a prepojky OneWire nad spodnými konektormi
    "R1": (13, 55, 90), "R7": (28, 55, 90), "R8": (43, 55, 90), "R6": (61, 55, 90),
    "JP5": (32, 58, 0), "JP6": (47, 58, 0),
    # ESP32 naležato vľavo v strede, anténa k ľavému okraju (pod anténou bez medi)
    "U1": (6.9, 21.2, 90),
    # I2C pull-upy, 3V3 kondenzátor
    "R2": (60, 30, 0), "R3": (60, 34, 0), "C5": (61, 40.5, 0),
    # 5V vstup
    "C1": (21, 8.5, 0), "C2": (31, 8.5, 90),
    # diery M3 (obal 7 × 7 mm): rohy + medzi ESP a relé + stred dolnej strany
    "H1": (0.5, 0.5, 0), "H2": (DOSKA_W - 7.5, 0.5, 0), "H3": (0.5, DOSKA_H - 7.5, 0),
    "H4": (DOSKA_W - 7.5, DOSKA_H - 7.5, 0), "H5": (64, 46.5, 0), "H6": (80, DOSKA_H - 7.5, 0),
}


def write_pcb(sheet_uuid):
    import pcbnew
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(2)
    OX, OY = 100.0, 50.0       # posun dosky na hárku
    mm = pcbnew.FromMM

    def P(x, y):
        return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))

    # obrys
    pts = [(0, 0), (DOSKA_W, 0), (DOSKA_W, DOSKA_H), (0, DOSKA_H)]
    for i in range(4):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*pts[i]))
        s.SetEnd(P(*pts[(i + 1) % 4]))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        b.Add(s)
    # siete
    netobj = {}
    for n in NETS:
        ni = pcbnew.NETINFO_ITEM(b, n)
        b.Add(ni)
        netobj[n] = ni
    libroot = "/usr/share/kicad/footprints"
    for c in C:
        lib, name = c["fp"].split(":")
        path = os.path.join(OUT, "fve.pretty") if lib == "fve" else os.path.join(libroot, lib + ".pretty")
        fp = pcbnew.FootprintLoad(path, name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(c["ref"])
        fp.SetValue(c["val"])
        fp.SetPath(pcbnew.KIID_PATH(f"/{sheet_uuid}/{c['uuid']}") if False else pcbnew.KIID_PATH(f"/{c['uuid']}"))
        fp.SetSheetname("Root")
        fp.SetSheetfile(f"{PROJ}.kicad_sch")
        x, y, rot = PLACE[c["ref"]]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(0, 0))
        fp.BuildCourtyardCaches()
        cb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if cb.GetWidth() == 0:
            cb = fp.GetBoundingBox(False)
        fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x) - cb.GetLeft() + fp.GetPosition().x,
                                       mm(OY + y) - cb.GetTop() + fp.GetPosition().y))
        if c["val"] == "DNP":
            fp.SetDNP(True)
        if c["ref"].startswith("J") and not c["ref"].startswith("JP") and True:
            fp.Reference().SetVisible(False)     # názov svorky je v popise pod/nad ňou
        for pad in fp.Pads():
            net = c["pins"].get(pad.GetNumber(), "")
            if net:
                pad.SetNet(netobj[net])
        b.Add(fp)
        # popis svorky na sieťotlač: názov + názvy pinov v poradí
        if c["ref"].startswith("J") and not c["ref"].startswith("JP") and True:
            fp.BuildCourtyardCaches()
            bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
            nazov = c["popis"].replace("DS18B20 ", "").replace(" (Mean Well)", "")
            piny = " ".join(c["pinnames"])
            for i, txt in enumerate((nazov, piny)):
                t = pcbnew.PCB_TEXT(b)
                t.SetText(txt)
                t.SetLayer(pcbnew.F_SilkS)
                t.SetTextSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
                t.SetTextThickness(mm(0.13))
                # J18 (rev B) je tesne pod polovicou dosky, ale patrí k J15 → popis tiež pod ním
                if rot == 0 and (y < DOSKA_H / 2 or c["ref"] == "J18"):   # horný rad: pod svorkou
                    t.SetPosition(pcbnew.VECTOR2I(bb.Centre().x, bb.GetBottom() + mm(0.9 + i * 1.2)))
                elif rot == 0:                           # spodný rad: nad svorkou
                    t.SetPosition(pcbnew.VECTOR2I(bb.Centre().x, bb.GetTop() - mm(2.1 - i * 1.2)))
                    if "XH" in c["fp"]:
                        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
                elif x > DOSKA_W / 2:                    # pravý okraj: vľavo od konektora, zvislo
                    t.SetTextAngleDegrees(90)
                    t.SetPosition(pcbnew.VECTOR2I(bb.GetLeft() - mm(2.1 - i * 1.2), bb.Centre().y))
                else:                                    # ľavý okraj: vpravo od svorky, zvislo
                    t.SetTextAngleDegrees(90)
                    t.SetPosition(pcbnew.VECTOR2I(bb.GetRight() + mm(0.9 + i * 1.2), bb.Centre().y))
                b.Add(t)
    # označenia súčiastok v blokoch DimmerLink: vodorovne POD spodnú pájaciu dieru
    # (aby boli vidno aj po osadení — user 2026-11-15)
    for ref in ("R4", "R9", "R10", "C3", "R5", "R11", "R12", "C4", "R3"):
        f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
        pads = list(f.Pads())
        px = sum(pd.GetPosition().x for pd in pads) // len(pads)
        py = max(pd.GetPosition().y for pd in pads)
        r = f.Reference()
        r.SetTextAngleDegrees(0)
        r.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        r.SetTextThickness(mm(0.12))
        vodorovna = len({pd.GetPosition().y for pd in pads}) == 1      # ležiaca súčiastka
        r.SetPosition(pcbnew.VECTOR2I(px, py + mm(2.4 if vodorovna else 1.6)))
    # popis prepojok OneWire
    for ref, txt in (("JP5", "1-2 G5\n2-3 G21"), ("JP6", "1-2 G13\n2-3 G21"),
                     ("JP7", "1-2 G5\n2-3 G21"), ("JP8", "1-2 G13\n2-3 G21")):
        f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
        f.BuildCourtyardCaches()
        fb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
        t = pcbnew.PCB_TEXT(b)
        t.SetText(txt)
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        t.SetTextThickness(mm(0.12))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetPosition(pcbnew.VECTOR2I(fb.GetRight() + mm(0.5), fb.Centre().y))
        b.Add(t)
    # pravidlo prepojok
    t = pcbnew.PCB_TEXT(b)
    t.SetText("JP5+JP7 / JP6+JP8 nie naraz 1-2!")
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    t.SetTextThickness(mm(0.12))
    t.SetPosition(P(108, 49.8))
    b.Add(t)
    # zóny GND na oboch vrstvách
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(b)
        z.SetLayer(lay)
        z.SetNet(netobj["GND"])
        z.SetLocalClearance(mm(0.4))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in ((0.5, 0.5), (DOSKA_W - 0.5, 0.5), (DOSKA_W - 0.5, DOSKA_H - 0.5), (0.5, DOSKA_H - 0.5)):
            ol.Append(mm(OX + x), mm(OY + y))
        b.Add(z)
    # zakázaná oblasť pod anténou ESP32 (žiadna meď) — od ľavého okraja po 1. rad pinov
    u1 = next(f for f in b.GetFootprints() if f.GetReference() == "U1")
    u1.BuildCourtyardCaches()
    ub = u1.GetCourtyard(pcbnew.F_CrtYd).BBox()
    ka = pcbnew.ZONE(b)
    ka.SetIsRuleArea(True)
    ka.SetDoNotAllowTracks(True)
    ka.SetDoNotAllowVias(True)
    ka.SetDoNotAllowCopperPour(True)
    ka.SetDoNotAllowPads(False)
    ka.SetDoNotAllowFootprints(False)
    ka.SetLayerSet(pcbnew.LSET.AllCuMask())
    ol = ka.Outline()
    ol.NewOutline()
    for (x, y) in ((mm(OX + 0.5), ub.GetTop()), (ub.GetLeft(), ub.GetTop()),
                   (ub.GetLeft(), ub.GetBottom()), (mm(OX + 0.5), ub.GetBottom())):
        ol.Append(int(x), int(y))
    ka.SetZoneName("antena_ESP32")
    b.Add(ka)
    # nadpis
    t = pcbnew.PCB_TEXT(b)
    t.SetText("FVE diverter — doska ESP32 + DimmerLink  rev B 2026-11  (5V/3V3, NIE 230V)")
    t.SetLayer(pcbnew.B_SilkS)
    t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
    t.SetTextThickness(mm(0.2))
    t.SetPosition(P(DOSKA_W / 2, DOSKA_H / 2))
    b.Add(t)
    path = os.path.join(OUT, f"{PROJ}.kicad_pcb")
    b.Save(path)
    return path


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write_footprints()
    build_symbols()
    write_symlib()
    write_project()
    sh = write_schematic()
    p = write_pcb(sh)
    print("OK:", OUT)
    print("súčiastky:", len(C), "siete:", len(NETS))
