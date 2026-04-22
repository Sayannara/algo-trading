from ..config import STRATEGY_CONFIG


def _is_force_exit_time(ts):
    force_exit_time = STRATEGY_CONFIG["force_exit_time"]
    hh, mm = force_exit_time.split(":")
    return ts.strftime("%H:%M") == f"{hh}:{mm}"


def build_trade(df, entry_index, htf_context, reversal_signal):
    rr = STRATEGY_CONFIG["rr"]
    buffer = STRATEGY_CONFIG["buffer"]
    sl_priority_if_both_hit = STRATEGY_CONFIG["sl_priority_if_both_hit"]

    if df is None or entry_index is None:
        return None

    if not htf_context or not reversal_signal:
        return None

    direction = reversal_signal["direction"]
    entry = reversal_signal["entry"]
    liquidity_level = htf_context["liquidity_level"]

    if direction == "short":
        stop_loss = liquidity_level + buffer
        risk = stop_loss - entry
        if risk <= 0:
            return None
        take_profit = entry - (risk * rr)

    elif direction == "long":
        stop_loss = liquidity_level - buffer
        risk = entry - stop_loss
        if risk <= 0:
            return None
        take_profit = entry + (risk * rr)

    else:
        return None

    trade = {
        "type": direction,
        "entry": float(entry),
        "stop": float(stop_loss),
        "tp": float(take_profit),
        "rr": float(rr),
        "time": reversal_signal["signal_time"],
        "sweep_time": htf_context["sweep_time"],
        "exit_price": None,
        "exit_time": None,
        "exit_reason": None,
        "exit_index": None,
    }

    for j in range(entry_index + 1, len(df)):
        row = df.iloc[j]
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        ts = row["time"]

        if direction == "long":
            sl_hit = low <= stop_loss
            tp_hit = high >= take_profit

            if sl_hit and tp_hit:
                if sl_priority_if_both_hit:
                    trade["exit_price"] = float(stop_loss)
                    trade["exit_reason"] = "SL"
                else:
                    trade["exit_price"] = float(take_profit)
                    trade["exit_reason"] = "TP"
                trade["exit_time"] = int(ts.timestamp())
                trade["exit_index"] = j
                return trade

            if sl_hit:
                trade["exit_price"] = float(stop_loss)
                trade["exit_time"] = int(ts.timestamp())
                trade["exit_reason"] = "SL"
                trade["exit_index"] = j
                return trade

            if tp_hit:
                trade["exit_price"] = float(take_profit)
                trade["exit_time"] = int(ts.timestamp())
                trade["exit_reason"] = "TP"
                trade["exit_index"] = j
                return trade

        elif direction == "short":
            sl_hit = high >= stop_loss
            tp_hit = low <= take_profit

            if sl_hit and tp_hit:
                if sl_priority_if_both_hit:
                    trade["exit_price"] = float(stop_loss)
                    trade["exit_reason"] = "SL"
                else:
                    trade["exit_price"] = float(take_profit)
                    trade["exit_reason"] = "TP"
                trade["exit_time"] = int(ts.timestamp())
                trade["exit_index"] = j
                return trade

            if sl_hit:
                trade["exit_price"] = float(stop_loss)
                trade["exit_time"] = int(ts.timestamp())
                trade["exit_reason"] = "SL"
                trade["exit_index"] = j
                return trade

            if tp_hit:
                trade["exit_price"] = float(take_profit)
                trade["exit_time"] = int(ts.timestamp())
                trade["exit_reason"] = "TP"
                trade["exit_index"] = j
                return trade

        if _is_force_exit_time(ts):
            trade["exit_price"] = float(close)
            trade["exit_time"] = int(ts.timestamp())
            trade["exit_reason"] = STRATEGY_CONFIG["force_exit_time"]
            trade["exit_index"] = j
            return trade

    last_row = df.iloc[-1]
    trade["exit_price"] = float(last_row["Close"])
    trade["exit_time"] = int(last_row["time"].timestamp())
    trade["exit_reason"] = "data_end"
    trade["exit_index"] = len(df) - 1
    return trade