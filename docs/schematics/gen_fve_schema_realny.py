#!/usr/bin/env python3
# KOMPLETNÁ skutočná elektrotechnická schéma (STN/IEC značky) — silová časť.
# Nahrádza fve_schema_tuv_vzor.svg (bol to len vzor jednej vetvy na schválenie
# štýlu). fve_schema_silovy.svg (blokový/funkčný pohľad) ostáva nezmenená.
#
# Opravy oproti vzoru (podľa spätnej väzby 2026-09-21):
#  1) rbdimmer 40A-CS NEMÁ AC-IN-N/AC-OUT-N — len "AC IN" a "LOAD" (jeden
#     silový vodič, L, cez TRIAC). Modul má navyše tenký vodič "N", ktorého
#     účel nie je istý (pravdepodobne len referencia/napájanie elektroniky
#     modulu) — podľa používateľa sa zapája asi len do N svorkovnice, NEnesie
#     záťažový prúd. Kreslené ako samostatná tenká odbočka z N vodiča, NIE
#     ako vstup/výstup v sérii so záťažou.
#  2) N teraz vedie MIMO dimmera (súbežne vedľa neho), nie cezeň — preto sa
#     už nekrižuje/neprekrýva s L pod dimmerom ako vo vzore.
#  3) Doplnená podlahová vetva (identická topológia ako TUV, iné hodnoty) a
#     čerpadlá + PSU.
#
# Konvencie (rovnaké ako vo vzore):
#  - kríženie čiar BEZ bodky = nespojené; bodka = spojené.
#  - PE je spoločná ochranná zbernica — kreslená ako zemniace značky (⏚) v
#    každom bode, nie ako jedna dlhá čiara cez celé plátno.
#  - Číslovanie X1/X2 svoriek je ROVNAKÉ ako v fve_schema_silovy.svg (1-6
#    vstup, 7-14 výstup), aby boli obe schémy vzájomne čitateľné.

import os
import shutil
import subprocess

W = 2860
el = []

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, s, fs=12, anchor="start", col="#111", bold=False, italic=False):
    w = ' font-weight="bold"' if bold else ''
    i = ' font-style="italic"' if italic else ''
    el.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{fs}" '
              f'fill="{col}"{w}{i}>{esc(s)}</text>')

