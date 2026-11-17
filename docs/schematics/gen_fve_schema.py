#!/usr/bin/env python3
# Generátor SVG schémy FVE automatizácie prebytkov (ESP32 #2)
import os
import shutil
import subprocess
# Revízia 2026-07-13:
#   - TUV špirála 3 kW @ L1, PODLAHA špirála 600 W @ L2 (malá akumulačka)
#   - 2 SAMOSTATNÉ stykače (každá špirála vlastný), cievky spínané cez relé z ESP
#   - EMI filtre za každým stykačom (Schaffner FN2030-30-08 / malý na 600 W)
#   - 4 relé z ESP: 2× cievka stykača + 2× obehové čerpadlo (TUV, podlaha)
#   - Senzory: T podlaha, T TUV, prietok studenej do TUV, T vratná TUV,
#     opto vstup "Daikin žiada čerpadlo podlahy"
#   - ESP preberá DVE NESÚVISIACE funkcie (nemiešať!):
#     1) nahrádza TechController ECO — LEN čerpadlo TUV, podľa vlastných
#        teplotných/prietokových senzorov. S Daikinom to nemá NIČ spoločné.
#     2) NOVÁ funkcia (nie náhrada TechControlleru) — čerpadlo podlahy podľa
#        Daikinovej požiadavky cez OPTO. TechController ECO s podlahou
#        nikdy nič nemal.
# Doplnené 2026-08-16: ventilátor skrine (chladenie dimmerov) — MOSFET
#   modul FR120N na GPIO25, PWM podľa výkonu dimmerov (nie teploty skrine).
# Doplnené 2026-08-21: BYPASS STYKAČ na oboch vetvách (paralelne k TRIAC-u) —
#   nad ~97 % výkonu preberie vedenie prúdu stykač (0 strát), TRIAC pri 100 %
#   dispuje ~V_T×I trvalo (napr. TUV 1,5V×13A≈20W). ZOP ≥97 % / ROZ ≤95 %
#   (hysteréza). GPIO13 (TUV bypass), GPIO5 (podlaha bypass) — relé riešené
#   ako 3× samostatný 2-kanálový modul (TUV, podlaha, čerpadlá).
# Zmenené 2026-11-10: nové rozloženie pinov podľa esp32_pinout_zapojenie.png —
#   rbdimmer1 TUV TEMP/CUR-S/FAN 36/39/33, rbdimmer2 podlaha 34/35/32, relé
#   čerpadlá TUV 26 / podlaha 25, Daikin OPTO podlaha 27 / ohrev TUV 14, tacho
#   fanu skrine 22, prietok TUV 4, záložné relé fanu 13 (voliteľné).
# Zmenené 2026-11-15: DS18B20 každý na vlastnom pine — B1 G21+R1, B2 G5+R7,
#   B3 G13+R8 (klony nejdú po dvoch na zbernici); GPIO13 už nie je rezerva.
# Doplnené 2026-08-27: DimmerLink = PRIMÁRNE riešenie (nie ac_dimmer, nie
#   "alternatíva/TODO") — rozhodnutie, už kúpené 2× DimmerLink 1CH (jeden
#   na L1/TUV, jeden na L2/podlaha), každý vlastný hardvérový Z-C, spoločná
#   I2C zbernica (GPIO26 SDA / GPIO14 SCL). ESP32 GATE/ZC piny (GPIO4, 16,
#   27, 33) sa NEPOUŽÍVAJÚ — DimmerLink rieši firing hardvérovo, ESP32 len
#   posiela duty cez I2C. Máme aj 1× DimmerLink 2CH (kúpený skôr) — ten
#   ostáva NEZAPOJENÝ ako záložný diel (jeden zdieľaný Z-C pre oba kanály sa
#   pre 2 rôzne fázy nehodí).
# Doplnené 2026-09-08: DAIKIN — nový vstup "žiada ohrev TUV (bojler)".
#   Pôvodne Daikinovo relé spínalo 230 V priamo na špirálu bojlera; po
#   presune silových káblov špirály do NÁŠHO zapojenia je toto relé už len
#   POTENCIÁLPROSTÝ (dry) kontakt bez napätia → pripojené PRIAMO na GPIO27
#   (uvoľnený po prechode na DimmerLink) s interným pull-up, kontakt na
#   GND — BEZ optočlena (na rozdiel od podlahy, kde signál stále nesie
#   živých 230 V). Pred pripojením OVERIŤ multimetrom (napätie, oba stavy
#   relé), že je to naozaj dry kontakt — pozri TODO.
# Doplnené 2026-09-08: EMI filter — presnejšia svorková konvencia (LINE-L/
#   LINE-N, LOAD-L/LOAD-N, PE na kostru), s upozornením overiť vyrazené
#   označenie priamo na kuse (líši sa medzi výrobnými dávkami).
# Doplnené 2026-09-10: Daikin GPIO27 ZAP → špirála TUV NAPLNO cez bypass
#   stykač, bez ohľadu na FVE prebytok AJ watchdog (nezávislé od merania
#   prebytku, ako fungoval pôvodný priamy backup ohrev). Limit: max_t_tuv.
# Doplnené 2026-09-14: IZOLAČNÝ STYKAČ implementovaný ako "deň/noc" okno
#   (rozhodnutie 2026-08-21) — SNTP čas (nezávislé od HA) + hodiny
#   laditeľné z HA (den_start_hod/den_koniec_hod), NIE hysteréza na duty.
# Doplnené 2026-09-14 (2), OPRAVENÁ TOPOLÓGIA: BYPASS je paralelne k CELEJ
#   vetve (izolačný stykač + EMI filter + TRIAC/DimmerLink), NIE len k
#   TRIAC-u ako pôvodne — dve úplne nezávislé paralelné cesty od ističa
#   k špirále. Dôsledky: (1) izolačný stykač už nemusí riešiť žiadnu
#   poistku voči bypassu (nie sú v sérii, nemôže lámať jeho prúd) — spína
#   čisto deň/noc, bez výnimky. (2) Daikin backup TUV ovláda LEN bypass
#   stykač priamo (bez TRIAC-preload/armed — zbytočné pre zriedkavý nočný
#   event, mierne iskrenie prijateľné), vôbec sa nedotýka izolačného
#   stykača/EMI filtra/TRIAC-u. (3) Keď bypass vedie, EMI filter je tiež
#   obídený — v poriadku, bez vedenia TRIAC-u niet čo filtrovať.
# Doplnené 2026-09-13/14: Čerpadlo TUV — 2 dôvody podľa vzoru TECH EU-11
#   Eco Circulation (regulátor, ktorý ESP32 nahrádza; manuál preštudovaný),
#   oba ROZDIELOVO (bojler vs. vratná voda priamo, nie proti pevnému číslu
#   ako originál): (1) ODBER — prietok + rozdiel > 5°C → beh na pevný čas
#   (5 min). (2) ÚDRŽBA — rozdiel > 3°C bez ohľadu na odber → beh KONTINUÁLNE
#   (udrží teplú vodu v systéme priebežne, náhrada za "nechať bežať 24/7").
#   Oba zdieľajú časové okno (deň/víkend, na minúty, laditeľné z HA).
#   Defaulty NEOVERENÉ, doladiť pri oživení. Detaily: TODO_fve_diverter.md.
# Doplnené 2026-09-14: MANUÁLNE VYNÚTENIE výkonu (TUV aj podlaha samostatne,
#   laditeľné z HA) — 0=auto, 10-100%=vynúť hodnotu bez ohľadu na FVE prebytok
#   aj watchdog (rovnaký princíp ako Daikin). Použitie: napr. výpadok siete +
#   generátor. Prechádza cez existujúcu ZOP/ROZ sekvenciu (TRIAC-preload),
#   nie priamu vetvu ako Daikin. Prebíja aj deň/noc izolačného stykača, keď
#   je aktívne (potrebuje živú TRIAC vetvu pri hodnotách <100 %). Tepelný
#   strop zostáva rešpektovaný.
# Doplnené 2026-09-13: DETAIL panel (dole) — rbdimmer je konkrétne 40A-CS
#   variant (built-in current + teplotný senzor, potvrdené z pinoutu výrobcu).
#   TEMP/CUR-S piny NEjdú cez DimmerLink (ten prenáša cez I2C len VCC/GND/
#   Z-C/DIM) — musia priamo na ADC ESP32 (GPIO34/35 TUV, GPIO36/39 podlaha,
#   zámerne ADC1, nie ADC2, kvôli WiFi). FAN+5V pin dosky = jej vlastný malý
#   fan na chladiči TRIAC-u — úplne nezávislé od skriňového ventilátora
#   (GPIO25 vyššie), doska si ho rieši sama, ESP32 sa toho nedotýka.

