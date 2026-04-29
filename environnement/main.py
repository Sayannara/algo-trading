import os, json, webbrowser
import pytz
import config
from mt5 import charger_donnees

def to_tz_ts(ts, tz):
    """Décale le timestamp UTC pour que LWC affiche en heure locale."""
    offset = int(ts.astimezone(tz).utcoffset().total_seconds())
    return int(ts.timestamp()) + offset

os.system('cls' if os.name == 'nt' else 'clear')


# ── CHEMINS ───────────────────────────────────────────────────
ROOT     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, "chart_template.html")
OUTPUT   = os.path.join(ROOT, "output.html")

# ── DONNÉES ───────────────────────────────────────────────────

SYMBOL    = "EURUSD"
DATE_FROM = "2026-04-01"
DATE_TO   = "2026-04-28"
TIMEFRAME = "M30"

df = charger_donnees(symbol=SYMBOL, date_from=DATE_FROM, date_to=DATE_TO, timeframe=TIMEFRAME)

tz = pytz.timezone(config.TIMEZONE)   # ← ajouter

candles = [
    {"time": to_tz_ts(r.time, tz), "open": float(r.Open),   # ← to_tz_ts au lieu de int(r.time.timestamp())
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


if config.INDICATORS.get('trend_quality', False):
    from indicators.trend_quality import compute_trend_quality
    tq_score, tq_text, tq_color, tq_labels = compute_trend_quality(df, config)

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
html = html.replace("{{tq_score}}", json.dumps(tq_score))
html = html.replace("{{tq_text}}", json.dumps(tq_text))
html = html.replace("{{tq_color}}", json.dumps(tq_color))
html = html.replace("{{ind_tq_labels}}", json.dumps(tq_labels))

open(OUTPUT, "w", encoding="utf-8").write(html)
# webbrowser.open(f"file://{OUTPUT}")
print(f"✅ {len(candles)} bougies — output.html ouvert")