def wire(pts, col="#111", wdth=1.6, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    p = " ".join(f"{x},{y}" for x, y in pts)
    el.append(f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="{wdth}"{d}/>')

def dot(x, y, r=3, col="#111"):
    el.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')

def rect(x, y, w, h, fill="#ffffff", stroke="#111", sw=1.6, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

def breaker(x, y0, y1, label="", rating="", label_x=None):
    wire([(x, y0), (x, y1)])
    mid = (y0 + y1) / 2
    rect(x-6, mid-9, 12, 18, fill="#fff")
    lx = label_x if label_x is not None else x+16
    if label:
        txt(lx, mid-4, label, fs=11, bold=True)
    if rating:
        txt(lx, mid+11, rating, fs=9.5, col="#555", italic=True)

def rcd_box(xs, y0, y1, label, sub, label_x):
    rect(min(xs)-26, y0, (max(xs)-min(xs))+52, y1-y0, fill="#ffffff")
    for x in xs:
        wire([(x, y0), (x, y1)])
    cx = sum(xs)/len(xs)
    cy = (y0+y1)/2
    el.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="#fff" stroke="#111" stroke-width="1.4"/>')
    txt(cx, cy+5, "Δ", fs=15, anchor="middle", bold=True)
    txt(label_x, y0+18, label, fs=11.5, bold=True)
    txt(label_x, y0+34, sub, fs=9.5, col="#555", italic=True)

def no_contact(x, y0, y1, num_top, num_bot):
    stub = 14
    wire([(x, y0), (x, y0+stub)])
    wire([(x, y1-stub), (x, y1)])
    wire([(x-6, y0+stub), (x+6, y0+stub)])
    wire([(x-6, y1-stub), (x+6, y1-stub)])
    wire([(x-5, y0+stub), (x+9, y1-stub)], wdth=2.0)
    if num_top:
        txt(x-12, y0+2, num_top, fs=10.5, anchor="end", bold=True)
    if num_bot:
        txt(x-12, y1+2, num_bot, fs=10.5, anchor="end", bold=True)

def coil(cx, y0, h, device, gpio_note):
    w = 34
    rect(cx-w/2, y0, w, h)
    txt(cx, y0+h/2+4, device, fs=12, anchor="middle", bold=True)
    txt(cx-w/2-6, y0-4, "A1", fs=9.5, anchor="end", col="#555")
    txt(cx-w/2-6, y0+h+12, "A2", fs=9.5, anchor="end", col="#555")
    if gpio_note:
        txt(cx+w/2+8, y0+h/2+4, gpio_note, fs=9.5, col="#555", italic=True)
    return (cx, y0), (cx, y0+h)

def terminal(x, y, num, side="right", block=""):
    dot(x, y, r=3.2)
    if side == "right":
        txt(x+8, y+4, num, fs=10, bold=True)
    else:
        txt(x-8, y+4, num, fs=10, anchor="end", bold=True)
    if block:
        txt(x, y-14, block, fs=9, anchor="middle", col="#555", italic=True)

def ic_block(x, y, w, h, title, sub, pins_top=None, pins_bottom=None, pins_left=None, pins_right=None):
    rect(x, y, w, h)
    txt(x+w/2, y+18, title, fs=12, anchor="middle", bold=True)
    if sub:
        txt(x+w/2, y+33, sub, fs=9.5, anchor="middle", col="#555", italic=True)
    stub = 16
    result = {}
    def place(pins, side):
        n = len(pins)
        for i, label in enumerate(pins):
            if side in ("top", "bottom"):
                px = x + w*(i+1)/(n+1)
                if side == "top":
                    wire([(px, y-stub), (px, y)])
                    txt(px, y-stub-4, label, fs=9, anchor="middle")
                    result[label] = (px, y-stub)
                else:
                    wire([(px, y+h), (px, y+h+stub)])
                    txt(px, y+h+stub+11, label, fs=9, anchor="middle")
                    result[label] = (px, y+h+stub)
            else:
                py = y + h*(i+1)/(n+1)
                if side == "left":
                    wire([(x-stub, py), (x, py)])
                    txt(x-stub-4, py+3, label, fs=9, anchor="end")
                    result[label] = (x-stub, py)
                else:
                    wire([(x+w, py), (x+w+stub, py)])
                    txt(x+w+stub+4, py+3, label, fs=9, anchor="start")
                    result[label] = (x+w+stub, py)
    if pins_top: place(pins_top, "top")
    if pins_bottom: place(pins_bottom, "bottom")
    if pins_left: place(pins_left, "left")
    if pins_right: place(pins_right, "right")
    return result

def ground(x, y, label=""):
    wire([(x, y), (x, y+10)])
    for i, wid in enumerate((14, 9, 4)):
        yy = y+10+i*5
        wire([(x-wid/2, yy), (x+wid/2, yy)], wdth=1.8, col="#2e7d32")
    if label:
        txt(x+12, y+16, label, fs=9, col="#2e7d32", italic=True)

def heater(cx, y, w, h, label, sub):
    rect(cx-w/2, y, w, h)
    zx0, zx1 = cx-w/2+14, cx+w/2-14
    n = 6
    pts = [(zx0, y+h/2)]
    for i in range(1, n):
        pts.append((zx0 + (zx1-zx0)*i/n, y+h/2 + (14 if i % 2 else -14)))
    pts.append((zx1, y+h/2))
    wire(pts, wdth=1.8)
    txt(cx, y+h+18, label, fs=12, anchor="middle", bold=True)
    txt(cx, y+h+34, sub, fs=9.5, anchor="middle", col="#555", italic=True)

def motor(cx, y, r, label, sub):
    el.append(f'<circle cx="{cx}" cy="{y+r}" r="{r}" fill="#fff" stroke="#111" stroke-width="1.6"/>')
    txt(cx, y+r+5, "M", fs=15, anchor="middle", bold=True)
    txt(cx, y+2*r+18, label, fs=11.5, anchor="middle", bold=True)
    txt(cx, y+2*r+33, sub, fs=9.5, anchor="middle", col="#555", italic=True)

# ============================================================
txt(W/2, 32, "FVE diverter — SILOVÁ ČASŤ, skutočná elektrotechnická schéma (STN/IEC značky)", fs=20, anchor="middle", bold=True)
txt(W/2, 54, "Kompletná — TUV + podlaha + čerpadlá/logika · číslovanie X1/X2 zhodné s fve_schema_silovy.svg (tá ostáva ako blokový pohľad)",
    fs=11.5, anchor="middle", col="#555")

ox_tuv, ox_pod, ox_pump = 260, 1110, 1970
Y0 = 92

# --- hlavný istič + RCD (spoločné pre všetky tri vetvy: L1 TUV, L2 podlaha, L3 logika+čerpadlá) ---
Nx_tuv = ox_tuv + 100
Nmain_x = Nx_tuv
txt(ox_tuv, Y0-8, "L1", fs=10.5, anchor="middle", col="#555")
txt(ox_pod, Y0-8, "L2", fs=10.5, anchor="middle", col="#555")
txt(ox_pump, Y0-8, "L3", fs=10.5, anchor="middle", col="#555")
txt(Nmain_x, Y0-8, "N", fs=10.5, anchor="middle", col="#555")
for x in (ox_tuv, ox_pod, ox_pump, Nmain_x):
    wire([(x, Y0), (x, Y0+60)])
y2 = Y0 + 60
breaker(ox_tuv, y2, y2+64, "Hlavný istič", "3F, L1+L2+L3+N (spoločný)", label_x=(ox_tuv+ox_pod)/2-60)
breaker(ox_pod, y2, y2+64)
breaker(ox_pump, y2, y2+64)
breaker(Nmain_x, y2, y2+64)
y3 = y2 + 64
rcd_box((ox_tuv, ox_pod, ox_pump, Nmain_x), y3+18, y3+82, "RCD 25 A / 30 mA / Typ A",
        "4-pól: L1+L2+L3+N", label_x=(ox_tuv+ox_pod)/2-60)
y4 = y3 + 82

# N-bus spoločný — odbočuje LEN N (nikdy L), a robí to PRED ističmi, aby sa
# vizuálne nedalo zameniť za odbočku do L1/L2/L3. Každá fáza L1/L2/L3
# pokračuje rovno, nezávisle, priamo z RCD do svojho vlastného ističa.
NBUS_Y = y4 + 15
Nx_pod, Nx_pump = ox_pod+100, ox_pump+100
wire([(Nmain_x, y4), (Nmain_x, NBUS_Y), (Nx_pump, NBUS_Y)])
dot(Nmain_x, NBUS_Y)
dot(Nx_pod, NBUS_Y)
FA_Y0 = y4 + 30
wire([(Nx_pod, NBUS_Y), (Nx_pod, FA_Y0)])
wire([(Nx_pump, NBUS_Y), (Nx_pump, FA_Y0)])
for x in (ox_tuv, ox_pod, ox_pump):
    wire([(x, y4), (x, FA_Y0)])

breaker(ox_tuv, FA_Y0, FA_Y0+64, "FA1 — B16", "TUV / L1", label_x=ox_tuv-150)
wire([(Nx_tuv, FA_Y0), (Nx_tuv, FA_Y0+64)])
breaker(ox_pod, FA_Y0, FA_Y0+64, "FA2 — B6", "podlaha / L2", label_x=ox_pod-150)
wire([(Nx_pod, FA_Y0), (Nx_pod, FA_Y0+64)])
breaker(ox_pump, FA_Y0, FA_Y0+64, "FA3 — B6", "logika + čerpadlá / L3", label_x=ox_pump+150)
wire([(Nx_pump, FA_Y0), (Nx_pump, FA_Y0+64)])
y4 = FA_Y0

Y_TUV0 = y4+64
Y_POD0 = y4+64
Y_PUMP0 = y4+64

# ============================================================
def heating_branch(ox, start_y, x1n_l, x1n_n, x2n_l, x2n_n,
                    kiso, kbyp, gpio_iso, gpio_byp,
                    emi_name, emi_model,
                    dl_name, dl_addr,
                    load_title, load_sub, cable_spec):
    Nx = ox + 100
    RELx1 = ox + 200
    Nfeed1_x = ox - 50
    BYPLx, BYPNx = ox + 420, ox + 520
    RELx2 = ox + 600
    Nfeed2_x = ox + 350

    terminal(ox, start_y+26, x1n_l, block="X1")
    terminal(Nx, start_y+26, x1n_n)
    ground(Nx+50, start_y+26, "PE (z hlavného rozvádzača)")
    wire([(ox, start_y), (ox, start_y+26)])
    wire([(Nx, start_y), (Nx, start_y+26)])
    y6 = start_y + 26

    BUS_L_y, BUS_N_y = y6+36, y6+48
    wire([(ox, y6), (ox, BUS_L_y)])
    wire([(Nx, y6), (Nx, BUS_N_y)])
    wire([(ox, BUS_L_y), (BYPLx, BUS_L_y)])
    wire([(Nx, BUS_N_y), (BYPNx, BUS_N_y)])
    for px in (ox, BYPLx):
        dot(px, BUS_L_y)
    for px in (Nx, BYPNx):
        dot(px, BUS_N_y)
    txt((ox+BYPLx)/2, BUS_L_y-6, "L-bus", fs=9, anchor="middle", col="#555", italic=True)
    txt((Nx+BYPNx)/2, BUS_N_y+15, "N-bus", fs=9, anchor="middle", col="#555", italic=True)

    CY0 = BUS_N_y + 34
    CH = 60
    no_contact(ox, CY0, CY0+CH, "1", "2")
    no_contact(Nx, CY0, CY0+CH, "3", "4")
    wire([(ox, BUS_L_y), (ox, CY0)])
    wire([(Nx, BUS_N_y), (Nx, CY0)])
    midx = (ox+Nx)/2
    wire([(ox, CY0+CH/2), (Nx, CY0+CH/2)], dash="4,3", wdth=1.1, col="#777")
    txt(midx, CY0-18, f"IZOLAČNÝ STYKAČ {kiso}", fs=10, anchor="middle", col="#555", italic=True)

    COIL1_y0 = CY0 + CH + 26
    wire([(midx, CY0+CH/2), (midx, COIL1_y0-6)], dash="4,3", wdth=1.1, col="#777")
    coil1_top, coil1_bot = coil(midx, COIL1_y0, 38, kiso, f"25A, 2-pól ◄ relé {gpio_iso}")

    wire([(ox, BUS_L_y), (RELx1, BUS_L_y)])
    dot(ox, BUS_L_y)
    wire([(RELx1, BUS_L_y), (RELx1, BUS_L_y+30)])
    no_contact(RELx1, BUS_L_y+30, BUS_L_y+70, "", "")
    txt(RELx1+14, BUS_L_y+55, f"relé ◄ {gpio_iso}", fs=9.5, col="#555", italic=True)
    txt(RELx1+14, BUS_L_y+68, "(riadenie mimo tejto schémy)", fs=8.5, col="#777", italic=True)
    safe_y = CY0 + CH + 12
    wire([(RELx1, BUS_L_y+70), (RELx1, safe_y), (coil1_top[0], safe_y), (coil1_top[0], coil1_top[1])])

    wire([(Nx, BUS_N_y), (Nfeed1_x, BUS_N_y)])
    dot(Nx, BUS_N_y)
    wire([(Nfeed1_x, BUS_N_y), (Nfeed1_x, coil1_bot[1]), (coil1_bot[0], coil1_bot[1])])

    y7 = CY0 + CH

    no_contact(BYPLx, CY0, CY0+CH, "1", "2")
    no_contact(BYPNx, CY0, CY0+CH, "3", "4")
    wire([(BYPLx, BUS_L_y), (BYPLx, CY0)])
    wire([(BYPNx, BUS_N_y), (BYPNx, CY0)])
    bmidx = (BYPLx+BYPNx)/2
    wire([(BYPLx, CY0+CH/2), (BYPNx, CY0+CH/2)], dash="4,3", wdth=1.1, col="#777")
    txt(bmidx, CY0-18, f"BYPASS {kbyp} (paral. k celej vetve)", fs=10, anchor="middle", col="#555", italic=True)

    wire([(bmidx, CY0+CH/2), (bmidx, COIL1_y0-6)], dash="4,3", wdth=1.1, col="#777")
    coil2_top, coil2_bot = coil(bmidx, COIL1_y0, 38, kbyp, f"25A, 2-pól ◄ relé {gpio_byp}")

    wire([(BYPLx, BUS_L_y), (RELx2, BUS_L_y)])
    dot(BYPLx, BUS_L_y)
    wire([(RELx2, BUS_L_y), (RELx2, BUS_L_y+30)])
    no_contact(RELx2, BUS_L_y+30, BUS_L_y+70, "", "")
    txt(RELx2+14, BUS_L_y+55, f"relé ◄ {gpio_byp}", fs=9.5, col="#555", italic=True)
    wire([(RELx2, BUS_L_y+70), (RELx2, safe_y), (coil2_top[0], safe_y), (coil2_top[0], coil2_top[1])])

    wire([(BYPNx, BUS_N_y), (Nfeed2_x, BUS_N_y)])
    dot(BYPNx, BUS_N_y)
    wire([(Nfeed2_x, BUS_N_y), (Nfeed2_x, coil2_bot[1]), (coil2_bot[0], coil2_bot[1])])

    # --- EMI filter (IC-štýl), L aj N cezeň (potrebuje oba na filtrovanie) ---
    EMI_y = COIL1_y0 + 38 + 30
    EMI_w, EMI_h = 200, 70
    EMI_x = ox - 40
    wire([(ox, y7), (ox, EMI_y)])
    wire([(Nx, y7), (Nx, EMI_y)])
    ic_block(EMI_x, EMI_y, EMI_w, EMI_h, f"{emi_name} — EMI FILTER", emi_model,
             pins_top=["LINE-L", "LINE-N"], pins_bottom=["LOAD-L", "LOAD-N"])
    ground(EMI_x+EMI_w+30, EMI_y+EMI_h/2, "PE (kovové telo filtra)")
    EMI_pin_L = EMI_x + EMI_w*(1)/(3)
    EMI_pin_N = EMI_x + EMI_w*(2)/(3)
    wire([(ox, EMI_y-16), (EMI_pin_L, EMI_y-16), (EMI_pin_L, EMI_y)])
    wire([(Nx, EMI_y-16), (EMI_pin_N, EMI_y-16), (EMI_pin_N, EMI_y)])
    y8 = EMI_y + EMI_h + 50

    # --- TRIAC/dimmer modul — LEN "AC IN"/"LOAD" (žiadne -N varianty).
    #     N vedie SÚBEŽNE vedľa modulu (N-koridor), nie cezeň.
    DIM_w, DIM_h = 120, 90
    DIM_x = EMI_pin_L - DIM_w/2
    DIM_y = y8 + 62
    N_corridor_x = EMI_pin_L + DIM_w/2 + 60

    txt(EMI_pin_L, DIM_y-46, dl_name, fs=12, anchor="middle", bold=True)
    txt(EMI_pin_L, DIM_y-32, "TRIAC v sérii s L · N NEJDE cez modul", fs=9.5, anchor="middle", col="#555", italic=True)
    pins = ic_block(DIM_x, DIM_y, DIM_w, DIM_h, "", "",
             pins_top=["AC IN"], pins_bottom=["LOAD"],
             pins_left=["VCC", "GND", "Z-C", "DIM"], pins_right=["N"])
    DIM_pin_AC = pins["AC IN"]
    DIM_pin_LOAD = pins["LOAD"]
    wire([(EMI_pin_L, y8-16), (EMI_pin_L, DIM_y-16), (DIM_pin_AC[0], DIM_y-16), (DIM_pin_AC[0], DIM_y)])
    txt(DIM_x-16, DIM_y+DIM_h+20, "I2C+napájanie DimmerLink", fs=8.7, col="#555", italic=True)
    txt(DIM_x-16, DIM_y+DIM_h+32, f"z ESP32 ({dl_addr}) — NÍZKONAPÄŤOVÉ,", fs=8.7, col="#555", italic=True)
    txt(DIM_x-16, DIM_y+DIM_h+44, "viď panel RIADENIE v fve_schema.svg", fs=8.7, col="#555", italic=True)

    # N-koridor: rovno z EMI LOAD-N, MIMO dimmera, s tenkou odbočkou do jeho "N" pinu
    wire([(EMI_pin_N, y8-16), (N_corridor_x, y8-16)])
    n_tap_y = pins["N"][1]
    wire([(N_corridor_x, y8-16), (N_corridor_x, n_tap_y)])
    dot(N_corridor_x, n_tap_y)
    txt(N_corridor_x+8, n_tap_y-18, "N: tenký vodič, účel", fs=8, col="#e65100", italic=True)
    txt(N_corridor_x+8, n_tap_y-8, "nejasný — asi len ref.,", fs=8, col="#e65100", italic=True)
    txt(N_corridor_x+8, n_tap_y+16, "nenesie záťažový prúd", fs=8, col="#e65100", italic=True)

    y9 = DIM_y + DIM_h + 55
    JY_L = y9 + 20
    JY_N = JY_L + 14
    wire([(N_corridor_x, n_tap_y), (N_corridor_x, JY_N)])
    wire([(DIM_pin_LOAD[0], DIM_pin_LOAD[1]), (DIM_pin_LOAD[0], JY_L)])

    wire([(bmidx-17, y7), (bmidx-17, JY_L), (DIM_pin_LOAD[0], JY_L)])
    wire([(bmidx+17, y7), (bmidx+17, JY_N), (N_corridor_x, JY_N)])
    dot(DIM_pin_LOAD[0], JY_L)
    dot(N_corridor_x, JY_N)
    txt(N_corridor_x+16, JY_N+4, "spoj (TRIAC alebo bypass)", fs=9.5, col="#555", italic=True)

    X2y = JY_N + 36
    wire([(DIM_pin_LOAD[0], JY_L), (DIM_pin_LOAD[0], X2y)])
    wire([(N_corridor_x, JY_N), (N_corridor_x, X2y)])
    terminal(DIM_pin_LOAD[0], X2y, x2n_l, block="X2")
    terminal(N_corridor_x, X2y, x2n_n)
    ground(N_corridor_x+50, X2y, "PE")

    y10 = X2y + 40
    cx = (DIM_pin_LOAD[0]+N_corridor_x)/2
    txt(cx, y10-8, cable_spec, fs=10, anchor="middle", bold=True)
    wire([(DIM_pin_LOAD[0], X2y), (DIM_pin_LOAD[0], y10+40)])
    wire([(N_corridor_x, X2y), (N_corridor_x, y10+40)])
    HY = y10 + 40
    heater(cx, HY, 140, 60, load_title, load_sub)
    ground(cx+90, HY+30, "PE (kryt)")
    return HY + 60 + 34  # spodok vrátane popisku

bottom_tuv = heating_branch(
    ox_tuv, Y_TUV0, "X1:1", "X1:2", "X2:7", "X2:8",
    "K1", "K2", "GPIO17", "GPIO16",
    "F1", "FN2030-30-08 · 30A",
    "D1 — rbdimmer1 + DimmerLink1", "I2C 0x50",
    "TUV špirála", "3 kW @ 230 V, v bojleri", "K4: CYKY-J 3×2,5 mm² (L,N,PE)")

bottom_pod = heating_branch(
    ox_pod, Y_POD0, "X1:3", "X1:4", "X2:9", "X2:10",
    "K3", "K4", "GPIO19", "GPIO18",
    "F2", "Schurter 5500.2623.01 · 10A",
    "D2 — rbdimmer2 + DimmerLink2", "I2C 0x51",
    "Podlaha špirála", "600 W @ 230 V, rozdeľovač", "K5: CYKY-J 3×1,5 mm² (L,N,PE)")

# ============================================================
# LOGIKA + ČERPADLÁ
# ============================================================
Nx_pump = ox_pump + 100
terminal(ox_pump, Y_PUMP0+26, "X1:5", block="X1")
terminal(Nx_pump, Y_PUMP0+26, "X1:6")
ground(Nx_pump+50, Y_PUMP0+26, "PE")
wire([(ox_pump, Y_PUMP0), (ox_pump, Y_PUMP0+26)])
wire([(Nx_pump, Y_PUMP0), (Nx_pump, Y_PUMP0+26)])
yb = Y_PUMP0 + 26

BUS_y_L, BUS_y_N = yb+36, yb+48
PSU_x = ox_pump
P1x = ox_pump + 220
P2x = ox_pump + 420
wire([(ox_pump, yb), (ox_pump, BUS_y_L), (P2x, BUS_y_L)])
wire([(Nx_pump, yb), (Nx_pump, BUS_y_N), (P2x+100, BUS_y_N)])
for px in (ox_pump, P1x, P2x):
    dot(px, BUS_y_L)
for px in (Nx_pump, P1x+100, P2x+100):
    dot(px, BUS_y_N)
txt((ox_pump+P2x)/2, BUS_y_L-6, "L-bus", fs=9, anchor="middle", col="#555", italic=True)
txt((Nx_pump+P2x+100)/2, BUS_y_N+15, "N-bus", fs=9, anchor="middle", col="#555", italic=True)

PSU_y = BUS_y_N + 30
wire([(ox_pump, BUS_y_L), (ox_pump, PSU_y)])
wire([(Nx_pump, BUS_y_N), (Nx_pump, PSU_y)])
ic_block(PSU_x-30, PSU_y, 180, 60, "Mean Well MDR-20-5", "230V→5V/3A",
         pins_top=["AC-L", "AC-N"], pins_bottom=["+5V", "GND"])
txt(PSU_x-30, PSU_y+95, "→ ESP32 + relé", fs=9, col="#555", italic=True)
txt(PSU_x-30, PSU_y+108, "(viď panel RIADENIE)", fs=9, col="#555", italic=True)

def pump(px, gpio, label, sub):
    Nx = px + 100
    wire([(px, BUS_y_L), (px, BUS_y_L+40)])
    no_contact(px, BUS_y_L+40, BUS_y_L+90, "1", "2")
    txt(px+16, BUS_y_L+70, f"relé ◄ {gpio}", fs=9.5, col="#555", italic=True)
    wire([(Nx, BUS_y_N), (Nx, BUS_y_L+90)])
    X2y = BUS_y_L + 140
    wire([(px, BUS_y_L+90), (px, X2y)])
    wire([(Nx, BUS_y_L+90), (Nx, X2y)])
    return px, Nx, X2y

p1x, p1n, X2y1 = pump(P1x, "GPIO26", "Čerpadlo TUV", "obehové, pri bojleri")
p2x, p2n, X2y2 = pump(P2x, "GPIO25", "Čerpadlo podlaha", "obehové, pri rozdeľovači")
X2y_pumps = max(X2y1, X2y2)
terminal(p1x, X2y_pumps, "X2:11", block="X2")
terminal(p1n, X2y_pumps, "X2:12")
terminal(p2x, X2y_pumps, "X2:13", block="X2")
terminal(p2n, X2y_pumps, "X2:14")
ground(p2n+50, X2y_pumps, "PE")

y_after = X2y_pumps + 40
wire([(p1x, X2y_pumps), (p1x, y_after+30)])
wire([(p1n, X2y_pumps), (p1n, y_after+30)])
wire([(p2x, X2y_pumps), (p2x, y_after+30)])
wire([(p2n, X2y_pumps), (p2n, y_after+30)])
txt((p1x+p1n)/2, y_after-6, "K6: 3×1,5 mm² (L,N,PE)", fs=9.5, anchor="middle", bold=True)
txt((p2x+p2n)/2, y_after-6, "K7: 3×1,5 mm² (L,N,PE)", fs=9.5, anchor="middle", bold=True)
motor((p1x+p1n)/2, y_after+30, 32, "Čerpadlo TUV", "obehové, pri bojleri")
motor((p2x+p2n)/2, y_after+30, 32, "Čerpadlo podlaha", "obehové, pri rozdeľovači")
ground((p1x+p1n)/2+45, y_after+30+64-10, "PE")
ground((p2x+p2n)/2+45, y_after+30+64-10, "PE")
bottom_pumps = y_after+30+64+34+20

# ============================================================
# Legenda + poznámky
# ============================================================
lx0, ly0 = 2620, 90
rect(lx0, ly0, 210, 300, fill="#fff")
txt(lx0+10, ly0+22, "Legenda značiek", fs=13, bold=True)
ly = ly0 + 46
breaker(lx0+20, ly, ly+34, "", "")
txt(lx0+40, ly+22, "istič", fs=9.5)
ly += 52
rcd_box((lx0+10, lx0+30), ly, ly+34, "", "", label_x=lx0+70)
txt(lx0+70, ly+22, "RCD", fs=9.5)
ly += 52
no_contact(lx0+20, ly, ly+34, "", "")
txt(lx0+40, ly+22, "kontakt (NO)", fs=9.5)
ly += 52
coil(lx0+20+17, ly, 30, "K", "")
txt(lx0+80, ly+20, "cievka stykača", fs=9.5)
ly += 48
ground(lx0+20, ly)
txt(lx0+40, ly+14, "PE / uzemnenie", fs=9.5)
ly += 34
wire([(lx0+10, ly), (lx0+30, ly)], dash="4,3", col="#777")
txt(lx0+40, ly+4, "mech. väzba (nie vodič)", fs=9)
ly += 22
dot(lx0+18, ly)
txt(lx0+40, ly+4, "spoj vodičov (bodka)", fs=9)
ly += 24
txt(lx0+10, ly+6, "kríženie bez bodky = nespojené", fs=8.7, italic=True, col="#555")

ny0 = ly0 + 320
rect(lx0, ny0, 210, 280, fill="#fff9c4", stroke="#f9a825")
txt(lx0+10, ny0+20, "Predpoklad na overenie", fs=11.5, col="#e65100", bold=True)
notes = [
 "Stykače K1-K4 = 2-pól (L+N),",
 "\"2×NO\" = kontakty 1-2 (L) a",
 "3-4 (N) — over podľa",
 "datasheetu.",
 "",
 "rbdimmer 40A-CS (opravené",
 "2026-09-21): má LEN AC IN a",
 "LOAD (jeden silový vodič, L).",
 "Tenký vodič \"N\" na doske —",
 "účel neistý, pravdepodobne",
 "len referencia pre elektroniku",
 "modulu, ide priamo do N",
 "svorkovnice, NEnesie záťažový",
 "prúd. Over v dokumentácii.",
 "",
 "EMI filter potrebuje L aj N",
 "(inak by nefiltroval) — na",
 "rozdiel od dimmera.",
]
for i, n in enumerate(notes):
    txt(lx0+10, ny0+40+i*14.5, n, fs=9.3, col="#5d4037")

body = "\n".join(el)
Hreal = max(bottom_tuv, bottom_pod, bottom_pumps, ny0+40+len(notes)*14.5+20) + 20
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hreal}" '
       f'viewBox="0 0 {W} {Hreal}" font-family="DejaVu Sans, Arial, sans-serif">\n'
       f'<rect x="0" y="0" width="{W}" height="{Hreal}" fill="#ffffff"/>\n'
       + body + "\n</svg>\n")

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fve_schema_realny.svg")
with open(path, "w") as f:
    f.write(svg)
print("SVG zapísané:", path, "-", len(svg), "bajtov, H =", Hreal)

if shutil.which("rsvg-convert"):
    png = path[:-4] + ".png"
    subprocess.run(["rsvg-convert", "-o", png, path], check=True)
    print("PNG zapísané:", png)
