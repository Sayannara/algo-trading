from __future__ import annotations

from datetime import datetime, timedelta, time as dt_time
import math

import pandas as pd
import pytz


# ── DEFAULTS ──────────────────────────────────────────────────────────────────
DEFAULT_TQ_CONFIG = {
    "enabled": True,
    "show_labels": True,
    "lookback_days": 12,
    "min_days": 4,
    "use_decay": True,
    "decay": 0.85,
    "label_position": "aboveBar",
    "label_shape": "circle",
    # Sessions internes — indépendantes de config.SESSIONS
    "sessions": {
        "tokyo":   {"start": "00:00", "end": "08:00"},
        "london":  {"start": "08:00", "end": "14:00"},
        "newyork": {"start": "14:00", "end": "22:00"},
    },
}

_LAST_TQ_HISTORY: list[dict] = []


# ── HELPERS ───────────────────────────────────────────────────────────────────
def _get_cfg(config) -> dict:
    cfg = {k: v for k, v in DEFAULT_TQ_CONFIG.items()}
    cfg["sessions"] = {k: dict(v) for k, v in DEFAULT_TQ_CONFIG["sessions"].items()}
    user = getattr(config, "TREND_QUALITY", None) or {}
    for k, v in user.items():
        if k == "sessions":
            cfg["sessions"].update(v)
        else:
            cfg[k] = v
    return cfg


def _parse_time(s: str) -> dt_time:
    h, m = s.split(":")
    return dt_time(int(h), int(m))


def _to_lwc_ts(ts, tz) -> int:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    local = ts.tz_convert(tz)
    offset = int(local.utcoffset().total_seconds())
    return int(ts.timestamp()) + offset


def _fmt(x) -> str:
    return "N/A" if (x is None or (isinstance(x, float) and math.isnan(x))) else f"{x:.5f}"


def _weighted_mean(vals, weights, default=0.0) -> float:
    pairs = [(v, w) for v, w in zip(vals, weights) if w > 0 and not math.isnan(v)]
    if not pairs:
        return default
    return sum(v * w for v, w in pairs) / sum(w for _, w in pairs)


# ── DAILY SESSION HIGHS/LOWS ──────────────────────────────────────────────────
def _build_daily(df: pd.DataFrame, cfg: dict, tz) -> pd.DataFrame:
    work = df.copy()
    work["time"] = pd.to_datetime(work["time"], utc=True, errors="coerce")
    work = work.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    work["local_time"] = work["time"].dt.tz_convert(tz)
    work["local_date"] = work["local_time"].dt.date

    first_bar = work.groupby("local_date")["time"].first().to_dict()
    sess_defs = {
        bucket: {
            "start": _parse_time(v["start"]),
            "end":   _parse_time(v["end"]),
        }
        for bucket, v in cfg["sessions"].items()
    }

    rows = []
    for day in sorted(work["local_date"].unique()):
        row = {"date": day, "marker_time": first_bar.get(day)}
        has_data = False

        for bucket, s in sess_defs.items():
            local_start = tz.localize(datetime.combine(day, s["start"]))
            local_end   = tz.localize(datetime.combine(day, s["end"]))
            if local_end <= local_start:
                local_end += timedelta(days=1)

            chunk = work.loc[
                (work["local_time"] >= local_start) &
                (work["local_time"] <  local_end)
            ]

            if chunk.empty:
                row[f"{bucket}_high"] = math.nan
                row[f"{bucket}_low"]  = math.nan
            else:
                row[f"{bucket}_high"] = float(chunk["High"].max())
                row[f"{bucket}_low"]  = float(chunk["Low"].min())
                has_data = True

        if has_data and row["marker_time"] is not None:
            rows.append(row)

    return pd.DataFrame(rows).reset_index(drop=True) if rows else pd.DataFrame()


# ── SCORING ───────────────────────────────────────────────────────────────────
def _intraday_alignment(row: pd.Series) -> float:
    buckets = list(DEFAULT_TQ_CONFIG["sessions"].keys())
    pairs, score = [], []
    for i in range(len(buckets)):
        for j in range(i + 1, len(buckets)):
            h1 = row.get(f"{buckets[i]}_high", math.nan)
            l1 = row.get(f"{buckets[i]}_low",  math.nan)
            h2 = row.get(f"{buckets[j]}_high", math.nan)
            l2 = row.get(f"{buckets[j]}_low",  math.nan)
            if any(math.isnan(v) for v in [h1, l1, h2, l2]):
                continue
            bullish = h1 <= h2 and l1 <= l2
            bearish = h1 >= h2 and l1 >= l2
            pairs.append(1.0 if (bullish or bearish) else 0.0)
    return sum(pairs) / len(pairs) if pairs else 0.0


