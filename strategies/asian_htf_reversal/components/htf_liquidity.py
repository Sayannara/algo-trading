from ..config import STRATEGY_CONFIG


def _is_in_trading_window(ts):
    start_hour = STRATEGY_CONFIG["trading_start_hour"]
    end_hour = STRATEGY_CONFIG["trading_end_hour"]
    return start_hour <= ts.hour < end_hour


def _get_previous_tokyo_session(df_slice):
    tokyo_start = STRATEGY_CONFIG["tokyo_start_hour"]
    tokyo_end = STRATEGY_CONFIG["tokyo_end_hour"]

    if df_slice is None or df_slice.empty:
        return None

    current_ts = df_slice.iloc[-1]["time"]
    current_date = current_ts.date()

    previous_days = sorted({ts.date() for ts in df_slice["time"] if ts.date() < current_date}, reverse=True)

    for day in previous_days:
        session = df_slice[
            (df_slice["time"].dt.date == day) &
            (df_slice["time"].dt.hour >= tokyo_start) &
            (df_slice["time"].dt.hour < tokyo_end)
        ].copy()

        if not session.empty:
            return session

    return None


def detect_htf_liquidity_context(df_slice, trend_bias=None):
    if df_slice is None or len(df_slice) < 10:
        return None

    current = df_slice.iloc[-1]
    current_ts = current["time"]

    if not _is_in_trading_window(current_ts):
        return None

    tokyo_session = _get_previous_tokyo_session(df_slice)
    if tokyo_session is None or tokyo_session.empty:
        return None

    tokyo_high = float(tokyo_session["High"].max())
    tokyo_low = float(tokyo_session["Low"].min())

    short_sweep = current["High"] > tokyo_high
    long_sweep = current["Low"] < tokyo_low

    if trend_bias == "short" and short_sweep:
        return {
            "bias": "short",
            "liquidity_level": tokyo_high,
            "sweep_time": int(current_ts.timestamp()),
            "reference_high": tokyo_high,
            "reference_low": tokyo_low,
            "session_type": "tokyo_previous",
        }

    if trend_bias == "long" and long_sweep:
        return {
            "bias": "long",
            "liquidity_level": tokyo_low,
            "sweep_time": int(current_ts.timestamp()),
            "reference_high": tokyo_high,
            "reference_low": tokyo_low,
            "session_type": "tokyo_previous",
        }

    if trend_bias is None:
        if short_sweep:
            return {
                "bias": "short",
                "liquidity_level": tokyo_high,
                "sweep_time": int(current_ts.timestamp()),
                "reference_high": tokyo_high,
                "reference_low": tokyo_low,
                "session_type": "tokyo_previous",
            }

        if long_sweep:
            return {
                "bias": "long",
                "liquidity_level": tokyo_low,
                "sweep_time": int(current_ts.timestamp()),
                "reference_high": tokyo_high,
                "reference_low": tokyo_low,
                "session_type": "tokyo_previous",
            }

    return None