import os
import json
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd

import config


def get_mt5_data():
    if not mt5.initialize():
        print(f"Erreur initialisation MT5: {mt5.last_error()}")
        return None

    rates = mt5.copy_rates_range(
        config.SYMBOL,
        config.TIMEFRAME,
        config.DATE_START,
        config.DATE_END
    )
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("Aucune donnée récupérée depuis MT5.")
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "tick_volume": "Volume",
        },
        inplace=True
    )
    df = df.sort_values("time").reset_index(drop=True)

    return df


def parse_news_windows(news_input: str):
    windows = []
    if not news_input:
        return windows

    chunks = [x.strip() for x in news_input.split("/") if x.strip()]
    for chunk in chunks:
        if "-" not in chunk:
            continue
        start_str, end_str = chunk.split("-", 1)
        try:
            start_h, start_m = map(int, start_str.split(":"))
            end_h, end_m = map(int, end_str.split(":"))
            windows.append(((start_h, start_m), (end_h, end_m)))
        except Exception:
            continue
    return windows


def is_news_time(ts: pd.Timestamp, news_windows):
    if not news_windows:
        return False

    hhmm = ts.hour * 60 + ts.minute
    for (sh, sm), (eh, em) in news_windows:
        start_val = sh * 60 + sm
        end_val = eh * 60 + em
        if start_val <= hhmm <= end_val:
            return True
    return False