def _score_window(window: pd.DataFrame, use_decay: bool, decay: float) -> float:
    if len(window) < 2:
        return 50.0

    buckets = list(DEFAULT_TQ_CONFIG["sessions"].keys())
    structure_scores, directions, weights = [], [], []
    n = len(window) - 1

    for i in range(1, len(window)):
        w = decay ** (n - i) if use_decay else 1.0
        prev, curr = window.iloc[i - 1], window.iloc[i]

        for b in buckets:
            ph, pl = prev.get(f"{b}_high", math.nan), prev.get(f"{b}_low",  math.nan)
            ch, cl = curr.get(f"{b}_high", math.nan), curr.get(f"{b}_low",  math.nan)
            if any(math.isnan(v) for v in [ph, pl, ch, cl]):
                continue

            up   = int(ch > ph) + int(cl > pl)
            down = int(ch < ph) + int(cl < pl)

            if   up == 2 or down == 2:   struct = 1.0
            elif up == 1 and down == 0:  struct = 0.55
            elif down == 1 and up == 0:  struct = 0.55
            elif up == 1 and down == 1:  struct = 0.15
            else:                        struct = 0.0

            direction = 1 if up > down else -1 if down > up else 0

            structure_scores.append(struct)
            directions.append(direction)
            weights.append(w)

    move_q    = _weighted_mean(structure_scores, weights, 0.0)
    dir_dom   = abs(_weighted_mean(directions, weights, 0.0))
    intra_q   = _intraday_alignment(window.iloc[-1])

    score = 100.0 * (0.65 * move_q + 0.25 * dir_dom + 0.10 * intra_q)
    return round(max(0.0, min(100.0, score)), 1)


def _to_text_color(score: float) -> tuple[str, str]:
    if score >= 80: return "Très fort", "#00C853"
    if score >= 65: return "Fort",      "#64DD17"
    if score >= 50: return "Moyen",     "#FFD54F"
    if score >= 35: return "Faible",    "#FF7043"
    return "Range", "#EF5350"


# ── PUBLIC API ────────────────────────────────────────────────────────────────
def compute_trend_quality(df: pd.DataFrame, config) -> tuple[float, str, str, list]:
    global _LAST_TQ_HISTORY

    cfg      = _get_cfg(config)
    tz       = pytz.timezone(getattr(config, "TIMEZONE", "UTC"))
    daily    = _build_daily(df, cfg, tz)

    if daily.empty:
        _LAST_TQ_HISTORY = []
        return 50.0, "En attente...", "#9E9E9E", []

    lookback    = max(2, int(cfg["lookback_days"]))
    min_days    = max(2, int(cfg["min_days"]))
    use_decay   = bool(cfg["use_decay"])
    decay       = float(cfg["decay"])
    show_labels = bool(cfg["show_labels"])
    lbl_pos     = cfg["label_position"]
    lbl_shape   = cfg["label_shape"]

    history, labels = [], []

    for i in range(len(daily)):
        start_idx = max(0, i - lookback + 1)
        window    = daily.iloc[start_idx:i + 1].reset_index(drop=True)
        row       = daily.iloc[i]
        lwc_time  = _to_lwc_ts(row["marker_time"], tz)

        if len(window) < min_days:
            score, text, color = 50.0, "En attente...", "#9E9E9E"
        else:
            score = _score_window(window, use_decay, decay)
            text, color = _to_text_color(score)

        history.append({"time": lwc_time, "score": score, "text": text, "color": color, "date": str(row["date"])})

        if show_labels:
            buckets = list(cfg["sessions"].keys())
            label_text = (
                f"TQ {int(round(score))}% {text}\n" +
                "\n".join(
                    f"{b.capitalize():8}: H {_fmt(row.get(f'{b}_high'))} / L {_fmt(row.get(f'{b}_low'))}"
                    for b in buckets
                )
            )
            labels.append({"time": lwc_time, "position": lbl_pos, "color": color, "shape": lbl_shape, "text": label_text})

    history.sort(key=lambda x: x["time"])
    labels.sort(key=lambda x: x["time"])
    _LAST_TQ_HISTORY = history

    final = history[-1]
    return final["score"], final["text"], final["color"], labels


def get_score_at(lwc_timestamp: int, history: list | None = None) -> float | None:
    data = history if history is not None else _LAST_TQ_HISTORY
    last = None
    for item in data:
        if item["time"] <= int(lwc_timestamp):
            last = item
        else:
            break
    return None if last is None else last["score"]