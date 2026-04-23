import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import pandas as pd

from indicators import (
    get_mt5_data,
    detect_fvg_groups,
    attach_ict_ob_to_fvg,
    calculer_sessions,
    calculer_trend_quality,
)


@dataclass
class Trade:
    direction: str          # "long" ou "short"
    entry_time: int
    entry_price: float
    sl: float
    tp: float
    size: float
    exit_time: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    ob_start: Optional[int] = None
    ob_end: Optional[int] = None
    session_tokyo_high: Optional[float] = None
    trend_score: Optional[float] = None


def _build_df_with_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values("time").reset_index(drop=True)
    df["timestamp"] = df["time"].apply(lambda t: int(t.timestamp()))
    return df


def _build_ob_frame(ob_zones: List[Dict[str, Any]]) -> pd.DataFrame:
    if not ob_zones:
        return pd.DataFrame(columns=["type", "start", "end", "max_p", "min_p"])
    return pd.DataFrame(ob_zones)[["type", "start", "end", "max_p", "min_p"]]


def _build_tokyo_highs(df: pd.DataFrame) -> pd.DataFrame:
    df_local = df.copy()
    if df_local["time"].dt.tz is None:
        df_local["time_local"] = df_local["time"].dt.tz_localize("Etc/UTC").dt.tz_convert("Europe/Zurich")
    else:
        df_local["time_local"] = df_local["time"].dt.tz_convert("Europe/Zurich")

    df_local["date"] = df_local["time_local"].dt.date
    df_local["hour"] = df_local["time_local"].dt.hour

    def get_session(h):
        if 0 <= h < 8:
            return "TKY"
        elif 8 <= h < 14:
            return "LDN"
        else:
            return "NY"

    df_local["session"] = df_local["hour"].apply(get_session)

    session_stats = (
        df_local
        .groupby(["date", "session"])
        .agg({"High": "max"})
        .reset_index()
    )

    tokyo = session_stats[session_stats["session"] == "TKY"].copy()
    tokyo.rename(columns={"High": "tokyo_high"}, inplace=True)
    return tokyo[["date", "tokyo_high"]]


def _attach_tokyo_high_to_bars(df: pd.DataFrame, tokyo_highs: pd.DataFrame) -> pd.Series:
    df_local = df.copy()
    if df_local["time"].dt.tz is None:
        df_local["time_local"] = df_local["time"].dt.tz_localize("Etc/UTC").dt.tz_convert("Europe/Zurich")
    else:
        df_local["time_local"] = df_local["time"].dt.tz_convert("Europe/Zurich")

    df_local["date"] = df_local["time_local"].dt.date

    merged = df_local[["date"]].merge(tokyo_highs, on="date", how="left")
    merged["tokyo_high_prev"] = merged["tokyo_high"].shift(1)
    merged["tokyo_high_effective"] = merged["tokyo_high_prev"].bfill()
    return merged["tokyo_high_effective"]


