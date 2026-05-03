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
df = charger_donnees(
    symbol    = config.SYMBOL,
    date_from = config.DATE_FROM,
    date_to   = config.DATE_TO,
    timeframe = config.TIMEFRAME,
)

tz = pytz.timezone(config.TIMEZONE) 

candles = [
    {"time": to_tz_ts(r.time, tz), "open": float(r.Open),   # ← to_tz_ts au lieu de int(r.time.timestamp())
     "high": float(r.High), "low": float(r.Low), "close": float(r.Close)}
    for r in df.itertuples(index=False)
]

trades      = []
price_lines = []


# ── INDICATEURS ───────────────────────────────────────────────

## Sessions
sessions_zones   = []
sessions_history = {}

if config.INDICATORS.get('sessions', False):
    from indicators.sessions import compute_sessions
    sessions_zones, sessions_history = compute_sessions(df, config)
    print(f"   ↳ Sessions : {len(sessions_zones)} zones")


## Trend quality
tq_score   = 50.0
tq_text    = "En attente..."
tq_color   = "#9E9E9E"
tq_labels  = []
tq_history = []

if config.INDICATORS.get('trend_quality', False):
    from indicators.trend_quality import compute_trend_quality
    tq_score, tq_text, tq_color, tq_labels, tq_history = compute_trend_quality(df, config)


## Display trade
from display_trades import load_trades
if config.INDICATORS.get('trades', False):
    trades_payload = load_trades(
        csv_path=os.path.join(ROOT, 'trades_result.csv'),
        symbol=config.SYMBOL,
        tz_name=config.TIMEZONE,
    )
    trades      = trades_payload["markers"]
    price_lines = trades_payload["price_lines"]
else:
    trades      = []
    price_lines = []

## Trade boxes
trade_boxes = []
if config.INDICATORS.get('trade_boxes', False):
    from display_trades import load_trade_boxes
    trade_boxes = load_trade_boxes(
        csv_path=os.path.join(ROOT, 'trades_result.csv'),
        symbol=config.SYMBOL,
        tz_name=config.TIMEZONE,
        candles=candles,
        timeframe=config.TIMEFRAME,
        max_rr=config.MAX_RR,
    )
    print(f"   ↳ Trade boxes : {len(trade_boxes)} boxes")

## OB + FVG
ob_fvg_data = []
if config.INDICATORS.get('ob_fvg', False):
    from indicators.ob_fvg import detect_ob_fvg
    raw_ob_fvg = detect_ob_fvg(df, config)
    
    for item in raw_ob_fvg:
        fvg = item['fvg']
        ob = item['ob']
        
        # Mapping index -> timestamp (heure locale via candles)
        fvg['start_time'] = candles[fvg['start_idx']]['time']
        fvg['end_time']   = candles[fvg['end_idx']]['time']
        
        if ob:
            ob['start_time']  = candles[ob['start_idx']]['time']
            
            # Extension de l'OB de X jours (en nombre de bougies)
            ext_days = config.OB_DETECTION.get('ob_extension_days', 3)
            tf = getattr(config, 'TIMEFRAME', 'M30')
            candles_per_day = 48
            if tf == "H1": candles_per_day = 24
            elif tf == "H4": candles_per_day = 6
            elif tf == "D1": candles_per_day = 1
            
            ext_idx = min(len(candles) - 1, ob['end_idx'] + int(ext_days * candles_per_day))
            ob['end_time']    = candles[ext_idx]['time']
            
        ob_fvg_data.append({"fvg": fvg, "ob": ob})
        
    print(f"   ↳ OB+FVG : {len(ob_fvg_data)} paires trouvées")