W, H = 1660, 3300
el = []

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def box(x, y, w, h, title, sub="", fill="#ffe0b2", stroke="#e65100", tcol="#3e2723", rx=8, fs=15):
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    cx = x + w/2
    if sub:
        el.append(f'<text x="{cx}" y="{y+h/2-3}" text-anchor="middle" '
                  f'font-size="{fs}" font-weight="bold" fill="{tcol}">{esc(title)}</text>')
        el.append(f'<text x="{cx}" y="{y+h/2+15}" text-anchor="middle" '
                  f'font-size="12" fill="{tcol}">{esc(sub)}</text>')
    else:
        el.append(f'<text x="{cx}" y="{y+h/2+5}" text-anchor="middle" '
                  f'font-size="{fs}" font-weight="bold" fill="{tcol}">{esc(title)}</text>')

def txt(x, y, s, fs=13, anchor="start", col="#222", bold=False, italic=False):
    w = ' font-weight="bold"' if bold else ''
    i = ' font-style="italic"' if italic else ''
    el.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{fs}" '
              f'fill="{col}"{w}{i}>{esc(s)}</text>')

def dbox(x, y, w, h, title, sub="", fill="#eceff1", stroke="#607d8b", tcol="#37474f", rx=8, fs=12.5):
    # prerušovaný rámik = ALTERNATÍVA / zatiaľ neoverené, nie aktuálne zapojenie
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-dasharray="6,4"/>')
    cx = x + w/2
    if sub:
        el.append(f'<text x="{cx}" y="{y+h/2-3}" text-anchor="middle" '
                  f'font-size="{fs}" font-weight="bold" fill="{tcol}">{esc(title)}</text>')
        el.append(f'<text x="{cx}" y="{y+h/2+14}" text-anchor="middle" '
                  f'font-size="10.5" fill="{tcol}">{esc(sub)}</text>')
    else:
        el.append(f'<text x="{cx}" y="{y+h/2+5}" text-anchor="middle" '
                  f'font-size="{fs}" font-weight="bold" fill="{tcol}">{esc(title)}</text>')

def wire(pts, col="#c62828", wdth=3, dash="", arrow=False):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    a = ' marker-end="url(#arr)"' if arrow else ''
    p = " ".join(f"{x},{y}" for x, y in pts)
    el.append(f'<polyline points="{p}" fill="none" stroke="{col}" '
              f'stroke-width="{wdth}"{d}{a}/>')

def resistor_v(x, y_top, y_bottom, col="#5d4037", wdth=1.8, n=6, dx=7):
    """Zvislý zig-zag symbol rezistora (US schéma štýl) medzi y_top a y_bottom."""
    h = y_bottom - y_top
    pts = [(x, y_top)]
    for i in range(1, n):
        pts.append((x + (dx if i % 2 else -dx), y_top + h/n*i))
    pts.append((x, y_bottom))
    wire(pts, col=col, wdth=wdth)

# ---- header / defs ----
el.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fcfcfa"/>')
el.append('<defs><marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="3" '
          'orient="auto" markerUnits="strokeWidth">'
          '<path d="M0,0 L8,3 L0,6 z" fill="#1565c0"/></marker></defs>')
txt(W/2, 36, "FVE automatizácia prebytkov — ESP32 #2  (TUV 3 kW → L1 · PODLAHA 600 W → L2)",
    fs=22, anchor="middle", col="#0d47a1", bold=True)
txt(W/2, 58, "Revízia · 2026-09-13 · TRIAC fázovka (2× DimmerLink, I2C) + PI · 2 izolačné + 2 bypass stykače · EMI filtre",
    fs=13, anchor="middle", col="#555")

# ============================================================
# SILNOPRÚD
# ============================================================
txt(120, 92, "SILNOPRÚD", fs=16, col="#b71c1c", bold=True)
el.append('<line x1="120" y1="98" x2="1140" y2="98" stroke="#b71c1c" stroke-width="1.5"/>')

L1, L2 = 210, 560          # záťažové vetvy (dimmer + špirála) — rozšírené, nech je
                           # miesto na bypass vetvu obchádzajúcu CELÚ vetvu (viď nižšie)
P1, P2 = 840, 1000         # obehové čerpadlá
PLOG   = 920               # istič pre logiku + čerpadlá
NX     = 1110              # N zvislá k zbernici

# Hlavný istič + RCD
box(120, 110, 1020, 42, "HLAVNÝ 3F ISTIČ", "L1   L2   L3   N", fill="#eeeeee", stroke="#424242")
box(120, 188, 1020, 50, "RCD 4-pól · 25 A · 30 mA · TYP A",
    "(TRIAC fázovka → jednosmerné zložky → TYP A povinný; L1+L2 zdieľajú N)",
    fill="#d1c4e9", stroke="#4527a0")
for xx in (L1, L2, PLOG, NX):
    wire([(xx,152),(xx,188)], col="#c62828", wdth=2.5)

