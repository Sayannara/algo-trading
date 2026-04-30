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