def detect_ltf_reversal(df, htf_context, impulse_threshold=0.0003):
    if len(df) < 3 or not htf_context:
        return None

    current = df.iloc[-1]
    previous = df.iloc[-2]
    bias = htf_context["bias"]

    candle_range = current["High"] - current["Low"]
    body = abs(current["Close"] - current["Open"])

    if candle_range <= 0:
        return None

    if bias == "short":
        bearish_reversal = (
            current["Close"] < current["Open"]
            and current["Close"] < previous["Low"]
            and body >= impulse_threshold
        )
        if bearish_reversal:
            return {
                "direction": "short",
                "entry": float(current["Close"]),
                "signal_time": int(current["time"].timestamp())
            }

    if bias == "long":
        bullish_reversal = (
            current["Close"] > current["Open"]
            and current["Close"] > previous["High"]
            and body >= impulse_threshold
        )
        if bullish_reversal:
            return {
                "direction": "long",
                "entry": float(current["Close"]),
                "signal_time": int(current["time"].timestamp())
            }

    return None