def run_strategy(df):
    trades = []

    if df is None or df.empty:
        return trades

    lookback = 20
    body_multiplier = 2.0
    hold_bars = 10

    if len(df) < lookback + hold_bars + 1:
        return trades

    for i in range(lookback, len(df) - hold_bars):
        current = df.iloc[i]

        candle_body = abs(float(current["Close"]) - float(current["Open"]))

        previous_bodies = []
        for j in range(i - lookback, i):
            row = df.iloc[j]
            body = abs(float(row["Close"]) - float(row["Open"]))
            previous_bodies.append(body)

        avg_body = sum(previous_bodies) / len(previous_bodies) if previous_bodies else 0.0

        if avg_body <= 0:
            continue

        is_big_green = (
            float(current["Close"]) > float(current["Open"]) and
            candle_body >= avg_body * body_multiplier
        )

        is_big_red = (
            float(current["Close"]) < float(current["Open"]) and
            candle_body >= avg_body * body_multiplier
        )

        if not is_big_green and not is_big_red:
            continue

        direction = "long" if is_big_green else "short"
        entry_price = float(current["Close"])
        entry_time = int(current["time"].timestamp())

        exit_row = df.iloc[i + hold_bars]
        exit_price = float(exit_row["Close"])
        exit_time = int(exit_row["time"].timestamp())

        trades.append({
            "type": direction,
            "entry": entry_price,
            "time": entry_time,
            "exit_price": exit_price,
            "exit_time": exit_time,
            "exit_reason": f"{hold_bars}_bars",
            "signal_open": float(current["Open"]),
            "signal_high": float(current["High"]),
            "signal_low": float(current["Low"]),
            "signal_close": float(current["Close"]),
            "signal_body": candle_body,
            "avg_body": avg_body,
        })

    return trades