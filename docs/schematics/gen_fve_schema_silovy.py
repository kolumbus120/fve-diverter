#!/usr/bin/env python3
# Generátor SVG — FVE diverter, SILOVÁ ČASŤ, elektrikárska schéma zapojenia
# (káble, svorky, prierezy, fyzické rozdelenie do rozvádzač/skriňa).
#
# Účel: doplnok k fve_schema.svg (ktorá je FUNKČNÁ/bloková a mieša silovú
# časť s riadením). Táto schéma je LEN silová časť, ale s detailom, ktorý
# funkčná schéma zámerne vynecháva — aby podľa nej vedel káblovať aj niekto,
# kto projekt predtým nevidel: prierezy vodičov, čísla svoriek, farby,
# fyzické umiestnenie (hlavný rozvádzač vs. nová skriňa FVE diverter).
#
# ⚠️ DÔLEŽITÝ ROZDIEL oproti fve_schema.svg: tam je N nakreslená ako jedna
# spoločná nespínaná zbernica priamo z RCD k záťaži (zjednodušenie pre
# prehľadnosť funkčnej schémy). TU vedie N fyzicky CEZ izolačný aj bypass
# stykač spolu s L (stykače sú 2-pólové, "2×NO" = 2 kontakty, jeden na L,
# jeden na N) a CEZ EMI filter (ten potrebuje oba vodiče, inak by nefiltroval
# nič). TRIAC/DimmerLink je v sérii LEN s L — N cez dimmer modul ide priamo
# (AC-OUT-N = nespínaná priechodná svorka). Toto je predpoklad potrebný pre
# fyzicky správne a bezpečné zapojenie (plná izolácia oboch vodičov, funkčný
# EMI filter) — OVERIŤ podľa datasheetu konkrétneho stykača (počet pólov) a
# rbdimmer 40A-CS dosky (že AC-OUT-N je naozaj priama priechodka).
#
# Prierezy vodičov sú NÁVRH podľa prúdu (TUV 3kW/230V≈13A, podlaha 600W≈2,6A)
# podľa bežnej SK/EÚ praxe — dĺžka reálnej trasy nie je známa, pri montáži
# overiť/prispôsobiť (najmä ak trasa > pár metrov alebo vedená v tepelne
# náročnom prostredí pri bojleri).

import os
import shutil
import subprocess

W = 1700
el = []

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def box(x, y, w, h, title, sub="", fill="#ffe0b2", stroke="#e65100", tcol="#3e2723", rx=8, fs=14):
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    cx = x + w/2
    if sub:
        el.append(f'<text x="{cx}" y="{y+h/2-4}" text-anchor="middle" '
                  f'font-size="{fs}" font-weight="bold" fill="{tcol}">{esc(title)}</text>')
        el.append(f'<text x="{cx}" y="{y+h/2+14}" text-anchor="middle" '
                  f'font-size="11" fill="{tcol}">{esc(sub)}</text>')
    else:
        el.append(f'<text x="{cx}" y="{y+h/2+5}" text-anchor="middle" '
                  f'font-size="{fs}" font-weight="bold" fill="{tcol}">{esc(title)}</text>')

def txt(x, y, s, fs=12, anchor="start", col="#222", bold=False, italic=False):
    w = ' font-weight="bold"' if bold else ''
    i = ' font-style="italic"' if italic else ''
    el.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{fs}" '
              f'fill="{col}"{w}{i}>{esc(s)}</text>')

def wire(pts, col="#c62828", wdth=3, dash="", arrow=False):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    a = ' marker-end="url(#arr)"' if arrow else ''
    p = " ".join(f"{x},{y}" for x, y in pts)
    el.append(f'<polyline points="{p}" fill="none" stroke="{col}" '
              f'stroke-width="{wdth}"{d}{a}/>')

def enclosure(x, y, w, h, title, stroke="#607d8b", fill="#fafafa"):
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
              f'fill="{fill}" fill-opacity="0.55" stroke="{stroke}" stroke-width="2.5" '
              f'stroke-dasharray="10,6"/>')
    txt(x+16, y+24, title, fs=15, col=stroke, bold=True)

