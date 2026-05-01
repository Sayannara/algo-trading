from datetime import datetime, timezone, timedelta
import pandas as pd
import MetaTrader5 as mt5

TIMEFRAME_MAP = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}

# Taille de chunk en jours selon le timeframe
CHUNK_DAYS = {
    "M1":  30,
    "M5":  90,
    "M15": 180,
    "M30": 365,
    "H1":  365,
    "H4":  365 * 3,
    "D1":  365 * 10,
}


def charger_donnees(symbol, date_from, date_to, timeframe,
                    path=None, login=None, password=None, server=None):

    kwargs = {}
    if path:            kwargs["path"]     = path
    if login is not None:    kwargs["login"]    = int(login)
    if password is not None: kwargs["password"] = str(password)
    if server is not None:   kwargs["server"]   = str(server)

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
        end_utc   = date_to.astimezone(timezone.utc)

        chunk_size = timedelta(days=CHUNK_DAYS.get(timeframe, 90))

        all_chunks = []
        chunk_start = start_utc

        while chunk_start < end_utc:
            chunk_end = min(chunk_start + chunk_size, end_utc)

            print(f"   ↳ Chargement {symbol} {timeframe} : {chunk_start.date()} → {chunk_end.date()}")

            rates = mt5.copy_rates_range(symbol, tf, chunk_start, chunk_end)

            if rates is not None and len(rates) > 0:
                all_chunks.append(pd.DataFrame(rates))
            elif mt5.last_error()[0] not in (0, 1):
                print(f"   ⚠️  Erreur chunk {chunk_start.date()} : {mt5.last_error()}")

            chunk_start = chunk_end

        if not all_chunks:
            raise RuntimeError(f"Aucune donnée récupérée pour {symbol} {timeframe}")

        df = pd.concat(all_chunks, ignore_index=True)
        df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)

        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.rename(columns={
            "open":        "Open",
            "high":        "High",
            "low":         "Low",
            "close":       "Close",
            "tick_volume": "Volume",
        })

        print(f"   ✅ Total : {len(df)} bougies chargées")
        return df[["time", "Open", "High", "Low", "Close", "Volume"]]

    finally:
        mt5.shutdown()