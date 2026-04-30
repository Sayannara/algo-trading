from __future__ import annotations

from datetime import datetime, timedelta, time as dt_time
import math

import pandas as pd
import pytz


DEFAULT_TQ_CONFIG = {
    "enabled": True,
    "show_labels": False,
    "lookback_days": 12,
    "min_days": 4,
    "use_decay": True,
    "decay": 0.85,
    "sessions": {
        "tokyo": {"start": "00:00", "end": "08:00"},
        "london": {"start": "08:00", "end": "14:00"},
        "newyork": {"start": "14:00", "end": "22:00"},
    },
}


_LAST_TQ_HISTORY = []


def _get_cfg(config) -> dict:
    cfg = {k: v for k, v in DEFAULT_TQ_CONFIG.items()}
    cfg["sessions"] = {k: dict(v) for k, v in DEFAULT_TQ_CONFIG["sessions"].items()}
    user = getattr(config, "TREND_QUALITY", None) or {}
    for k, v in user.items():
        if k == "sessions" and isinstance(v, dict):
            for name, sess in v.items():
                base = cfg["sessions"].get(name, {})
                cfg["sessions"][name] = {**base, **sess}
        else:
            cfg[k] = v
    return cfg


def _parse_time(value: str) -> dt_time:
    h, m = str(value).split(":")
    return dt_time(int(h), int(m))


def _fmt_score(score: float) -> tuple[float, str, str]:
    score = round(max(0.0, min(100.0, float(score))), 1)
    if score >= 80:
        return score, "Très fort", "#00C853"
    if score >= 65:
        return score, "Fort", "#64DD17"
    if score >= 50:
        return score, "Moyen", "#FFD54F"
    if score >= 35:
        return score, "Faible", "#FF7043"
    return score, "Range", "#EF5350"


def _weighted_mean(values, weights, default=50.0):
    pairs = [(v, w) for v, w in zip(values, weights) if w > 0 and not math.isnan(v)]
    if not pairs:
        return default
    return sum(v * w for v, w in pairs) / sum(w for _, w in pairs)


def _session_score(session_df: pd.DataFrame, use_decay: bool, decay: float) -> float:
    highs = session_df["High"].tolist()
    lows = session_df["Low"].tolist()
    if len(highs) < 2:
        return 50.0

    scores = []
    weights = []
    n = len(highs) - 1

    for i in range(1, len(highs)):
        w = (decay ** (n - i)) if use_decay else 1.0

        up = 0
        if highs[i] > highs[i - 1]:
            up += 1
        if lows[i] > lows[i - 1]:
            up += 1

        if up == 2:
            s = 100.0
        elif up == 1:
            s = 62.5
        else:
            down = 0
            if highs[i] < highs[i - 1]:
                down += 1
            if lows[i] < lows[i - 1]:
                down += 1

            if down == 2:
                s = 0.0
            elif down == 1:
                s = 37.5
            else:
                s = 50.0

        scores.append(s)
        weights.append(w)

    return _weighted_mean(scores, weights, default=50.0)


def _build_daily_sessions(df: pd.DataFrame, cfg: dict, tz) -> pd.DataFrame:
    work = df.copy()
    work["time"] = pd.to_datetime(work["time"], utc=True, errors="coerce")
    work = work.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    if work.empty:
        return pd.DataFrame()

    work["time_local"] = work["time"].dt.tz_convert(tz)
    work["date_local"] = work["time_local"].dt.date

    session_defs = {
        name: {
            "start": _parse_time(values["start"]),
            "end": _parse_time(values["end"]),
        }
        for name, values in cfg["sessions"].items()
    }

    rows = []

    for day in sorted(work["date_local"].unique()):
        row = {"date": day}

        for session_name, sess in session_defs.items():
            start_local = tz.localize(datetime.combine(day, sess["start"]))
            end_local = tz.localize(datetime.combine(day, sess["end"]))
            if end_local <= start_local:
                end_local += timedelta(days=1)

            chunk = work.loc[
                (work["time_local"] >= start_local) &
                (work["time_local"] < end_local)
            ]

            if chunk.empty:
                row[f"{session_name}_high"] = math.nan
                row[f"{session_name}_low"] = math.nan
            else:
                row[f"{session_name}_high"] = float(chunk["High"].max())
                row[f"{session_name}_low"] = float(chunk["Low"].min())

        rows.append(row)

    return pd.DataFrame(rows).reset_index(drop=True)


def compute_trend_quality(df: pd.DataFrame, config):
    global _LAST_TQ_HISTORY

    cfg = _get_cfg(config)
    tz = pytz.timezone(getattr(config, "TIMEZONE", "UTC"))

    if df is None or df.empty:
        _LAST_TQ_HISTORY = []
        return 50.0, "En attente...", "#9E9E9E", []

    daily = _build_daily_sessions(df, cfg, tz)
    if daily.empty:
        _LAST_TQ_HISTORY = []
        return 50.0, "En attente...", "#9E9E9E", []

    lookback = max(2, int(cfg.get("lookback_days", 12)))
    min_days = max(2, int(cfg.get("min_days", 4)))
    use_decay = bool(cfg.get("use_decay", True))
    decay = float(cfg.get("decay", 0.85))

    history = []

    for i in range(len(daily)):
        start_idx = max(0, i - lookback + 1)
        window = daily.iloc[start_idx:i + 1].reset_index(drop=True)

        if len(window) < min_days:
            score, text, color = 50.0, "En attente...", "#9E9E9E"
        else:
            session_scores = []

            for session_name in cfg["sessions"].keys():
                session_df = pd.DataFrame({
                    "High": window[f"{session_name}_high"],
                    "Low": window[f"{session_name}_low"],
                }).dropna()

                session_scores.append(
                    _session_score(session_df, use_decay=use_decay, decay=decay)
                )

            raw_score = sum(session_scores) / len(session_scores) if session_scores else 50.0
            score, text, color = _fmt_score(raw_score)

        history.append({
            "date": str(window.iloc[-1]["date"]),
            "score": score,
            "text": text,
            "color": color,
        })

    _LAST_TQ_HISTORY = history

    final = history[-1]
    return final["score"], final["text"], final["color"], []


def get_score_at(index: int, history=None):
    data = history if history is not None else _LAST_TQ_HISTORY
    if not data:
        return None

    idx = int(index)
    if idx < 0:
        return None
    if idx >= len(data):
        return data[-1]["score"]

    return data[idx]["score"]