# Ističe
box(L1-48, 280, 96, 42, "B16", "TUV / L1", fill="#eeeeee", stroke="#424242", fs=14)
box(L2-48, 280, 96, 42, "B6",  "podlaha / L2", fill="#eeeeee", stroke="#424242", fs=13)
box(PLOG-60, 280, 120, 42, "B6", "logika + čerpadlá", fill="#eeeeee", stroke="#424242", fs=13)
for xx in (L1, L2, PLOG):
    wire([(xx,238),(xx,280)], col="#c62828", wdth=2.5)
wire([(NX,238),(NX,760)], col="#1565c0", wdth=2.5)   # N dolu k zbernici

# Stykače (2 samostatné)
box(L1-78, 360, 156, 58, "STYKAČ 25 A (2×NO)", "cievka 230 V ◄ relé GPIO17",
    fill="#ffe0b2", stroke="#e65100", fs=13)
box(L2-78, 360, 156, 58, "STYKAČ 25 A (2×NO)", "cievka 230 V ◄ relé GPIO19",
    fill="#ffe0b2", stroke="#e65100", fs=13)
wire([(L1,322),(L1,360)], wdth=2.5)
wire([(L2,322),(L2,360)], wdth=2.5)

# EMI filtre
box(L1-92, 452, 184, 58, "EMI FILTER · 30 A", "FN2030-30-08 / RS PRO 237-8717",
    fill="#b2dfdb", stroke="#00695c", tcol="#004d40", fs=12.5)
box(L2-92, 452, 184, 58, "EMI FILTER · 10 A", "Schurter 5500.2623.01",
    fill="#b2dfdb", stroke="#00695c", tcol="#004d40", fs=12)
wire([(L1,418),(L1,452)], wdth=2.5)
wire([(L2,418),(L2,452)], wdth=2.5)
txt((L1+L2)/2, 445, "LINE-L/LINE-N ↑ sieť · LOAD-L/LOAD-N ↓ dimmer · kovové telo → PE",
    fs=10, anchor="middle", col="#00695c", italic=True)

# rbdimmery — Riadenie TRIAC-u: DimmerLink modul (I2C, hardvérový Z-C/firing),
# NIE ESP32 GPIO priamo. Z-C sníma fázu (L1/L2) hardvérovo, DIM0 → GATE rbdimmer.
def dimmer_branch(Lx, dtitle, dsub, dl_title, dl_sub):
    wire([(Lx,510),(Lx,552)], wdth=2.5)
    box(Lx-62, 552, 124, 52, dtitle, dsub, fill="#ffccbc", stroke="#bf360c", fs=11.5)
    wire([(Lx,604),(Lx,614)], wdth=2.5)
    # DimmerLink modul — hardvérový firing (Z-C tap z fázy + GATE → rbdimmer),
    # riadený z ESP32 cez I2C (nie priamo z tejto silnoprúdovej vetvy).
    box(Lx-68, 614, 136, 34, dl_title, dl_sub, fill="#bbdefb", stroke="#0d47a1", fs=9.5)
    wire([(Lx,648),(Lx,656)], wdth=2.5)

dimmer_branch(L1, "rbdimmer1", "40A TUV 3kW", "DimmerLink1", "I2C 0x50 · Z-C←L1")
dimmer_branch(L2, "rbdimmer2", "40A podl.600W", "DimmerLink2", "I2C 0x51 · Z-C←L2")

# BYPASS STYKAČ — 2026-09-14: paralelne k CELEJ vetve (izolačný stykač + EMI
# filter + TRIAC/DimmerLink), NIE len k TRIAC-u. Odbočka hneď za ističom,
# späť sa napojí tesne pred špirálou. Keď bypass vedie, celá vetva vľavo
# (stykač, EMI filter, TRIAC) je úplne obídená — nulová strata aj nulové EMI
# (TRIAC nevedie, netreba ho filtrovať).
def bypass_branch(Lx, bgpio):
    bx = Lx + 150
    bw, bh = 96, 46
    by = 460
    wire([(Lx,322),(bx,322),(bx,by)], wdth=2.5)
    box(bx-bw/2, by, bw, bh, "BYPASS", f"◄{bgpio}", fill="#ffe0b2", stroke="#e65100", fs=12)
    wire([(bx,by+bh),(bx,656),(Lx,656)], wdth=2.5)
    txt(bx, by-8, "obchádza celú vetvu", fs=9, anchor="middle", col="#e65100", italic=True)

bypass_branch(L1, "GPIO16")
bypass_branch(L2, "GPIO18")

# Špirály
box(L1-62, 656, 124, 52, "TUV špirála", "3 kW @ L1", fill="#ffcdd2", stroke="#b71c1c")
box(L2-62, 656, 124, 52, "Podlaha špirála", "600 W @ L2", fill="#ffcdd2", stroke="#b71c1c", fs=13)

# Obehové čerpadlá (napájané z B6 logika, spínané relé)
wire([(PLOG,322),(PLOG,530)], wdth=2.5)
wire([(PLOG,530),(P1,530),(P1,552)], wdth=2.5)
wire([(PLOG,530),(P2,530),(P2,552)], wdth=2.5)
box(P1-70, 552, 140, 52, "Čerpadlo TUV", "◄ relé GPIO26", fill="#ffcdd2", stroke="#b71c1c", fs=13)
box(P2-70, 552, 140, 52, "Čerpadlo podlaha", "◄ relé GPIO25", fill="#ffcdd2", stroke="#b71c1c", fs=13)

# N zbernica
wire([(140,760),(NX+20,760)], col="#1565c0", wdth=2.5)
for xx in (L1, L2):
    wire([(xx,708),(xx,760)], col="#1565c0", wdth=2)
for xx in (P1, P2):
    wire([(xx,604),(xx,760)], col="#1565c0", wdth=2)
txt(150, 752, "N — spoločná zbernica (vedená cez RCD)", fs=12, col="#1565c0", bold=True)

# ============================================================
# RIADENIE
# ============================================================
txt(120, 812, "RIADENIE — ESP32 DevKit  (TUV: nahrádza TechController ECO · podlaha: nová funkcia, Daikin OPTO)",
    fs=16, col="#0d47a1", bold=True)
el.append(f'<line x1="120" y1="818" x2="{W-40}" y2="818" stroke="#0d47a1" stroke-width="1.5"/>')

# ESP32
Ex, Ey, Ew, Eh = 700, 850, 270, 392
box(Ex, Ey, Ew, Eh, "ESP32-WROOM-32D", "", fill="#bbdefb", stroke="#0d47a1", fs=17)
txt(Ex+Ew/2, Ey+38, "DevKitC 38-pin · piny: esp32_pinout_zapojenie", fs=11, anchor="middle", col="#0d47a1")

