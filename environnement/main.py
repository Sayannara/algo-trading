import os, json, webbrowser, copy, importlib, sys
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

if ROOT not in sys.path:
    sys.path.append(ROOT)

# ── GESTION CONFIG MULTI-TIMEFRAME ────────────────────────────
class EnvConfig:
    def __init__(self, base_module, tf_dict):
        # Récupération des globales (TIMEZONE, SYMBOL, etc.)
        for k in dir(base_module):
            if not k.startswith("__") and not isinstance(getattr(base_module, k), dict):
                setattr(self, k, getattr(base_module, k))
        
        # Injection directe du bloc LTF ou HTF
        for k, v in tf_dict.items():
            setattr(self, k, copy.deepcopy(v))

ltf_dict = getattr(config, 'LTF', {})
htf_dict = getattr(config, 'HTF', {})

ltf_config = EnvConfig(config, ltf_dict)
htf_config = EnvConfig(config, htf_dict) if htf_dict.get("ENABLED") else None

tz = pytz.timezone(config.TIMEZONE) 

# ── FONCTION GLOBALE DE TRAITEMENT PAR TIMEFRAME ──────────────
def process_tf(cfg):
    df = charger_donnees(
        symbol    = cfg.SYMBOL,
        date_from = cfg.DATE_FROM,
        date_to   = cfg.DATE_TO,
        timeframe = cfg.TIMEFRAME,
    )
    
    candles = [
        {"time": to_tz_ts(r.time, tz), "open": float(r.Open),
         "high": float(r.High), "low": float(r.Low), "close": float(r.Close)}
        for r in df.itertuples(index=False)
    ]
    
    sessions_zones, sessions_history = [], {}
    if cfg.INDICATORS.get('sessions', False):
        from indicators.sessions import compute_sessions
        sessions_zones, sessions_history = compute_sessions(df, cfg)
        print(f"   ↳ {cfg.TIMEFRAME} Sessions : {len(sessions_zones)} zones")
        
    tq_score, tq_text, tq_color, tq_labels, tq_history = 50.0, "En attente...", "#9E9E9E", [], []
    if cfg.INDICATORS.get('trend_quality', False):
        from indicators.trend_quality import compute_trend_quality
        tq_score, tq_text, tq_color, tq_labels, tq_history = compute_trend_quality(df, cfg)

    trades, price_lines, trade_boxes = [], [], []
    if cfg.INDICATORS.get('trades', False):
        from display_trades import load_trades
        trades_payload = load_trades(os.path.join(ROOT, 'trades_result.csv'), cfg.SYMBOL, cfg.TIMEZONE)
        trades, price_lines = trades_payload["markers"], trades_payload["price_lines"]
        
    if cfg.INDICATORS.get('trade_boxes', False):
        from display_trades import load_trade_boxes
        trade_boxes = load_trade_boxes(os.path.join(ROOT, 'trades_result.csv'), cfg.SYMBOL, cfg.TIMEZONE, candles, cfg.TIMEFRAME, cfg.MAX_RR)
        print(f"   ↳ {cfg.TIMEFRAME} Trade boxes : {len(trade_boxes)} boxes")

    ob_fvg_data = []
    if cfg.INDICATORS.get('ob_fvg', False):
        from indicators.ob_fvg import detect_ob_fvg
        raw_ob_fvg = detect_ob_fvg(df, cfg)
        
        for item in raw_ob_fvg:
            fvg, ob = item['fvg'], item['ob']
            fvg['start_time'] = candles[fvg['start_idx']]['time']
            fvg['end_time']   = candles[fvg['end_idx']]['time']
            if ob:
                ob['start_time']  = candles[ob['start_idx']]['time']
                ext_days = cfg.OB_DETECTION.get('ob_extension_days', 3)
                candles_per_day = {"M1":1440, "M5":288, "M15":96, "M30":48, "H1":24, "H4":6, "D1":1}.get(cfg.TIMEFRAME, 48)
                ext_idx = min(len(candles) - 1, ob['end_idx'] + int(ext_days * candles_per_day))
                ob['end_time']    = candles[ext_idx]['time']
                
                # Config couleurs directes
                m = ob.get('method', 1)
                vis = cfg.OB_DETECTION.get('visuals', {}).get(f"method_{m}", {})
                is_bullish = fvg['direction'] == 'bullish'
                
                c_hex = vis.get("bullish_color" if is_bullish else "bearish_color", "#000")
                o_val = vis.get("bullish_opacity" if is_bullish else "bearish_opacity", 0.2)
                
                def h2rgba(h, o):
                    h = h.lstrip('#')
                    try:
                        return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{o})"
                    except: return h
                
                ob['fill_color'] = h2rgba(c_hex, o_val)
                ob['border_color'] = c_hex

            ob_fvg_data.append({"fvg": fvg, "ob": ob})
        print(f"   ↳ {cfg.TIMEFRAME} OB+FVG : {len(ob_fvg_data)} paires trouvées")

    fvg_data = []
    if cfg.INDICATORS.get('fvg', False):
        from indicators.fvg import detect_fvg
        raw_fvg = detect_fvg(df, cfg)
        for fvg in raw_fvg:
            fvg['start_time'] = candles[fvg['start_idx']]['time']
            fvg['end_time']   = candles[fvg['end_idx']]['time']
            fvg_data.append(fvg)
        print(f"   ↳ {cfg.TIMEFRAME} FVG : {len(fvg_data)} gaps trouvés")

    return {
        "df": df, "candles": candles, "sessions_zones": sessions_zones,
        "tq_score": tq_score, "tq_text": tq_text, "tq_color": tq_color, "tq_labels": tq_labels, "tq_history": tq_history,
        "trades": trades, "price_lines": price_lines, "trade_boxes": trade_boxes,
        "ob_fvg_data": ob_fvg_data, "fvg_data": fvg_data
    }