def backtest_ob_trend_strategy(
    df: pd.DataFrame,
    ob_zones: List[Dict[str, Any]],
    trend_info: Dict[str, Any],
    size_lots: float = 5.0,
    trend_long_min: float = 60.0,
    trend_short_max: float = 40.0,
    sl_buffer: float = 0.00005
) -> List[Trade]:
    trades: List[Trade] = []

    if df is None or df.empty or not ob_zones or trend_info is None:
        return trades

    trend_score = float(trend_info.get("score", 50.0))

    df_i = _build_df_with_index(df)
    ob_df = _build_ob_frame(ob_zones)
    tokyo_highs = _build_tokyo_highs(df_i)
    tokyo_high_series = _attach_tokyo_high_to_bars(df_i, tokyo_highs)

    has_trade = False
    current_trade: Optional[Trade] = None

    for i in range(len(df_i)):
        row = df_i.iloc[i]
        t = int(row["timestamp"])
        o = float(row["Open"])
        h = float(row["High"])
        l = float(row["Low"])
        c = float(row["Close"])
        tokyo_high = float(tokyo_high_series.iloc[i]) if not pd.isna(tokyo_high_series.iloc[i]) else None

        active_obs = ob_df[(ob_df["start"] <= t) & (ob_df["end"] >= t)]

        if current_trade is not None:
            if current_trade.direction == "long":
                if l <= current_trade.sl:
                    current_trade.exit_time = t
                    current_trade.exit_price = current_trade.sl
                    current_trade.exit_reason = "SL"
                    trades.append(current_trade)
                    current_trade = None
                    has_trade = False
                elif tokyo_high is not None and h >= current_trade.tp:
                    current_trade.exit_time = t
                    current_trade.exit_price = current_trade.tp
                    current_trade.exit_reason = "TP"
                    trades.append(current_trade)
                    current_trade = None
                    has_trade = False

            elif current_trade.direction == "short":
                if h >= current_trade.sl:
                    current_trade.exit_time = t
                    current_trade.exit_price = current_trade.sl
                    current_trade.exit_reason = "SL"
                    trades.append(current_trade)
                    current_trade = None
                    has_trade = False
                elif tokyo_high is not None and l <= current_trade.tp:
                    current_trade.exit_time = t
                    current_trade.exit_price = current_trade.tp
                    current_trade.exit_reason = "TP"
                    trades.append(current_trade)
                    current_trade = None
                    has_trade = False

        if current_trade is not None:
            continue

        if active_obs.empty:
            continue

        if tokyo_high is None:
            continue

        for _, ob in active_obs.iterrows():
            ob_type = ob["type"]
            ob_top = float(ob["max_p"])
            ob_bot = float(ob["min_p"])
            ob_start = int(ob["start"])
            ob_end = int(ob["end"])

            if trend_score >= trend_long_min and ob_type == "bullish_ob":
                if (l <= ob_top) and (h >= ob_bot):
                    entry_price = c
                    sl = ob_bot - sl_buffer
                    tp = tokyo_high

                    current_trade = Trade(
                        direction="long",
                        entry_time=t,
                        entry_price=entry_price,
                        sl=sl,
                        tp=tp,
                        size=size_lots,
                        ob_start=ob_start,
                        ob_end=ob_end,
                        session_tokyo_high=tokyo_high,
                        trend_score=trend_score,
                    )
                    has_trade = True
                    break

            elif trend_score <= trend_short_max and ob_type == "bearish_ob":
                if (l <= ob_top) and (h >= ob_bot):
                    entry_price = c
                    sl = ob_top + sl_buffer
                    tp = tokyo_high

                    current_trade = Trade(
                        direction="short",
                        entry_time=t,
                        entry_price=entry_price,
                        sl=sl,
                        tp=tp,
                        size=size_lots,
                        ob_start=ob_start,
                        ob_end=ob_end,
                        session_tokyo_high=tokyo_high,
                        trend_score=trend_score,
                    )
                    has_trade = True
                    break

    return trades


def trades_to_dicts(trades: List[Trade]) -> List[Dict[str, Any]]:
    out = []
    for t in trades:
        out.append({
            "direction": t.direction,
            "entry_time": t.entry_time,
            "entry_price": t.entry_price,
            "sl": t.sl,
            "tp": t.tp,
            "size": t.size,
            "exit_time": t.exit_time,
            "exit_price": t.exit_price,
            "exit_reason": t.exit_reason,
            "ob_start": t.ob_start,
            "ob_end": t.ob_end,
            "session_tokyo_high": t.session_tokyo_high,
            "trend_score": t.trend_score,
        })
    return out


def run_strategy():
    df = get_mt5_data()
    if df is None:
        return [], None, None, None

    trend_info = calculer_trend_quality(df)
    fvg_zones, summary = detect_fvg_groups(df)
    ob_zones = attach_ict_ob_to_fvg(df, fvg_zones)
    session_zones = calculer_sessions(df)

    trades = backtest_ob_trend_strategy(df, ob_zones, trend_info)

    return trades, trend_info, fvg_zones, ob_zones

if __name__ == "__main__":
    run_strategy()