def pin_row(x, y, w, pins, title=""):
    """pins: list of (num, label). Vráti dict num->stred-x pinu."""
    if title:
        txt(x, y-10, title, fs=11.5, col="#37474f", bold=True)
    n = len(pins)
    pw = w / n
    centers = {}
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="34" rx="4" '
              f'fill="#eceff1" stroke="#37474f" stroke-width="1.5"/>')
    for i, (num, label) in enumerate(pins):
        px = x + i*pw
        if i > 0:
            el.append(f'<line x1="{px}" y1="{y}" x2="{px}" y2="{y+34}" stroke="#90a4ae" stroke-width="1"/>')
        cx = px + pw/2
        centers[num] = cx
        txt(cx, y+14, num, fs=10.5, anchor="middle", col="#37474f", bold=True)
        txt(cx, y+28, label, fs=9.5, anchor="middle", col="#37474f")
    return centers

def pe_cell(x, y, w=55):
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="34" rx="4" fill="#c8e6c9" stroke="#2e7d32" stroke-width="1.5"/>')
    txt(x+w/2, y+14, "PE", fs=10.5, anchor="middle", col="#2e7d32", bold=True)
    txt(x+w/2, y+28, "spoločná", fs=9, anchor="middle", col="#2e7d32")

el.append('<defs><marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="3" '
          'orient="auto" markerUnits="strokeWidth">'
          '<path d="M0,0 L8,3 L0,6 z" fill="#1565c0"/></marker></defs>')

txt(W/2, 34, "FVE diverter — SILOVÁ ČASŤ — elektrikárska schéma zapojenia", fs=22, anchor="middle", col="#0d47a1", bold=True)
txt(W/2, 56, "Káble, svorky, prierezy · dopĺňa funkčnú schému fve_schema.svg (tam zjednodušené) · Revízia 2026-09-20",
    fs=12.5, anchor="middle", col="#555")

# ============================================================
# ENCLOSURE 1 — hlavný domový rozvádzač
# ============================================================
E1x, E1y, E1w, E1h = 50, 84, 1360, 386
enclosure(E1x, E1y, E1w, E1h, "HLAVNÝ DOMOVÝ ROZVÁDZAČ (existujúci)")

TUVx, PODx, LOGx = 300, 700, 1150
E_RIGHT = E1x + E1w  # 1410 — spoločná pravá hrana oboch rámov

box(90, 118, 1280, 38, "HLAVNÝ 3F ISTIČ", "L1  L2  L3  N", fill="#eeeeee", stroke="#424242", fs=13)
box(90, 172, 1280, 46, "RCD 4-pól · 25 A · 30 mA · Typ A",
    "TRIAC fázovka → jednosmerné zložky → Typ A povinný", fill="#d1c4e9", stroke="#4527a0", fs=12.5)
for xx in (TUVx, PODx, LOGx):
    wire([(xx, 156), (xx, 172)], wdth=2.5)
    wire([(xx, 218), (xx, 248)], wdth=2.5)

box(TUVx-55, 248, 110, 40, "FA1 — B16", "TUV / L1", fill="#eeeeee", stroke="#424242", fs=12.5)
box(PODx-55, 248, 110, 40, "FA2 — B6", "podlaha / L2", fill="#eeeeee", stroke="#424242", fs=12.5)
box(LOGx-70, 248, 140, 40, "FA3 — B6", "logika + čerpadlá", fill="#eeeeee", stroke="#424242", fs=12.5)

# L pokračuje z ističa priamo na výstup (kábel K1/K2/K3)
for xx in (TUVx, PODx, LOGx):
    wire([(xx, 288), (xx, 400)], wdth=2.5)

# N a PE lišty — jeden spoločný prívod z RCD (ľavý okraj), taps po stĺpcoch
NB_y, PB_y = 314, 344
el.append(f'<rect x="90" y="{NB_y}" width="1280" height="16" fill="#bbdefb" stroke="#1565c0"/>')
txt(96, NB_y+12, "N lišta (spoločná, z RCD)", fs=10.5, col="#0d47a1", bold=True)
el.append(f'<rect x="90" y="{PB_y}" width="1280" height="16" fill="#c8e6c9" stroke="#2e7d32"/>')
txt(96, PB_y+12, "PE lišta (spoločná, na kostru rozvádzača)", fs=10.5, col="#2e7d32", bold=True)
wire([(110, 218), (110, NB_y)], col="#1565c0", wdth=2)
wire([(130, 218), (130, PB_y)], col="#2e7d32", wdth=2, dash="4,3")
for xx in (TUVx, PODx, LOGx):
    wire([(xx, NB_y+16), (xx, 400)], col="#1565c0", wdth=2)
    wire([(xx+16, PB_y+16), (xx+16, 400)], col="#2e7d32", wdth=2, dash="4,3")