# Ľavé vstupy (senzory)
left = [
    ("DS18B20 B1 — TUV bojler", "GPIO21", "#c8e6c9", "#1b5e20"),
    ("DS18B20 B2 — vratná voda TUV", "GPIO5", "#c8e6c9", "#1b5e20"),
    ("DS18B20 B3 — voda podlaha", "GPIO13", "#c8e6c9", "#1b5e20"),
    ("Prietok studenej → TUV (odber TÚV)", "GPIO4", "#c8e6c9", "#1b5e20"),
    ("OPTO — Daikin žiada čerp. podlahy", "GPIO27", "#fff3e0", "#e65100"),
    ("OPTO — Daikin ohrev TUV (K3M)", "GPIO14", "#fff3e0", "#e65100"),
]
y0, step = 888, 51
# DS18B20 od 2026-11-14 KAŽDÝ NA VLASTNOM PINE (lacné klony nejdú po dvoch na
# jednej zbernici) — každý DATA vodič má vlastný pull-up 4,7 kΩ na 3,3 V
# (R1 G21, R7 G5, R8 G13, v skrini pri ESP). B4 (skriňa) zrušený.
_pull = {"GPIO21": "R1", "GPIO5": "R7", "GPIO13": "R8", "GPIO4": "R6"}  # R6 = prietokomer
for i,(name,gpio,fl,st) in enumerate(left):
    cy = y0 + i*step
    box(96, cy-19, 250, 38, name, "", fill=fl, stroke=st, fs=11.5)
    wire([(346,cy),(Ex,cy)], col="#2e7d32", wdth=1.6, arrow=True)
    txt(Ex-6, cy-4, gpio, fs=11, anchor="end", col="#0d47a1", bold=True)
    if gpio in _pull:
        _rx = 560
        el.append(f'<circle cx="{_rx}" cy="{cy}" r="3" fill="#b71c1c"/>')
        resistor_v(_rx, cy-38, cy-8, col="#b71c1c", dx=5)
        wire([(_rx, cy-8), (_rx, cy)], col="#b71c1c", wdth=1.8)
        wire([(_rx-8, cy-38), (_rx+8, cy-38)], col="#b71c1c", wdth=1.8)
        txt(_rx - 12, cy-28, "+3,3V", fs=9, anchor="end", col="#b71c1c", bold=True)
        txt(_rx + 12, cy-18, f"{_pull[gpio]} 4,7kΩ", fs=9.5, col="#b71c1c", bold=True)
txt(96, y0+len(left)*step-8,
    "DS18B20 × 3 — KAŽDÝ na vlastnom pine (klony nejdú po dvoch na zbernici)",
    fs=10.5, col="#1b5e20", italic=True)
txt(96, y0+len(left)*step+7,
    "Každý DATA vodič vlastný pull-up 4,7 kΩ na 3,3 V: R1 G21 · R7 G5 · R8 G13",
    fs=10.5, col="#b71c1c", italic=True, bold=True)
txt(96, y0+len(left)*step+22,
    "Každý DS18B20: červený VDD → 3,3 V · čierny → GND · žltý DATA → svoj GPIO",
    fs=10, col="#555", italic=True)

# Pravé výstupy (akčné členy)
right = [
    ("GPIO2/15", "I2C → DimmerLink1 (0x50) + DimmerLink2 (0x51)"),
    ("GPIO17", "Relé → cievka stykača TUV (izolačný)"),
    ("GPIO16", "Relé → cievka BYPASS stykača TUV"),
    ("GPIO19", "Relé → cievka stykača podlaha (izolačný)"),
    ("GPIO18",  "Relé → cievka BYPASS stykača podlaha"),
    ("GPIO26", "Relé → čerpadlo TUV"),
    ("GPIO25", "Relé → čerpadlo podlaha"),
    ("GPIO23", "PWM priamo → pin 4 ventilátora (4-vodič.)"),
]
y0r, stepr, rh = 905, 42, 34
cy_of = {}
for i,(gpio,name) in enumerate(right):
    cy = y0r + i*stepr
    cy_of[gpio] = cy
    box(1075, cy-rh/2, 260, rh, name, "", fill="#ffe0b2", stroke="#e65100", fs=10.5)
    wire([(Ex+Ew,cy),(1075,cy)], col="#1565c0", wdth=1.6, arrow=True)
    txt(Ex+Ew+6, cy-4, gpio, fs=11, anchor="start", col="#0d47a1", bold=True)

# Zoskupenie do 3× samostatný 2-kanálový relé modul (namiesto 1× spoločného)
def relay_module_bracket(gpio_a, gpio_b, label):
    bx = 1075 + 260 + 6
    ya, yb = cy_of[gpio_a], cy_of[gpio_b]
    wire([(bx,ya),(bx+6,ya)], col="#757575", wdth=1.3)
    wire([(bx,ya),(bx,yb)], col="#757575", wdth=1.3)
    wire([(bx,yb),(bx+6,yb)], col="#757575", wdth=1.3)
    txt(bx+11, (ya+yb)/2+4, label, fs=9.5, col="#757575", italic=True)

txt(1075+260+6, cy_of["GPIO2/15"]-7, "GPIO2=SDA/TX pin · GPIO15=SCL/RX pin", fs=9.5, col="#757575", italic=True)
txt(1075+260+6, cy_of["GPIO2/15"]+9, "pull-up 4,7kΩ→3,3V POVINNÝ (1× SDA + 1× SCL, spoločné pre celú zbernicu)", fs=9.5, col="#b71c1c", italic=True)
# Vizuálny symbol pull-up rezistorov na I2C vodiči (SDA aj SCL — zjednodušene
# nakreslené ako 1 spoločný vodič v tomto prehľade, reálne 2 samostatné
# rezistory, jeden na SDA, jeden na SCL, pozri DETAIL panely nižšie).
_i2c_cy = cy_of["GPIO2/15"]
_rx = 1052   # vpravo od textu "GPIO2/15" (končí ~1032), vľavo od boxu (1075)
wire([(_rx, _i2c_cy - 48), (_rx, _i2c_cy - 38)], col="#b71c1c", wdth=1.8)
resistor_v(_rx, _i2c_cy - 38, _i2c_cy - 8, col="#b71c1c")
wire([(_rx, _i2c_cy - 8), (_rx, _i2c_cy)], col="#b71c1c", wdth=1.8)
el.append(f'<circle cx="{_rx}" cy="{_i2c_cy}" r="2.5" fill="#b71c1c"/>')
txt(_rx - 8, _i2c_cy - 43, "+3,3V", fs=9, anchor="end", col="#b71c1c", bold=True)
txt(_rx - 8, _i2c_cy - 20, "2× 4,7kΩ", fs=9, anchor="end", col="#b71c1c")
relay_module_bracket("GPIO17", "GPIO16", "2-kan. modul")
relay_module_bracket("GPIO19", "GPIO18", "2-kan. modul")
relay_module_bracket("GPIO26", "GPIO25", "2-kan. modul")

