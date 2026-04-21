def build_trade(df, htf_context, reversal_signal, rr=2.0, buffer=0.00015):
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

    return {
        "type": direction,
        "entry": float(entry),
        "stop": float(stop_loss),
        "tp": float(take_profit),
        "rr": float(rr),
        "time": reversal_signal["signal_time"]
    }