txt(TUVx, 420, "K1 →", fs=12.5, anchor="middle", col="#b71c1c", bold=True)
txt(PODx, 420, "K2 →", fs=12.5, anchor="middle", col="#b71c1c", bold=True)
txt(LOGx, 420, "K3 →", fs=12.5, anchor="middle", col="#b71c1c", bold=True)

# ============================================================
# KÁBLOVÉ TRASY K1/K2/K3 — hlavný rozvádzač → skriňa FVE diverter
# ============================================================
cable_y0, cable_y1 = 480, 560
for xx in (TUVx, PODx, LOGx):
    wire([(xx, cable_y0), (xx, cable_y1)], wdth=3, arrow=True)

txt(TUVx+14, cable_y0+16, "K1: CYKY-J 3×2,5 mm²", fs=11, col="#b71c1c", bold=True)
txt(TUVx+14, cable_y0+31, "(L,N,PE) · TUV · ~13 A", fs=9.5, col="#555", italic=True)
txt(PODx+14, cable_y0+16, "K2: CYKY-J 3×1,5 mm²", fs=11, col="#b71c1c", bold=True)
txt(PODx+14, cable_y0+31, "(L,N,PE) · podlaha · ~2,6 A", fs=9.5, col="#555", italic=True)
txt(LOGx+14, cable_y0+16, "K3: CYKY-J 3×1,5 mm²", fs=11, col="#b71c1c", bold=True)
txt(LOGx+14, cable_y0+31, "(L,N,PE) · logika+čerpadlá", fs=9.5, col="#555", italic=True)
txt(90, cable_y0+50, "⚠️ Typ/dĺžka trasy upraviť podľa reálnej montáže (CYKY-J v stene / CYKY-O na povrchu) — prierezy sú návrh podľa prúdu, nie podľa dĺžky trasy.",
    fs=10, col="#e65100", italic=True)

# ============================================================
# ENCLOSURE 2 — skriňa FVE diverter
# ============================================================
E2y = 596
X1y = E2y + 66          # 662 — dosť pod nadpisom rámu (E2y+24)
IN_y, IP_y = X1y + 56, X1y + 78     # 718, 740
BR_TOP = IN_y + 60                   # 778 — odbočka na vetvu (tap + bypass)
ISO_y = BR_TOP + 26                  # 804
BYP_y = BR_TOP + 46                  # 824
EMI_y = ISO_y + 66                   # 870
DIM_y = EMI_y + 62                   # 932
JUNC_y = DIM_y + 78                  # 1010
X2y = JUNC_y + 40                    # 1050
E2_bottom = X2y + 34 + 20            # 1104
E2h = E2_bottom - E2y

enclosure(50, E2y, 1360, E2h, "SKRIŇA FVE DIVERTER (nová, k dostavbe)", stroke="#e65100")

x1pins = pin_row(90, X1y, 1250, [
    ("1","L·TUV"), ("2","N·TUV"), ("3","L·POD"), ("4","N·POD"), ("5","L·LOG"), ("6","N·LOG"),
], title="X1 — VSTUPNÁ SVORKOVNICA (od hlavného rozvádzača)")
pe1_x = 1345
pe_cell(pe1_x, X1y, w=55)

wire([(TUVx, cable_y1), (TUVx, X1y)], wdth=3)
wire([(PODx, cable_y1), (PODx, X1y)], wdth=3)
wire([(LOGx, cable_y1), (LOGx, X1y)], wdth=3)
wire([(TUVx+16, cable_y1), (pe1_x+27, cable_y1), (pe1_x+27, X1y)], col="#2e7d32", wdth=2, dash="4,3")

# interná N + PE lišta v skrini
el.append(f'<rect x="90" y="{IN_y}" width="1280" height="16" fill="#bbdefb" stroke="#1565c0"/>')
txt(96, IN_y+12, "N — vnútorná lišta (nespínaná, spoločná)", fs=10, col="#0d47a1", bold=True)
el.append(f'<rect x="90" y="{IP_y}" width="1280" height="16" fill="#c8e6c9" stroke="#2e7d32"/>')
txt(96, IP_y+12, "PE — vnútorná lišta skrine (na DIN lištu + kovové telo)", fs=10, col="#2e7d32", bold=True)
wire([(pe1_x+30, X1y+34), (pe1_x+30, IP_y+8), (90+1250, IP_y+8)], col="#2e7d32", wdth=2, dash="4,3")