# HLK napájanie
box(360, 1300, 230, 66, "Mean Well MDR-20-5", "230V → 5V / 3A · DIN", fill="#e0e0e0", stroke="#424242")
wire([(475,1300),(475,1252),(Ex+60,1252)], col="#000", wdth=2)
txt(600, 1330, "L,N z B6  →  5V / GND do ESP32", fs=11, col="#424242")

# Ventilátor skrine — 4-vodičový PWM fan (GND/VCC/Tacho/PWM), žiadny MOSFET
Fx, Fw = 1250, 380
box(Fx, 1268, Fw, 78, "Ventilátor skrine 5 V — 4-vodič. PWM", "chladenie dimmerov · floor 35% + dobeh 60s",
    fill="#ffcdd2", stroke="#b71c1c", fs=12)
txt(Fx+10, 1364, "pin1 GND · pin2 VCC · pin3 Tacho→GPIO22 · pin4 PWM◄GPIO23", fs=9.5, col="#8d0000")
Rx2, Rw2 = Fx+40, 200
box(Rx2, 1395, Rw2, 46, "ZRUŠENÉ: relé cutoff VCC", "nezapojené (GPIO13 = DS18B20 B3)",
    fill="#f5f5f5", stroke="#9e9e9e", fs=10.5)
wire([(1290,1260),(1290,1268)], col="#1565c0", wdth=2)             # PWM od GPIO23 boxu
wire([(Rx2+Rw2/2,1346),(Rx2+Rw2/2,1395)], col="#c62828", wdth=2)   # 5V → relé
wire([(Rx2+Rw2/2,1441),(Fx+100,1441),(Fx+100,1346)], col="#c62828", wdth=2)  # relé → VCC fanu
txt(Fx, 1465, "Relé ZRUŠENÉ 2026-11-10 (PWM 0 % fan zastaví) — VCC priamo 5 V; GPIO13 teraz DS18B20 B3.", fs=10, col="#0d47a1", italic=True)
txt(Fx, 1480, "PWM na GPIO23, priamo do pinu 4 fanu. Tacho (pin3) → GPIO22 (vedľa PWM, od 2026-11-10).", fs=10, col="#0d47a1", italic=True)

# Farby vodičov fanu — VŠEOBECNÝ PC/Noctua 4-pin štandard, NIE overené pre tento
# konkrétny kus (značka/model nezaznamenané) — over multimetrom pred zapojením.
FCx, FCy, FCw, FCh = Fx, 1500, Fw, 170
el.append(f'<rect x="{FCx}" y="{FCy}" width="{FCw}" height="{FCh}" rx="8" '
          f'fill="#fff3e0" stroke="#e65100" stroke-width="2"/>')
txt(FCx+14, FCy+22, "Farby vodičov (štandard, OVERIŤ multimetrom!)", fs=11, bold=True, col="#bf360c")
fan_colors = [
    ("pin1 GND", "čierna"),
    ("pin2 VCC", "žltá"),
    ("pin3 Tacho", "zelená"),
    ("pin4 PWM", "modrá"),
]
for i,(pin,col_) in enumerate(fan_colors):
    txt(FCx+14, FCy+46+i*20, f"{pin} — {col_}", fs=10.5, col="#5d4037")
txt(FCx+14, FCy+46+4*20+4, "Intel/Noctua konvencia — iný výrobca môže mať iné farby,", fs=9, col="#e65100", italic=True)
txt(FCx+14, FCy+46+4*20+18, "rozhoduje poloha pinu (zárez/šípka na konektore fanu), nie farba.", fs=9, col="#e65100", italic=True)

# Poznámky
nx, ny, nw, nh = 645, 1268, 590, 900
el.append(f'<rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="8" '
          f'fill="#fff9c4" stroke="#f9a825" stroke-width="2"/>')
