from ..config import STRATEGY_CONFIG


def _parse_force_exit_hour():
    force_exit_time = STRATEGY_CONFIG["force_exit_time"]
    hour, minute = force_exit_time.split(":")
    return int(hour), int(minute)


def _simulate_exit(df, entry_index, direction, entry, stop_loss, take_profit):
    force_hour, force_minute = _parse_force_exit_hour()
    sl_priority = STRATEGY_CONFIG["sl_priority_if_both_hit"]

    for j in range(entry_index + 1, len(df)):
        row = df.iloc[j]
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        ts = row["time"]

        if direction == "long":
            hit_sl = low <= stop_loss
            hit_tp = high >= take_profit

            if hit_sl and hit_tp:
                if sl_priority:
                    return stop_loss, int(ts.timestamp()), "SL"
                return take_profit, int(ts.timestamp()), "TP"

            if hit_sl:
                return stop_loss, int(ts.timestamp()), "SL"

            if hit_tp:
                return take_profit, int(ts.timestamp()), "TP"

        elif direction == "short":
            hit_sl = high >= stop_loss
            hit_tp = low <= take_profit

            if hit_sl and hit_tp:
                if sl_priority:
                    return stop_loss, int(ts.timestamp()), "SL"
                return take_profit, int(ts.timestamp()), "TP"

            if hit_sl:
                return stop_loss, int(ts.timestamp()), "SL"

            if hit_tp:
                return take_profit, int(ts.timestamp()), "TP"

        if ts.hour > force_hour or (ts.hour == force_hour and ts.minute >= force_minute):
            return close, int(ts.timestamp()), STRATEGY_CONFIG["force_exit_time"]

    last_row = df.iloc[-1]
    return float(last_row["Close"]), int(last_row["time"].timestamp()), "data_end"


def build_trade(df, htf_context, reversal_signal):
    if not htf_context or not reversal_signal or df is None or df.empty:
        return None

    direction = reversal_signal["direction"]
    entry = float(reversal_signal["entry"])
    liquidity_level = float(htf_context["liquidity_level"])
    tokyo_high = float(htf_context["reference_high"])
    tokyo_low = float(htf_context["reference_low"])
    buffer = STRATEGY_CONFIG["buffer"]

    if direction == "short":
        stop_loss = liquidity_level + buffer
        take_profit = tokyo_low
        risk = stop_loss - entry

        if risk <= 0:
            return None

        if take_profit >= entry:
            return None

    elif direction == "long":
        stop_loss = liquidity_level - buffer
        take_profit = tokyo_high
        risk = entry - stop_loss

        if risk <= 0:
            return None

        if take_profit <= entry:
            return None

    else:
        return None

    entry_time = reversal_signal["signal_time"]
    entry_ts = df["time"].astype("int64") // 10**9
    matching_idx = df.index[entry_ts == entry_time]

    if len(matching_idx) == 0:
        entry_index = len(df) - 1
    else:
        entry_index = df.index.get_loc(matching_idx[-1])

    exit_price, exit_time, exit_reason = _simulate_exit(
        df=df,
        entry_index=entry_index,
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )

    rr_realized = 0.0
    if direction == "long":
        rr_realized = (exit_price - entry) / risk
    elif direction == "short":
        rr_realized = (entry - exit_price) / risk

    return {
        "type": direction,
        "entry": float(entry),
        "stop": float(stop_loss),
        "tp": float(take_profit),
        "rr": float(rr_realized),
        "time": int(entry_time),
        "sweep_time": int(htf_context["sweep_time"]),
        "exit_price": float(exit_price),
        "exit_time": int(exit_time),
        "exit_reason": exit_reason,
        "tokyo_high": tokyo_high,
        "tokyo_low": tokyo_low,
    }