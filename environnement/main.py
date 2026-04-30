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

SYMBOL    = "AUDUSD"
DATE_FROM = "2024-01-01"
DATE_TO   = "2026-04-29"
TIMEFRAME = "M15"

df = charger_donnees(symbol=SYMBOL, date_from=DATE_FROM, date_to=DATE_TO, timeframe=TIMEFRAME)

tz = pytz.timezone(config.TIMEZONE)   # ← ajouter

candles = [
    {"time": to_tz_ts(r.time, tz), "open": float(r.Open),   # ← to_tz_ts au lieu de int(r.time.timestamp())
     "high": float(r.High), "low": float(r.Low), "close": float(r.Close)}
    for r in df.itertuples(index=False)
]

trades      = []
price_lines = []

# ── INDICATEURS ───────────────────────────────────────────────
sessions_zones   = []
sessions_history = {}

if config.INDICATORS.get('sessions', False):
    from indicators.sessions import compute_sessions
    sessions_zones, sessions_history = compute_sessions(df, config)
    print(f"   ↳ Sessions : {len(sessions_zones)} zones")


tq_score   = 50.0
tq_text    = "En attente..."
tq_color   = "#9E9E9E"
tq_labels  = []
tq_history = []

if config.INDICATORS.get('trend_quality', False):
    from indicators.trend_quality import compute_trend_quality
    tq_score, tq_text, tq_color, tq_labels, tq_history = compute_trend_quality(df, config)

if config.INDICATORS.get('trades', False):
    from display_trades import load_trades
    raw = load_trades(
        csv_path=os.path.join(ROOT, 'trades_result.csv'),
        symbol='AUDUSD',
        tz_name=config.TIMEZONE,
    )
    trades      = [t for t in raw if '_type' not in t]
    price_lines = [t for t in raw if t.get('_type') == 'price_line']
    print(f"   ↳ Trades : {len(trades)//2} trades chargés")

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
html = html.replace("{{tq_history}}", json.dumps(tq_history))

html = html.replace("{{trades}}",      json.dumps(trades))
html = html.replace("{{price_lines}}", json.dumps(price_lines))

open(OUTPUT, "w", encoding="utf-8").write(html)
# webbrowser.open(f"file://{OUTPUT}")
print(f"✅ {len(candles)} bougies — output.html ouvert")