# ── EXÉCUTION LTF & HTF ───────────────────────────────────────
print(f"=== PROCESS LTF ({ltf_config.TIMEFRAME}) ===")
ltf_ctx = process_tf(ltf_config)

htf_ctx = None
if htf_config:
    print(f"\n=== PROCESS HTF ({htf_config.TIMEFRAME}) ===")
    htf_ctx = process_tf(htf_config)

# ── IMPORT OB HTF -> LTF ──────────────────────────────────────
if htf_ctx and ltf_config.INDICATORS.get('import_htf_ob', False):
    print(f"   ↳ IMPORT : Utilisation des OB du {htf_config.TIMEFRAME} dans le {ltf_config.TIMEFRAME}")
    ltf_ctx["ob_fvg_data"] = copy.deepcopy(htf_ctx["ob_fvg_data"])
    ltf_ctx["fvg_data"] = copy.deepcopy(htf_ctx["fvg_data"])

# ── STRATÉGIES ────────────────────────────────────────────────
print("\n=== STRATÉGIES ===")
if hasattr(ltf_config, 'STRATEGIES'):
    for strat_name, enabled in ltf_config.STRATEGIES.items():
        if enabled:
            try:
                strat_module = importlib.import_module(f"strategies.{strat_name}")
                if hasattr(strat_module, 'execute'):
                    ctx = {"LTF": ltf_ctx, "HTF": htf_ctx}
                    try:
                        strat_result = strat_module.execute(ltf_ctx["df"], ltf_ctx["candles"], ltf_ctx["ob_fvg_data"], ltf_ctx["tq_history"], ltf_config, ctx=ctx)
                    except TypeError:
                        strat_result = strat_module.execute(ltf_ctx["df"], ltf_ctx["candles"], ltf_ctx["ob_fvg_data"], ltf_ctx["tq_history"], ltf_config)

                    if isinstance(strat_result, dict):
                        ltf_ctx["trades"].extend(strat_result.get("markers", []))
                        ltf_ctx["trade_boxes"].extend(strat_result.get("trade_boxes", []))
                        print(f"   ↳ Stratégie {strat_name} : {len(strat_result.get('trade_boxes', []))} trades")
                    elif isinstance(strat_result, list):
                        ltf_ctx["trades"].extend(strat_result)
                        print(f"   ↳ Stratégie {strat_name} : {len(strat_result)} marqueurs")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"   ⚠️ Erreur stratégie {strat_name}: {e}")

# ── FUSION & INJECTION HTML ───────────────────────────────────

def generate_html(ctx, cfg, filename):
    html = open(TEMPLATE, encoding="utf-8").read()
    html = html.replace("{{candles}}",       json.dumps(ctx["candles"]))
    html = html.replace("{{sessions}}",      json.dumps(ctx["sessions_zones"]))
    html = html.replace("{{trades}}",        json.dumps(ctx["trades"]))
    html = html.replace("{{price_lines}}",   json.dumps(ctx["price_lines"]))
    html = html.replace("{{zones}}",         "[]")
    html = html.replace("{{ind_ema}}",       "[]")
    html = html.replace("{{ind_sma}}",       "[]")
    html = html.replace("{{ind_volume}}",    "[]")
    html = html.replace("{{ind_baseline}}",  "[]")
    html = html.replace("{{ind_custom}}",    "[]")

    html = html.replace("{{tq_score}}",      json.dumps(ctx["tq_score"]))
    html = html.replace("{{tq_text}}",       json.dumps(ctx["tq_text"]))
    html = html.replace("{{tq_color}}",      json.dumps(ctx["tq_color"]))
    html = html.replace("{{ind_tq_labels}}", json.dumps(ctx["tq_labels"]))
    html = html.replace("{{tq_history}}",    json.dumps(ctx["tq_history"]))

    html = html.replace("{{symbol}}",    json.dumps(cfg.SYMBOL))
    html = html.replace("{{timeframe}}", json.dumps(cfg.TIMEFRAME))

    html = html.replace("{{trade_boxes}}", json.dumps(ctx["trade_boxes"]))
    html = html.replace("{{ob_fvg_data}}", json.dumps(ctx["ob_fvg_data"]))
    html = html.replace("{{fvg_data}}", json.dumps(ctx["fvg_data"]))

    ob_colors_js = "{"
    for m in [1, 2, 3]:
        cfg_m = cfg.OB_DETECTION.get("visuals", {}).get(f"method_{m}", {})
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

    output_path = os.path.join(ROOT, filename)
    open(output_path, "w", encoding="utf-8").write(html)
    print(f"✅ {len(ctx['candles'])} bougies — {filename} généré")


if htf_ctx:
    generate_html(htf_ctx, htf_config, "output_htf.html")

generate_html(ltf_ctx, ltf_config, "output_ltf.html")
