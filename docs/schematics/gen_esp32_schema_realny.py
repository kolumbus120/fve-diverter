#!/usr/bin/env python3
# ESP32 — skutočná elektrotechnická schéma NÍZKONAPÄŤOVEJ (riadiacej) časti
# FVE divertera (STN/IEC značky). Doplnok k:
#   - esp32_pinout_zapojenie.png  (obrázok dosky, pin po pine — rýchla orientácia)
#   - fve_schema_realny.svg       (silová časť: stykače K1–K4, dimmery D1/D2, čerpadlá)
#
# Stav zapojenia: platné od 2026-11-10 (nový pinout), 1 kΩ na GPIO14 zrušený
# 2026-11-13. Snímač prietoku B5 (GPIO4, Hall z TECH EU-11) doplnený 2026-11-14:
# napájanie +3V3 + R6 4,7 kΩ pull-up → bez diódy, výstup nikdy nad 3,3 V.
# DS18B20 od 2026-11-14 každý na VLASTNOM pine (klony nejdú po dvoch na zbernici):
# B1 GPIO21+R1, B2 GPIO5+R7, B3 GPIO13+R8. B4 (skriňa) zrušený — niet pinu.
#
# Konvencie:
#  - bodka = spojené; kríženie bez bodky = NEspojené
#  - × na konci pinu = pin nezapojený
#  - napájacie siete (+3V3, +5V, GND) cez značky napájania — všetky s rovnakým
#    menom sú spojené; signály medzi blokmi cez menovky sietí (vlajky)
#  - rezistor/kondenzátor podľa IEC (obdĺžnik / dve dosky)
#  - ESP32-DevKitC 38-pin: piny v SKUTOČNOM poradí na doske (ľavý a pravý rad
#    1–19, pohľad zhora, anténa hore)
#
# Zdroj k rbdimmer 40A-CS (rbdimmer.com/docs/hardware-connection, 2026-11-13):
# VCC = logická úroveň MCU (3,3 V), TEMP → ADC, FAN = logický vstup (aktívny
# HIGH, tranzistor na doske), 5V = SAMOSTATNÝ vstup 5 V pre ventilátor dosky
# (z regulovaného 5 V zdroja). Výstupné napätie TEMP/CUR-S doc neuvádza.

import os
import shutil
import subprocess

W, H = 2600, 1960
el = []

BLK = "#111"
GREY = "#555"
C33 = "#e65100"     # +3V3
C5 = "#c62828"      # +5V
CG = "#2e7d32"      # GND
CAC = "#b71c1c"     # 230 V
CNET = "#0d47a1"    # menovky sietí


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, fs=12, anchor="start", col=BLK, bold=False, italic=False):
    w = ' font-weight="bold"' if bold else ''
    i = ' font-style="italic"' if italic else ''
    el.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{fs}" '
              f'fill="{col}"{w}{i}>{esc(s)}</text>')