txt(nx+14, ny+24, "Kľúčové poznámky", fs=14, col="#e65100", bold=True)
notes = [
    "PI regulácia beží NA ESP32 — číta Shelly 3EM (súčet fáz!) priamo.",
    "EMI filter: LINE→sieť, LOAD→dimmer, kovové telo POVINNE na PE.",
    "Sériová tlmivka 200 µH/25 A LEN ak meranie (AM/DAB/WiFi/Zigbee) ukáže rušenie.",
    "600 W filter: Schurter 5500.2623.01 (10A, máme) — montáž až po EMI meraní.",
    "⚠️ TOPOLÓGIA 2026-09-14: BYPASS je paralelne k CELEJ vetve (izolačný stykač",
    "+ EMI filter + TRIAC/DimmerLink), NIE len k TRIAC-u. Dve nezávislé paralelné",
    "cesty od ističa k špirále — bypass obchádza úplne všetko vrátane EMI filtra",
    "(keď TRIAC nevedie, niet čo filtrovať). Stykače sa navzájom NIKDY neovplyvňujú.",
    "Izolačný stykač (TRIAC vetva) = mechanické odpojenie pri poruche TRIAC-u,",
    "spína čisto DEŇ/NOC (SNTP + hodiny laditeľné z HA), NIE hysteréza na duty",
    "(inak by sa spínal stovky-krát denne). Nezávislý od bypassu. Jediná výnimka:",
    "manuálne vynútenie výkonu (nižšie) prebíja deň/noc, keď je aktívne.",
    "MANUÁLNE VYNÚTENIE výkonu (2026-09-14, laditeľné z HA, TUV aj podlaha",
    "samostatne): 0=auto, 10-100%=vynúť túto hodnotu bez ohľadu na FVE prebytok",
    "aj watchdog (napr. výpadok siete + generátor → nastav 100% → ide cez bypass).",
    "Bypass stykač: FVE cesta má ZOP ≥97 % / ROZ ≤95 % (hysteréza + TRIAC-preload/",
    "armed, aby TRIAC prevzal prúd predtým) — rieši časté prepínanie bez opotrebenia.",
    "Daikin cesta (viď nižšie) je NEZÁVISLÁ od FVE hysterézy — priamo, bez preloadu.",
    "PODLAHA má IDENTICKÚ topológiu aj logiku ako TUV vyššie (bypass paralelne",
    "k celej vetve, izolačný stykač čisto deň/noc, FVE ZOP/ROZ hysteréza) — jediný",
    "rozdiel je, že podlaha NEMÁ Daikin backup cestu (tá je výhradne pre TUV).",
    "⚠️ TechController ECO ↔ Daikin/podlaha: NESÚVISIA. TechController = LEN čerpadlo",
    "TUV (teplota/prietok). Podlaha+OPTO Daikin = NOVÁ funkcia, nie náhrada TechControlleru.",
    "OPTO vstup z Daikinu izoluje jeho signál → čerpadlo beží aj keď Daikin OFF.",
    "Daikin ohrev TUV (GPIO14) = AC 230 V OPTO paralelne na cievku stykača K3M",
    "(A1/A2, hydrobox EHBH08DA9W7) — NIE suchý kontakt (silové kontakty K3M pri",
    "3,3 V nespoľahlivé). 2-kan. AC opto modul: K3M → GPIO14, čerpadlo podl. → GPIO27.",
    "Daikin GPIO14 ZAP → zopne LEN bypass stykač TUV, priamo, okamžite (bez FVE",
    "hysterézy) — bez ohľadu na FVE prebytok aj watchdog. Izolačný stykač/EMI/TRIAC",
    "sa vôbec nedotýka, beží ďalej nezávisle podľa deň/noc. Limit: len max_t_tuv.",
    "Čerpadlo TUV (2026-09-13/14, vzor TECH EU-11 Eco Circulation — nahrádzaný",
    "regulátor), 2 dôvody navyše k FVE/Daikin: ODBER — prietok A rozdiel bojler−",
    "vratná > 5°C → beh na pevný čas (5 min). ÚDRŽBA — rozdiel > 3°C bez ohľadu",
    "na odber → beh KONTINUÁLNE kým rozdiel neklesne (udrží teplú vodu v systéme).",
    "Oba zdieľajú časové okno (deň/víkend, na minúty, laditeľné z HA).",
    "Pull-up: OPTO 27 + 14 = interný (pullup:true), debounce delayed_on/off 500 ms.",
    "OPTO modul napájať z 3,3 V (nie 5 V); GPIO14 bez sériového rezistora (opto obmedzí prúd).",
    "TRIAC firing: DimmerLink modul (hardvérový Z-C/firing, I2C) — NIE natívny ac_dimmer.",
    "2× DimmerLink 1CH, vlastná fáza/adresa (0x50 TUV, 0x51 podlaha) — 2. kus nastaviť",
    "na 0x51 RAZ vopred (sám na zbernici), potom spojiť na spoločnú I2C.",
    "Relé: 3× 2-kanál TUV(17+16), podlaha(19+18), čerpadlá(26+25), ALWAYS_OFF+inverted.",
    "Watchdog: Shelly/meranie nedostupné > 60 s → dimmery OKAMŽITE na 0 %, bypass",
    "rozopne cez bežnú ROZ sekvenciu (TRIAC-preload, nie narovinu). Daikin cesta nezávislá.",
    "Ventilátor skrine: 4-vodičový PWM fan, rýchlosť rieši fan sám (GPIO23) — f(výkon dimmerov).",
    "Záložné relé VCC fanu ZRUŠENÉ (PWM 0 % fan zastaví) — GPIO13 použitý pre DS18B20 B3.",
    "Tacho ventilátora (pin3) na GPIO22 (pulse_counter, ×0,5 pre 2 pulzy/otáčku) —",
    "presunuté 2026-11-10 z GPIO4 (vedľa PWM GPIO23); prietok TUV teraz na GPIO4.",
    "Fyzicky GPIO2/15: rezistor → pin header; oba DimmerLink vodiče (skrútené) → svorka.",
]
for i,n in enumerate(notes):
    txt(nx+14, ny+46+i*18, "• "+n, fs=11.2, col="#5d4037")

# Legenda
lx, ly = 1330, 110
el.append(f'<rect x="{lx}" y="{ly}" width="300" height="186" rx="8" '
          f'fill="#ffffff" stroke="#888" stroke-width="1.5"/>')
txt(lx+12, ly+22, "Legenda", fs=14, bold=True, col="#333")
leg = [("#ffe0b2","#e65100","Silnoprúd / spínanie"),
       ("#b2dfdb","#00695c","EMI filter (Schaffner)"),
       ("#ffcdd2","#b71c1c","Záťaž (špirály, čerpadlá)"),
       ("#bbdefb","#0d47a1","Riadenie / ESP32"),
       ("#c8e6c9","#1b5e20","Senzory"),
       ("#e1f5fe","#01579b","Suchý kontakt (bez opto)"),
       ("#d1c4e9","#4527a0","Ochrana (RCD)"),
       ("#e0e0e0","#424242","Napájanie / istenie")]
for i,(fl,st,lab) in enumerate(leg):
    yy = ly+40+i*18
    el.append(f'<rect x="{lx+14}" y="{yy-10}" width="22" height="13" rx="3" fill="{fl}" stroke="{st}"/>')
    txt(lx+44, yy, lab, fs=11.5, col="#333")

# ============================================================================
# ZÁLOHA (spare, nezapojené) — DimmerLink 2CH
# ============================================================================
Sx, Sw = 1330, 300
Sy, Sh = 320, 186
el.append(f'<rect x="{Sx-10}" y="{Sy-14}" width="{Sw+20}" height="{Sh}" rx="10" '
          f'fill="#fafafa" stroke="#607d8b" stroke-width="1.5" stroke-dasharray="4,3"/>')
txt(Sx+Sw/2, Sy+8, "ZÁLOHA (spare, nezapojené)", fs=13.5, anchor="middle", col="#37474f", bold=True)
txt(Sx+Sw/2, Sy+26, "DimmerLink 2CH — náhradný diel", fs=11, anchor="middle", col="#607d8b", italic=True)
notes_spare = [
    "Máme aj 1× DimmerLink 2CH (kúpený skôr,",
    "PRED rozhodnutím o 2× 1CH vyššie).",
    "NEPOUŽÍVA sa v zapojení — 1 zdieľaný Z-C",
    "pre oba kanály (predpokladá spoločnú fázu),",
    "nehodí sa pre TUV/L1 + podlaha/L2 naraz.",
    "Odložený ako náhradný diel — ak by jeden",
    "z 2× DimmerLink 1CH zlyhal, dá sa dočasne",
    "nasadiť (1 kanál, druhý ostane nevyužitý).",
]
for i,n in enumerate(notes_spare):
    txt(Sx, Sy+50+i*15, n, fs=9.5, col="#455a64")

