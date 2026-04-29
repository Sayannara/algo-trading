# indicators/sessions.py

import pytz
from datetime import time as dtime


def _in_session(t: dtime, start_str: str, end_str: str) -> bool:
    h0, m0 = map(int, start_str.split(':'))
    h1, m1 = map(int, end_str.split(':'))
    start, end = dtime(h0, m0), dtime(h1, m1)
    if end == dtime(0, 0):
        return t >= start
    if start < end:
        return start <= t < end
    return t >= start or t < end


def _hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def _to_tz_ts(ts, tz) -> int:
    ts_utc = ts if ts.tzinfo else pytz.utc.localize(ts)
    offset = int(ts_utc.astimezone(tz).utcoffset().total_seconds())
    return int(ts_utc.timestamp()) + offset


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
        alpha = ses.get('fill_alpha', 0.12)
        zones.append({
            'time_start':   s['time_start'],
            'time_end':     s['time_end'],
            'price_top':    s['high'],
            'price_bottom': s['low'],
            'color':        _hex_rgba(ses['color'], alpha),
            'border_color': ses['color'],
            'label':        ses['name'],
        })
        hist = history[ses['name']]
        hist.append({
            'high':       s['high'],
            'low':        s['low'],
            'time_start': s['raw_start'],
            'time_end':   s['raw_end'],
        })
        if len(hist) > 3:
            hist.pop(0)
        current[key] = None

    for row in df.itertuples(index=False):
        ts       = row.time
        ts_utc   = ts if ts.tzinfo else pytz.utc.localize(ts)
        ts_local = ts_utc.astimezone(tz)
        t_local  = ts_local.time()
        chart_ts = _to_tz_ts(ts, tz)
        raw_ts   = int(ts_utc.timestamp())

        for key, ses in sessions_conf.items():
            if not ses['enabled']:
                continue
            if _in_session(t_local, ses['start'], ses['end']):
                if current[key] is None:
                    current[key] = {
                        'time_start': chart_ts, 'time_end': chart_ts,
                        'raw_start':  raw_ts,   'raw_end':  raw_ts,
                        'high': float(row.High), 'low': float(row.Low),
                    }
                else:
                    current[key]['time_end'] = chart_ts
                    current[key]['raw_end']  = raw_ts
                    current[key]['high'] = max(current[key]['high'], float(row.High))
                    current[key]['low']  = min(current[key]['low'],  float(row.Low))
            else:
                if current[key] is not None:
                    _close(key, ses)

    for key, ses in sessions_conf.items():
        if ses['enabled'] and current[key] is not None:
            _close(key, ses)

    return zones, history


def get_session_high(history: dict, name: str, n: int = 0):
    h = history.get(name, [])
    return h[-(n + 1)]['high'] if len(h) >= n + 1 else None


def get_session_low(history: dict, name: str, n: int = 0):
    h = history.get(name, [])
    return h[-(n + 1)]['low'] if len(h) >= n + 1 else None