def wire(pts, col=BLK, wdth=1.6, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    p = " ".join(f"{x},{y}" for x, y in pts)
    el.append(f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="{wdth}"{d}/>')


def dot(x, y, r=3.2, col=BLK):
    el.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')


def rect(x, y, w, h, fill="#ffffff", stroke=BLK, sw=1.6, dash="", rx=0):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
              f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def nc(x, y):
    """× = nezapojený pin."""
    s = 5
    wire([(x-s, y-s), (x+s, y+s)], col=GREY, wdth=1.4)
    wire([(x-s, y+s), (x+s, y-s)], col=GREY, wdth=1.4)


def ground(x, y, col=CG):
    """Zem — vodič z (x,y) dole + 3 čiarky."""
    wire([(x, y), (x, y+10)], col=col)
    for i, wid in enumerate((16, 10, 4)):
        yy = y+10+i*5
        wire([(x-wid/2, yy), (x+wid/2, yy)], wdth=1.8, col=col)


def port(x, y, name, d="up"):
    """Značka napájania: vodič z (x,y) smerom d, na konci priečka + meno."""
    col = C5 if "5V" in name else (C33 if "3V3" in name else CG)
    L = 14
    if d == "up":
        wire([(x, y), (x, y-L)], col=col)
        wire([(x-8, y-L), (x+8, y-L)], col=col, wdth=2.4)
        txt(x, y-L-5, name, fs=10, anchor="middle", col=col, bold=True)
    elif d == "down":
        wire([(x, y), (x, y+L)], col=col)
        wire([(x-8, y+L), (x+8, y+L)], col=col, wdth=2.4)
        txt(x, y+L+14, name, fs=10, anchor="middle", col=col, bold=True)
    elif d == "left":
        wire([(x, y), (x-L, y)], col=col)
        wire([(x-L, y-8), (x-L, y+8)], col=col, wdth=2.4)
        txt(x-L-5, y+4, name, fs=10, anchor="end", col=col, bold=True)
    else:
        wire([(x, y), (x+L, y)], col=col)
        wire([(x+L, y-8), (x+L, y+8)], col=col, wdth=2.4)
        txt(x+L+5, y+4, name, fs=10, anchor="start", col=col, bold=True)


def netlabel(x, y, name, d="left"):
    """Menovka siete — vlajka na konci vodiča v (x,y), smerom d."""
    w = 9 + 7.2*len(name)
    h = 16
    if d == "left":
        pts = [(x, y), (x-7, y-h/2), (x-w, y-h/2), (x-w, y+h/2), (x-7, y+h/2)]
        tx = x - 7 - (w-7)/2
    else:
        pts = [(x, y), (x+7, y-h/2), (x+w, y-h/2), (x+w, y+h/2), (x+7, y+h/2)]
        tx = x + 7 + (w-7)/2
    p = " ".join(f"{a},{b}" for a, b in pts)
    el.append(f'<polygon points="{p}" fill="#e3f2fd" stroke="{CNET}" stroke-width="1.3"/>')
    txt(tx, y+4, name, fs=10, anchor="middle", col=CNET, bold=True)


def res_v(x, y0, y1, ref, val, side="right", col=BLK, dash=""):
    """IEC rezistor zvislo medzi y0 a y1 (dash = voliteľný/podmienečný)."""
    m = (y0+y1)/2
    wire([(x, y0), (x, m-15)], col=col, dash=dash)
    rect(x-6, m-15, 12, 30, stroke=col, dash=dash)
    wire([(x, m+15), (x, y1)], col=col, dash=dash)
    if side == "right":
        txt(x+11, m-2, ref, fs=10.5, bold=True, col=col)
        txt(x+11, m+11, val, fs=10, col=col)
    else:
        txt(x-11, m-2, ref, fs=10.5, bold=True, col=col, anchor="end")
        txt(x-11, m+11, val, fs=10, col=col, anchor="end")


def cap_v(x, y0, y1, ref, val):
    m = (y0+y1)/2
    wire([(x, y0), (x, m-3)])
    wire([(x-9, m-3), (x+9, m-3)], wdth=2.2)
    wire([(x-9, m+3), (x+9, m+3)], wdth=2.2)
    wire([(x, m+3), (x, y1)])
    txt(x+13, m-1, ref, fs=10, bold=True)
    txt(x+13, m+11, val, fs=9.5)


def pin_stub(x, y, name, side, stub=16, fs=9.5):
    """Pin bloku: krátky vodič von z hrany + meno pinu vnútri bloku. Vráti koniec."""
    if side == "left":
        wire([(x-stub, y), (x, y)])
        txt(x+5, y+3.5, name, fs=fs, anchor="start")
        return (x-stub, y)
    if side == "right":
        wire([(x, y), (x+stub, y)])
        txt(x-5, y+3.5, name, fs=fs, anchor="end")
        return (x+stub, y)
    if side == "top":
        wire([(x, y-stub), (x, y)])
        txt(x, y+12, name, fs=fs, anchor="middle")
        return (x, y-stub)
    wire([(x, y), (x, y+stub)])
    txt(x, y-5, name, fs=fs, anchor="middle")
    return (x, y+stub)


def no_contact_v(x, y, mirror=False):
    """Zapínací kontakt relé (NO) zvislo: NO hore (y-10), COM dole (y+10)."""
    s = -1 if mirror else 1
    wire([(x, y-10), (x, y-6)])
    wire([(x-5, y-6), (x+5, y-6)])
    wire([(x, y+10), (x, y+7)])
    wire([(x, y+7), (x+s*9, y-7)], wdth=2.0)       # jazýček (rozopnutý)
    return (x, y-10), (x, y+10)


def relay_module(x, y, w, h, ref, title, chans, in_side, pwr_side):
    """2-kanálový relé modul (optočlen + tranzistor + relé, vstup aktívny v LOW).
    chans: [(pin_y, 'IN1', 'KA1', 'text k výstupu')] — zakreslené len použité
    kontakty COM + NO (NC nezapojený). in_side: strana IN pinov, kontakty na
    opačnej. pwr_side: 'top'/'bottom' — VCC, GND, JD-VCC. Vráti konce IN pinov."""
    rect(x, y, w, h, fill="#fff8e1", stroke="#e65100", sw=1.8)
    if pwr_side == "bottom":
        txt(x+w/2, y+14, f"{ref} — {title}", fs=10.5, anchor="middle", bold=True, col="#bf360c")
    elif in_side == "left":       # hore sú napájacie piny → nadpis vonku na strane kontaktov
        txt(x+w+22, y+2, f"{ref} — {title}", fs=10.5, anchor="start", bold=True, col="#bf360c")
    else:
        txt(x-22, y+2, f"{ref} — {title}", fs=10.5, anchor="end", bold=True, col="#bf360c")
    ends = {}
    for (py_, pin, ka, note) in chans:
        left = in_side == "left"
        ends[pin] = pin_stub(x if left else x+w, py_, pin, "left" if left else "right")
        cx_coil = x + 72 if left else x + w - 72
        kx = x + w - 52 if left else x + 52
        edge = x + w if left else x
        sgn = 1 if left else -1
        # IN → (optočlen + tranzistor, zjednodušene) → cievka relé
        wire([(x+30 if left else x+w-30, py_), (cx_coil-sgn*14, py_)], col=GREY, wdth=1.1, dash="3,2")
        rect(cx_coil-14, py_-8, 28, 16)
        txt(cx_coil, py_-11, ka, fs=9, anchor="middle", bold=True)
        wire([(cx_coil+sgn*14, py_), (kx-sgn*4, py_)], col="#777", wdth=1.0, dash="4,3")
        no, com = no_contact_v(kx, py_, mirror=not left)
        wire([no, (edge, no[1])]); wire([com, (edge, com[1])])
        for yy, lab in ((no[1], "NO"), (com[1], "COM")):
            wire([(edge, yy), (edge+sgn*16, yy)])
            txt(edge-sgn*3, yy-2, lab, fs=7.5, anchor="end" if left else "start", col=GREY)
        txt(edge+sgn*22, py_+4, note, fs=9.5, anchor="start" if left else "end", col=CAC)
    px = [x + w*0.25, x + w*0.5, x + w*0.75]
    for xx, nm, fl in zip(px, ["VCC", "GND", "JD-VCC"], ["+3V3", "GND", "+5V"]):
        if pwr_side == "top":
            e = pin_stub(xx, y, nm, "top", stub=12, fs=8.5)
            port(e[0], e[1], fl, "up")
        else:
            e = pin_stub(xx, y+h, nm, "bottom", stub=12, fs=8.5)
            if fl == "GND":
                ground(e[0], e[1])
            else:
                port(e[0], e[1], fl, "down")
    return ends


def opto_symbol(cx, cy):
    """Optočlen (AC vstup — 2 antiparalelné LED zjednodušene 1 LED + fototranzistor)."""
    # LED (trojuholník dole + priečka)
    lx = cx - 22
    el.append(f'<polygon points="{lx-7},{cy-7} {lx+7},{cy-7} {lx},{cy+5}" fill="#fff" stroke="{BLK}" stroke-width="1.4"/>')
    wire([(lx-7, cy+5), (lx+7, cy+5)], wdth=1.4)
    wire([(lx, cy-16), (lx, cy-7)], wdth=1.2)
    wire([(lx, cy+5), (lx, cy+16)], wdth=1.2)
    # šípky svetla
    for dy in (-4, 3):
        wire([(lx+10, cy+dy), (cx-2, cy+dy)], wdth=1.0)
        el.append(f'<polygon points="{cx-2},{cy+dy-3} {cx+3},{cy+dy} {cx-2},{cy+dy+3}" fill="{BLK}"/>')
    # fototranzistor
    tx = cx + 12
    wire([(tx, cy-9), (tx, cy+9)], wdth=2.0)
    wire([(tx, cy-4), (tx+12, cy-14), (tx+12, cy-16)], wdth=1.2)       # kolektor
    wire([(tx, cy+4), (tx+12, cy+14), (tx+12, cy+16)], wdth=1.2)       # emitor
    el.append(f'<polygon points="{tx+12},{cy+14} {tx+5},{cy+12} {tx+9},{cy+8}" fill="{BLK}"/>')
    return (lx, cy-16), (lx, cy+16), (tx+12, cy-16), (tx+12, cy+16)


# =============================================================================
# HLAVIČKA + LEGENDA
# =============================================================================
txt(W/2, 38, "ESP32 FVE diverter — RIADIACA ČASŤ, skutočná elektrotechnická schéma (STN/IEC značky)",
    fs=21, anchor="middle", bold=True)
txt(W/2, 62, "Nízke napätie 3,3 V / 5 V okolo ESP32 · platné od 2026-11-10 (nový pinout) · silová časť: "
    "fve_schema_realny · rozloženie pinov na doske: esp32_pinout_zapojenie",
    fs=11.5, anchor="middle", col=GREY)

lgx, lgy = 60, 96
rect(lgx, lgy, 640, 170, fill="#fafafa", stroke="#999", sw=1.2)
txt(lgx+12, lgy+20, "Legenda", fs=13, bold=True)
# bodka
wire([(lgx+20, lgy+42), (lgx+60, lgy+42)]); wire([(lgx+40, lgy+32), (lgx+40, lgy+52)]); dot(lgx+40, lgy+42)
txt(lgx+72, lgy+46, "bodka = vodiče SPOJENÉ", fs=10.5)
wire([(lgx+20, lgy+72), (lgx+60, lgy+72)]); wire([(lgx+40, lgy+62), (lgx+40, lgy+82)])
txt(lgx+72, lgy+76, "kríženie bez bodky = NESPOJENÉ", fs=10.5)
wire([(lgx+20, lgy+102), (lgx+40, lgy+102)], col=GREY); nc(lgx+40, lgy+102)
txt(lgx+72, lgy+106, "× = pin nezapojený", fs=10.5)
port(lgx+40, lgy+150, "+3V3", "up")
txt(lgx+72, lgy+140, "napájanie: všetky rovnaké značky sú jedna sieť", fs=10.5)
txt(lgx+72, lgy+154, "(+3V3 z ESP, +5V z Mean Wellu, GND spoločná)", fs=9.5, col=GREY, italic=True)
netlabel(lgx+430, lgy+42, "SDA", "right")
txt(lgx+490, lgy+46, "menovka siete —", fs=10.5)
txt(lgx+430, lgy+62, "rovnaké meno = spojené vodičom", fs=10.5)
rect(lgx+430, lgy+82, 26, 14); txt(lgx+464, lgy+94, "rezistor (IEC)", fs=10.5)
wire([(lgx+433, lgy+112), (lgx+453, lgy+112)], wdth=2.2); wire([(lgx+433, lgy+118), (lgx+453, lgy+118)], wdth=2.2)
txt(lgx+464, lgy+120, "kondenzátor", fs=10.5)
txt(lgx+430, lgy+146, "230 V vodiče/texty", fs=10.5, col=CAC, bold=True)

# =============================================================================
# U1 — ESP32-DevKitC (38-pin), piny v skutočnom poradí
# =============================================================================
EX0, EX1 = 1100, 1420
P0, PITCH = 300, 44
def py(i):
    return P0 + i*PITCH

LEFT = ["3V3", "EN", "GPIO36 (VP)", "GPIO39 (VN)", "GPIO34", "GPIO35", "GPIO32", "GPIO33",
        "GPIO25", "GPIO26", "GPIO27", "GPIO14", "GPIO12", "GND", "GPIO13",
        "GPIO9 (D2)", "GPIO10 (D3)", "GPIO11 (CMD)", "5V"]
RIGHT = ["GND", "GPIO23", "GPIO22", "GPIO1 (TX)", "GPIO3 (RX)", "GPIO21", "GND", "GPIO19",
         "GPIO18", "GPIO5", "GPIO17", "GPIO16", "GPIO4", "GPIO0", "GPIO2", "GPIO15",
         "GPIO8 (D1)", "GPIO7 (D0)", "GPIO6 (CLK)"]
rect(EX0, P0-42, EX1-EX0, 18*PITCH+84, fill="#e3f2fd", stroke=CNET, sw=2.2, rx=6)
txt((EX0+EX1)/2, P0-18, "U1  ESP32-DevKitC", fs=15, anchor="middle", bold=True, col=CNET)
txt((EX0+EX1)/2, P0+18*PITCH+32, "ESP32-WROOM-32 · 38-pin · pohľad zhora", fs=10, anchor="middle",
    col=CNET, italic=True)
LP, RP = {}, {}
for i, nm in enumerate(LEFT):
    y = py(i)
    wire([(EX0-40, y), (EX0, y)])
    txt(EX0+8, y+4, nm, fs=10.5, bold=nm.startswith("GPIO") or nm in ("3V3", "5V", "GND"))
    txt(EX0-4, y-4, str(i+1), fs=8, anchor="end", col=GREY)
    LP[nm] = (EX0-40, y)
for i, nm in enumerate(RIGHT):
    y = py(i)
    wire([(EX1, y), (EX1+40, y)])
    txt(EX1-8, y+4, nm, fs=10.5, anchor="end", bold=nm.startswith("GPIO") or nm == "GND")
    txt(EX1+4, y-4, str(i+1), fs=8, col=GREY)
    RP[nm] = (EX1+40, y)
txt(EX0-40, P0-30, "ľavý rad (J2)", fs=9, col=GREY, italic=True)
txt(EX1+40, P0-30, "pravý rad (J3)", fs=9, anchor="end", col=GREY, italic=True)

# --- nezapojené piny ---
for nm in ("EN", "GPIO12", "GPIO9 (D2)", "GPIO10 (D3)", "GPIO11 (CMD)"):
    nc(*LP[nm])
for nm in ("GPIO1 (TX)", "GPIO3 (RX)", "GPIO0", "GPIO8 (D1)", "GPIO7 (D0)", "GPIO6 (CLK)"):
    nc(*RP[nm])
x, y = LP["GPIO12"]; txt(x-10, y+4, "NEPOUŽÍVAŤ — strapping (1,8 V flash)", fs=9, anchor="end", col=CAC, italic=True)
x, y = LP["GPIO10 (D3)"]; txt(x-10, y+4, "interný flash — nepoužívať", fs=9, anchor="end", col=GREY, italic=True)
x, y = LP["EN"]; txt(x-10, y+4, "reset", fs=9, anchor="end", col=GREY, italic=True)
x, y = RP["GPIO5"]; wire([(x, y), (x+50, y)], col="#1b5e20"); netlabel(x+50, y, "OW_VRATNA", "right")
x, y = RP["GPIO4"]; wire([(x, y), (x+50, y)]); netlabel(x+50, y, "PRIETOK", "right")
x, y = RP["GPIO0"]; txt(x+10, y+4, "BOOT — nepoužívať", fs=9, col=GREY, italic=True)
x, y = RP["GPIO1 (TX)"]; txt(x+10, y+4, "USB UART", fs=9, col=GREY, italic=True)
x, y = RP["GPIO8 (D1)"]; txt(x+10, y+4, "GPIO6–8 interný flash", fs=9, col=GREY, italic=True)

# --- napájanie ESP ---
x, y = LP["3V3"]; wire([(x, y), (x-30, y)], col=C33); port(x-30, y, "+3V3", "left")
txt(x-80, y-14, "výstup stabilizátora ESP (zdroj pre celú +3V3 sieť)", fs=9, anchor="end", col=C33, italic=True)
x, y = LP["5V"]; wire([(x, y), (x-30, y)], col=C5); port(x-30, y, "+5V", "left")
txt(x-80, y+18, "napájanie ESP z Mean Wellu (vstup)", fs=9, anchor="end", col=C5, italic=True)
x, y = LP["GND"]; wire([(x, y), (x-24, y)], col=CG); ground(x-24, y)
for nm_y in (0, 6):
    x, y = RP["GND"] if nm_y == 0 else (EX1+40, py(6))
    wire([(x, y), (x+24, y)], col=CG); ground(x+24, y)

# --- GPIO13 → OneWire B3 (podlaha) ---
x, y = LP["GPIO13"]
wire([(x, y), (x-40, y)], col="#1b5e20"); netlabel(x-40, y, "OW_PODLAHA", "left")

# --- rbdimmer signály → menovky ---
for nm, net in (("GPIO36 (VP)", "TUV_TEMP"), ("GPIO39 (VN)", "TUV_CUR"), ("GPIO34", "POD_TEMP"),
                ("GPIO35", "POD_CUR"), ("GPIO32", "POD_FAN"), ("GPIO33", "TUV_FAN")):
    x, y = LP[nm]
    wire([(x, y), (x-24, y)])
    netlabel(x-24, y, net, "left")
txt(EX0-200, py(2)-20, "ADC1 vstupy (36/39/34/35 len vstup)", fs=9, anchor="middle", col=GREY, italic=True)

# =============================================================================
# A3 — relé modul ČERPADLÁ (GPIO25/26) a U4 — AC opto modul (GPIO27/14)
# =============================================================================
A3x, A3w = 660, 260
A3y = py(8) - 34
e = relay_module(A3x, A3y, A3w, py(9)+16-A3y, "A3", "relé 2-kan. ČERPADLÁ",
                 [(py(8), "IN1", "KA5", "COM ← L, NO → čerpadlo podlaha (230 V)"),
                  (py(9), "IN2", "KA6", "COM ← L, NO → čerpadlo TUV (230 V)")],
                 in_side="right", pwr_side="top")
x, y = LP["GPIO25"]; wire([(x, y), e["IN1"]])
x, y = LP["GPIO26"]; wire([(x, y), e["IN2"]])

U4x, U4y, U4w, U4h = 660, 724, 260, 100
rect(U4x, U4y, U4w, U4h, fill="#fce4ec", stroke=CAC, sw=1.8)
txt(U4x-22, U4y+U4h+4, "U4 — AC 230 V opto modul 2-kan.", fs=10.5,
    anchor="end", bold=True, col=CAC)
for (yy, outpin, gp, ac_txt, ch) in ((py(10), "OUT2", "GPIO27", ("← čerpadlo podlahy L", "← čerpadlo podlahy N"), "CH2"),
                                     (py(11), "OUT1", "GPIO14", ("← K3M cievka A1", "← K3M cievka A2"), "CH1")):
    cx, cy = U4x + 140, yy+4
    a, k, c_, e_ = opto_symbol(cx, cy)
    # AC vstup — dve svorky vľavo
    ya, yb = yy-11, yy+11
    wire([(U4x-16, ya), (U4x, ya)], col=CAC); wire([(U4x-16, yb), (U4x, yb)], col=CAC)
    txt(U4x+4, ya+3, "AC", fs=7.5, col=CAC)
    wire([(U4x, ya), (U4x+60, ya), (U4x+60, a[1]), a], col=CAC, wdth=1.2)
    wire([(U4x, yb), (U4x+70, yb), (U4x+70, k[1]), k], col=CAC, wdth=1.2)
    rect(U4x+22, ya-5, 22, 10, stroke=CAC, sw=1.2)          # predradný R na AC strane
    txt(U4x-22, ya+4, ac_txt[0], fs=9.5, anchor="end", col=CAC)
    txt(U4x-22, yb+4, ac_txt[1], fs=9.5, anchor="end", col=CAC)
    txt(cx-40, yy-2, ch, fs=8, anchor="end", col=GREY)
    # výstup: kolektor → OUT, emitor → GND modulu
    wire([c_, (c_[0], yy-6), (U4x+U4w, yy-6)], wdth=1.2)
    wire([e_, (c_[0]+18, e_[1])], wdth=1.2)
    txt(c_[0]+22, e_[1]+3, "GND", fs=7.5, col=CG)
    wire([(U4x+U4w, yy-6), (U4x+U4w+16, yy-6)])
    txt(U4x+U4w-4, yy-9, outpin, fs=8.5, anchor="end")
    x, y = LP[gp]
    wire([(x, y), (1010, y), (1010, yy-6), (U4x+U4w+16, yy-6)])
for xx, nm in ((U4x+70, "VCC"), (U4x+210, "GND")):
    e2 = pin_stub(xx, U4y+U4h, nm, "bottom", stub=12, fs=8.5)
    if nm == "VCC":
        port(e2[0], e2[1], "+3V3", "down")
    else:
        ground(e2[0], e2[1])
txt(U4x-22, U4y+U4h+20, "230 V — iba svorky AC vstupu!", fs=10, anchor="end", col=CAC, bold=True)
txt(U4x-22, U4y+U4h+38, "U4: výstup aktívny v LOW · VCC = 3,3 V (NIE 5 V — pull-up modulu by dal", fs=9, anchor="end", col=CAC, italic=True)
txt(U4x-22, U4y+U4h+50, "5 V na GPIO) · bez sériového rezistora", fs=9, anchor="end", col=CAC, italic=True)

# =============================================================================
# PRAVÁ STRANA — M1 ventilátor, DS18B20 zbernica, relé moduly A1/A2, I2C
# =============================================================================
# --- M1 ventilátor skrine (4-pin PWM) ---
M1x, M1y, M1w, M1h = 1720, 312, 190, 104
rect(M1x, M1y, M1w, M1h, fill="#e0f7fa", stroke="#00838f", sw=1.8)
el.append(f'<circle cx="{M1x+130}" cy="{M1y+52}" r="24" fill="#fff" stroke="{BLK}" stroke-width="1.6"/>')
txt(M1x+130, M1y+58, "M", fs=16, anchor="middle", bold=True)
txt(M1x+M1w/2, M1y-8, "M1 — ventilátor skrine 5 V, 4-pin PWM", fs=11.5, anchor="middle", bold=True, col="#006064")
pwm = pin_stub(M1x, py(1), "4 PWM", "left")
tach = pin_stub(M1x, py(2), "3 TACHO", "left")
x, y = RP["GPIO23"]; wire([(x, y), pwm])
x, y = RP["GPIO22"]; wire([(x, y), tach])
txt(1600, py(1)-6, "PWM 25 kHz", fs=9, anchor="middle", col=GREY, italic=True)
txt(1600, py(2)-6, "interný pull-up ESP (3,3 V)", fs=9, anchor="middle", col=GREY, italic=True)
v5 = pin_stub(M1x+M1w, M1y+30, "2 +5V", "right", stub=14)
port(v5[0], v5[1], "+5V", "right")
g1 = pin_stub(M1x+M1w, M1y+74, "1 GND", "right", stub=14)
wire([g1, (g1[0]+10, g1[1])], col=CG); ground(g1[0]+10, g1[1])

# --- OneWire: 3 samostatné zbernice (od 2026-11-14) — B1 G21+R1, B2 G5+R7, B3 G13+R8 ---
OWY = py(5)                   # 520 — DATA B1 (GPIO21)
GOW = "#1b5e20"
x, y = RP["GPIO21"]
wire([(x, y), (2050, OWY)], col=GOW, wdth=2.0)
R1x = 1560
res_v(R1x, OWY-74, OWY, "R1", "4,7 kΩ")
dot(R1x, OWY, col=GOW)
port(R1x, OWY-74, "+3V3", "up")
txt(R1x+78, OWY-36, "R1, R7, R8 v skrini pri ESP —", fs=9.5, col=GOW, bold=True)
txt(R1x+78, OWY-22, "každý DS18B20 vlastný pin + pull-up", fs=9.5, col=GOW, bold=True)
txt(2040, OWY-6, "OneWire G21", fs=9, anchor="end", col=GOW, italic=True)
GR, VR = OWY-50, OWY-25        # spoločné vodiče GND / VDD pre snímače
wire([(1975, GR), (2500, GR)], col=CG)
ground(1975, GR)
wire([(2010, VR), (2530, VR)], col=C33)
port(2530, VR, "+3V3", "right")
sensors = [(2050, "B1", "TUV bojler", None),
           (2250, "B2", "vratná voda TUV", ("OW_VRATNA", "R7")),
           (2450, "B3", "voda podlaha", ("OW_PODLAHA", "R8"))]
for cx, ref, lab, own in sensors:
    by = 312
    rect(cx-46, by, 92, 62, fill="#e8f5e9", stroke=GOW, sw=1.6)
    txt(cx, by+18, f"{ref} DS18B20", fs=10.5, anchor="middle", bold=True, col=GOW)
    txt(cx, by+32, lab, fs=8.5, anchor="middle", col=GOW, italic=True)
    for dx, pn, target, col in ((-28, "GND", GR, CG), (28, "VDD", VR, C33)):
        txt(cx+dx, by+56, pn, fs=7.5, anchor="middle", col=GREY)
        wire([(cx+dx, by+62), (cx+dx, target)], col=col)
        dot(cx+dx, target, r=2.8, col=col)
    txt(cx, by+56, "DQ", fs=7.5, anchor="middle", col=GREY)
    if own is None:
        wire([(cx, by+62), (cx, OWY)], col=GOW)
        dot(cx, OWY, r=2.8, col=GOW)
    else:
        net, rref = own
        yb = OWY + 25
        wire([(cx, by+62), (cx, yb), (cx+16, yb)], col=GOW)
        netlabel(cx+16, yb, net, "right")
        res_v(cx, yb, yb+60, rref, "4,7 kΩ", side="left", col=GOW)
        dot(cx, yb, r=2.8, col=GOW)
        port(cx, yb+60, "+3V3", "down")
txt(2050-46, 296, "káble: čierny GND · žltý DQ · červený VDD (farby over) — GND/VDD spoločné, DQ každý zvlášť", fs=9, col=GREY, italic=True)
txt(2215, OWY+156, "B4 (skriňa) zrušený — klony DS18B20 nejdú", fs=8.5, col=GREY, italic=True)
txt(2215, OWY+168, "po dvoch na zbernici a voľný pin už nie je.", fs=8.5, col=GREY, italic=True)

# --- A2 relé modul PODLAHA (GPIO19/18) ---
A2x, A2w = 1700, 250
A2y = py(7) - 34
e = relay_module(A2x, A2y, A2w, py(8)+16-A2y, "A2", "relé 2-kan. PODLAHA",
                 [(py(7), "IN1", "KA3", "COM ← L, NO → cievka K3 izolačný podlaha"),
                  (py(8), "IN2", "KA4", "COM ← L, NO → cievka K4 BYPASS podlaha")],
                 in_side="left", pwr_side="top")
x, y = RP["GPIO19"]; wire([(x, y), e["IN1"]])
x, y = RP["GPIO18"]; wire([(x, y), e["IN2"]])

# --- A1 relé modul TUV (GPIO17/16) ---
A1x, A1w = 1700, 250
A1y = py(10) - 46
e = relay_module(A1x, A1y, A1w, py(11)+34-A1y, "A1", "relé 2-kan. TUV",
                 [(py(10), "IN1", "KA1", "COM ← L, NO → cievka K1 izolačný TUV"),
                  (py(11), "IN2", "KA2", "COM ← L, NO → cievka K2 BYPASS TUV")],
                 in_side="left", pwr_side="bottom")
x, y = RP["GPIO17"]; wire([(x, y), e["IN1"]])
x, y = RP["GPIO16"]; wire([(x, y), e["IN2"]])

# --- I2C pull-upy R2/R3 + menovky SDA/SCL ---
x, y = RP["GPIO2"]
wire([(x, y), (1690, y)]); netlabel(1690, y, "SDA", "right")
R2x = 1600
res_v(R2x, y-50, y, "R2", "4,7 kΩ"); dot(R2x, y); port(R2x, y-50, "+3V3", "up")
x, y = RP["GPIO15"]
wire([(x, y), (1690, y)]); netlabel(1690, y, "SCL", "right")
R3x = 1650
res_v(R3x, y, y+60, "R3", "4,7 kΩ"); dot(R3x, y); port(R3x, y+60, "+3V3", "down")
txt(1760, py(14)+4+18, "I2C → U2 DimmerLink1 (0x50) + U3 DimmerLink2 (0x51)", fs=9.5, col=CNET, italic=True)
txt(1760, py(15)+22, "R2/R3 JEDEN pár pre celú zbernicu", fs=9.5, col=CNET, bold=True)

# --- B5 snímač prietoku (Hall, 3-vodičový, z TECH EU-11) + R6 ---
B5x, B5y, B5w, B5h = 2170, 945, 250, 100
rect(B5x, B5y, B5w, B5h, fill="#e1f5fe", stroke="#01579b", sw=1.8)
txt(B5x+B5w/2+30, B5y+40, "B5 snímač prietoku", fs=11.5, anchor="middle", bold=True, col="#01579b")
txt(B5x+B5w/2+30, B5y+56, "Hall, 3 vodiče (z TECH EU-11)", fs=9, anchor="middle", col="#01579b", italic=True)
txt(B5x+B5w/2+30, B5y+70, "studená voda → zásobník TUV", fs=9, anchor="middle", col="#01579b", italic=True)
vcc5 = pin_stub(B5x+50, B5y, "VCC červený", "top")
port(vcc5[0], vcc5[1], "+3V3", "up")
out5 = pin_stub(B5x, B5y+B5h/2, "OUT žltý", "left")
gnd5 = pin_stub(B5x+50, B5y+B5h, "GND čierny", "bottom")
ground(*gnd5)
R6x = 2100
wire([out5, (2050, out5[1])])
netlabel(2050, out5[1], "PRIETOK", "left")
res_v(R6x, out5[1]-70, out5[1], "R6", "4,7 kΩ", side="left")
dot(R6x, out5[1]); port(R6x, out5[1]-70, "+3V3", "up")
txt(2000, 1100, "Napájanie z +3V3 → na GPIO4 nikdy viac ako 3,3 V, dióda netreba (pri akomkoľvek výstupe snímača).", fs=9, col="#01579b", bold=True)
txt(2000, 1114, "R6 v skrini pri ESP. Ak snímač pri 3,3 V nepulzuje: postup v Zásadách zapojenia (5 V len po meraní / s diódou).", fs=9, col=GREY, italic=True)

# =============================================================================
# DIMMERY — U2/U3 DimmerLink + D1/D2 rbdimmer 40A-CS (signálová časť)
# =============================================================================
DY = 1190
txt(60, DY, "DIMMERY — signálová časť (silové svorky AC IN / LOAD / N rbdimmerov: viď fve_schema_realny)",
    fs=14, bold=True, col=CNET)
wire([(60, DY+8), (1300, DY+8)], col=CNET, wdth=1.2)

def dimmer_branch(ox, ul_ref, addr, d_ref, label, nets, r_ntc):
    by0 = DY + 92
    pins_y = [by0+30, by0+70, by0+110, by0+150]
    # DimmerLink
    Ux, Uw = ox+120, 160
    rect(Ux, by0, Uw, 180, fill="#e3f2fd", stroke=CNET, sw=1.8)
    txt(Ux+Uw/2, by0-10, f"{ul_ref} DimmerLink {addr}", fs=11.5, anchor="middle", bold=True, col=CNET)
    l_names = ["VCC", "TX/SDA", "RX/SCL", "GND"]
    r_names = ["VCC", "GND", "Z-C", "DIM"]
    lend = {n: pin_stub(Ux, yy, n, "left") for n, yy in zip(l_names, pins_y)}
    rend = {n: pin_stub(Ux+Uw, yy, n, "right") for n, yy in zip(r_names, pins_y)}
    port(*lend["VCC"], "+3V3", "left")
    wire([lend["TX/SDA"], (lend["TX/SDA"][0]-14, pins_y[1])]); netlabel(lend["TX/SDA"][0]-14, pins_y[1], "SDA", "left")
    wire([lend["RX/SCL"], (lend["RX/SCL"][0]-14, pins_y[2])]); netlabel(lend["RX/SCL"][0]-14, pins_y[2], "SCL", "left")
    gx = lend["GND"][0]-14
    wire([lend["GND"], (gx, pins_y[3])], col=CG); ground(gx, pins_y[3])
    # rbdimmer
    Dx, Dw = ox+370, 150
    rect(Dx, by0, Dw, 180, fill="#fff3e0", stroke="#e65100", sw=1.8)
    txt(Dx+Dw/2, by0-10, f"{d_ref} rbdimmer 40A-CS", fs=11.5, anchor="middle", bold=True, col="#bf360c")
    dl_names = ["VCC", "GND", "Z-C", "DIM"]
    dr_names = ["TEMP", "CUR-S", "FAN", "5V"]
    dl = {n: pin_stub(Dx, yy, n, "left") for n, yy in zip(dl_names, pins_y)}
    dr = {n: pin_stub(Dx+Dw, yy, n, "right") for n, yy in zip(dr_names, pins_y)}
    for n in dl_names:
        wire([rend[n], dl[n]])
    # C 100 nF tesne pri DimmerLinku (VCC–GND)
    cx = Ux+Uw+30
    dot(cx, pins_y[0]); dot(cx, pins_y[1])
    cap_v(cx, pins_y[0], pins_y[1], nets[3], "100 nF")
    for n, net in zip(dr_names[:3], nets[:3]):
        wire([dr[n], (dr[n][0]+44, dr[n][1])])
        netlabel(dr[n][0]+44, dr[n][1], net, "right")
    # Pull-up NTC — POTVRDENÉ meraním 2026-11-13: TEMP–GND = 10,87 kΩ bez
    # napájania (holý NTC 10 kΩ B3950, ~23 °C) → doska delič nemá, R4/R5 treba.
    rx = dr["TEMP"][0] + 22
    ty = dr["TEMP"][1]
    res_v(rx, ty-62, ty, r_ntc, "10 kΩ")
    dot(rx, ty)
    port(rx, ty-62, "+3V3", "up")
    port(*dr["5V"], "+5V", "right")
    txt(Dx+Dw/2, by0+200, label, fs=10, anchor="middle", col=GREY, italic=True)
    txt(Ux+Uw/2, by0+200, "4 vodiče k rbdimmeru, samostatne", fs=9, anchor="middle", col=GREY, italic=True)

dimmer_branch(40, "U2", "0x50", "D1", "TUV 3 kW (L1)", ("TUV_TEMP", "TUV_CUR", "TUV_FAN", "C1"), "R4")
dimmer_branch(680, "U3", "0x51", "D2", "podlaha 600 W (L2)", ("POD_TEMP", "POD_CUR", "POD_FAN", "C2"), "R5")
_nl = [
    ("⚠ TEMP a CUR-S NEPRIPÁJAŤ na ESP, kým nie sú zmerané (výrobca napätie neuvádza) — postup: docs/MERANIE_rbdimmer.md; TODO_fve_diverter.md.", CAC, True),
    ("TEMP = holý NTC 10 kΩ B3950 na chladiči (zmerané 2026-11-13: TEMP–GND 10,87 kΩ pri ~23 °C, doska delič NEMÁ)", BLK, False),
    ("   → R4/R5 10 kΩ z TEMP na +3V3 POVINNÉ (delič: ~1,65 V pri 25 °C, ~0,6 V pri 60 °C — vždy pod 3,3 V).", BLK, False),
    ("CUR-S: typ snímača neznámy (doska má trimer CURRENT SENSOR ADJUSTMENT). Ak je výstup okolo polovice napájania (Hall/ACS),", CAC, False),
    ("   treba v ESPHome ct_clamp (RMS), nie bežné ADC; ak by bol napájaný z 5 V pinu, môže prekročiť 3,3 V → delič.", CAC, False),
    ("FAN = logický vstup (aktívny HIGH), ventilátor dosky spína tranzistor na doske; pin 5V = samostatné napájanie ventilátora z +5V.", GREY, False),
    ("U3: pred spojením zbernice prestaviť adresu 0x50 → 0x51 (sám na zbernici).", GREY, False),
]
for i, (t_, c_, b_) in enumerate(_nl):
    txt(60, DY+322+i*16, t_, fs=10, col=c_, bold=b_)

# =============================================================================
# PS1 — Mean Well MDR-20-5
# =============================================================================
PSx, PSy, PSw, PSh = 160, 1680, 200, 110
rect(PSx, PSy, PSw, PSh, fill="#eeeeee", stroke="#424242", sw=1.8)
txt(PSx+PSw/2, PSy-10, "PS1 Mean Well MDR-20-5", fs=11.5, anchor="middle", bold=True)
txt(PSx+PSw/2, PSy+PSh/2-4, "AC/DC", fs=12, anchor="middle", bold=True, col=GREY)
txt(PSx+PSw/2, PSy+PSh/2+12, "5 V / 3 A · DIN", fs=9.5, anchor="middle", col=GREY)
l_ = pin_stub(PSx, PSy+35, "L", "left"); n_ = pin_stub(PSx, PSy+75, "N", "left")
wire([l_, (l_[0]-40, l_[1])], col=CAC); wire([n_, (n_[0]-40, n_[1])], col=CAC)
txt(l_[0]-44, l_[1]+4, "L", fs=10, anchor="end", col=CAC, bold=True)
txt(n_[0]-44, n_[1]+4, "N", fs=10, anchor="end", col=CAC, bold=True)
txt(PSx-50, PSy+PSh+20, "230 V z ističa logiky (viď fve_schema_realny)", fs=9, col=CAC, italic=True)
vp = pin_stub(PSx+PSw, PSy+35, "+V", "right"); vm = pin_stub(PSx+PSw, PSy+75, "−V", "right")
port(*vp, "+5V", "right")
wire([vm, (vm[0]+14, vm[1])], col=CG); ground(vm[0]+14, vm[1])
txt(PSx+PSw+80, PSy+20, "+5V odberatelia: ESP (5V pin), JD-VCC A1–A3 (6 cievok relé),", fs=9.5, col=C5)
txt(PSx+PSw+80, PSy+34, "M1 ventilátor skrine, 5V pin D1 a D2 (ventilátory dosiek).", fs=9.5, col=C5)
txt(PSx+PSw+80, PSy+56, "+3V3 (z ESP) odberatelia: VCC relé modulov, U2/U3, U4,", fs=9.5, col=C33)
txt(PSx+PSw+80, PSy+70, "B1–B3, B5, pull-upy R1–R3, R6–R8 — spolu desiatky mA, cievky relé NIE.", fs=9.5, col=C33)
txt(PSx+PSw+80, PSy+92, "GND: jedna spoločná zem (ESP, Mean Well −V, všetky moduly).", fs=9.5, col=CG)

# =============================================================================
# ZOZNAM SÚČIASTOK
# =============================================================================
BX, BY = 1480, 1150
rows = [
    ("U1", "ESP32-DevKitC (WROOM-32)", "38-pin; napájanie 5V pin; 3V3 = výstup"),
    ("U2", "DimmerLink 2CH", "I2C 0x50, kanál 1 (DIM0) → D1 (TUV)"),
    ("U3", "DimmerLink 2CH", "I2C 0x51, kanál 1 (DIM0) → D2 (podlaha)"),
    ("U4", "AC 230 V opto modul 2-kan.", "CH1 K3M → GPIO14, CH2 čerp. → GPIO27; VCC 3,3 V"),
    ("D1, D2", "rbdimmer 40A-CS", "TUV / podlaha; silová časť vo fve_schema_realny"),
    ("A1", "relé modul 2-kan. (JD-VCC)", "KA1 GPIO17 → K1, KA2 GPIO16 → K2 (TUV)"),
    ("A2", "relé modul 2-kan. (JD-VCC)", "KA3 GPIO19 → K3, KA4 GPIO18 → K4 (podlaha)"),
    ("A3", "relé modul 2-kan. (JD-VCC)", "KA5 GPIO25 čerp. podlaha, KA6 GPIO26 čerp. TUV"),
    ("B1–B3", "DS18B20 (vodotesný)", "B1 bojler G21 · B2 vratná G5 · B3 podlaha G13"),
    ("R1", "rezistor 4,7 kΩ 0,25 W", "OneWire pull-up GPIO21 (B1) → +3V3"),
    ("R7, R8", "rezistor 4,7 kΩ 0,25 W", "OneWire pull-up GPIO5 (B2), GPIO13 (B3) → +3V3"),
    ("R2, R3", "rezistor 4,7 kΩ 0,25 W", "I2C pull-up SDA (GPIO2), SCL (GPIO15) → +3V3"),
    ("C1, C2", "kondenzátor 100 nF keram.", "VCC–GND tesne pri U2 / U3"),
    ("M1", "ventilátor 5 V 4-pin PWM", "PWM GPIO23, tacho GPIO22"),
    ("PS1", "Mean Well MDR-20-5", "230 V AC → 5 V / 3 A, DIN"),
    ("R4, R5", "rezistor 10 kΩ 0,25 W", "NTC pull-up TEMP D1/D2 → +3V3 (holý NTC, zmerané)"),
    ("B5", "snímač prietoku Hall 3-vod.", "z TECH EU-11; VCC +3V3, OUT → GPIO4 (PRIETOK)"),
    ("R6", "rezistor 4,7 kΩ 0,25 W", "pull-up OUT B5 (GPIO4) → +3V3"),
]
cw = [90, 280, 420]
rect(BX, BY, sum(cw), 26 + 22*len(rows), fill="#fff", stroke="#999", sw=1.2)
txt(BX+8, BY-10, "Zoznam súčiastok (riadiaca časť)", fs=13, bold=True)
hx = BX
for w_, h_ in zip(cw, ("Ozn.", "Súčiastka", "Poznámka")):
    txt(hx+8, BY+18, h_, fs=10.5, bold=True)
    hx += w_
wire([(BX, BY+26), (BX+sum(cw), BY+26)], col="#999", wdth=1)
for i, r in enumerate(rows):
    yy = BY + 26 + 22*(i+1) - 7
    hx = BX
    for j, (w_, c) in enumerate(zip(cw, r)):
        txt(hx+8, yy, c, fs=10, bold=(j == 0))
        hx += w_

# =============================================================================
# POZNÁMKY
# =============================================================================
NX, NY = 1480, 1600
notes = [
    ("Zásady zapojenia", True, BLK),
    ("• Relé moduly A1–A3: jumper JD-VCC VYBRATÝ — VCC = +3V3 (strana optočlena), JD-VCC = +5V (cievky). Vstup aktívny v LOW.", False, BLK),
    ("• Kontakty KA1–KA4 spínajú len ovládacie 230 V cievok stykačov K1–K4; KA5/KA6 spínajú L čerpadiel (do 230 V / 10 A).", False, CAC),
    ("• Pull-upy: spolu 6 ks 4,7 kΩ — R1/R7/R8 (OneWire), R2/R3 (I2C), R6 (prietok). Všetky na +3V3, nikdy na 5 V.", False, BLK),
    ("• U4: AC strana (230 V) a DC strana (3,3 V) fyzicky oddelené, AC vodiče mimo signálových káblov.", False, CAC),
    ("• I2C káble čo najkratšie (< 30 cm), C1/C2 100 nF priamo na svorkách U2/U3.", False, BLK),
    ("• GPIO12 nezapájať (strapping — ESP by nenaštartoval). GPIO6–11 = interný flash.", False, BLK),
    ("• B5 prietok: napájať z +3V3 (EU-11 dával 12 V, Hall väčšinou ide aj na 3,3 V). Ak pri tečúcej vode nepulzuje:", False, BLK),
    ("   napájaj z +5V, žltý ODPOJ od ESP a zmeraj voči GND pri tečúcej vode: stále ~0 V → zapoj ako je, OK;", False, CAC),
    ("   ukáže 2–5 V (snímač má vlastný pull-up) → treba dióda BAT85/1N4148 do žltého (katóda k snímaču, anóda ku GPIO4).", False, CAC),
]
for i, (s, b, c) in enumerate(notes):
    txt(NX, NY + i*20, s, fs=11 if not b else 13, bold=b, col=c)

# Popisové pole
TBx, TBy = 1480, 1840
rect(TBx, TBy, 790, 90, fill="#fafafa", stroke="#999", sw=1.2)
txt(TBx+12, TBy+24, "FVE diverter — ESP32 riadiaca časť", fs=13, bold=True)
txt(TBx+12, TBy+46, "Súbor: docs/schematics/esp32_schema_realny.svg · generátor gen_esp32_schema_realny.py", fs=10, col=GREY)
txt(TBx+12, TBy+64, "Platné od 2026-11-10 (pinout) · revízia 2026-11-14 (B5 prietok + R6, DS18B20 každý vlastný pin R7/R8)", fs=10, col=GREY)
txt(TBx+12, TBy+82, "Súvisí: esp32_pinout_zapojenie.png · fve_schema_realny.svg · esp32-fve-diverter/fve-diverter.yaml", fs=10, col=GREY)

# =============================================================================
here = os.path.dirname(os.path.abspath(__file__))
svg = os.path.join(here, "esp32_schema_realny.svg")
with open(svg, "w") as f:
    f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">\n')
    f.write(f'<rect width="{W}" height="{H}" fill="#ffffff"/>\n')
    f.write("\n".join(el))
    f.write("\n</svg>\n")
print("SVG zapísané:", svg)
if shutil.which("rsvg-convert"):
    png = svg[:-4] + ".png"
    subprocess.run(["rsvg-convert", "-o", png, svg], check=True)
    print("PNG zapísané:", png)
