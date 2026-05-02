from datetime import datetime, timezone
import pandas as pd
import MetaTrader5 as mt5

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

def charger_donnees(symbol, date_from, date_to, timeframe, path=None, login=None, password=None, server=None):
    kwargs = {}

    if path:
        kwargs["path"] = path
    if login is not None:
        kwargs["login"] = int(login)
    if password is not None:
        kwargs["password"] = str(password)
    if server is not None:
        kwargs["server"] = str(server)

    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    try:
        tf = TIMEFRAME_MAP[timeframe]

        if isinstance(date_from, str):
            date_from = datetime.fromisoformat(date_from)
        if isinstance(date_to, str):
            date_to = datetime.fromisoformat(date_to)

        if date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)
        if date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)

        start_utc = date_from.astimezone(timezone.utc)
        end_utc = date_to.astimezone(timezone.utc)

        rates = mt5.copy_rates_range(symbol, tf, start_utc, end_utc)
        if rates is None:
            raise RuntimeError(f"copy_rates_range() failed: {mt5.last_error()}")

        df = pd.DataFrame(rates)
        if df.empty:
            return df

        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)

        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "tick_volume": "Volume"
        })

        return df[["time", "Open", "High", "Low", "Close", "Volume"]]

    finally:
        mt5.shutdown()