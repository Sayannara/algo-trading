from ..config import STRATEGY_CONFIG


def detect_htf_liquidity_context(df_slice, trend_bias=None):
    lookback = STRATEGY_CONFIG["htf_lookback"]

    if df_slice is None or len(df_slice) < lookback + 2:
        return None

    current = df_slice.iloc[-1]
    recent = df_slice.iloc[-lookback-1:-1]

    recent_high = recent["High"].max()
    recent_low = recent["Low"].min()

    short_sweep = current["High"] > recent_high and current["Close"] < recent_high
    long_sweep = current["Low"] < recent_low and current["Close"] > recent_low

    if trend_bias == "short" and short_sweep:
        return {
            "bias": "short",
            "liquidity_level": float(recent_high),
            "sweep_time": int(current["time"].timestamp()),
            "reference_high": float(recent_high),
            "reference_low": float(recent_low),
        }

    if trend_bias == "long" and long_sweep:
        return {
            "bias": "long",
            "liquidity_level": float(recent_low),
            "sweep_time": int(current["time"].timestamp()),
            "reference_high": float(recent_high),
            "reference_low": float(recent_low),
        }

    if trend_bias is None:
        if short_sweep:
            return {
                "bias": "short",
                "liquidity_level": float(recent_high),
                "sweep_time": int(current["time"].timestamp()),
                "reference_high": float(recent_high),
                "reference_low": float(recent_low),
            }

        if long_sweep:
            return {
                "bias": "long",
                "liquidity_level": float(recent_low),
                "sweep_time": int(current["time"].timestamp()),
                "reference_high": float(recent_high),
                "reference_low": float(recent_low),
            }

    return None