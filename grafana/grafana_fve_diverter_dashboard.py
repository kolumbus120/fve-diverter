#!/usr/bin/env python3
# Grafana dashboard „FVE diverter — energia do špirál“ (uid fve-diverter), 2026-11-16.
# GENERÁTOR — dashboard upravuj TU, nie ručne v Grafane (pri ďalšom spustení sa prepíše).
# Použitie:
#   GRAFANA_URL=http://grafana:3000 GRAFANA_DS_UID=<uid InfluxDB zdroja> INFLUX_BUCKET=<bucket> \
#   GRAFANA_TOKEN=<service account token> ./grafana_fve_diverter_dashboard.py [--dry-run]
# Po nahratí uloží snapshot grafana_fve_diverter_dashboard.json vedľa skriptu.
#
# Zdroj dát: HA → integrácia InfluxDB v2 (Flux, bucket INFLUX_BUCKET), measurement = jednotka
# (W/kWh), tag entity_id bez „sensor.“, field value. HA zapisuje len zmeny → pri výkone
# fill(usePrevious). Všetky hodnoty sú ODHAD z ESP (úroveň dimmera × menovitý výkon
# špirály); K3M zo siete/slnka podľa Shelly (od 2026-11-16, viď fve-diverter.yaml).
import json
import os
import sys
import urllib.request

G = os.environ.get("GRAFANA_URL", "http://localhost:3000")
UID = "fve-diverter"
BUCKET = os.environ.get("INFLUX_BUCKET", "homeassistant")   # bucket integrácie InfluxDB v HA
DS = {"type": "influxdb", "uid": os.environ.get("GRAFANA_DS_UID", "influxdb")}   # uid InfluxDB (Flux) zdroja v Grafane
HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "grafana_fve_diverter_dashboard.json")

# (kľúč entity bez prípony, popis, farba)
SERIE = [
    ("tuv", "TUV z FVE", "orange"),
    ("podlahy", "Podlaha z FVE", "yellow"),
    ("tuv_k3m_zo_slnka", "TUV cez K3M — zo slnka", "green"),
    ("tuv_k3m_zo_siete", "TUV cez K3M — zo siete", "red"),
]
VYKON = {   # kľúč → entity_id výkonu
    "tuv": "fve_diverter_vykon_do_tuv_odhad",
    "podlahy": "fve_diverter_vykon_do_podlahy_odhad",
    "tuv_k3m_zo_slnka": "fve_diverter_vykon_do_tuv_k3m_zo_slnka_odhad",
    "tuv_k3m_zo_siete": "fve_diverter_vykon_do_tuv_k3m_zo_siete_odhad",
}
TZ = 'import "timezone"\noption location = timezone.location(name: "Europe/Prague")\n'


def q(ref, flux, legend=None):
    t = {"refId": ref, "datasource": DS, "query": flux}
    return t


def flt(measurement, entity):
    return (f'from(bucket: "{BUCKET}")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
            f'  |> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["entity_id"] == "{entity}" '
            f'and r["_field"] == "value")\n')


def meno(nazov):
    return f'  |> map(fn: (r) => ({{_time: r._time, _value: r._value, _field: "{nazov}"}}))\n'


