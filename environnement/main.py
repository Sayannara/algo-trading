import os, json, webbrowser
import config
from mt5 import charger_donnees


os.system('cls' if os.name == 'nt' else 'clear')

# ── CONFIG ────────────────────────────────────────────────────
SYMBOL    = "EURUSD"
DATE_FROM = "2026-04-01"
DATE_TO   = "2026-04-28"
TIMEFRAME = "M30"

# ── CHEMINS ───────────────────────────────────────────────────
ROOT     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, "chart_template.html")
OUTPUT   = os.path.join(ROOT, "output.html")

# ── DONNÉES ───────────────────────────────────────────────────
df = charger_donnees(symbol=SYMBOL, date_from=DATE_FROM, date_to=DATE_TO, timeframe=TIMEFRAME)

candles = [
    {"time": int(r.time.timestamp()), "open": float(r.Open),
     "high": float(r.High), "low": float(r.Low), "close": float(r.Close)}
    for r in df.itertuples(index=False)
]

# ── INDICATEURS ───────────────────────────────────────────────
sessions_zones   = []
sessions_history = {}

if config.INDICATORS.get('sessions', False):
    from indicators.sessions import compute_sessions
    sessions_zones, sessions_history = compute_sessions(df, config)
    print(f"   ↳ Sessions : {len(sessions_zones)} zones")


# ── INJECTION ─────────────────────────────────────────────────
html = open(TEMPLATE, encoding="utf-8").read()
html = html.replace("{{candles}}",       json.dumps(candles))
html = html.replace("{{sessions}}",      json.dumps(sessions_zones))
html = html.replace("{{trades}}",        "[]")
html = html.replace("{{price_lines}}",   "[]")
html = html.replace("{{zones}}",         "[]")
html = html.replace("{{ind_ema}}",       "[]")
html = html.replace("{{ind_sma}}",       "[]")
html = html.replace("{{ind_volume}}",    "[]")
html = html.replace("{{ind_baseline}}", "[]")
html = html.replace("{{ind_custom}}",    "[]")

open(OUTPUT, "w", encoding="utf-8").write(html)
# webbrowser.open(f"file://{OUTPUT}")
print(f"✅ {len(candles)} bougies — output.html ouvert")