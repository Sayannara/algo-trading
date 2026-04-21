from .components.htf_liquidity import detect_htf_liquidity_context
from .components.ltf_reversal import detect_ltf_reversal
from .components.trade_management import build_trade


def run_strategy(df):
    trades = []

    if df is None or df.empty:
        return trades

    for i in range(50, len(df)):
        df_slice = df.iloc[:i + 1].copy()

        htf_context = detect_htf_liquidity_context(df_slice)
        if not htf_context:
            continue

        reversal_signal = detect_ltf_reversal(df_slice, htf_context)
        if not reversal_signal:
            continue

        trade = build_trade(df_slice, htf_context, reversal_signal)
        if trade:
            trades.append(trade)

    return trades