def farba(nazov, c):
    return {"matcher": {"id": "byName", "options": nazov},
            "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]}


panels = []
pid = 0


def panel(p, x, y, w, h):
    global pid
    pid += 1
    p.update({"id": pid, "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h}})
    panels.append(p)


# --- 1) Dnes (stav denných počítadiel z ESP) ---------------------------------
for i, (k, n, c) in enumerate(SERIE):
    flux = (f'from(bucket: "{BUCKET}")\n  |> range(start: -2d)\n'
            f'  |> filter(fn: (r) => r["_measurement"] == "kWh" and r["entity_id"] == "fve_diverter_energia_do_{k}_dnes" '
            f'and r["_field"] == "value")\n  |> last()\n')
    panel({"type": "stat", "title": f"Dnes — {n}",
           "targets": [q("A", flux)],
           "fieldConfig": {"defaults": {"unit": "kwatth", "decimals": 2,
                                        "color": {"mode": "fixed", "fixedColor": c}}, "overrides": []},
           "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                       "colorMode": "value", "graphMode": "none", "textMode": "value"}},
          i * 6, 0, 6, 4)

# --- 2) Za zvolené obdobie (rozdiel celkových počítadiel) --------------------
for i, (k, n, c) in enumerate(SERIE):
    flux = (flt("kWh", f"fve_diverter_energia_do_{k}_celkom")
            + "  |> difference(nonNegative: true)\n  |> sum()\n")
    panel({"type": "stat", "title": f"Za obdobie — {n}",
           "targets": [q("A", flux)],
           "fieldConfig": {"defaults": {"unit": "kwatth", "decimals": 2, "noValue": "0",
                                        "color": {"mode": "fixed", "fixedColor": c}}, "overrides": []},
           "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                       "colorMode": "value", "graphMode": "none", "textMode": "value"}},
          i * 6, 4, 6, 4)

# --- 3) Energia po dňoch (max denného počítadla v daný deň) ------------------
tg = []
for i, (k, n, c) in enumerate(SERIE):
    flux = (TZ + flt("kWh", f"fve_diverter_energia_do_{k}_dnes")
            + '  |> aggregateWindow(every: 1d, fn: max, createEmpty: false, timeSrc: "_start")\n' + meno(n))
    tg.append(q(chr(65 + i), flux))
# K3M spolu (aj dni pred rozdelením 2026-11-16) — čiara cez stĺpce
tg.append(q("E", TZ + flt("kWh", "fve_diverter_energia_do_tuv_daikin_k3m_dnes")
            + '  |> aggregateWindow(every: 1d, fn: max, createEmpty: false, timeSrc: "_start")\n'
            + meno("TUV cez K3M — spolu")))
panel({"type": "timeseries", "title": "Energia do špirál po dňoch (odhad)",
       "description": "Stĺpce: FVE (TUV, podlaha) a ohrev na žiadosť Daikinu (K3M) rozdelený podľa Shelly "
                      "na zo slnka / zo siete (od 16.11.2026). Batériu nevidíme — vybíjanie batérie do "
                      "špirály je v „zo slnka“. Čiara: K3M spolu (aj pred rozdelením).",
       "targets": tg,
       "fieldConfig": {"defaults": {"unit": "kwatth", "decimals": 2,
                                    "custom": {"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1,
                                               "barAlignment": -1,
                                               "stacking": {"mode": "normal", "group": "A"}}},
                       "overrides": [farba(n, c) for _, n, c in SERIE] + [
                           {"matcher": {"id": "byName", "options": "TUV cez K3M — spolu"},
                            "properties": [{"id": "custom.drawStyle", "value": "line"},
                                           {"id": "custom.stacking", "value": {"mode": "none", "group": "B"}},
                                           {"id": "custom.fillOpacity", "value": 0},
                                           {"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}},
                                           {"id": "custom.lineWidth", "value": 2},
                                           {"id": "color", "value": {"mode": "fixed", "fixedColor": "purple"}}]}]},
       "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["sum"]},
                   "tooltip": {"mode": "multi", "sort": "none"}},
       "timeFrom": "30d"},
      0, 8, 24, 9)

# --- 4) Výkon do špirál + prípojka -------------------------------------------
tv = []
for i, (k, n, c) in enumerate(SERIE):
    flux = (flt("W", VYKON[k])
            + "  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: true)\n"
            + "  |> fill(usePrevious: true)\n" + meno(n))
    tv.append(q(chr(65 + i), flux))
tv.append(q("E", flt("W", "fve_diverter_pripojka_shelly_esp")
            + "  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n"
            + meno("Prípojka (Shelly, + odber / − pretok)")))
panel({"type": "timeseries", "title": "Výkon do špirál (odhad) a prípojka",
       "description": "Plocha = výkon do špirál (naskladané). Čiara = prípojka zo Shelly (+ odber zo siete, "
                      "− pretok). K3M zo siete = odber zo siete v tej chvíli, najviac výkon špirály.",
       "targets": tv,
       "fieldConfig": {"defaults": {"unit": "watt", "decimals": 0,
                                    "custom": {"drawStyle": "line", "lineInterpolation": "stepAfter",
                                               "fillOpacity": 40, "lineWidth": 1,
                                               "stacking": {"mode": "normal", "group": "A"}}},
                       "overrides": [farba(n, c) for _, n, c in SERIE] + [
                           {"matcher": {"id": "byName", "options": "Prípojka (Shelly, + odber / − pretok)"},
                            "properties": [{"id": "custom.stacking", "value": {"mode": "none", "group": "B"}},
                                           {"id": "custom.fillOpacity", "value": 0},
                                           {"id": "custom.lineInterpolation", "value": "linear"},
                                           {"id": "custom.lineWidth", "value": 1},
                                           {"id": "color", "value": {"mode": "fixed", "fixedColor": "blue"}}]}]},
       "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max"]},
                   "tooltip": {"mode": "multi", "sort": "none"}}},
      0, 17, 24, 10)

dash = {
    "uid": UID,
    "title": "FVE diverter — energia do špirál",
    "tags": ["fve", "diverter"],
    "timezone": "browser",
    "time": {"from": "now-24h", "to": "now"},
    "refresh": "1m",
    "schemaVersion": 39,
    "panels": panels,
}

if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        print(json.dumps(dash, ensure_ascii=False, indent=1))
        sys.exit(0)
    tok = os.environ["GRAFANA_TOKEN"]
    hdr = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    body = json.dumps({"dashboard": dash, "overwrite": True,
                       "message": "generátor grafana_fve_diverter_dashboard.py"}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"{G}/api/dashboards/db", body, hdr)))
    print(r.get("status"), r.get("url"), "verzia", r.get("version"))
    live = json.load(urllib.request.urlopen(urllib.request.Request(f"{G}/api/dashboards/uid/{UID}", headers=hdr)))
    with open(SNAPSHOT, "w") as f:
        json.dump(live["dashboard"], f, ensure_ascii=False, indent=2)
    print("snapshot:", SNAPSHOT)