def branch_top(x, l_pin, n_pin):
    wire([(x1pins[l_pin], X1y+34), (x1pins[l_pin], BR_TOP), (x, BR_TOP)], wdth=2.5)
    wire([(x1pins[n_pin], X1y+34), (x1pins[n_pin], IN_y)], col="#1565c0", wdth=2)
    wire([(x-40, IN_y+8), (x, IN_y+8), (x, BR_TOP)], col="#1565c0", wdth=2)
    txt(x, BR_TOP-8, "L+N (2 vod.)", fs=9, anchor="middle", col="#b71c1c", italic=True)

def heating_branch(x, l_pin, n_pin, iso_label, iso_gpio, emi_label, emi_sub, dl_label, dl_sub,
                    byp_gpio):
    branch_top(x, l_pin, n_pin)
    bx = x + 165
    wire([(x, BR_TOP), (bx, BR_TOP), (bx, BYP_y)], wdth=2.5)
    box(bx-56, BYP_y, 112, 44, "BYPASS", f"◄{byp_gpio} (L+N)", fill="#ffe0b2", stroke="#e65100", fs=11)

    wire([(x, BR_TOP), (x, ISO_y)], wdth=2.5)
    box(x-92, ISO_y, 184, 60, iso_label, f"2-pól (L+N) · 25 A ◄ relé {iso_gpio}", fill="#ffe0b2", stroke="#e65100", fs=11.5)

    wire([(x, ISO_y+60), (x, EMI_y)], wdth=2.5)
    box(x-92, EMI_y, 184, 56, emi_label, emi_sub, fill="#b2dfdb", stroke="#00695c", tcol="#004d40", fs=11)

    wire([(x, EMI_y+56), (x, DIM_y)], wdth=2.5)
    box(x-92, DIM_y, 184, 56, dl_label, dl_sub, fill="#ffccbc", stroke="#bf360c", fs=10.5)

    wire([(x, DIM_y+56), (x, JUNC_y)], wdth=2.5)
    wire([(bx, BYP_y+44), (bx, JUNC_y), (x, JUNC_y)], wdth=2.5)
    el.append(f'<circle cx="{x}" cy="{JUNC_y}" r="4" fill="#b71c1c"/>')
    wire([(x, JUNC_y), (x, X2y)], wdth=3)

X2y_pins_l = {}

heating_branch(TUVx, "1", "2", "IZOLAČNÝ STYKAČ K1", "GPIO17",
               "EMI FILTER F1 · 30 A", "FN2030-30-08 · LINE→sieť, LOAD→dimmer",
               "rbdimmer1 + DimmerLink1", "TRIAC len na L · N priamo (AC-OUT-N)",
               "GPIO16")

heating_branch(PODx, "3", "4", "IZOLAČNÝ STYKAČ K3", "GPIO19",
               "EMI FILTER F2 · 10 A", "Schurter 5500.2623.01",
               "rbdimmer2 + DimmerLink2", "TRIAC len na L · N priamo (AC-OUT-N)",
               "GPIO18")

txt(TUVx+165, BYP_y-8, "L+N, obchádza celú vetvu", fs=8.5, anchor="middle", col="#e65100", italic=True)
txt(PODx+165, BYP_y-8, "L+N, obchádza celú vetvu", fs=8.5, anchor="middle", col="#e65100", italic=True)
txt(TUVx+15, JUNC_y+4, "spoj (TRIAC alebo bypass)", fs=9, col="#555", italic=True)
txt(PODx+15, JUNC_y+4, "spoj (TRIAC alebo bypass)", fs=9, col="#555", italic=True)

# --- LOG vetva: PSU + 2× čerpadlo ---
PUMP_TUV_x, PUMP_POD_x = 1040, 1250
wire([(x1pins["5"], X1y+34), (x1pins["5"], BR_TOP), (LOGx, BR_TOP)], wdth=2.5)
wire([(x1pins["6"], X1y+34), (x1pins["6"], IN_y)], col="#1565c0", wdth=2)
wire([(LOGx, BR_TOP), (PUMP_TUV_x, BR_TOP)], wdth=2.5)
wire([(LOGx, BR_TOP), (PUMP_POD_x, BR_TOP)], wdth=2.5)
wire([(LOGx-40, IN_y+8), (PUMP_POD_x, IN_y+8)], col="#1565c0", wdth=2)
for xx in (PUMP_TUV_x, LOGx, PUMP_POD_x):
    wire([(xx, IN_y+8), (xx, ISO_y)], col="#1565c0", wdth=2)

