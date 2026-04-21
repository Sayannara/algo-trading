def detect_htf_liquidity_context(df, lookback=20):
    if len(df) < lookback + 2:
        return None

    current = df.iloc[-1]
    recent = df.iloc[-lookback-1:-1]

    recent_high = recent["High"].max()
    recent_low = recent["Low"].min()

    if current["High"] > recent_high and current["Close"] < recent_high:
        return {
            "bias": "short",
            "liquidity_level": float(recent_high),
            "sweep_time": int(current["time"].timestamp())
        }

    if current["Low"] < recent_low and current["Close"] > recent_low:
        return {
            "bias": "long",
            "liquidity_level": float(recent_low),
            "sweep_time": int(current["time"].timestamp())
        }

    return None