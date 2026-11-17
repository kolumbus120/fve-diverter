#!/usr/bin/env python3
# Prepojovacie priechody GND (stitching vias): spoja vyliatu meď GND na vrchu (F.Cu) a spodku
# (B.Cu) na viacerých miestach, nielen cez GND piny. User 2026-11-16.
# Použitie (na natrasovanej doske, spúšťa ho aj route.py):
#   python3 prechodky.py
# Postup: vyliať zóny → v mriežke KROK mm hľadať miesta, kde je GND meď na OBOCH vrstvách
# s rezervou okolo priechodu (výplň už drží medzeru 0,4 mm od cudzej medi, okraja aj dier)
# → mimo obalov súčiastok a popisov → pridať priechod → znova vyliať.
# Opakované spustenie najprv zmaže priechody, ktoré pridal skôr (vo výplni nemajú trasu).
import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "fve_doska", "fve_doska.kicad_pcb")
KROK = 5.0          # mm, rozostup mriežky
VIA_D, VIA_DRILL = 0.8, 0.4   # rovnaké ako signálové priechody (min. vŕtanie 0,4 mm)
REZERVA = 0.1       # mm navyše okolo medi priechodu
OKOLIE_SUC = 0.5    # mm okolo obalu súčiastky / popisu

mm = pcbnew.FromMM


def vypln(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def main():
    b = pcbnew.LoadBoard(PCB)
    gnd = b.FindNet("GND")
    # staré stitching priechody (GND priechod bez trasy, ktorá v ňom končí) preč
    konce = set()
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T:
            konce.add((t.GetStart().x, t.GetStart().y))
            konce.add((t.GetEnd().x, t.GetEnd().y))
    for t in list(b.GetTracks()):
        if (t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == gnd.GetNetCode()
                and (t.GetPosition().x, t.GetPosition().y) not in konce):
            b.Remove(t)
    vypln(b)
    zony = {ly: [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == gnd.GetNetCode()
                 and z.IsOnLayer(ly)] for ly in (pcbnew.F_Cu, pcbnew.B_Cu)}

    def v_medi(ly, p):
        return any(z.GetFilledPolysList(ly).Contains(p) for z in zony[ly])

    # zakázané obdĺžniky: obaly súčiastok (okrem modulov na lištách, pod nimi je miesto)
    # a texty potlače na doske
    zakaz = []
    for f in b.GetFootprints():
        if f.GetReference() in ("U1", "U2", "U3"):
            continue
        f.BuildCourtyardCaches()
        bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() == 0:
            bb = f.GetBoundingBox(False)
        zakaz.append(bb)
    for d in b.GetDrawings():
        if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and d.Type() == pcbnew.PCB_TEXT_T:
            zakaz.append(d.GetBoundingBox())
    for bb in zakaz:
        bb.Inflate(mm(OKOLIE_SUC))

    r = mm(VIA_D / 2 + REZERVA)
    obrys = b.GetBoardEdgesBoundingBox()
    pridane = 0
    y = obrys.GetTop() + mm(KROK / 2)
    while y < obrys.GetBottom():
        x = obrys.GetLeft() + mm(KROK / 2)
        while x < obrys.GetRight():
            p = pcbnew.VECTOR2I(int(x), int(y))
            body = [p] + [pcbnew.VECTOR2I(int(x + r * math.cos(a)), int(y + r * math.sin(a)))
                          for a in (i * math.pi / 8 for i in range(16))]
            if (not any(bb.Contains(p) for bb in zakaz)
                    and all(v_medi(ly, q) for ly in (pcbnew.F_Cu, pcbnew.B_Cu) for q in body)):
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(p)
                v.SetWidth(mm(VIA_D), pcbnew.F_Cu)   # KiCad 9: šírka podľa vrstvy (bez nej assert)
                v.SetDrill(mm(VIA_DRILL))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(gnd)
                b.Add(v)
                pridane += 1
            x += mm(KROK)
        y += mm(KROK)
    vypln(b)
    b.Save(PCB)
    print("prepojovacie priechody GND:", pridane)


if __name__ == "__main__":
    main()
