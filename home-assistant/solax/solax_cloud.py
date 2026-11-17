#!/usr/bin/env python3
"""
Solax cloud API - vracia jeden metriku podla argumentu.
Cache tokenu: /config/.solax_token_cache (platný 30 dní)
Cache odpovede: /tmp/solax_data_cache.json (platný 4 min)
"""
import urllib.request, urllib.parse, json, os, time, sys

# Client ID / Secret sú v /config/secrets.yaml (solax_client_id,
# solax_client_secret) — v skripte NIE SÚ (presunuté 2026-11-10).
# Do /config/secrets.yaml pridaj:
#   solax_client_id: "YOUR_SOLAX_CLIENT_ID"
#   solax_client_secret: "YOUR_SOLAX_CLIENT_SECRET"
SECRETS_FILE = "/config/secrets.yaml"

def _secret(key):
    import re as _re
    with open(SECRETS_FILE) as f:
        for line in f:
            m = _re.match(r'^\s*' + key + r'\s*:\s*["\']?([^"\'#\n]+?)["\']?\s*(#.*)?$', line)
            if m:
                return m.group(1).strip()
    raise Exception(f"{key} chýba v {SECRETS_FILE}")

CLIENT_ID = _secret("solax_client_id")
CLIENT_SECRET = _secret("solax_client_secret")
BASE = "https://openapi-eu.solaxcloud.com"
DEV_SN = "YOUR_INVERTER_SN"
TOKEN_FILE = "/config/.solax_token_cache"
DATA_CACHE = "/tmp/solax_data_cache.json"
CACHE_TTL = 240  # 4 minúty

FIELD = sys.argv[1] if len(sys.argv) > 1 else "pv_power"

def get_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                c = json.load(f)
            if time.time() < c["expires_at"] - 86400:
                return c["token"]
        except Exception:
            pass
    body = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }).encode()
    req = urllib.request.Request(f"{BASE}/openapi/auth/oauth/token", data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
    if resp.get("code") != 0:
        raise Exception(f"Token error: {resp}")
    token = resp["result"]["access_token"]
    with open(os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump({"token": token, "expires_at": time.time() + resp["result"]["expires_in"]}, f)
    return token

def api_get(path, token, params=""):
    req = urllib.request.Request(f"{BASE}{path}{'?' + params if params else ''}")
    req.add_header("Authorization", f"bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def cache_ttl(c):
    """Bežne 240 s. Pre FVE diverter (2026-11-15): Solax nahráva do cloudu
    každých ~5 min — keď je údaj v cache starší ako 5 min (nový už má byť),
    stačí cache 60 s, aby regulácia dostala nový údaj čo najskôr."""
    if FIELD != "realtime":
        return CACHE_TTL
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(c["data"]["data_time"].replace("Z", "+00:00"))
        if time.time() - dt.timestamp() > 300:
            return 60
    except Exception:
        return 60
    return CACHE_TTL

def fetch_data():
    # Použi cache ak je čerstvý
    if os.path.exists(DATA_CACHE):
        try:
            with open(DATA_CACHE) as f:
                c = json.load(f)
            if time.time() - c.get("ts", 0) < cache_ttl(c):
                return c["data"]
        except Exception:
            pass
    token = get_token()
    inv = api_get("/openapi/v2/device/realtime_data", token,
                  f"snList={DEV_SN}&deviceType=1&businessType=1")
    d = inv["result"][0] if inv.get("result") else {}
    bat = api_get("/openapi/v2/device/realtime_data", token,
                  f"snList={DEV_SN}&deviceType=2&requestSnType=1&businessType=1")
    b = bat["result"][0] if bat.get("result") else {}
    data = {
        "pv_power": round(d.get("MPPTTotalInputPower") or 0),
        "battery_soc": round(b.get("batterySOC") or 0),
        "battery_power": round(b.get("chargeDischargePower") or 0),
        "battery_remaining_kwh": round(b.get("batteryRemainings") or 0, 2),
        "battery_total_charge": round(b.get("totalDeviceCharge") or 0, 2),
        "battery_total_discharge": round(b.get("totalDeviceDischarge") or 0, 2),
        "grid_power": round(d.get("gridPower") or 0),
        "daily_yield": round(d.get("dailyYield") or 0, 1),
        "device_status": d.get("deviceStatus", 0),
        "export_dnes": round(d.get("todayExportEnergy") or 0, 1),
        "export_celkom": round(d.get("totalExportEnergy") or 0, 2),
        "import_dnes": round(d.get("todayImportEnergy") or 0, 1),
        "import_celkom": round(d.get("totalImportEnergy") or 0, 2),
        # Čas merania (2026-11-15) — pre FVE diverter: ESP podľa neho spozná nový údaj
        "data_time": d.get("dataTime") or b.get("dataTime") or "",
    }
    try:
        with open(DATA_CACHE, "w") as f:
            json.dump({"ts": time.time(), "data": data}, f)
    except Exception:
        pass
    return data

try:
    data = fetch_data()
    if FIELD == "realtime":
        # Jeden JSON pre FVE diverter (2026-11-15): stav = čas merania, atribúty
        # z TOHO ISTÉHO čítania (konzistentné hodnoty).
        print(json.dumps({k: data.get(k) for k in
                          ("data_time", "battery_power", "battery_soc", "grid_power", "pv_power")}))
        sys.exit(0)
    print(data[FIELD])
except Exception as e:
    sys.stderr.write(f"ERROR: {e}\n")
    defaults = {"pv_power": 0, "battery_soc": 0, "battery_power": 0,
                "battery_remaining_kwh": 0.0,
                "battery_total_charge": 0.0, "battery_total_discharge": 0.0,
                "grid_power": 0, "daily_yield": 0.0, "device_status": 0,
                "export_dnes": 0.0, "export_celkom": 0.0,
                "import_dnes": 0.0, "import_celkom": 0.0}
    print(defaults.get(FIELD, 0))
    sys.exit(1)
