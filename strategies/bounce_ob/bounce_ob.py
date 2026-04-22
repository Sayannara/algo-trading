import pandas as pd

from .config import (
    OB_EXTENSION_HOURS,
    MIN_GAP_PIPS,
    MIN_OB_BODY_PIPS,
    FIRST_RETEST_DELAY_HOURS,
    ENTRY_RETEST_DELAY_HOURS,
    REJECTION_CLOSE_BUFFER_PIPS,
    SL_BUFFER_PIPS,
    TOKYO_START_HOUR,
    TOKYO_END_HOUR,
    PIP_SIZE,
    ALLOW_ONLY_ONE_TRADE_AT_A_TIME,
)


def _prepare_dataframe(df):
    data = df.copy()
    data["time"] = pd.to_datetime(data["time"])
    data = data.sort_values("time").reset_index(drop=True)
    return data


def _resample_htf(df):
    htf = (
        df.set_index("time")
        .resample("30min")
        .agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
        })
        .dropna()
        .reset_index()
    )
    return htf


def _body_size_pips(candle):
    return abs(float(candle["Close"]) - float(candle["Open"])) / PIP_SIZE


def _detect_order_blocks(htf):
    obs = []

    for i in range(1, len(htf) - 1):
        prev_candle = htf.iloc[i - 1]
        ob_candle = htf.iloc[i]
        next_candle = htf.iloc[i + 1]

        body_pips = _body_size_pips(ob_candle)
        if body_pips < MIN_OB_BODY_PIPS:
            continue

        bullish_ob = (
            float(ob_candle["Close"]) < float(ob_candle["Open"])
            and float(next_candle["Close"]) > float(next_candle["Open"])
        )

        bearish_ob = (
            float(ob_candle["Close"]) > float(ob_candle["Open"])
            and float(next_candle["Close"]) < float(next_candle["Open"])
        )

        bullish_gap_pips = (float(next_candle["Low"]) - float(prev_candle["High"])) / PIP_SIZE
        bearish_gap_pips = (float(prev_candle["Low"]) - float(next_candle["High"])) / PIP_SIZE

        if bullish_ob and bullish_gap_pips >= MIN_GAP_PIPS:
            obs.append({
                "type": "bullish",
                "created_time": pd.Timestamp(ob_candle["time"]),
                "low": float(ob_candle["Low"]),
                "high": float(ob_candle["High"]),
                "gap_pips": float(bullish_gap_pips),
                "valid_until": pd.Timestamp(ob_candle["time"]) + pd.Timedelta(hours=OB_EXTENSION_HOURS),
                "first_retest_time": None,
                "first_retest_rejected": False,
                "entry_taken": False,
            })

        if bearish_ob and bearish_gap_pips >= MIN_GAP_PIPS:
            obs.append({
                "type": "bearish",
                "created_time": pd.Timestamp(ob_candle["time"]),
                "low": float(ob_candle["Low"]),
                "high": float(ob_candle["High"]),
                "gap_pips": float(bearish_gap_pips),
                "valid_until": pd.Timestamp(ob_candle["time"]) + pd.Timedelta(hours=OB_EXTENSION_HOURS),
                "first_retest_time": None,
                "first_retest_rejected": False,
                "entry_taken": False,
            })

    return obs


def _candle_touches_ob(row, ob):
    return float(row["High"]) >= ob["low"] and float(row["Low"]) <= ob["high"]


def _is_rejection_candle(row, ob):
    buffer_price = REJECTION_CLOSE_BUFFER_PIPS * PIP_SIZE

    if not _candle_touches_ob(row, ob):
        return False

    if ob["type"] == "bullish":
        return float(row["Close"]) > (ob["high"] + buffer_price)

    if ob["type"] == "bearish":
        return float(row["Close"]) < (ob["low"] - buffer_price)

    return False


def _tokyo_window_for_trade(current_time):
    day_start = pd.Timestamp(current_time).normalize()
    start = day_start + pd.Timedelta(hours=TOKYO_START_HOUR)
    end = day_start + pd.Timedelta(hours=TOKYO_END_HOUR)
    return start, end


def _get_tokyo_range(df, current_time):
    start, end = _tokyo_window_for_trade(current_time)
    session = df[(df["time"] >= start) & (df["time"] < end)]

    if session.empty:
        return None

    return {
        "high": float(session["High"].max()),
        "low": float(session["Low"].min()),
        "start": start,
        "end": end,
    }


