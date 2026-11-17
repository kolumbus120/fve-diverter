#!/usr/bin/env python3
# Teplomery DS18B20 — schéma NA VÝŠKU pre mobil (šírka 1080 px, veľké písmo).
# Obsah zhodný s esp32_schema_realny (B1–B3) a esp32_pinout_zapojenie, len
# prekreslený tak, aby sa dal čítať na telefóne bez zoomovania.
#
# Stav 2026-11-15: každý DS18B20 na VLASTNOM pine (lacné klony nejdú po dvoch
# na jednej zbernici) — B1 bojler G21+R1, B2 vratná G5+R7, B3 podlaha G13+R8.
# Výstup: mobil_teplomery.svg (+ .png cez rsvg-convert).
import os
import shutil
import subprocess

W = 1080
el = []

RED, YEL, BLK = "#d32f2f", "#fbc02d", "#212121"
GRN, GRN_L = "#1b5e20", "#e8f5e9"
C33, GREY = "#e65100", "#616161"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, fs=30, anchor="start", col=BLK, bold=False, italic=False):
    st = (' font-weight="bold"' if bold else "") + (' font-style="italic"' if italic else "")
    el.append(f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" fill="{col}"{st}>{esc(s)}</text>')


def rect(x, y, w, h, fill, stroke, rx=14, sw=3, dash=False):
    d = ' stroke-dasharray="10 8"' if dash else ""
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(pts, col, w=6, outline=None):
    p = " ".join(f"{x},{y}" for x, y in pts)
    if outline:
        el.append(f'<polyline points="{p}" fill="none" stroke="{outline}" stroke-width="{w+4}" stroke-linejoin="round"/>')
    el.append(f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>')


def dot(x, y, col, r=9):
    el.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')


def pill(x, y, w, h, s, fill, fg="#fff", fs=32):
    rect(x, y, w, h, fill, fill, rx=h/2, sw=2)
    txt(x + w/2, y + h/2 + fs*0.36, s, fs=fs, anchor="middle", col=fg, bold=True)


# ---------------------------------------------------------------- hlavička
y = 70
txt(W/2, y, "Teplomery DS18B20", fs=52, anchor="middle", bold=True, col=GRN)
y += 50
txt(W/2, y, "zapojenie na ESP32 FVE diverter · stav 2026-11-15", fs=28, anchor="middle", col=GREY)
y += 40
rect(40, y, W-80, 150, "#fff8e1", "#f9a825", sw=3)
txt(70, y+50, "Každý snímač na VLASTNOM pine", fs=34, bold=True, col="#e65100")
txt(70, y+95, "+ vlastný rezistor 4,7 kΩ z DATA na 3,3 V.", fs=30)
txt(70, y+133, "Lacné klony nejdú po dvoch na jednom drôte.", fs=28, col=GREY, italic=True)
y += 190

# ---------------------------------------------------------------- karty snímačov
SENS = [
    ("B1", "TUV bojler", "GPIO21", "R1", "pravý rad, 6. pin zhora",
     "OK — adresa 0x4900000023440328", GRN),
    ("B2", "vratná voda TUV", "GPIO5", "R7", "pravý rad, 10. pin zhora",
     "OK — adresa 0x9A00000022326128", GRN),
    ("B3", "voda podlaha", "GPIO13", "R8", "ľavý rad, 15. pin zhora",
     "OK — adresa 0x690000002229DA28", GRN),
]
CARD_H = 600
for ref, name, gpio, rref, where, status, scol in SENS:
    rect(30, y, W-60, CARD_H, "#ffffff", GRN, sw=4, rx=22)
    # názov
    rect(30, y, W-60, 92, GRN_L, GRN, sw=4, rx=22)
    el.append(f'<rect x="32" y="{y+60}" width="{W-64}" height="30" fill="{GRN_L}"/>')
    txt(60, y+62, f"{ref}  {name}", fs=42, bold=True, col=GRN)
    pill(W-60-250, y+20, 220, 54, gpio, GRN, fs=34)

    # snímač (sonda + kábel)
    sx, top = 70, y + 150
    rows = {"VDD": top + 20, "DATA": top + 150, "GND": top + 280}
    rect(sx, top-10, 120, 320, "#eceff1", "#455a64", rx=18, sw=3)
    txt(sx+60, top+138, "DS", fs=30, anchor="middle", bold=True, col="#37474f")
    txt(sx+60, top+176, "18B20", fs=30, anchor="middle", bold=True, col="#37474f")
    # svorky na ESP vpravo
    TX = 760
    term = {"VDD": ("3V3", C33), "DATA": (gpio, GRN), "GND": ("GND", BLK)}
    wires = {"VDD": (RED, None, "červený"), "DATA": (YEL, BLK, "žltý"), "GND": (BLK, None, "čierny")}
    for k, yy in rows.items():
        col, outl, cname = wires[k]
        line([(sx+120, yy), (TX, yy)], col, w=10, outline=outl)
        txt(sx+140, yy-18, f"{cname} · {k}", fs=28, col=BLK if k != "VDD" else RED, bold=True)
        lab, tc = term[k]
        pill(TX, yy-30, 260, 60, lab, tc, fs=32)
    # pull-up rezistor medzi VDD a DATA (pri ESP)
    RX = 620
    r_top, r_bot = rows["VDD"], rows["DATA"]
    dot(RX, r_top, RED)
    dot(RX, r_bot, GRN)
    line([(RX, r_top), (RX, r_top+30)], C33, w=5)
    line([(RX, r_bot-30), (RX, r_bot)], C33, w=5)
    rect(RX-20, r_top+30, 40, r_bot-r_top-60, "#fff3e0", C33, rx=4, sw=4)
    txt(RX-32, (r_top+r_bot)/2-4, rref, fs=32, anchor="end", bold=True, col=C33)
    txt(RX-32, (r_top+r_bot)/2+32, "4,7 kΩ", fs=28, anchor="end", bold=True, col=C33)
    # kde na doske + stav
    txt(60, y+CARD_H-80, f"{gpio} = {where}", fs=30, col=BLK)
    txt(60, y+CARD_H-32, status, fs=28, bold=True, col=scol)
    y += CARD_H + 30

# ---------------------------------------------------------------- mini doska
txt(W/2, y+40, "Kde sú piny na doske", fs=40, anchor="middle", bold=True, col=GRN)
txt(W/2, y+82, "ESP32-DevKitC 38-pin, pohľad zhora, anténa hore", fs=26, anchor="middle", col=GREY)
y += 120
LEFT = ["3V3", "EN", "36", "39", "34", "35", "32", "33", "25", "26", "27", "14", "12",
        "GND", "13", "D2", "D3", "CMD", "5V"]
RIGHT = ["GND", "23", "22", "TX", "RX", "21", "GND", "19", "18", "5", "17", "16", "4",
         "0", "2", "15", "D1", "D0", "CLK"]
HL = {"3V3": ("3V3 → VDD + R", C33), "GND": ("GND", BLK),
      "21": ("B1 bojler", GRN), "5": ("B2 vratná", GRN), "13": ("B3 podlaha", GRN)}
STEP = 46
BX, BW = W/2 - 130, 260
by0 = y + 90
rect(BX, y, BW, 90 + 19*STEP + 70, "#263238", "#000", rx=18, sw=3)
rect(BX+60, y+14, BW-120, 60, "#37474f", "#90a4ae", rx=6, sw=2)
txt(W/2, y+54, "anténa", fs=24, anchor="middle", col="#cfd8dc")
rect(W/2-45, y+90+19*STEP+18, 90, 52, "#9e9e9e", "#616161", rx=6, sw=2)
txt(W/2, y+90+19*STEP+52, "USB", fs=22, anchor="middle", col=BLK, bold=True)
for i in range(19):
    py = by0 + i*STEP
    for side, names in (("L", LEFT), ("R", RIGHT)):
        nm = names[i]
        px = BX + 22 if side == "L" else BX + BW - 22
        hl = HL.get(nm)
        dot(px, py, "#ffd600" if hl else "#bdbdbd", r=11 if hl else 8)
        tx = px + 22 if side == "L" else px - 22
        txt(tx, py+8, nm, fs=22, anchor="start" if side == "L" else "end",
            col="#ffffff" if hl else "#90a4ae", bold=bool(hl))
        if hl:
            lab, c = hl
            if side == "L":
                line([(BX, py), (BX-40, py)], c, w=5)
                pill(BX-40-250, py-22, 250, 44, lab, c, fs=24)
            else:
                line([(BX+BW, py), (BX+BW+40, py)], c, w=5)
                pill(BX+BW+40, py-22, 250, 44, lab, c, fs=24)
y += 90 + 19*STEP + 70 + 40

# ---------------------------------------------------------------- poznámky
notes = [
    ("Rezistory R1, R7, R8 daj do skrine pri ESP", True),
    ("(medzi svorku DATA a 3,3 V), nie k snímaču.", False),
    ("GND a 3,3 V môžu mať snímače spoločné,", True),
    ("DATA musí ísť každý na svoj pin.", False),
    ("Kontrola: v HA tlačidlo „Test — hľadať DS18B20“", True),
    ("→ ukáže adresy na G21 / G5 / G13.", False),
]
rect(30, y, W-60, 40 + len(notes)*44, "#f5f5f5", "#9e9e9e", sw=2)
yy = y + 50
for s, b in notes:
    txt(60, yy, s, fs=29, bold=b)
    yy += 44
H = int(y + 40 + len(notes)*44 + 40)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="DejaVu Sans, Arial, sans-serif">\n<rect width="100%" height="100%" fill="#ffffff"/>\n'
       + "\n".join(el) + "\n</svg>\n")
HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, "mobil_teplomery.svg")
with open(out, "w") as f:
    f.write(svg)
print("SVG zapísané:", out, W, "×", H)
if shutil.which("rsvg-convert"):
    subprocess.run(["rsvg-convert", "-o", out[:-4] + ".png", out], check=True)
    print("PNG zapísané:", out[:-4] + ".png")