box(LOGx-95, ISO_y, 190, 60, "Mean Well MDR-20-5", "230V→5V/3A · napája ESP32+relé", fill="#e0e0e0", stroke="#424242", fs=11.5)
wire([(LOGx, BR_TOP), (LOGx, ISO_y)], wdth=2.5)
txt(LOGx+105, ISO_y+18, "→ logika (viď panel", fs=9, col="#555", italic=True)
txt(LOGx+105, ISO_y+32, "RIADENIE v fve_schema.svg)", fs=9, col="#555", italic=True)

box(PUMP_TUV_x-85, EMI_y, 170, 56, "Relé — čerpadlo TUV", "spína L ◄ GPIO26 · N priamo", fill="#ffe0b2", stroke="#e65100", fs=11)
box(PUMP_POD_x-85, EMI_y, 170, 56, "Relé — čerp. podlaha", "spína L ◄ GPIO25 · N priamo", fill="#ffe0b2", stroke="#e65100", fs=11)
wire([(PUMP_TUV_x, ISO_y+60), (PUMP_TUV_x, EMI_y)], wdth=2.5)
wire([(PUMP_POD_x, ISO_y+60), (PUMP_POD_x, EMI_y)], wdth=2.5)
wire([(PUMP_TUV_x, EMI_y+56), (PUMP_TUV_x, X2y)], wdth=3)
wire([(PUMP_POD_x, EMI_y+56), (PUMP_POD_x, X2y)], wdth=3)

x2pins = pin_row(90, X2y, 1250, [
    ("7","L·TUV"), ("8","N·TUV"), ("9","L·POD"), ("10","N·POD"),
    ("11","L·ČTUV"), ("12","N·ČTUV"), ("13","L·ČPOD"), ("14","N·ČPOD"),
], title="X2 — VÝSTUPNÁ SVORKOVNICA (k spotrebičom)")
pe2_x = pe1_x
pe_cell(pe2_x, X2y, w=55)
wire([(90+1250, IP_y+8), (pe2_x+27, IP_y+8), (pe2_x+27, X2y)], col="#2e7d32", wdth=2, dash="4,3")

# ============================================================
# KÁBLOVÉ TRASY K4..K7 — skriňa → spotrebiče
# ============================================================
out_y0, out_y1 = E2_bottom + 24, E2_bottom + 96
outs = [
    (TUVx, "K4: CYKY-J 3×2,5 mm²", "→ TUV špirála (bojler)"),
    (PODx, "K5: CYKY-J 3×1,5 mm²", "→ podlaha špirála"),
    (PUMP_TUV_x, "K6: 3×1,5 mm²", "→ čerp. TUV"),
    (PUMP_POD_x, "K7: 3×1,5 mm²", "→ čerp. podlaha"),
]
for xx, lab, dst in outs:
    wire([(xx, out_y0), (xx, out_y1)], wdth=3, arrow=True)
    txt(xx+10, out_y0+16, lab, fs=10, col="#b71c1c", bold=True)
    txt(xx+10, out_y0+30, dst, fs=9, col="#555", italic=True)

field_y = out_y1 + 20
box(TUVx-95, field_y, 190, 60, "TUV špirála", "3 kW @ 230 V · v bojleri", fill="#ffcdd2", stroke="#b71c1c", fs=12)
box(PODx-95, field_y, 190, 60, "Podlaha špirála", "600 W @ 230 V · rozdeľovač", fill="#ffcdd2", stroke="#b71c1c", fs=12)
box(PUMP_TUV_x-80, field_y, 160, 60, "Čerpadlo TUV", "obehové, pri bojleri", fill="#ffcdd2", stroke="#b71c1c", fs=11.5)
box(PUMP_POD_x-80, field_y, 160, 60, "Čerpadlo podlaha", "obehové, pri rozdeľovači", fill="#ffcdd2", stroke="#b71c1c", fs=11)

# ============================================================
# Legenda
# ============================================================
lx, ly = 1430, 84
el.append(f'<rect x="{lx}" y="{ly}" width="220" height="256" rx="8" fill="#ffffff" stroke="#888" stroke-width="1.5"/>')
txt(lx+12, ly+22, "Legenda", fs=14, bold=True, col="#333")
leg = [
    ("#ffe0b2","#e65100","Silnoprúd / spínanie"),
    ("#b2dfdb","#00695c","EMI filter"),
    ("#ffccbc","#bf360c","TRIAC / dimmer"),
    ("#ffcdd2","#b71c1c","Záťaž (špirály, čerpadlá)"),
    ("#e0e0e0","#424242","Napájanie / istenie"),
    ("#d1c4e9","#4527a0","Ochrana (RCD)"),
    ("#eceff1","#37474f","Svorkovnica (X1/X2)"),
]
for i,(fl,st,lab) in enumerate(leg):
    yy = ly+42+i*20
    el.append(f'<rect x="{lx+14}" y="{yy-10}" width="22" height="13" rx="3" fill="{fl}" stroke="{st}"/>')
    txt(lx+44, yy, lab, fs=10.8, col="#333")
