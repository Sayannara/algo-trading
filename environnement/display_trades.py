import pandas as pd
import pytz

OUTCOME_STYLE = {
    'TP1':      {'color': '#26a69a', 'shape': 'arrowUp',   'label': 'TP1'},
    'TP2':      {'color': '#00C853', 'shape': 'arrowUp',   'label': 'TP2'},
    'Trail':    {'color': '#FF9800', 'shape': 'circle',    'label': 'Trail'},
    'TRAIL':    {'color': '#FF9800', 'shape': 'circle',    'label': 'Trail'},
    'SL_INIT':  {'color': '#ef5350', 'shape': 'arrowDown', 'label': 'SL'},
    'EOD':      {'color': '#9E9E9E', 'shape': 'square',    'label': 'EOD'},
    'BE':       {'color': '#FFC107', 'shape': 'circle',    'label': 'BE'},
}


def load_trades(csv_path: str, symbol: str, tz_name: str) -> list[dict]:
    tz = pytz.timezone(tz_name)

    df = pd.read_csv(csv_path)
    # colonnes réelles : date,symbol,...,direction,entry,entry_time,...,outcome,exit_time,exit_price,...
    df = df[df['symbol'] == symbol].copy()

    if df.empty:
        return []

    trades = []

    for _, row in df.iterrows():
        entry_ts = _to_lwc_ts(pd.Timestamp(row['entry_time']), tz)
        exit_ts  = _to_lwc_ts(pd.Timestamp(row['exit_time']),  tz)

        outcome  = str(row.get('outcome', '')).strip().upper()
        direction = str(row.get('direction', '')).strip().lower()  # bullish / bearish
        style    = OUTCOME_STYLE.get(outcome, {'color': '#ffffff', 'shape': 'circle', 'label': outcome})

        is_long = direction == 'bullish'

        # Marker d'entrée
        trades.append({
            'time':     entry_ts,
            'position': 'belowBar' if is_long else 'aboveBar',
            'color':    '#26a69a' if is_long else '#ef5350',
            'shape':    'arrowUp' if is_long else 'arrowDown',
            'text':     'BUY' if is_long else 'SELL',
        })

        # Ligne de prix au niveau d'entrée
        trades.append({
            '_type': 'price_line',
            'price': float(row['entry']),  # colonne réelle
            'color': '#26a69a' if is_long else '#ef5350',
            'label': f"Entry {direction.upper()}",
        })

        # Marker de sortie
        trades.append({
            'time':     exit_ts,
            'position': 'aboveBar' if is_long else 'belowBar',
            'color':    style['color'],
            'shape':    style['shape'],
            'text':     style['label'],
        })

        # Ligne de prix au niveau de sortie
        trades.append({
            '_type': 'price_line',
            'price': float(row['exit_price']),  # colonne réelle
            'color': style['color'],
            'label': f"Exit {outcome}",
        })

    return trades


def _to_lwc_ts(ts: pd.Timestamp, tz) -> int:
    if ts.tzinfo is None:
        ts = ts.tz_localize('UTC')
    else:
        ts = ts.tz_convert('UTC')
    local  = ts.tz_convert(tz)
    offset = int(local.utcoffset().total_seconds())
    return int(ts.timestamp()) + offset