def compute_atr(df, period=14):
    prev_close = df["Close"].shift(1)
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - prev_close).abs()
    tr3 = (df["Low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def get_min_tick(symbol: str):
    info = mt5.symbol_info(symbol)
    if info is not None and hasattr(info, "point") and info.point:
        return float(info.point)
    return getattr(config, "FALLBACK_MIN_TICK", 0.00001)


def compute_display_value(gap_sum_price, close_price, atr_value, measure_type, min_tick):
    if measure_type == "Ticks":
        return gap_sum_price / min_tick if min_tick else 0.0
    if measure_type == "Pourcentage (%)":
        return (gap_sum_price / close_price) * 100 if close_price else 0.0
    if measure_type == "ATR":
        return gap_sum_price / atr_value if atr_value and atr_value > 0 else 0.0
    return 0.0


def format_display_value(value, measure_type):
    if measure_type == "Ticks":
        return f"{round(value)} ticks"
    if measure_type == "Pourcentage (%)":
        return f"{value:.2f} %"
    if measure_type == "ATR":
        return f"{value:.2f} ATR"
    return f"{value:.2f}"


def detect_fvg_groups(df):
    if df is None or df.empty or len(df) < 3:
        return [], {"count": 0, "avg": 0.0, "median": 0.0, "unit": ""}

    measure_type = getattr(config, "TYPE_MESURE", "Ticks")
    min_val_forex = float(getattr(config, "MIN_VALEUR_FOREX", 150.0))
    min_val_others = float(getattr(config, "MIN_VALEUR_AUTRES", 1500.0))
    mode_affichage = getattr(config, "MODE_AFFICHAGE", "Tout afficher (Marquer les News)")
    news_input = getattr(config, "HEURES_NEWS_INPUT", "13:30-14:00/16:00-16:30")
    extend_bars = int(getattr(config, "EXTEND_BOX_BARS", 1))

    news_windows = parse_news_windows(news_input)
    df = df.copy()
    df["ATR14"] = compute_atr(df, 14)
    df["is_news"] = df["time"].apply(lambda x: is_news_time(x, news_windows))

    symbol_info = mt5.symbol_info(config.SYMBOL)
    symbol_type = "forex"
    if symbol_info is not None and hasattr(symbol_info, "path") and symbol_info.path:
        if "Forex" not in str(symbol_info.path):
            symbol_type = "other"

    est_forex = symbol_type == "forex" or "EURUSD" in config.SYMBOL.upper() or "/" in config.SYMBOL
    min_val_active = min_val_forex if est_forex else min_val_others
    min_tick = get_min_tick(config.SYMBOL)

    zones = []
    valid_gap_values = []

    active_bull = None
    active_bear = None

    for i in range(2, len(df)):
        low_now = float(df.loc[i, "Low"])
        high_now = float(df.loc[i, "High"])
        close_now = float(df.loc[i, "Close"])
        atr_now = float(df.loc[i, "ATR14"]) if pd.notna(df.loc[i, "ATR14"]) else None
        bar_time = df.loc[i, "time"]
        bar_is_news = bool(df.loc[i, "is_news"])

        high_2 = float(df.loc[i - 2, "High"])
        low_2 = float(df.loc[i - 2, "Low"])

        bullish_gap = low_now > high_2
        bearish_gap = high_now < low_2

        if bullish_gap:
            gap_price = low_now - high_2

            if active_bull is not None and i == active_bull["last_index"] + 1:
                active_bull["top"] = max(active_bull["top"], low_now)
                active_bull["bottom"] = min(active_bull["bottom"], high_2)
                active_bull["sum_gap_price"] += gap_price
                active_bull["contains_news"] = active_bull["contains_news"] or bar_is_news
                active_bull["last_index"] = i
                active_bull["right_index"] = i + extend_bars
            else:
                if active_bull is not None and active_bull["show"]:
                    zones.append(active_bull)
                    valid_gap_values.append(active_bull["display_value"])

                display_value = compute_display_value(
                    gap_price,
                    close_now,
                    atr_now,
                    measure_type,
                    min_tick
                )

                active_bull = {
                    "title": "",
                    "type": "bullish_fvg",
                    "start_index": i - 1,
                    "right_index": i + extend_bars,
                    "last_index": i,
                    "top": low_now,
                    "bottom": high_2,
                    "sum_gap_price": gap_price,
                    "contains_news": bar_is_news,
                    "display_value": display_value,
                    "show": False,
                    "text": "",
                }

            active_bull["display_value"] = compute_display_value(
                active_bull["sum_gap_price"],
                close_now,
                atr_now,
                measure_type,
                min_tick
            )

            base_text = format_display_value(active_bull["display_value"], measure_type)
            text = base_text + ("\n[NEWS]" if active_bull["contains_news"] else "")

            validation_size = active_bull["display_value"] >= min_val_active

            show = False
            if mode_affichage == "Tout afficher (Marquer les News)":
                show = validation_size
            elif mode_affichage == "Tout SANS les News":
                show = validation_size and not active_bull["contains_news"]
            elif mode_affichage == "N'afficher QUE les News":
                show = validation_size and active_bull["contains_news"]

            active_bull["show"] = show
            active_bull["text"] = text
            active_bull["title"] = "Bullish FVG"
            active_bull["bg"] = "rgba(0, 170, 0, 0.15)" if active_bull["contains_news"] else "rgba(0, 170, 0, 0.08)"
            active_bull["border"] = "rgba(0, 200, 0, 0.70)"
            active_bull["text_color"] = "#ffd54f" if active_bull["contains_news"] else "#ffffff"

        if bearish_gap:
            gap_price = low_2 - high_now

            if active_bear is not None and i == active_bear["last_index"] + 1:
                active_bear["top"] = max(active_bear["top"], low_2)
                active_bear["bottom"] = min(active_bear["bottom"], high_now)
                active_bear["sum_gap_price"] += gap_price
                active_bear["contains_news"] = active_bear["contains_news"] or bar_is_news
                active_bear["last_index"] = i
                active_bear["right_index"] = i + extend_bars
            else:
                if active_bear is not None and active_bear["show"]:
                    zones.append(active_bear)
                    valid_gap_values.append(active_bear["display_value"])

                display_value = compute_display_value(
                    gap_price,
                    close_now,
                    atr_now,
                    measure_type,
                    min_tick
                )

                active_bear = {
                    "title": "",
                    "type": "bearish_fvg",
                    "start_index": i - 1,
                    "right_index": i + extend_bars,
                    "last_index": i,
                    "top": low_2,
                    "bottom": high_now,
                    "sum_gap_price": gap_price,
                    "contains_news": bar_is_news,
                    "display_value": display_value,
                    "show": False,
                    "text": "",
                }

            active_bear["display_value"] = compute_display_value(
                active_bear["sum_gap_price"],
                close_now,
                atr_now,
                measure_type,
                min_tick
            )

            base_text = format_display_value(active_bear["display_value"], measure_type)
            text = base_text + ("\n[NEWS]" if active_bear["contains_news"] else "")

            validation_size = active_bear["display_value"] >= min_val_active

            show = False
            if mode_affichage == "Tout afficher (Marquer les News)":
                show = validation_size
            elif mode_affichage == "Tout SANS les News":
                show = validation_size and not active_bear["contains_news"]
            elif mode_affichage == "N'afficher QUE les News":
                show = validation_size and active_bear["contains_news"]

            active_bear["show"] = show
            active_bear["text"] = text
            active_bear["title"] = "Bearish FVG"
            active_bear["bg"] = "rgba(220, 0, 0, 0.15)" if active_bear["contains_news"] else "rgba(220, 0, 0, 0.08)"
            active_bear["border"] = "rgba(255, 80, 80, 0.75)"
            active_bear["text_color"] = "#ffd54f" if active_bear["contains_news"] else "#ffffff"

    if active_bull is not None and active_bull["show"]:
        zones.append(active_bull)
        valid_gap_values.append(active_bull["display_value"])

    if active_bear is not None and active_bear["show"]:
        zones.append(active_bear)
        valid_gap_values.append(active_bear["display_value"])

    final_zones = []
    for z in zones:
        start_idx = max(0, int(z["start_index"]))
        end_idx = min(len(df) - 1, int(z["right_index"]))

        final_zones.append({
            "title": z["title"],
            "type": z["type"],
            "start": int(df.loc[start_idx, "time"].timestamp()),
            "end": int(df.loc[end_idx, "time"].timestamp()),
            "max_p": float(z["top"]),
            "min_p": float(z["bottom"]),
            "color_bg": z["bg"],
            "color_border": z["border"],
            "text_color": z["text_color"],
            "text": z["text"],
            "contains_news": z["contains_news"],
            "display_value": z["display_value"],
        })

    if valid_gap_values:
        stats = pd.Series(valid_gap_values)
        summary = {
            "count": int(stats.count()),
            "avg": float(stats.mean()),
            "median": float(stats.median()),
            "unit": "ticks" if measure_type == "Ticks" else "%" if measure_type == "Pourcentage (%)" else "ATR",
        }
    else:
        summary = {
            "count": 0,
            "avg": 0.0,
            "median": 0.0,
            "unit": "ticks" if measure_type == "Ticks" else "%" if measure_type == "Pourcentage (%)" else "ATR",
        }

    return final_zones, summary


def build_chart_data(df):
    candles = []
    for _, row in df.iterrows():
        candles.append({
            "time": int(row["time"].timestamp()),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        })
    return candles


def main():
    df = get_mt5_data()
    if df is None:
        return

    zones, summary = detect_fvg_groups(df)
    candles = build_chart_data(df)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "template.html")
    output_path = os.path.join(current_dir, "output.html")

    if not os.path.exists(template_path):
        print(f"Template introuvable: {template_path}")
        return

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{{donnees_javascript}}", json.dumps(candles))
    html = html.replace("{{strategy_javascript}}", json.dumps(zones))
    html = html.replace("{{stats_javascript}}", json.dumps(summary))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"{len(candles)} bougies chargées")
    print(f"{len(zones)} FVG affichés")
    print(
        f"Bilan FVG sur {summary['count']} GAPs filtrés | "
        f"Moyenne: {summary['avg']:.2f} {summary['unit']} | "
        f"Médiane: {summary['median']:.2f} {summary['unit']}"
    )
    print(f"Fichier généré: {output_path}")


if __name__ == "__main__":
    main()