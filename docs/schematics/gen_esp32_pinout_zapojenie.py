#!/usr/bin/env python3
# Pinout ESP32-DevKitC (podklad = oficiálny obrázok Espressif
# esp32-devkitC-v4-pinout.png, orezaný len na dosku + prvé popisky pinov
# 3V3/EN/GPIOxx) + vedľa každého pinu čo sa naň v FVE diverteri zapája.
# Výstup: esp32_pinout_zapojenie.svg (+ .png cez rsvg-convert).
#
# 2026-11-10: prvá verzia — NÁVRH nového rozloženia (rbdimmer1 TUV
#   TEMP/CUR-S/FAN = 36/39/33, rbdimmer2 podlaha = 34/35/32; čerpadlo
#   podlaha zatiaľ nepriradené). Stĺpec "NOVÉ" = zmena oproti fve-diverter.yaml
# 2026-11-10 (2): dohodnuté s userom — čerpadlá 25 podlaha / 26 TUV, Daikin
#   vstupy 27 opto podlaha / 14 ohrev TUV, záložné relé fanu → 13 (voliteľné),
#   4. DS18B20 v skrini voliteľne. Výmena 22↔4: tacho fanu skrine 22 (vedľa
#   PWM 23), prietok studenej → TUV na 4.
#   k tomuto dňu.
# 2026-11-15: DS18B20 každý vlastný pin (G21+R1, G5+R7, G13+R8), prietok R6. YAML sa mení až po prejdení zapojenia s userom.
import base64, os, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "esp32-devkitC-v4-pinout.png")

# Orez pôvodného obrázka (súradnice v pixeloch 1600×1091) — overené zoomom:
# zelené GPIO štítky vľavo začínajú x≈541 (modré RTC končí ≈540), vpravo
# GPIO štítky končia x≈1058 (ďalší štítok začína ≈1060).
CX0, CX1, CY0, CY1 = 541, 1058, 176, 786
ROW0, STEP = 264.0, 27.8       # stred 1. riadku pinov a rozstup (obe strany)

LEFT_W = 560                  # šírka ľavého stĺpca popisov
OX = LEFT_W + 20 - CX0        # posun obrázka na plátne (x)
OY = 150 - CY0                # posun obrázka na plátne (y)
W = LEFT_W + 20 + (CX1 - CX0) + 20 + LEFT_W
H = 1082

C = {  # kategória: (výplň, obrys, text)
    "rele":   ("#ffe0b2", "#e65100", "#3e2723"),
    "rbd1":   ("#e1bee7", "#6a1b9a", "#311b92"),
    "rbd2":   ("#c5cae9", "#283593", "#1a237e"),
    "vstup":  ("#c8e6c9", "#2e7d32", "#1b5e20"),
    "i2c":    ("#bbdefb", "#1565c0", "#0d47a1"),
    "fan":    ("#b2ebf2", "#00838f", "#004d40"),
    "nap":    ("#ffcdd2", "#c62828", "#b71c1c"),
    "gnd":    ("#e0e0e0", "#212121", "#212121"),
    "nie":    ("#f5f5f5", "#9e9e9e", "#757575"),
    "volny":  ("#ffffff", "#9e9e9e", "#616161"),
}