def _build_trade(row, ob, df):
    tokyo = _get_tokyo_range(df, row["time"])
    if tokyo is None:
        return None

    if ob["type"] == "bullish":
        entry = float(ob["high"])
        stop = float(ob["low"]) - (SL_BUFFER_PIPS * PIP_SIZE)
        tp = float(tokyo["high"])
        trade_type = "long"

        if tp <= entry:
            return None

    else:
        entry = float(ob["low"])
        stop = float(ob["high"]) + (SL_BUFFER_PIPS * PIP_SIZE)
        tp = float(tokyo["low"])
        trade_type = "short"

        if tp >= entry:
            return None

    return {
        "type": trade_type,
        "time": int(pd.Timestamp(row["time"]).timestamp()),
        "entry": float(entry),
        "stop": float(stop),
        "tp": float(tp),
        "exit_price": None,
        "exit_time": None,
        "exit_reason": "data_end",
        "ob_kind": ob["type"],
        "ob_low": float(ob["low"]),
        "ob_high": float(ob["high"]),
        "ob_created_time": int(pd.Timestamp(ob["created_time"]).timestamp()),
        "tokyo_start": int(pd.Timestamp(tokyo["start"]).timestamp()),
        "tokyo_end": int(pd.Timestamp(tokyo["end"]).timestamp()),
        "tokyo_high": float(tokyo["high"]),
        "tokyo_low": float(tokyo["low"]),
    }


def _resolve_trade(trade, df, start_index):
    for i in range(start_index, len(df)):
        row = df.iloc[i]
        high_ = float(row["High"])
        low_ = float(row["Low"])
        time_ = int(pd.Timestamp(row["time"]).timestamp())

        if trade["type"] == "long":
            if low_ <= trade["stop"]:
                trade["exit_price"] = float(trade["stop"])
                trade["exit_time"] = time_
                trade["exit_reason"] = "SL"
                return trade, i

            if high_ >= trade["tp"]:
                trade["exit_price"] = float(trade["tp"])
                trade["exit_time"] = time_
                trade["exit_reason"] = "TP"
                return trade, i

        else:
            if high_ >= trade["stop"]:
                trade["exit_price"] = float(trade["stop"])
                trade["exit_time"] = time_
                trade["exit_reason"] = "SL"
                return trade, i

            if low_ <= trade["tp"]:
                trade["exit_price"] = float(trade["tp"])
                trade["exit_time"] = time_
                trade["exit_reason"] = "TP"
                return trade, i

    last_row = df.iloc[-1]
    trade["exit_price"] = float(last_row["Close"])
    trade["exit_time"] = int(pd.Timestamp(last_row["time"]).timestamp())
    trade["exit_reason"] = "data_end"
    return trade, len(df) - 1


def run_strategy(df):
    trades = []

    if df is None or df.empty:
        return trades

    df = _prepare_dataframe(df)
    htf = _resample_htf(df)
    order_blocks = _detect_order_blocks(htf)

    last_exit_index = -1

    for ob in order_blocks:
        first_retest_min_time = ob["created_time"] + pd.Timedelta(hours=FIRST_RETEST_DELAY_HOURS)

        for i in range(len(df)):
            row = df.iloc[i]
            row_time = pd.Timestamp(row["time"])

            if row_time <= first_retest_min_time:
                continue

            if row_time > ob["valid_until"]:
                break

            if ob["entry_taken"]:
                break

            if ob["first_retest_time"] is None:
                if _is_rejection_candle(row, ob):
                    ob["first_retest_time"] = row_time
                    ob["first_retest_rejected"] = True
                continue

            if not ob["first_retest_rejected"]:
                continue

            second_retest_min_time = ob["first_retest_time"] + pd.Timedelta(hours=ENTRY_RETEST_DELAY_HOURS)

            if row_time <= second_retest_min_time:
                continue

            if not _candle_touches_ob(row, ob):
                continue

            if ALLOW_ONLY_ONE_TRADE_AT_A_TIME and i <= last_exit_index:
                continue

            trade = _build_trade(row, ob, df)
            if trade is None:
                break

            trade, exit_idx = _resolve_trade(trade, df, i)
            trades.append(trade)

            ob["entry_taken"] = True
            last_exit_index = exit_idx
            break

    return trades 