# ============================================================================
# DETAIL: rbdimmer 40A-CS ↔ DimmerLink ↔ ESP32 (+ vlastný fan chladiča)
# ============================================================================
# Dva SAMOSTATNÉ, plne popísané panely (TUV / PODLAHA) — zámerne bez
# "je to rovnaké, len iné čísla" skratky, nech je pri práci na jednej vetve
# vidno hneď všetko potrebné bez preskakovania medzi dvoma miestami v obrázku.
def dimmer_detail_panel(y_top, branch, dl_num, dl_addr, zc_phase, rb_num, rb_load,
                         temp_gpio, cur_gpio, fan_gpio):
    txt(120, y_top, f"DETAIL — vetva {branch}: rbdimmer{rb_num} 40A-CS ↔ DimmerLink{dl_num} ↔ ESP32",
        fs=16, col="#0d47a1", bold=True)
    el.append(f'<line x1="120" y1="{y_top+6}" x2="{W-40}" y2="{y_top+6}" '
              f'stroke="#0d47a1" stroke-width="1.5"/>')
    txt(120, y_top+22, f"{rb_load} · I2C adresa {dl_addr} · Z-C snímaný z {zc_phase}",
        fs=11, col="#555", italic=True)

    top = y_top + 43
    # -- ESP32: TRI nezávislé "porty" von — napájanie+I2C ku DimmerLinku,
    # ADC priamo k doske, FAN riadenie priamo k doske (obe bypassujú DimmerLink) --
    Ex, Ey, Ew, Eh = 120, top, 220, 195
    el.append(f'<rect x="{Ex}" y="{Ey}" width="{Ew}" height="{Eh}" rx="8" '
              f'fill="#bbdefb" stroke="#0d47a1" stroke-width="2"/>')
    txt(Ex+Ew/2, Ey+22, "ESP32", fs=16, anchor="middle", bold=True, col="#0d47a1")
    txt(Ex+12, Ey+45, "Napájanie + I2C → DimmerLink:", fs=10, bold=True, col="#0d47a1")
    txt(Ex+12, Ey+60, "3.3V, GND, GPIO2=SDA/TX, GPIO15=SCL/RX", fs=9.5, col="#0d47a1")
    txt(Ex+12, Ey+73, "(pull-up 4,7kΩ→3,3V: 1× SDA + 1× SCL pre celú zbernicu)", fs=8.5, col="#b71c1c", italic=True)
    txt(Ex+12, Ey+82, "ADC priamo (obchádza DimmerLink):", fs=10, bold=True, col="#bf360c")
    txt(Ex+12, Ey+97, f"{temp_gpio} = TEMP  ·  {cur_gpio} = CUR-S", fs=9.5, col="#bf360c")
    txt(Ex+12, Ey+111, "(ADC1, attenuation 12dB — WiFi-safe)", fs=8.5, italic=True, col="#bf360c")
    txt(Ex+12, Ey+134, "FAN riadenie priamo (bez MOSFETu):", fs=10, bold=True, col="#e65100")
    txt(Ex+12, Ey+149, f"{fan_gpio} → FAN pin (on/off, nie PWM)", fs=9.5, col="#e65100")
    txt(Ex+12, Ey+163, "(doska má vlastný tranzistor — pozri", fs=8.5, italic=True, col="#e65100")
    txt(Ex+12, Ey+175, "poznámku dole, over pri oživení)", fs=8.5, italic=True, col="#e65100")

    I2C_Y, ADC_Y, FAN_Y = Ey+40, Ey+78, Ey+130

    # -- DimmerLink modul — rieši LEN VCC/GND/Z-C/DIM, nič iné --
    Dx, Dy, Dw, Dh = 420, I2C_Y-30, 190, 60
    box(Dx, Dy, Dw, Dh, f"DimmerLink{dl_num}", f"I2C {dl_addr} · Z-C ← {zc_phase}",
        fill="#bbdefb", stroke="#0d47a1", fs=12)
    wire([(Ex+Ew, I2C_Y),(Dx, I2C_Y)], col="#0d47a1", wdth=2, arrow=True)
    # Pull-up symbol (rovnaký fyzický rezistor ako pri druhej vetve — JEDEN
    # spoločný set pre celú I2C zbernicu, nie samostatný per branch/panel).
    _rx3 = (Ex + Ew + Dx) / 2
    wire([(_rx3, I2C_Y - 42), (_rx3, I2C_Y - 32)], col="#b71c1c", wdth=1.5)
    resistor_v(_rx3, I2C_Y - 32, I2C_Y - 6, col="#b71c1c", n=6, dx=5)
    wire([(_rx3, I2C_Y - 6), (_rx3, I2C_Y)], col="#b71c1c", wdth=1.5)
    el.append(f'<circle cx="{_rx3}" cy="{I2C_Y}" r="2" fill="#b71c1c"/>')
    txt(_rx3, I2C_Y - 47, "+3,3V", fs=8, anchor="middle", col="#b71c1c", bold=True)
    txt(_rx3 + 6, I2C_Y - 17, "4,7kΩ", fs=7, anchor="start", col="#b71c1c")
    txt(_rx3, I2C_Y + 14, "(spoločné s", fs=7, anchor="middle", col="#b71c1c", italic=True)
    txt(_rx3, I2C_Y + 24, "druhou vetvou)", fs=7, anchor="middle", col="#b71c1c", italic=True)

    # -- rbdimmer 40A-CS — 8-pin konektor, vypísaný po jednom pine (žiadna
    # zámena "čo ide kam" nie je možná) --
    Rx, Ry, Rw = 700, top-10, 340
    pins = [
        ("VCC",   f"← DimmerLink{dl_num}",       "#bbdefb", "#0d47a1"),
        ("GND",   f"← DimmerLink{dl_num}",       "#bbdefb", "#0d47a1"),
        ("Z-C",   f"← DimmerLink{dl_num}",       "#bbdefb", "#0d47a1"),
        ("DIM",   f"← DimmerLink{dl_num}",       "#bbdefb", "#0d47a1"),
        ("TEMP",  f"→ ESP32 {temp_gpio} priamo", "#ffccbc", "#bf360c"),
        ("CUR-S", f"→ ESP32 {cur_gpio} priamo",  "#ffccbc", "#bf360c"),
        ("FAN",   f"← ESP32 {fan_gpio} priamo",  "#ffccbc", "#bf360c"),
        ("5V",    "→ vlastný fan (+), zdroj TODO","#fff3e0", "#e65100"),
    ]
    row_h, row_gap = 22, 3
    Rh = 34 + len(pins)*(row_h+row_gap)
    el.append(f'<rect x="{Rx}" y="{Ry}" width="{Rw}" height="{Rh}" rx="10" '
              f'fill="#fff8e1" stroke="#e65100" stroke-width="2"/>')
    txt(Rx+Rw/2, Ry+22, f"rbdimmer{rb_num} 40A-CS — konektor k MCU",
        fs=12.5, anchor="middle", bold=True, col="#bf360c")
    py = {}
    for i,(pname,desc,fl,st) in enumerate(pins):
        ry = Ry + 34 + i*(row_h+row_gap)
        py[pname] = ry + row_h/2
        box(Rx+12, ry, Rw-24, row_h, f"{pname}   {desc}", "", fill=fl, stroke=st, fs=10)

    # VCC/GND/Z-C/DIM ako jeden zväzok od DimmerLinku (4 vodiče, jedna vetva)
    wire([(Dx, py["VCC"]),(Rx, py["VCC"])], col="#0d47a1", wdth=2, arrow=True)
    txt(Dx+8, Dy-8, "4 vodiče: VCC/GND/Z-C/DIM", fs=9, col="#0d47a1", italic=True)

    # TEMP + CUR-S — vedené PRIAMO z ESP32, obchádzajú DimmerLink zhora
    adc_mid = (py["TEMP"]+py["CUR-S"])/2
    wire([(Ex+Ew, ADC_Y),(380, ADC_Y),(380, adc_mid),(Rx, adc_mid)],
         col="#bf360c", wdth=2, arrow=True)
    txt(390, adc_mid-8, "priamo, MIMO DimmerLinku!", fs=9.5, col="#bf360c", italic=True, bold=True)

    # FAN — tiež PRIAMO z ESP32 (2026-09-13 oprava: doska FAN nerieši sama,
    # je to len logický vstup do jej vlastného tranzistora — pozri poznámku
    # nižšie). Iná x-odbočka (405) než ADC (380), nech sa vizuálne nekrížia.
    wire([(Ex+Ew, FAN_Y),(405, FAN_Y),(405, py["FAN"]),(Rx, py["FAN"])],
         col="#e65100", wdth=2, arrow=True)

    # -- Vlastný fan dosky (2-vodičový, − vetva spínaná ESP32 cez FAN pin) --
    Fx, Fy, Fw, Fh = 1100, Ry+34+6*(row_h+row_gap)-15, 240, 108
    fan_mid = (py["FAN"]+py["5V"])/2
    box(Fx, Fy, Fw, Fh, "", "", fill="#ffe0b2", stroke="#e65100", fs=11.5)
    txt(Fx+Fw/2, Fy+20, "Vlastný fan chladiča", fs=11.5, anchor="middle", bold=True, col="#e65100")
    txt(Fx+Fw/2, Fy+35, f"chladí TRIAC {branch.lower()} vetvy", fs=9, anchor="middle",
        italic=True, col="#e65100")
    txt(Fx+12, Fy+55, "2-vodičový, spína ho ESP32:", fs=9, col="#e65100")
    txt(Fx+12, Fy+72, "+ (červený) → 5V pin", fs=9.5, col="#e65100")
    txt(Fx+12, Fy+88, f"− (čierny) → FAN pin ({fan_gpio})", fs=9.5, col="#e65100")
    wire([(Rx+Rw, fan_mid),(Fx, Fy+Fh/2)], col="#e65100", wdth=2, arrow=True)
    txt(Fx, Fy+Fh+18, "⚠️ 2026-09-13 OPRAVA: doska FAN nerieši autonómne (zdroj:",
        fs=9, col="#e65100", italic=True)
    txt(Fx, Fy+Fh+32, "GitHub robotdyn-dimmer/rbdimmerThermalESP32 API) — treba",
        fs=9, col="#e65100", italic=True)
    txt(Fx, Fy+Fh+46, "logiku z ESP32. Doska má vlastný tranzistor → MOSFET netreba,",
        fs=9, col="#e65100", italic=True)
    txt(Fx, Fy+Fh+60, "len digitálny signál. Fan len on/off (2 vodiče, žiadny PWM vstup).",
        fs=9, col="#e65100", italic=True)

    return max(Ry+Rh, Fy+Fh+75)