# (riadok, kategória, text, nové?)
LEFT = [
    (0,  "nap",  "3,3 V → VCC relé modulov (opto), DimmerLink, pull-upy", False),
    (1,  "nie",  "EN = reset (tlačidlo EN) — nezapájať", False),
    (2,  "rbd1", "rbdimmer1 TUV — TEMP (teplota dosky)", True),
    (3,  "rbd1", "rbdimmer1 TUV — CUR-S (prúd)", True),
    (4,  "rbd2", "rbdimmer2 podlaha — TEMP (teplota dosky)", True),
    (5,  "rbd2", "rbdimmer2 podlaha — CUR-S (prúd)", True),
    (6,  "rbd2", "rbdimmer2 podlaha — FAN (ventilátor dosky)", True),
    (7,  "rbd1", "rbdimmer1 TUV — FAN (ventilátor dosky)", True),
    (8,  "rele", "Relé → čerpadlo podlaha", True),
    (9,  "rele", "Relé → čerpadlo TUV", True),
    (10, "vstup", "← OPTO: Daikin žiada čerpadlo podlahy", True),
    (11, "vstup", "← OPTO: Daikin žiada ohrev TUV (cievka K3M)", True),
    (12, "nie",  "NEPOUŽÍVAŤ — strapping (napätie flash pri štarte)", False),
    (13, "gnd",  "GND — spoločná zem", False),
    (14, "vstup", "← DS18B20 B3 voda podlaha · R8 4,7 kΩ → 3,3 V", True),
    (15, "nie",  "interný flash — nepoužívať", False),
    (16, "nie",  "interný flash — nepoužívať", False),
    (17, "nie",  "interný flash — nepoužívať", False),
    (18, "nap",  "5 V ← Mean Well MDR-20-5 (aj JD-VCC relé, fan skrine)", False),
]
RIGHT = [
    (0,  "gnd",  "GND — spoločná zem", False),
    (1,  "fan",  "PWM → ventilátor skrine (pin 4, 25 kHz)", False),
    (2,  "fan",  "← tacho ventilátora skrine (pin 3)", True),
    (3,  "nie",  "UART0 TX (USB) — nepoužívať", False),
    (4,  "nie",  "UART0 RX (USB) — nepoužívať", False),
    (5,  "vstup", "← DS18B20 B1 TUV bojler · R1 4,7 kΩ → 3,3 V", False),
    (6,  "gnd",  "GND — spoločná zem", False),
    (7,  "rele", "Relé → stykač podlaha (izolačný)", False),
    (8,  "rele", "Relé → BYPASS stykač podlaha", False),
    (9,  "vstup", "← DS18B20 B2 vratná voda TUV · R7 4,7 kΩ → 3,3 V", True),
    (10, "rele", "Relé → stykač TUV (izolačný)", False),
    (11, "rele", "Relé → BYPASS stykač TUV", False),
    (12, "vstup", "← prietok studenej → TUV (Hall) · R6 4,7 kΩ → 3,3 V", True),
    (13, "nie",  "BOOT (tlačidlo) — nepoužívať", False),
    (14, "i2c",  "I2C SDA → DimmerLink 0x50 + 0x51 · 1× 4,7 kΩ → 3,3 V", False),
    (15, "i2c",  "I2C SCL → DimmerLink 0x50 + 0x51 · 1× 4,7 kΩ → 3,3 V", False),
    (16, "nie",  "interný flash — nepoužívať", False),
    (17, "nie",  "interný flash — nepoužívať", False),
    (18, "nie",  "interný flash — nepoužívať", False),
]

