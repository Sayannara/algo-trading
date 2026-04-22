from .config import STRATEGY_CONFIG
from .components.htf_liquidity import detect_htf_liquidity_context
from .components.ltf_reversal import detect_ltf_reversal
from .components.trade_management import build_trade


def get_trend_value_at_index(trend_data, index):
    if trend_data is None:
        return None

    if isinstance(trend_data, list):
        if index < len(trend_data):
            return trend_data[index]
        return None

    return None


def get_trend_bias(trend_value):
    if trend_value is None:
        return None

    buy_threshold = STRATEGY_CONFIG["trend_buy_threshold"]
    sell_threshold = STRATEGY_CONFIG["trend_sell_threshold"]
    allow_neutral = STRATEGY_CONFIG["allow_neutral_trades"]

    if trend_value > buy_threshold:
        return "long"

    if trend_value < sell_threshold:
        return "short"

    if allow_neutral:
        return "neutral"

    return None


def run_strategy(df, trend_data=None):
    trades = []

    if df is None or df.empty:
        return trades

    min_bars = STRATEGY_CONFIG["min_bars"]
    traded_session_dates = set()

    for i in range(min_bars, len(df)):
        df_slice = df.iloc[:i + 1].copy()
        current = df_slice.iloc[-1]
        current_date = current["time"].date()

        if current_date in traded_session_dates:
            continue

        trend_value = get_trend_value_at_index(trend_data, i)
        trend_bias = get_trend_bias(trend_value)

        if trend_bias is None:
            continue

        htf_context = detect_htf_liquidity_context(df_slice, trend_bias=trend_bias)
        if not htf_context:
            continue

        reversal_signal = detect_ltf_reversal(df_slice, htf_context)
        if not reversal_signal:
            continue

        trade = build_trade(df_slice, htf_context, reversal_signal)
        if trade:
            trades.append(trade)
            traded_session_dates.add(current_date)

    return trades