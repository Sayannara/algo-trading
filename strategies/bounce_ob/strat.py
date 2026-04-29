from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import pandas as pd

from indicators import (
    get_mt5_data,
    calculer_trend_quality,
    calculer_trend_quality_par_jour,
)
import config_strat


@dataclass
class LiquiditySignal:
    direction: str
    time: int
    price: float
    reason: str
    trend_score: float
    tokyo_high: float
    tokyo_low: float


def _build_df_with_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values("time").reset_index(drop=True)
    df["timestamp"] = df["time"].apply(lambda t: int(t.timestamp()))
    return df


def _get_local_time(row_time, tz_name: str):
    if row_time.tzinfo is None:
        return row_time.tz_localize("Etc/UTC").tz_convert(tz_name)
    return row_time.tz_convert(tz_name)


def _prepare_local_df(df: pd.DataFrame, tz_name: str) -> pd.DataFrame:
    out = df.copy()

    if out["time"].dt.tz is None:
        out["time_local"] = out["time"].dt.tz_localize("Etc/UTC").dt.tz_convert(tz_name)
    else:
        out["time_local"] = out["time"].dt.tz_convert(tz_name)

    out["date_local"] = out["time_local"].dt.date
    out["hour_local"] = out["time_local"].dt.hour
    return out


def _is_trading_hour(row_time, tz_name: str, start_h: int, end_h: int) -> bool:
    t_local = _get_local_time(row_time, tz_name)
    h = t_local.hour
    return (h >= start_h) and (h < end_h)


def _session_id(row_time, tz_name: str) -> str:
    t_local = _get_local_time(row_time, tz_name)
    return t_local.strftime("%Y-%m-%d")


def _build_tokyo_ranges(df: pd.DataFrame) -> pd.DataFrame:
    tz_name = config_strat.TRADING_TIMEZONE
    tokyo_start = int(getattr(config_strat, "TOKYO_START_HOUR", 0))
    tokyo_end = int(getattr(config_strat, "TOKYO_END_HOUR", 8))

    df_local = _prepare_local_df(df, tz_name)

    tokyo_df = df_local[
        (df_local["hour_local"] >= tokyo_start) &
        (df_local["hour_local"] < tokyo_end)
    ].copy()

    if tokyo_df.empty:
        return pd.DataFrame(columns=["date_local", "tokyo_high", "tokyo_low"])

    tokyo_ranges = (
        tokyo_df
        .groupby("date_local")
        .agg(
            tokyo_high=("High", "max"),
            tokyo_low=("Low", "min")
        )
        .reset_index()
    )

    return tokyo_ranges


def detect_tokyo_liquidity_sweeps(
    df: pd.DataFrame,
    trend_info: Optional[Dict[str, Any]] = None,
) -> List[LiquiditySignal]:
    signals: List[LiquiditySignal] = []

    if df is None or df.empty:
        return signals

    tz_name = config_strat.TRADING_TIMEZONE
    start_h = int(getattr(config_strat, "TRADING_START_HOUR", 8))
    end_h = int(getattr(config_strat, "TRADING_END_HOUR", 18))
    trend_long_min = float(getattr(config_strat, "TREND_LONG_MIN", 60.0))
    trend_short_max = float(getattr(config_strat, "TREND_SHORT_MAX", 40.0))
    one_signal_per_day = bool(getattr(config_strat, "ONE_SIGNAL_PER_DAY", True))

    trend_score = 50.0
    if trend_info is not None:
        trend_score = float(trend_info.get("score", 50.0))

    df_i = _build_df_with_index(df)
    df_i = _prepare_local_df(df_i, tz_name)

    tokyo_ranges = _build_tokyo_ranges(df_i)
    if tokyo_ranges.empty:
        return signals

    df_i = df_i.merge(tokyo_ranges, on="date_local", how="left")

    signaled_days = set()

    for i in range(len(df_i)):
        row = df_i.iloc[i]
        row_dt = row["time"]

        if not _is_trading_hour(row_dt, tz_name, start_h, end_h):
            continue

        if pd.isna(row["tokyo_high"]) or pd.isna(row["tokyo_low"]):
            continue

        day_id = _session_id(row_dt, tz_name)
        if one_signal_per_day and day_id in signaled_days:
            continue

        curr_high = float(row["High"])
        curr_low = float(row["Low"])
        curr_time = int(row["timestamp"])

        tokyo_high = float(row["tokyo_high"])
        tokyo_low = float(row["tokyo_low"])

        if (curr_high > tokyo_high) and (trend_score < trend_short_max):
            signals.append(
                LiquiditySignal(
                    direction="sell",
                    time=curr_time,
                    price=curr_high,
                    reason="Tokyo high liquidity sweep",
                    trend_score=trend_score,
                    tokyo_high=tokyo_high,
                    tokyo_low=tokyo_low,
                )
            )
            if one_signal_per_day:
                signaled_days.add(day_id)
            continue

        if (curr_low < tokyo_low) and (trend_score > trend_long_min):
            signals.append(
                LiquiditySignal(
                    direction="buy",
                    time=curr_time,
                    price=curr_low,
                    reason="Tokyo low liquidity sweep",
                    trend_score=trend_score,
                    tokyo_high=tokyo_high,
                    tokyo_low=tokyo_low,
                )
            )
            if one_signal_per_day:
                signaled_days.add(day_id)
            continue

    return signals


def signals_to_markers(signals: List[LiquiditySignal]) -> List[Dict[str, Any]]:
    markers = []

    for s in signals:
        is_buy = s.direction == "buy"
        markers.append({
            "time": int(s.time),
            "position": "belowBar" if is_buy else "aboveBar",
            "color": "#51cf66" if is_buy else "#ff6b6b",
            "shape": "arrowUp" if is_buy else "arrowDown",
            "text": f"{'BUY' if is_buy else 'SELL'} | {s.trend_score:.1f}%",
        })

    markers.sort(key=lambda m: m["time"])
    return markers


def signals_to_dicts(signals: List[LiquiditySignal]) -> List[Dict[str, Any]]:
    out = []
    for s in signals:
        out.append({
            "direction": s.direction,
            "time": s.time,
            "price": s.price,
            "reason": s.reason,
            "trend_score": s.trend_score,
            "tokyo_high": s.tokyo_high,
            "tokyo_low": s.tokyo_low,
        })
    return out


def run_strategy():
    df = get_mt5_data()
    if df is None:
        return {
            "df": None,
            "trend_info": None,
            "daily_trend": [],
            "markers": [],
            "trades": [],
            "fvg_zones": [],
            "ob_zones": [],
        }

    trend_info = calculer_trend_quality(df)
    daily_trend = calculer_trend_quality_par_jour(df)

    signals = detect_tokyo_liquidity_sweeps(df, trend_info)
    markers = signals_to_markers(signals)

    return {
        "df": df,
        "trend_info": trend_info,
        "daily_trend": daily_trend,
        "markers": markers,
        "trades": [],
        "fvg_zones": [],
        "ob_zones": [],
    }


if __name__ == "__main__":
    result = run_strategy()

    trend_info = result.get("trend_info")
    markers = result.get("markers", [])

    if trend_info is not None:
        print(f"Trend quality: {trend_info['text']} (score={trend_info['score']:.2f}%)")
    else:
        print("Trend quality: N/A")

    print(f"Signaux Tokyo liquidity sweep détectés: {len(markers)}")