## FVG Simple
fvg_data = []
if config.INDICATORS.get('fvg', False):
    from indicators.fvg import detect_fvg
    raw_fvg = detect_fvg(df, config)
    
    for fvg in raw_fvg:
        # Mapping index -> timestamp (heure locale via candles)
        fvg['start_time'] = candles[fvg['start_idx']]['time']
        fvg['end_time']   = candles[fvg['end_idx']]['time']
        fvg_data.append(fvg)
        
    print(f"   ↳ FVG : {len(fvg_data)} gaps trouvés")


# ══════════════════════════════════════════════════════════════
# STRATÉGIES
# ══════════════════════════════════════════════════════════════
import importlib
import sys
if ROOT not in sys.path:
    sys.path.append(ROOT)

if hasattr(config, 'STRATEGIES'):
    for strat_name, enabled in config.STRATEGIES.items():
        if enabled:
            try:
                strat_module = importlib.import_module(f"strategies.{strat_name}")
                if hasattr(strat_module, 'execute'):
                    strat_markers = strat_module.execute(df, candles, ob_fvg_data, tq_history, config)
                    if strat_markers:
                        trades.extend(strat_markers)
                        print(f"   ↳ Stratégie {strat_name} : {len(strat_markers)} marqueurs")
            except Exception as e:
                print(f"   ⚠️ Erreur stratégie {strat_name}: {e}")

# ── INJECTION ─────────────────────────────────────────────────
html = open(TEMPLATE, encoding="utf-8").read()
html = html.replace("{{candles}}",       json.dumps(candles))
html = html.replace("{{sessions}}",      json.dumps(sessions_zones))
html = html.replace("{{trades}}",        json.dumps(trades))
html = html.replace("{{price_lines}}",   json.dumps(price_lines))
html = html.replace("{{zones}}",         "[]")
html = html.replace("{{ind_ema}}",       "[]")
html = html.replace("{{ind_sma}}",       "[]")
html = html.replace("{{ind_volume}}",    "[]")
html = html.replace("{{ind_baseline}}",  "[]")
html = html.replace("{{ind_custom}}",    "[]")

html = html.replace("{{tq_score}}",      json.dumps(tq_score))
html = html.replace("{{tq_text}}",       json.dumps(tq_text))
html = html.replace("{{tq_color}}",      json.dumps(tq_color))
html = html.replace("{{ind_tq_labels}}", json.dumps(tq_labels))
html = html.replace("{{tq_history}}",    json.dumps(tq_history))

html = html.replace("{{symbol}}",    json.dumps(config.SYMBOL))
html = html.replace("{{timeframe}}", json.dumps(config.TIMEFRAME))

html = html.replace("{{trade_boxes}}", json.dumps(trade_boxes))
html = html.replace("{{ob_fvg_data}}", json.dumps(ob_fvg_data))
html = html.replace("{{fvg_data}}", json.dumps(fvg_data))

ob_colors_js = "{"
for m in [1, 2, 3]:
    cfg_m = config.OB_DETECTION.get("visuals", {}).get(f"method_{m}", {})
    def hex_to_rgba(hex_color, opacity):
        hex_color = hex_color.lstrip('#')
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return f"rgba({r}, {g}, {b}, {opacity})"
        except:
            return hex_color
            
    bull_c = cfg_m.get("bullish_color", "#00E676")
    bull_o = cfg_m.get("bullish_opacity", 0.2)
    bear_c = cfg_m.get("bearish_color", "#FF1744")
    bear_o = cfg_m.get("bearish_opacity", 0.2)
    
    ob_colors_js += f"""
    {m}: {{
        bullish: {{ fill: '{hex_to_rgba(bull_c, bull_o)}', border: '{bull_c}' }},
        bearish: {{ fill: '{hex_to_rgba(bear_c, bear_o)}', border: '{bear_c}' }}
    }},"""
ob_colors_js += "}"

html = html.replace("{{ob_colors}}", ob_colors_js)

open(OUTPUT, "w", encoding="utf-8").write(html)
# webbrowser.open(f"file://{OUTPUT}")
print(f"✅ {len(candles)} bougies — output.html ouvert")