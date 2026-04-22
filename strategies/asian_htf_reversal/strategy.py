from .config import STRATEGY_CONFIG
from .components.htf_liquidity import detect_htf_liquidity_context
from .components.ltf_reversal import detect_ltf_reversal
from .components.trade_management import build_trade


def get_trend_value_at_index(trend_data, index):
    if trend_data is None:
        return None

    if isinstance(trend_data, list):
        if index < len(trend_data):
            item = trend_data[index]
            if isinstance(item, dict):
                if "value" in item:
                    return item["value"]
                if "trend" in item:
                    return item["trend"]
                if "score" in item:
                    return item["score"]
        return None

    if isinstance(trend_data, dict):
        for key in ("value", "trend", "score"):
            if key in trend_data:
                return trend_data[key]

    return None


def get_trend_bias(trend_value):
    buy_threshold = STRATEGY_CONFIG["trend_buy_threshold"]
    sell_threshold = STRATEGY_CONFIG["trend_sell_threshold"]

    if trend_value is None:
        return None

    if trend_value > buy_threshold:
        return "long"

    if trend_value < sell_threshold:
        return "short"

    return None


def run_strategy(df, trend_data=None):
    trades = []

    if df is None or df.empty:
        return trades

    min_bars = STRATEGY_CONFIG["min_bars"]
    i = min_bars

    while i < len(df):
        df_slice = df.iloc[:i + 1].copy()

        current_trend_value = get_trend_value_at_index(trend_data, i)
        trend_bias = get_trend_bias(current_trend_value)

        if trend_bias is None and not STRATEGY_CONFIG["allow_neutral_trades"]:
            i += 1
            continue

        htf_context = detect_htf_liquidity_context(
            df_slice=df_slice,
            trend_bias=trend_bias
        )
        if not htf_context:
            i += 1
            continue

        reversal_signal = detect_ltf_reversal(
            df_slice=df_slice,
            htf_context=htf_context
        )
        if not reversal_signal:
            i += 1
            continue

        if trend_bias is not None and reversal_signal["direction"] != trend_bias:
            i += 1
            continue

        trade = build_trade(
            df=df,
            entry_index=i,
            htf_context=htf_context,
            reversal_signal=reversal_signal
        )

        if trade:
            trades.append(trade)

            exit_index = trade.get("exit_index")
            if isinstance(exit_index, int) and exit_index > i:
                i = exit_index + 1
                continue

        i += 1

    return trades