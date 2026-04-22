def run_strategy(df):
    trades = []

    if df is None or df.empty:
        return trades

    lookback = 20
    body_multiplier = 4.0
    range_multiplier = 2.5
    hold_bars = 10
    rr = 1.5
    min_body_floor = 0.0008
    min_range_floor = 0.0012
    cooldown_bars = 15

    min_required = lookback + hold_bars + 2
    if len(df) < min_required:
        return trades

    i = lookback

    while i < len(df) - hold_bars:
        current = df.iloc[i]

        o = float(current["Open"])
        h = float(current["High"])
        l = float(current["Low"])
        c = float(current["Close"])
        t = int(current["time"].timestamp())

        body = abs(c - o)
        candle_range = h - l

        prev_bodies = []
        prev_ranges = []

        for j in range(i - lookback, i):
            row = df.iloc[j]
            prev_o = float(row["Open"])
            prev_h = float(row["High"])
            prev_l = float(row["Low"])
            prev_c = float(row["Close"])

            prev_bodies.append(abs(prev_c - prev_o))
            prev_ranges.append(prev_h - prev_l)

        avg_body = sum(prev_bodies) / len(prev_bodies) if prev_bodies else 0.0
        avg_range = sum(prev_ranges) / len(prev_ranges) if prev_ranges else 0.0

        if avg_body <= 0 or avg_range <= 0:
            i += 1
            continue

        body_threshold = max(avg_body * body_multiplier, min_body_floor)
        range_threshold = max(avg_range * range_multiplier, min_range_floor)

        is_big_green = c > o and body >= body_threshold and candle_range >= range_threshold
        is_big_red = c < o and body >= body_threshold and candle_range >= range_threshold

        if not is_big_green and not is_big_red:
            i += 1
            continue

        direction = "long" if is_big_green else "short"

        if direction == "long":
            entry = c
            stop = l
            risk = entry - stop
            if risk <= 0:
                i += 1
                continue
            tp = entry + (risk * rr)

        else:
            entry = c
            stop = h
            risk = stop - entry
            if risk <= 0:
                i += 1
                continue
            tp = entry - (risk * rr)

        exit_price = None
        exit_time = None
        exit_reason = None
        exit_index = None

        for k in range(i + 1, min(i + hold_bars + 1, len(df))):
            row = df.iloc[k]
            hk = float(row["High"])
            lk = float(row["Low"])
            ck = float(row["Close"])
            tk = int(row["time"].timestamp())

            if direction == "long":
                sl_hit = lk <= stop
                tp_hit = hk >= tp

                if sl_hit and tp_hit:
                    exit_price = stop
                    exit_time = tk
                    exit_reason = "SL"
                    exit_index = k
                    break

                if sl_hit:
                    exit_price = stop
                    exit_time = tk
                    exit_reason = "SL"
                    exit_index = k
                    break

                if tp_hit:
                    exit_price = tp
                    exit_time = tk
                    exit_reason = "TP"
                    exit_index = k
                    break

            else:
                sl_hit = hk >= stop
                tp_hit = lk <= tp

                if sl_hit and tp_hit:
                    exit_price = stop
                    exit_time = tk
                    exit_reason = "SL"
                    exit_index = k
                    break

                if sl_hit:
                    exit_price = stop
                    exit_time = tk
                    exit_reason = "SL"
                    exit_index = k
                    break

                if tp_hit:
                    exit_price = tp
                    exit_time = tk
                    exit_reason = "TP"
                    exit_index = k
                    break

            if k == i + hold_bars:
                exit_price = ck
                exit_time = tk
                exit_reason = "10_bars"
                exit_index = k
                break

        if exit_price is None:
            last_idx = min(i + hold_bars, len(df) - 1)
            last_row = df.iloc[last_idx]
            exit_price = float(last_row["Close"])
            exit_time = int(last_row["time"].timestamp())
            exit_reason = "data_end"
            exit_index = last_idx

        trades.append({
            "type": direction,
            "entry": float(entry),
            "time": t,
            "stop": float(stop),
            "tp": float(tp),
            "exit_price": float(exit_price),
            "exit_time": int(exit_time),
            "exit_reason": exit_reason,
            "signal_open": float(o),
            "signal_high": float(h),
            "signal_low": float(l),
            "signal_close": float(c),
            "signal_body": float(body),
            "signal_range": float(candle_range),
            "avg_body": float(avg_body),
            "avg_range": float(avg_range),
            "body_threshold": float(body_threshold),
            "range_threshold": float(range_threshold),
        })

        i = exit_index + cooldown_bars if exit_index is not None else i + 1

    return trades