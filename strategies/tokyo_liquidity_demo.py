import pandas as pd
from indicators.sessions_market import calculer_sessions

LOT_SIZE = 5.0
FORCED_CLOSE_HOUR = 23

def run(df):
    return generer_strategie_tokyo_liquidity(df)

def generer_strategie_tokyo_liquidity(df):
    trades = []

    if df is None or df.empty:
        print("⚠️ DataFrame vide pour la stratégie Tokyo.")
        return trades

    df = df.copy().sort_values("time").reset_index(drop=True)
    sessions = calculer_sessions(df)
    tokyo_sessions = [s for s in sessions if s.get("title") == "Tokyo"]

    print(f"🟣 Tokyo sessions détectées : {len(tokyo_sessions)}")

    if not tokyo_sessions:
        return trades

    for tokyo in tokyo_sessions:
        tokyo_start = pd.to_datetime(tokyo["start"], unit="s", utc=True)
        tokyo_end   = pd.to_datetime(tokyo["end"],   unit="s", utc=True)
        tokyo_high  = float(tokyo["max_p"])
        tokyo_low   = float(tokyo["min_p"])
        same_day    = tokyo_start.date()

        post_tokyo = df[
            (df["time"] > tokyo_end) &
            (df["time"].dt.date == same_day)
        ].copy()

        if post_tokyo.empty:
            continue

        trade = None

        for _, row in post_tokyo.iterrows():
            t     = row["time"]
            high  = float(row["High"])
            low   = float(row["Low"])

            if t.hour >= FORCED_CLOSE_HOUR:
                break

            if high > tokyo_high:
                trade = {
                    "strategy":     "Tokyo Liquidity Demo",
                    "session_date": str(same_day),
                    "direction":    "short",
                    "lots":         LOT_SIZE,
                    "sweep_type":   "tokyo_high_taken",
                    "sweep_time":   int(t.timestamp()),
                    "entry_time":   int(t.timestamp()),
                    "entry":        tokyo_high,
                    "sl":           tokyo_high * 1.01,
                    "tp":           tokyo_low,
                    "tokyo_high":   tokyo_high,
                    "tokyo_low":    tokyo_low,
                    "exit_time":    None,
                    "exit_price":   None,
                    "exit_reason":  None,
                }
                break

            if low < tokyo_low:
                trade = {
                    "strategy":     "Tokyo Liquidity Demo",
                    "session_date": str(same_day),
                    "direction":    "long",
                    "lots":         LOT_SIZE,
                    "sweep_type":   "tokyo_low_taken",
                    "sweep_time":   int(t.timestamp()),
                    "entry_time":   int(t.timestamp()),
                    "entry":        tokyo_low,
                    "sl":           tokyo_low * 0.99,
                    "tp":           tokyo_high,
                    "tokyo_high":   tokyo_high,
                    "tokyo_low":    tokyo_low,
                    "exit_time":    None,
                    "exit_price":   None,
                    "exit_reason":  None,
                }
                break

        if trade is None:
            continue

        post_entry = post_tokyo[
            post_tokyo["time"] >= pd.to_datetime(trade["entry_time"], unit="s", utc=True)
        ]

        for _, row in post_entry.iterrows():
            t     = row["time"]
            high  = float(row["High"])
            low   = float(row["Low"])
            close = float(row["Close"])

            if trade["direction"] == "short":
                if high >= trade["sl"] and low <= trade["tp"]:
                    trade.update({"exit_time": int(t.timestamp()), "exit_price": trade["sl"], "exit_reason": "SL"})
                    break
                if high >= trade["sl"]:
                    trade.update({"exit_time": int(t.timestamp()), "exit_price": trade["sl"], "exit_reason": "SL"})
                    break
                if low <= trade["tp"]:
                    trade.update({"exit_time": int(t.timestamp()), "exit_price": trade["tp"], "exit_reason": "TP"})
                    break

            elif trade["direction"] == "long":
                if low <= trade["sl"] and high >= trade["tp"]:
                    trade.update({"exit_time": int(t.timestamp()), "exit_price": trade["sl"], "exit_reason": "SL"})
                    break
                if low <= trade["sl"]:
                    trade.update({"exit_time": int(t.timestamp()), "exit_price": trade["sl"], "exit_reason": "SL"})
                    break
                if high >= trade["tp"]:
                    trade.update({"exit_time": int(t.timestamp()), "exit_price": trade["tp"], "exit_reason": "TP"})
                    break

            if t.hour >= FORCED_CLOSE_HOUR:
                trade.update({"exit_time": int(t.timestamp()), "exit_price": close, "exit_reason": "23:00"})
                break

        if trade["exit_time"] is None:
            last_row = post_entry.iloc[-1]
            trade.update({
                "exit_time":   int(last_row["time"].timestamp()),
                "exit_price":  float(last_row["Close"]),
                "exit_reason": "data_end"
            })

        trades.append(trade)

    print(f"📊 Trades Tokyo générés : {len(trades)}")
    return trades