el = []
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, fs=13, anchor="start", col="#212121", bold=False, italic=False):
    st = (' font-weight="bold"' if bold else "") + (' font-style="italic"' if italic else "")
    el.append(f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" fill="{col}"{st}>{esc(s)}</text>')
def rect(x, y, w, h, fill, stroke, rx=5, dash=False, sw=1.4):
    d = ' stroke-dasharray="4 3"' if dash else ""
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def line(x1, y1, x2, y2, col="#757575", w=1.2):
    el.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"/>')

def row_y(i):
    return ROW0 + i * STEP + OY

BOX_H = 22
# Ľavé popisy: box končí kúsok pred štítkom pinu
LBX1 = CX0 + OX - 14
LBX0 = 70
for i, cat, s, new in LEFT:
    f, st, tc = C[cat]
    y = row_y(i)
    rect(LBX0, y - BOX_H / 2, LBX1 - LBX0, BOX_H, f, st, dash=(cat == "volny" or s.startswith("voliteľné")))
    txt(LBX1 - 10, y + 4.5, s, fs=12.5, anchor="end", col=tc, bold=(cat not in ("nie", "volny")))
    line(LBX1, y, (568 if i in (0, 1, 13, 18) else CX0) + OX - 1, y, col=st)
    if new:
        rect(LBX0 + 6, y - 8, 44, 16, "#fff176", "#f9a825", rx=8, sw=1)
        txt(LBX0 + 28, y + 4, "NOVÉ", fs=10, anchor="middle", col="#5d4037", bold=True)

RBX0 = CX1 + OX + 14
RBX1 = W - 70
for i, cat, s, new in RIGHT:
    f, st, tc = C[cat]
    y = row_y(i)
    rect(RBX0, y - BOX_H / 2, RBX1 - RBX0, BOX_H, f, st, dash=(cat == "volny"))
    txt(RBX0 + 10, y + 4.5, s, fs=12.5, col=tc, bold=(cat not in ("nie", "volny")))
    line((1031 if i in (0, 6) else CX1) + OX + 1, y, RBX0, y, col=st)
    if new:
        rect(RBX1 - 50, y - 8, 44, 16, "#fff176", "#f9a825", rx=8, sw=1)
        txt(RBX1 - 28, y + 4, "NOVÉ", fs=10, anchor="middle", col="#5d4037", bold=True)

# Zátvorky = konektory rbdimmerov (vľavo od boxov)
def bracket(i_a, i_b, col, label1, label2, x=LBX0 - 8):
    ya, yb = row_y(i_a) - 9, row_y(i_b) + 9
    el.append(f'<path d="M{x+6},{ya} H{x} V{yb} H{x+6}" fill="none" stroke="{col}" stroke-width="2"/>')
    ym = (ya + yb) / 2
    el.append(f'<text x="{x-6}" y="{ym}" font-size="11" fill="{col}" font-weight="bold" text-anchor="middle" '
              f'transform="rotate(-90 {x-6} {ym})">{esc(label1)}</text>')
    if label2:
        el.append(f'<text x="{x-20}" y="{ym}" font-size="10" fill="{col}" text-anchor="middle" '
                  f'transform="rotate(-90 {x-20} {ym})">{esc(label2)}</text>')
bracket(2, 3, C["rbd1"][1], "rbd1 TUV", "")
bracket(4, 6, C["rbd2"][1], "rbdimmer2", "3 piny vedľa seba")
bracket(7, 7, C["rbd1"][1], "", "")
# prepojenie FAN rbd1 (33) so skupinou 36/39 — tenká čiarkovaná linka
x = LBX0 - 8
el.append(f'<path d="M{x},{row_y(3)+9} V{row_y(7)-9}" fill="none" stroke="{C["rbd1"][1]}" '
          f'stroke-width="1.2" stroke-dasharray="3 3"/>')

# Nadpis
txt(W / 2, 46, "ESP32-DevKitC (ESP32-WROOM-32) — zapojenie pinov FVE diverter",
    fs=24, anchor="middle", col="#212121", bold=True)
txt(W / 2, 74, "PLATNÉ od 2026-11-10 · zapracované do fve-diverter.yaml · žlté NOVÉ = zmena oproti "
    "zapojeniu pred 2026-11-10 (prekáblovať)", fs=13.5, anchor="middle", col="#bf360c", italic=True)
txt(W / 2, 96, "Podklad: oficiálny pinout Espressif (esp32-devkitC-v4-pinout.png). "
    "Šípka ► pri GPIO34–39 = len vstup (bez interného pull-upu).",
    fs=12, anchor="middle", col="#616161")

# Obrázok dosky (orezaný cez clipPath)
with open(IMG, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
el.append(f'<clipPath id="dosk"><rect x="{CX0+OX}" y="{CY0+OY}" width="{CX1-CX0}" height="{CY1-CY0}"/></clipPath>')
el.append(f'<image clip-path="url(#dosk)" x="{OX}" y="{OY}" width="1600" height="1091" '
          f'href="data:image/png;base64,{b64}"/>')

# zakryť zvyšok šedého štítku "PU" pred EN (siaha až po x≈568)
el.append(f'<rect x="{CX0+OX-1}" y="{row_y(1)-13}" width="{569-CX0}" height="26" fill="#ffffff"/>')
line(LBX1, row_y(1), 570 + OX, row_y(1), col=C["nie"][1])

# Legenda farieb
ly = CY1 + OY + 30
items = [("rele", "relé → stykače / čerpadlá"), ("rbd1", "rbdimmer1 TUV (L1, 3 kW)"),
         ("rbd2", "rbdimmer2 podlaha (L2, 600 W)"), ("i2c", "I2C DimmerLink"),
         ("vstup", "vstupy / senzory"), ("fan", "ventilátor skrine"),
         ("nap", "napájanie"), ("nie", "nepoužívať"), ("volny", "voľný / voliteľné")]
lx = 70
for cat, s in items:
    f, st, tc = C[cat]
    rect(lx, ly - 12, 18, 16, f, st, rx=3, dash=(cat == "volny"))
    txt(lx + 24, ly + 1, s, fs=12, col="#212121")
    lx += 24 + 7.0 * len(s) + 18

# Poznámky
ny = ly + 34
notes = [
    ("Zmeny oproti zapojeniu pred 2026-11-10:", True, "#bf360c"),
    ("• rbdimmer1 TUV: TEMP 34→36, CUR-S 35→39, FAN 32→33 · rbdimmer2 podlaha: TEMP 36→34, CUR-S 39→35, FAN 25→32", False, "#212121"),
    ("• Relé čerpadlá: podlaha →25, TUV 14→26 (25+26 vedľa seba = jeden 2-kan. modul; GPIO14 pri štarte vysiela signál → relé by mohlo cuknúť).", False, "#212121"),
    ("• Daikin vstupy: 2-kan. AC 230 V opto modul — čerpadlo podlahy → GPIO27, cievka K3M (ohrev TUV/BSH) → GPIO14 (modul napájať z 3,3 V).", False, "#212121"),
    ("• Záložné relé VCC ventilátora skrine ZRUŠENÉ (test: PWM 0 % fan zastaví) — GPIO13 teraz DS18B20 B3 (od 2026-11-14).", False, "#212121"),
    ("• Ventilátor skrine PWM 23 + tacho 4→22 vedľa seba; prietok studenej → TUV 22→4.", False, "#212121"),
    ("• 2026-11-14: DS18B20 KAŽDÝ NA VLASTNOM PINE (klony nejdú po dvoch na zbernici): B1 bojler G21+R1, B2 vratná G5+R7, B3 podlaha G13+R8. 4. (skriňa) zrušený.", True, "#1b5e20"),
    ("Prečo nie GPIO12: strapping pin MTDI — ak je pri štarte HIGH (relé modul ho cez optočlen ťahá hore), ESP zvolí 1,8 V flash a nenaštartuje.", True, "#b71c1c"),
    ("Konektory rbdimmerov: rbdimmer2 = GPIO34·35·32 tri piny vedľa seba (jeden 3-pin konektor). rbdimmer1 = GPIO36·39 spolu + FAN na GPIO33 zvlášť "
     "(FAN musí byť výstup — 34–39 sú len vstupy).", False, "#212121"),
    ("Relé moduly: jumper JD-VCC vybratý, VCC = 3,3 V (pin 3V3), JD-VCC = 5 V z Mean Wellu, aktívne v LOW. "
     "Pull-upy SPOLU 6 ks 4,7 kΩ na 3,3 V: R1 G21, R7 G5, R8 G13 (DS18B20), R6 G4 (prietok), R2 G2 SDA, R3 G15 SCL.", False, "#212121"),
]
for s, bold, col in notes:
    txt(70, ny, s, fs=12.5, col=col, bold=bold)
    ny += 22

# obrázok dosky dopredu (pod spojovacie čiary)
img = [e for e in el if e.startswith(('<clipPath', '<image'))]
el = img + [e for e in el if e not in img]

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="DejaVu Sans, Arial, sans-serif">\n<rect width="100%" height="100%" fill="#ffffff"/>\n'
       + "\n".join(el) + "\n</svg>\n")
out = os.path.join(HERE, "esp32_pinout_zapojenie.svg")
with open(out, "w") as f:
    f.write(svg)
print("SVG zapísané:", out, len(svg), "bajtov")
if shutil.which("rsvg-convert"):
    subprocess.run(["rsvg-convert", "-o", out[:-4] + ".png", out], check=True)
    print("PNG zapísané:", out[:-4] + ".png")
