#!/usr/bin/env python3
# Test deliča — TEMP a CUR-S z dosiek rbdimmer (40A-CS) na ESP32. Schéma NA VÝŠKU pre mobil
# (šírka 1080 px, veľké písmo), štýl ako mobil_teplomery.
#
# Stav 2026-11-16: CUR-S nezmeraný (3,3 alebo 5 V?) a dimmery sú zabudované v skrini → namiesto
# merania multimetrom ide CUR-S na ESP rovno cez delič 10k/18k (bezpečné v oboch prípadoch,
# 5 V → 3,2 V). Pokojové napätie (0 A) v HA prezradí napájanie snímača. TEMP = holý NTC 10k
# proti GND (zmerané 10,87 kΩ) → pull-up 10 kΩ na 3,3 V, napätie nikdy nad 3,3 V.
# Označenie rezistorov = nová doska pcb/ (R4/R5 TEMP, R9/R10 a R11/R12 delič CUR-S).
# Výstup: mobil_test_delica.svg (+ .png cez rsvg-convert).
import os
import shutil
import subprocess

W = 1080
el = []

RED, BLK, GREY = "#d32f2f", "#212121", "#616161"
C33 = "#e65100"                    # 3,3 V
BLU, BLU_L = "#1565c0", "#e3f2fd"  # TEMP
PUR = "#6a1b9a"                    # CUR-S
GRN, GRN_L = "#1b5e20", "#e8f5e9"
RES_F = "#fff3e0"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, fs=30, anchor="start", col=BLK, bold=False, italic=False):
    st = (' font-weight="bold"' if bold else "") + (' font-style="italic"' if italic else "")
    el.append(f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" fill="{col}"{st}>{esc(s)}</text>')


def rect(x, y, w, h, fill, stroke, rx=14, sw=3, dash=False):
    d = ' stroke-dasharray="10 8"' if dash else ""
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(pts, col, w=6):
    p = " ".join(f"{x},{y}" for x, y in pts)
    el.append(f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>')


def dot(x, y, col, r=9):
    el.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')


def pill(x, y, w, h, s, fill, fg="#fff", fs=32):
    rect(x, y, w, h, fill, fill, rx=h/2, sw=2)
    txt(x + w/2, y + h/2 + fs*0.36, s, fs=fs, anchor="middle", col=fg, bold=True)


def res_v(x, y1, y2, ref, val, col=C33):
    """Zvislý rezistor medzi y1 a y2 (bodky na koncoch), popis vľavo."""
    m = (y2 - y1) * 0.22
    line([(x, y1), (x, y1 + m)], col, w=5)
    line([(x, y2 - m), (x, y2)], col, w=5)
    rect(x - 20, y1 + m, 40, y2 - y1 - 2*m, RES_F, col, rx=4, sw=4)
    txt(x - 32, (y1 + y2)/2 - 4, ref, fs=30, anchor="end", bold=True, col=col)
    txt(x - 32, (y1 + y2)/2 + 30, val, fs=26, anchor="end", bold=True, col=col)


def res_h(x1, x2, y, ref, val, col=C33):
    """Vodorovný rezistor v sérii (x1–x2), popis nad ním."""
    rect(x1, y - 20, x2 - x1, 40, RES_F, col, rx=4, sw=4)
    txt((x1 + x2)/2, y - 34, f"{ref} {val}", fs=28, anchor="middle", bold=True, col=col)


# ---------------------------------------------------------------- hlavička
y = 70
txt(W/2, y, "Test deliča TEMP a CUR-S", fs=52, anchor="middle", bold=True, col=PUR)
y += 50
txt(W/2, y, "dosky rbdimmer → ESP32 FVE diverter · 2026-11-16", fs=28, anchor="middle", col=GREY)
y += 40
rect(40, y, W-80, 290, "#fff8e1", "#f9a825", sw=3)
txt(70, y+50, "Prečo delič na CUR-S", fs=34, bold=True, col=C33)
txt(70, y+95, "Nevieme, či snímač prúdu beží na 3,3 V alebo 5 V.", fs=28)
txt(70, y+135, "Delič 10k/18k zníži napätie na 64 %: aj 5 V", fs=28)
txt(70, y+175, "príde na ESP ako 3,2 V → ESP sa nič nestane.", fs=28)
txt(70, y+215, "Čo je pravda, ukáže napätie v HA pri 0 A.", fs=28, bold=True)
txt(70, y+262, "Pred prácou v skrini vypni istič dimmerov (230 V)!", fs=28, bold=True, col=RED)
y += 330

# ---------------------------------------------------------------- karty dimmerov
DIM = [
    ("D1", "TUV (bojler)", "GPIO36", "GPIO39", "R4", "R9", "R10",
     "Dimmer TUV — TEMP napätie", "Prúd dimmer TUV (CUR-S)"),
    ("D2", "podlaha", "GPIO34", "GPIO35", "R5", "R11", "R12",
     "Dimmer podlaha — TEMP napätie", "Prúd dimmer podlaha (CUR-S)"),
]
CARD_H = 1000
for ref, name, g_t, g_c, r_t, r_s, r_g, ha_t, ha_c in DIM:
    rect(30, y, W-60, CARD_H, "#ffffff", PUR, sw=4, rx=22)
    rect(30, y, W-60, 92, "#f3e5f5", PUR, sw=4, rx=22)
    el.append(f'<rect x="32" y="{y+60}" width="{W-64}" height="30" fill="#f3e5f5"/>')
    txt(60, y+62, f"{ref}  {name}", fs=42, bold=True, col=PUR)
    pill(W-60-330, y+20, 300, 54, f"{g_t[4:]} · {g_c[4:]}", PUR, fs=32)

    top = y + 170
    R = {"5V": top, "3V3": top + 110, "TEMP": top + 240, "CUR": top + 390, "GND": top + 530}
    # doska rbdimmer (vľavo)
    BX0, BX1 = 50, 250
    rect(BX0, top - 60, BX1 - BX0, R["GND"] - top + 110, "#eceff1", "#455a64", rx=18, sw=3)
    txt((BX0+BX1)/2, top - 22, "rbdimmer", fs=26, anchor="middle", bold=True, col="#37474f")
    pins = {"5V": ("5V", RED), "TEMP": ("TEMP", BLU), "CUR": ("CUR-S", PUR), "GND": ("GND", BLK)}
    for k, (lab, c) in pins.items():
        txt(BX1 - 16, R[k] + 10, lab, fs=28, anchor="end", bold=True, col=c)
        dot(BX1, R[k], c, r=10)
    txt(BX0 + 14, R["TEMP"] + 50, "NTC 10k", fs=22, col=GREY, italic=True)
    txt(BX0 + 14, R["TEMP"] + 76, "→ GND", fs=22, col=GREY, italic=True)
    txt(BX0 + 14, R["CUR"] + 50, "snímač", fs=22, col=GREY, italic=True)
    txt(BX0 + 14, R["CUR"] + 76, "prúdu", fs=22, col=GREY, italic=True)

    TX, TW = 770, 250          # svorky ESP / napájania vpravo
    # 5 V — napájanie snímača prúdu
    line([(BX1, R["5V"]), (TX, R["5V"])], RED, w=8)
    txt(BX1 + 24, R["5V"] - 16, "napájanie snímača prúdu", fs=24, col=RED, bold=True)
    pill(TX, R["5V"] - 30, TW, 60, "5V Mean Well", RED, fs=28)
    # 3,3 V — len pre pull-up TEMP
    RX_T = 470
    line([(RX_T, R["3V3"]), (TX, R["3V3"])], C33, w=8)
    dot(RX_T, R["3V3"], C33)
    pill(TX, R["3V3"] - 30, TW, 60, "3V3", C33, fs=32)
    # TEMP
    line([(BX1, R["TEMP"]), (TX, R["TEMP"])], BLU, w=8)
    txt(BX1 + 24, R["TEMP"] - 16, "TEMP", fs=26, col=BLU, bold=True)
    dot(RX_T, R["TEMP"], BLU)
    res_v(RX_T, R["3V3"], R["TEMP"], r_t, "10 kΩ")
    pill(TX, R["TEMP"] - 30, TW, 60, g_t, BLU, fs=32)
    # CUR-S → R sériový → uzol → GPIO, R na GND
    RS1, RS2, NODE = 330, 470, 600
    line([(BX1, R["CUR"]), (RS1, R["CUR"])], PUR, w=8)
    res_h(RS1, RS2, R["CUR"], r_s, "10 kΩ")
    line([(RS2, R["CUR"]), (TX, R["CUR"])], PUR, w=8)
    dot(NODE, R["CUR"], PUR)
    res_v(NODE, R["CUR"], R["GND"], r_g, "18 kΩ")
    dot(NODE, R["GND"], BLK)
    pill(TX, R["CUR"] - 30, TW, 60, g_c, PUR, fs=32)
    # GND
    line([(BX1, R["GND"]), (TX, R["GND"])], BLK, w=8)
    txt(BX1 + 24, R["GND"] - 16, "GND", fs=26, col=BLK, bold=True)
    pill(TX, R["GND"] - 30, TW, 60, "GND", BLK, fs=32)

    yy = R["GND"] + 90
    txt(60, yy, f"{r_t} 10 kΩ: z TEMP na 3,3 V (pri ESP).", fs=28)
    txt(60, yy + 42, f"{r_s} 10 kΩ v sérii do CUR-S, {r_g} 18 kΩ", fs=28)
    txt(60, yy + 80, f"z {g_c} na GND (pri ESP).", fs=28)
    txt(60, yy + 128, f"HA: „{ha_t}“", fs=26, col=BLU, bold=True)
    txt(60, yy + 166, f"HA: „{ha_c}“", fs=26, col=PUR, bold=True)
    y += CARD_H + 30

# ---------------------------------------------------------------- mini doska
txt(W/2, y+40, "Kde sú piny na doske", fs=40, anchor="middle", bold=True, col=PUR)
txt(W/2, y+82, "ESP32-DevKitC 38-pin, pohľad zhora, anténa hore", fs=26, anchor="middle", col=GREY)
y += 120
LEFT = ["3V3", "EN", "36", "39", "34", "35", "32", "33", "25", "26", "27", "14", "12",
        "GND", "13", "D2", "D3", "CMD", "5V"]
RIGHT = ["GND", "23", "22", "TX", "RX", "21", "GND", "19", "18", "5", "17", "16", "4",
         "0", "2", "15", "D1", "D0", "CLK"]
HL = {"3V3": ("3V3 → R4, R5", C33), "GND": ("GND → R10, R12", BLK),
      "36": ("TEMP TUV", BLU), "39": ("CUR-S TUV", PUR),
      "34": ("TEMP podlaha", BLU), "35": ("CUR-S podlaha", PUR)}
STEP = 46
BX, BW = W/2 - 130, 260
by0 = y + 90
rect(BX, y, BW, 90 + 19*STEP + 70, "#263238", "#000", rx=18, sw=3)
rect(BX+60, y+14, BW-120, 60, "#37474f", "#90a4ae", rx=6, sw=2)
txt(W/2, y+54, "anténa", fs=24, anchor="middle", col="#cfd8dc")
rect(W/2-45, y+90+19*STEP+18, 90, 52, "#9e9e9e", "#616161", rx=6, sw=2)
txt(W/2, y+90+19*STEP+52, "USB", fs=22, anchor="middle", col=BLK, bold=True)
gnd_done = False
for i in range(19):
    py = by0 + i*STEP
    for side, names in (("L", LEFT), ("R", RIGHT)):
        nm = names[i]
        px = BX + 22 if side == "L" else BX + BW - 22
        hl = HL.get(nm)
        if nm == "GND" and (side == "L" or gnd_done):
            hl = None          # stačí jeden GND pin (pravý horný)
        if nm == "GND" and hl:
            gnd_done = True
        dot(px, py, "#ffd600" if hl else "#bdbdbd", r=11 if hl else 8)
        tx = px + 22 if side == "L" else px - 22
        txt(tx, py+8, nm, fs=22, anchor="start" if side == "L" else "end",
            col="#ffffff" if hl else "#90a4ae", bold=bool(hl))
        if hl:
            lab, c = hl
            if side == "L":
                line([(BX, py), (BX-40, py)], c, w=5)
                pill(BX-40-260, py-21, 260, 42, lab, c, fs=23)
            else:
                line([(BX+BW, py), (BX+BW+40, py)], c, w=5)
                pill(BX+BW+40, py-21, 260, 42, lab, c, fs=23)
y += 90 + 19*STEP + 70 + 40

# ---------------------------------------------------------------- vyhodnotenie
txt(W/2, y+40, "Čo ukáže HA (dimmer VYP, 0 A)", fs=40, anchor="middle", bold=True, col=PUR)
y += 80


def tabulka(y, title, col, rows):
    h = 70 + len(rows)*96
    rect(30, y, W-60, h, "#ffffff", col, sw=3, rx=18)
    txt(60, y+50, title, fs=32, bold=True, col=col)
    yy = y + 70
    for val, a, b in rows:
        el.append(f'<line x1="50" y1="{yy}" x2="{W-50}" y2="{yy}" stroke="#e0e0e0" stroke-width="2"/>')
        txt(60, yy+42, val, fs=32, bold=True, col=col)
        txt(300, yy+40, a, fs=27, bold=True)
        txt(300, yy+76, b, fs=25, col=GREY)
        yy += 96
    return y + h + 30


y = tabulka(y, "TEMP napätie", BLU, [
    ("~1,7 V", "OK — NTC pri izbovej teplote", "→ zapni „Teplota TRIAC — zapojená“"),
    ("nad 3 V", "TEMP nie je pripojený", "(len pull-up, NTC chýba) → skontroluj vodič"),
    ("~0 V", "skrat na GND alebo chýba 3,3 V", "→ skontroluj R4/R5 a 3V3"),
])
y = tabulka(y, "CUR-S (delič 10k/18k)", PUR, [
    ("~1,06 V", "snímač na 3,3 V (1,65 V × 0,64)", "delič môže ostať, na doske stačí 0 Ω"),
    ("~1,6 V", "snímač na 5 V (2,5 V × 0,64)", "delič MUSÍ ostať"),
    ("~0 V", "iný výstup alebo chýba 5 V", "→ skontroluj 5V pin dosky, potom test so záťažou"),
])

# ---------------------------------------------------------------- poznámky
notes = [
    ("Rezistory daj do skrine pri ESP, nie k dimmeru.", True),
    ("Dimmer ani DimmerLink netreba odpájať.", False),
    ("GND je už spoločná cez DimmerLink.", False),
    ("Nemáš 18 kΩ? R10/R12 = 10 kΩ (polovica),", True),
    ("tiež bezpečné — očakávaj 0,83 V / 1,25 V.", False),
    ("Hodnoty pošli Claudovi → potom test so záťažou", True),
    ("(TUV ~90 %, bypass VYP) a kalibrácia podľa Shelly.", False),
]
rect(30, y, W-60, 40 + len(notes)*44, "#f5f5f5", "#9e9e9e", sw=2)
yy = y + 50
for s, b in notes:
    txt(60, yy, s, fs=28, bold=b)
    yy += 44
H = int(y + 40 + len(notes)*44 + 40)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="DejaVu Sans, Arial, sans-serif">\n<rect width="100%" height="100%" fill="#ffffff"/>\n'
       + "\n".join(el) + "\n</svg>\n")
HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, "mobil_test_delica.svg")
with open(out, "w") as f:
    f.write(svg)
print("SVG zapísané:", out, W, "×", H)
if shutil.which("rsvg-convert"):
    subprocess.run(["rsvg-convert", "-o", out[:-4] + ".png", out], check=True)
    print("PNG zapísané:", out[:-4] + ".png")