panel1_bottom = dimmer_detail_panel(2185, "TUV", 1, "0x50", "L1", 1, "TUV 3 kW @ L1",
                                     "GPIO36", "GPIO39", "GPIO33")
panel2_bottom = dimmer_detail_panel(panel1_bottom+55, "PODLAHA", 2, "0x51", "L2", 2,
                                     "podlaha 600 W @ L2", "GPIO34", "GPIO35", "GPIO32")
txt(120, panel2_bottom+30,
    "Skriňový ventilátor (GPIO23, sekcia vyššie) je výhradne pre CELÚ skrinku — nezávislý",
    fs=10.5, col="#455a64", italic=True)
txt(120, panel2_bottom+46,
    "od týchto dvoch fanov na jednotlivých doskách (tri nezávislé chladenia spolu). Oba typy",
    fs=10.5, col="#455a64", italic=True)
txt(120, panel2_bottom+62,
    "idú teraz priamo z GPIO, bez MOSFETu — rozdiel je, že skriňový fan je 4-vodičový PWM",
    fs=10.5, col="#455a64", italic=True)
txt(120, panel2_bottom+78,
    "(GPIO23 nesie 25kHz priamo do PWM pinu fanu, ten si rýchlosť rieši sám), kým fany na",
    fs=10.5, col="#455a64", italic=True)
txt(120, panel2_bottom+94,
    "doskách sú jednoduché 2-vodičové ZAP/VYP (doska má vlastný tranzistor, žiadna PWM).",
    fs=10.5, col="#455a64", italic=True)
txt(120, panel2_bottom+110,
    "GPIO34/35/36/39 (TEMP/CUR-S vyššie) sú HW input-only (žiadny výstupný driver) — FAN",
    fs=10.5, col="#455a64", italic=True)
txt(120, panel2_bottom+126,
    "preto musí na výstupovo schopný pin (GPIO33 TUV / GPIO32 podlaha).",
    fs=10.5, col="#455a64", italic=True)

body = "\n".join(el)

def render(name, y0, y1):
    """Jeden spoločný súradnicový priestor (viď 'el' vyššie), len iný výrez
    cez viewBox — žiadna duplikácia obsahu/súradníc, len iný pohľad naň.
    Kvôli tlači (A4/A3 na výšku) — jeden veľký obrázok sa nedá rozumne
    vytlačiť, samostatné súbory áno."""
    h = y1 - y0
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
           f'viewBox="0 {y0} {W} {h}" font-family="DejaVu Sans, Arial, sans-serif">\n'
           + body + "\n</svg>\n")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.svg")
    with open(path, "w") as f:
        f.write(svg)
    print("SVG zapísané:", path, "-", len(svg), "bajtov")
    return path

# Celá schéma naraz (pôvodné, zachované pre prehľad/odkazy v README a poznámkach)
paths = [render("fve_schema", 0, H)]
# Rozdelené na 3 samostatné výtlačky/pohľady (rovnaký obsah, len orezané):
paths.append(render("fve_schema_zapojenie", 0, 810))                # SILNOPRÚD + legenda
paths.append(render("fve_schema_riadenie", 805, 2170))               # ESP32 GPIO mapa + poznámky
paths.append(render("fve_schema_dimmer_detail", 2170, H))            # rbdimmer/DimmerLink/ESP32 detail

if shutil.which("rsvg-convert"):
    for p in paths:
        png = p[:-4] + ".png"
        subprocess.run(["rsvg-convert", "-o", png, p], check=True)
        print("PNG zapísané:", png)
else:
    print("rsvg-convert nenájdený — PNG treba vygenerovať ručne (viď README).")