yy = ly+42+len(leg)*20+10
wire([(lx+16, yy), (lx+36, yy)], col="#c62828", wdth=3); txt(lx+44, yy+4, "L / silový vodič", fs=10.8, col="#333")
yy += 20
wire([(lx+16, yy), (lx+36, yy)], col="#1565c0", wdth=2); txt(lx+44, yy+4, "N", fs=10.8, col="#333")
yy += 20
wire([(lx+16, yy), (lx+36, yy)], col="#2e7d32", wdth=2, dash="4,3"); txt(lx+44, yy+4, "PE (žltozelená)", fs=10.8, col="#333")

# ============================================================
# Poznámky / predpoklady na overenie
# ============================================================
nx, ny, nw = 1430, 366, 220
notes_h = 720
el.append(f'<rect x="{nx}" y="{ny}" width="{nw}" height="{notes_h}" rx="8" fill="#fff9c4" stroke="#f9a825" stroke-width="2"/>')
txt(nx+12, ny+22, "Predpoklady na overenie", fs=13, col="#e65100", bold=True)
notes = [
    "⚠️ Stykače (izolačný aj bypass) sú tu",
    "kreslené ako 2-pólové (L+N spolu) —",
    "\"2×NO\" = 2 kontakty, jeden na L, jeden",
    "na N. Vo fve_schema.svg je N zjedno-",
    "dušená ako spoločná zbernica. Tu je to",
    "fyzicky presnejšie (plná izolácia +",
    "funkčný EMI filter potrebuje oba",
    "vodiče). OVERIŤ podľa datasheetu",
    "konkrétneho stykača (počet pólov).",
    "",
    "⚠️ rbdimmer 40A-CS: predpoklad, že",
    "AC-OUT-N je priama, nespínaná",
    "priechodka (TRIAC len na L). Over v",
    "dokumentácii dosky pred zapojením.",
    "",
    "⚠️ PE nejde cez stykač/EMI/dimmer —",
    "je to samostatná ochranná zbernica.",
    "Kovové telo EMI filtrov, DIN lišta a",
    "telo skrine sa pripájajú na PE lištu",
    "(odrušenie bez bondingu nefunguje).",
    "Over vyrazené označenie LINE/LOAD",
    "na kuse (líši sa medzi dávkami).",
    "",
    "⚠️ Prierezy K1–K7 sú návrh podľa",
    "prúdu (bežná SK/EÚ prax), NIE podľa",
    "reálnej dĺžky trasy — tú nepoznám.",
    "Pri dlhšej trase (>~15 m) alebo vedení",
    "v tepelnej blízkosti bojlera prepočítať",
    "úbytok napätia / zvoliť teplotne",
    "odolný kábel na poslednom úseku ku",
    "špirále bojlera.",
    "",
    "⚠️ Čerpadlá — ak majú vlastný sieťový",
    "kábel/vidlicu od výrobcu, K6/K7 a X2",
    "piny 11–14 sa nahradia zásuvkou.",
    "",
    "Riadiaca (nízkonapäťová) časť GPIO/",
    "senzory NIE JE tu — viď samostatný",
    "panel \"RIADENIE\" vo fve_schema.svg.",
]
for i,n in enumerate(notes):
    txt(nx+12, ny+42+i*16, n, fs=10, col="#5d4037")

H = max(field_y + 90, ny + notes_h + 30)

body = "\n".join(el)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
       f'viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">\n'
       + f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fcfcfa"/>\n'
       + body + "\n</svg>\n")

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fve_schema_silovy.svg")
with open(path, "w") as f:
    f.write(svg)
print("SVG zapísané:", path, "-", len(svg), "bajtov, H =", H)

if shutil.which("rsvg-convert"):
    png = path[:-4] + ".png"
    subprocess.run(["rsvg-convert", "-o", png, path], check=True)
    print("PNG zapísané:", png)
else:
    print("rsvg-convert nenájdený — PNG treba vygenerovať ručne.")
