#!/usr/bin/env python3
# Autorouter: KiCad doska → Specctra DSN → Freerouting → SES → späť do dosky,
# vyliatie zón GND. Použitie:
#   python3 route.py /cesta/k/freerouting-2.5.0.jar
# (Freerouting: https://github.com/freerouting/freerouting/releases — Java 21)
# Alternatíva v KiCade: Súbor → Exportovať → Specctra DSN, spustiť Freerouting
# s GUI, potom Súbor → Importovať → Specctra Session.
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "fve_doska", "fve_doska.kicad_pcb")

if __name__ == "__main__":
    jar = sys.argv[1]
    b = pcbnew.LoadBoard(PCB)
    mm = pcbnew.FromMM
    # Triedy spojov priamo do dosky (DSN export berie tie z dosky): napájanie 1 mm, signály 0,4 mm
    ns = b.GetDesignSettings().m_NetSettings
    d = ns.GetDefaultNetclass()
    # user 2026-11-15: medzery aj najtenšie trasy min. 0,4 mm
    MIN = 0.4
    # Freerouting dostane medzeru s rezervou (0,42 mm): pri pinoch zužuje trasy a ich
    # rozšírenie späť na 0,4 mm (nižšie) by inak zmenšilo medzeru pod 0,4 (rev B: 0,397 mm).
    # Pred uložením sa vráti skutočné pravidlo 0,4 mm, s ktorým beží DRC.
    TRAS = MIN + 0.02
    d.SetTrackWidth(mm(MIN)); d.SetClearance(mm(TRAS)); d.SetViaDiameter(mm(0.8)); d.SetViaDrill(mm(0.4))
    nap = pcbnew.NETCLASS("Napajanie")
    nap.SetTrackWidth(mm(1.0)); nap.SetClearance(mm(TRAS)); nap.SetViaDiameter(mm(1.0)); nap.SetViaDrill(mm(0.5))
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = mm(MIN)
    ds.m_MinClearance = mm(MIN)
    ns.SetNetclass("Napajanie", nap)
    for net in ("+5V", "+3V3", "GND"):
        ns.SetNetclassPatternAssignment(net, "Napajanie")
    ns.RecomputeEffectiveNetclasses()
    b.SynchronizeNetsAndNetClasses(True)
    # GND trasovať normálne (nie len cez vyliatu meď) → zóny dočasne preč, po trasovaní späť
    zony = [z for z in b.Zones() if not z.GetIsRuleArea()]
    for z in zony:
        b.Remove(z)
    for t in list(b.GetTracks()):        # staré trasy preč (nové trasovanie od nuly)
        b.Remove(t)
    dsn, ses = PCB[:-10] + ".dsn", PCB[:-10] + ".ses"
    assert pcbnew.ExportSpecctraDSN(b, dsn)
    java = os.environ.get("JAVA", "/usr/lib/jvm/java-25-openjdk-amd64/bin/java")   # Freerouting 2.5 = Java 25
    subprocess.run([java, "-jar", jar, "-de", dsn, "-do", ses, "-mp", "40", "--gui.enabled=false"],
                   check=True, timeout=1200)
    assert pcbnew.ImportSpecctraSES(b, ses)
    for z in zony:
        b.Add(z)
    d.SetClearance(mm(MIN)); nap.SetClearance(mm(MIN))     # späť skutočné pravidlo 0,4 mm
    ns.RecomputeEffectiveNetclasses()
    b.Save(PCB)
    # Freerouting pri pinoch zužuje trasy (neckdown) — nič tenšie ako 0,4 mm. Rieši sa TEXTOVO
    # v uloženom súbore: po ImportSpecctraSES KiCad 9.0.2 v Pythone vracia trasy ako
    # neiterovateľný SwigPyObject (GetTracks aj TracksInNet, 2026-11-16).
    txt = open(PCB).read()
    zuzene = 0

    def rozsir(m):
        global zuzene
        if float(m.group(2)) < MIN - 1e-9:
            zuzene += 1
            return f"{m.group(1)}{MIN}"
        return m.group(0)
    txt = re.sub(r"(\(segment\b[^()]*(?:\((?!width)[^()]*\)[^()]*)*\(width )([0-9.]+)", rozsir, txt)
    open(PCB, "w").write(txt)
    print("rozšírené zúžené úseky:", zuzene)
    # vyliať GND v NOVOM procese (v tomto je po importe SES väzba pcbnew pokazená — aj LoadBoard
    # vracia SwigPyObject) — až po rozšírení trás; prechodky.py vylieva a pridá prepojovacie
    # priechody GND medzi vrchom a spodkom (user 2026-11-16)
    subprocess.run([sys.executable, os.path.join(HERE, "prechodky.py")], check=True)
    os.remove(dsn)
    os.remove(ses)
    print("OK, segmentov:", txt.count("(segment"))
