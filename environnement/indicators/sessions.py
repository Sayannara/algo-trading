# indicators/sessions.py
# ─────────────────────────────────────────────────────────────
# Calcule les zones de session (rectangles) et conserve
# le high/low des 3 dernières sessions fermées.
#
# Retourne :
#   zones   : list[dict]  → zones pour le chart
#   history : dict        → { 'New York': [{high, low, time_start, time_end}, ...] }
# ─────────────────────────────────────────────────────────────

import pytz
from datetime import time as dtime


def _in_session(t: dtime, start_str: str, end_str: str) -> bool:
    """Gère les sessions normales et celles qui passent minuit."""
    h0, m0 = map(int, start_str.split(':'))
    h1, m1 = map(int, end_str.split(':'))
    start, end = dtime(h0, m0), dtime(h1, m1)
    if end == dtime(0, 0):       # 00:00 = fin de journée
        return t >= start
    if start < end:              # session normale (ex: 09:00-14:00)
        return start <= t < end
    return t >= start or t < end # overnight (ex: 21:00-06:00)


def _hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def compute_sessions(df, config):
    tz            = pytz.timezone(config.TIMEZONE)
    sessions_conf = config.SESSIONS

    current = {key: None for key in sessions_conf}
    history = {s['name']: [] for s in sessions_conf.values()}
    zones   = []

    def _close(key, ses):
        s = current[key]
        if s is None:
            return
        zones.append({
            'time_start':   s['time_start'],
            'time_end':     s['time_end'],
            'price_top':    s['high'],
            'price_bottom': s['low'],
            'color':        _hex_rgba(ses['color'], 0.12),
            'border_color': ses['color'],
            'label':        ses['name'],
        })
        hist = history[ses['name']]
        hist.append({'high': s['high'], 'low': s['low'],
                     'time_start': s['time_start'], 'time_end': s['time_end']})
        if len(hist) > 3:
            hist.pop(0)
        current[key] = None

    for row in df.itertuples(index=False):
        ts = row.time
        ts_local = (pytz.utc.localize(ts) if ts.tzinfo is None else ts).astimezone(tz)
        t_local  = ts_local.time()
        unix_ts  = int(pytz.utc.localize(ts).timestamp() if ts.tzinfo is None else ts.timestamp())

        for key, ses in sessions_conf.items():
            if not ses['enabled']:
                continue
            if _in_session(t_local, ses['start'], ses['end']):
                if current[key] is None:
                    current[key] = {'time_start': unix_ts, 'time_end': unix_ts,
                                    'high': float(row.High), 'low': float(row.Low)}
                else:
                    current[key]['time_end'] = unix_ts
                    current[key]['high'] = max(current[key]['high'], float(row.High))
                    current[key]['low']  = min(current[key]['low'],  float(row.Low))
            else:
                if current[key] is not None:
                    _close(key, ses)

    # Fermer les sessions encore ouvertes en fin de données
    for key, ses in sessions_conf.items():
        if ses['enabled'] and current[key] is not None:
            _close(key, ses)

    return zones, history


# ── Helpers pour les stratégies ───────────────────────────────
# n=0 → dernière session fermée, n=1 → avant-dernière, n=2 → encore avant

def get_session_high(history: dict, name: str, n: int = 0):
    h = history.get(name, [])
    return h[-(n+1)]['high'] if len(h) >= n+1 else None

def get_session_low(history: dict, name: str, n: int = 0):
    h = history.get(name, [])
    return h[-(n+1)]['low'] if len(h) >= n+1 else None