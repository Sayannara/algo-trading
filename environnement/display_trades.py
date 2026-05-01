import pandas as pd
import pytz

OUTCOME_STYLE = {
    'TP1':      {'color': '#26a69a', 'shape': 'arrowUp',   'label': 'TP1'},
    'TP2':      {'color': '#00C853', 'shape': 'arrowUp',   'label': 'TP2'},
    'TRAIL':    {'color': '#FF9800', 'shape': 'circle',    'label': 'Trail'},
    'Trail':    {'color': '#FF9800', 'shape': 'circle',    'label': 'Trail'},
    'SL_INIT':  {'color': '#ef5350', 'shape': 'arrowDown', 'label': 'SL'},
    'EOD':      {'color': '#9E9E9E', 'shape': 'square',    'label': 'EOD'},
    'BE':       {'color': '#FFC107', 'shape': 'circle',    'label': 'BE'},
}


def load_trades(csv_path: str, symbol: str, tz_name: str) -> dict:
    """
    Lit trades_result.csv et retourne un dict:
      {
        "markers":     [ {time, position, color, shape, text}, ... ],
        "price_lines": [ {price, color, label}, ... ],
      }
    """
    tz = pytz.timezone(tz_name)

    df = pd.read_csv(csv_path)
    df = df[df['symbol'] == symbol].copy()

    if df.empty:
        return {"markers": [], "price_lines": []}

    markers = []
    price_lines = []

    for _, row in df.iterrows():
        entry_time = pd.Timestamp(row['entry_time'])
        exit_time  = pd.Timestamp(row['exit_time'])

        entry_ts = _to_lwc_ts(entry_time, tz)
        exit_ts  = _to_lwc_ts(exit_time, tz)

        outcome   = str(row.get('outcome', '')).strip()
        outcome_u = outcome.upper()
        direction = str(row.get('direction', '')).strip().lower()  # bullish / bearish
        style     = OUTCOME_STYLE.get(outcome_u, {'color': '#ffffff', 'shape': 'circle', 'label': outcome_u})

        is_long = direction == 'bullish'

        # Marker d'entrée
        markers.append({
            "time":     entry_ts,
            "position": "belowBar" if is_long else "aboveBar",
            "color":    "#26a69a" if is_long else "#ef5350",
            "shape":    "arrowUp" if is_long else "arrowDown",
            "text":     "BUY" if is_long else "SELL",
        })

        # Marker de sortie
        markers.append({
            "time":     exit_ts,
            "position": "aboveBar" if is_long else "belowBar",
            "color":    style["color"],
            "shape":    style["shape"],
            "text":     style["label"],
        })

        # Ligne au prix d'entrée (optionnel, pour plus tard)
        price_lines.append({
            "price": float(row["entry"]),
            "color": "#26a69a" if is_long else "#ef5350",
            "label": f"Entry {direction.upper()}",
        })

        # Ligne au prix de sortie (optionnel)
        price_lines.append({
            "price": float(row["exit_price"]),
            "color": style["color"],
            "label": f"Exit {outcome_u}",
        })

    return {
        "markers": markers,
        "price_lines": price_lines,
    }


def _to_lwc_ts(ts: pd.Timestamp, tz) -> int:
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    local  = ts.tz_convert(tz)
    offset = int(local.utcoffset().total_seconds())
    return int(ts.timestamp()) + offset


def load_trade_boxes(
    csv_path: str,
    symbol: str,
    tz_name: str,
    candles: list,
    timeframe: str,
    max_rr: int = 3,
) -> list:
    """
    Construit les trade_boxes à partir de trades_result.csv.
    Chaque box contient : TP rect, SL rect, ligne d'entrée, lignes RR.
    """
    tz = pytz.timezone(tz_name)
    df = pd.read_csv(csv_path)
    df = df[df['symbol'] == symbol].copy()

    if df.empty:
        return []

    # Index des timestamps des bougies pour calculer boxWidth
    candle_times = [c["time"] for c in candles]

    # Largeur de la box en nombre de bougies selon le timeframe
    tf_minutes = _tf_to_minutes(timeframe)
    if tf_minutes == 1:
        box_bars = 120
    elif tf_minutes <= 5:
        box_bars = 60
    else:
        box_bars = 30

    boxes = []

    for _, row in df.iterrows():
        entry_time = pd.Timestamp(row['entry_time'])
        entry_ts   = _to_lwc_ts(entry_time, tz)

        entry_price = float(row['entry'])
        sl_price    = float(row['sl'])
        direction   = str(row.get('direction', '')).strip().lower()
        is_long     = direction == 'bullish'

        sl_dist = abs(entry_price - sl_price)
        if sl_dist <= 0:
            continue

        # Trouver la position de la bougie d'entrée dans CANDLES
        try:
            entry_idx = candle_times.index(entry_ts)
        except ValueError:
            # Prendre la bougie la plus proche si timestamp exact absent
            entry_idx = min(
                range(len(candle_times)),
                key=lambda i: abs(candle_times[i] - entry_ts)
            )

        # Timestamp de la borne droite (entry + boxWidth bougies)
        right_idx = min(entry_idx + box_bars, len(candle_times) - 1)
        time_right = candle_times[right_idx]

        boxes.append({
            "time_entry": entry_ts,
            "time_right": time_right,
            "entry":      entry_price,
            "sl":         sl_price,
            "is_long":    is_long,
            "max_rr":     max_rr,
            "colors": {
                "tp_fill":    "rgba(0, 150, 136, 0.3)",
                "sl_fill":    "rgba(239, 83, 80, 0.3)",
                "entry_line": "#ffffff",
                "rr_line":    "rgba(255, 255, 255, 0.25)",
            }
        })

    return boxes


def _tf_to_minutes(timeframe: str) -> int:
    """Convertit un timeframe string (M1, M5, M15, H1…) en minutes."""
    tf = timeframe.upper()
    if tf.startswith("M"):
        return int(tf[1:])
    if tf.startswith("H"):
        return int(tf[1:]) * 60
    if tf.startswith("D"):
        return 1440
    return 15  # fallback