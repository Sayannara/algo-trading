from datetime import timedelta

import MetaTrader5 as mt5
import pandas as pd

import config


# =========================
#  Données MT5
# =========================

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


# =========================
#  Utils News / ATR / Ticks
# =========================

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
    return float(getattr(config, "FALLBACK_MIN_TICK", 0.00001))


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


def find_timestamp_at_or_before(df, target_dt):
    eligible = df[df["time"] <= target_dt]
    if eligible.empty:
        return int(df.iloc[-1]["time"].timestamp())
    return int(eligible.iloc[-1]["time"].timestamp())


# =========================
#  FVG (logique Pine-like)
# =========================

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

    est_forex = True
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
        bar_is_news = bool(df.loc[i, "is_news"])

        high_2 = float(df.loc[i - 2, "High"])
        low_2 = float(df.loc[i - 2, "Low"])

        bullish_gap = low_now > high_2
        bearish_gap = high_now < low_2

        # ------------ Bullish FVG ------------
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

                active_bull = {
                    "title": "Bullish FVG",
                    "type": "bullish_fvg",
                    "start_index": i - 1,
                    "right_index": i + extend_bars,
                    "last_index": i,
                    "top": low_now,
                    "bottom": high_2,
                    "sum_gap_price": gap_price,
                    "contains_news": bar_is_news,
                    "display_value": 0.0,
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
            # plus de tag [NEWS] dans le label
            text = base_text
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
            active_bull["bg"] = "rgba(0, 170, 0, 0.15)" if active_bull["contains_news"] else "rgba(0, 170, 0, 0.08)"
            active_bull["border"] = "rgba(0, 200, 0, 0.70)"
            active_bull["text_color"] = "#ffffff"

        # ------------ Bearish FVG ------------
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

                active_bear = {
                    "title": "Bearish FVG",
                    "type": "bearish_fvg",
                    "start_index": i - 1,
                    "right_index": i + extend_bars,
                    "last_index": i,
                    "top": low_2,
                    "bottom": high_now,
                    "sum_gap_price": gap_price,
                    "contains_news": bar_is_news,
                    "display_value": 0.0,
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
            text = base_text
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
            active_bear["bg"] = "rgba(220, 0, 0, 0.15)" if active_bear["contains_news"] else "rgba(220, 0, 0, 0.08)"
            active_bear["border"] = "rgba(255, 80, 80, 0.75)"
            active_bear["text_color"] = "#ffffff"

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


# =========================
#  OB ICT
# =========================

def attach_ict_ob_to_fvg(df, fvg_zones):
    ob_lookback = int(getattr(config, "OB_LOOKBACK", 5))
    min_ob_body = float(getattr(config, "MIN_OB_BODY", 0.00005))
    ob_extend_days = int(getattr(config, "OB_EXTEND_DAYS", 4))

    obs = []

    for zone in fvg_zones:
        if zone["type"] not in ("bullish_fvg", "bearish_fvg"):
            continue

        start_ts = zone["start"]
        idx_candidates = df.index[
            df["time"].apply(lambda t: int(t.timestamp()) == start_ts)
        ].tolist()

        if not idx_candidates:
            continue

        fvg_idx = idx_candidates[0]
        best_ob_idx = None
        direction = zone["type"]

        for j in range(fvg_idx - 1, max(-1, fvg_idx - 1 - ob_lookback), -1):
            o = float(df.loc[j, "Open"])
            c = float(df.loc[j, "Close"])
            body = abs(c - o)

            if body < min_ob_body:
                continue

            if direction == "bullish_fvg" and c < o:
                best_ob_idx = j
                break

            if direction == "bearish_fvg" and c > o:
                best_ob_idx = j
                break

        if best_ob_idx is None:
            continue

        ob_time_start = int(df.loc[best_ob_idx, "time"].timestamp())

        ob_start_dt = df.loc[best_ob_idx, "time"]
        ob_end_dt = ob_start_dt + timedelta(days=ob_extend_days)
        ob_time_end = find_timestamp_at_or_before(df, ob_end_dt)

        h = float(df.loc[best_ob_idx, "High"])
        l = float(df.loc[best_ob_idx, "Low"])

        if direction == "bullish_fvg":
            ob_type = "bullish_ob"
            bg = "rgba(0, 220, 0, 0.02)"
            border = "rgba(0, 255, 0, 0.95)"
        else:
            ob_type = "bearish_ob"
            bg = "rgba(255, 64, 64, 0.02)"
            border = "rgba(255, 120, 120, 0.95)"

        obs.append({
            "title": "",
            "type": ob_type,
            "start": ob_time_start,
            "end": ob_time_end,
            "max_p": h,
            "min_p": l,
            "color_bg": bg,
            "color_border": border,
            "text_color": "#ffffff",
            "text": "",
            "linked_fvg_start": start_ts,
        })

    return obs


# =========================
#  Sessions
# =========================

def obtenir_info_session(heure):
    if 0 <= heure < 8:
        return "Tokyo", "rgba(156, 39, 176, 0.10)", "transparent"
    elif 8 <= heure < 14:
        return "London", "rgba(255, 87, 34, 0.10)", "transparent"
    else:
        return "New York", "rgba(33, 150, 243, 0.10)", "transparent"


def calculer_sessions(df):
    blocs_sessions = []

    if df is None or df.empty:
        return blocs_sessions

    session_en_cours = None
    bloc_actuel = {}

    for _, row in df.iterrows():
        dt = row["time"]
        nom_session, couleur_bg, couleur_border = obtenir_info_session(dt.hour)
        temps_unix = int(dt.timestamp())

        if nom_session != session_en_cours:
            if session_en_cours is not None:
                blocs_sessions.append(bloc_actuel)

            session_en_cours = nom_session
            bloc_actuel = {
                "title": "",
                "type": "session",
                "session_name": nom_session,
                "color_bg": couleur_bg,
                "color_border": couleur_border,
                "border_style": "solid",
                "start": temps_unix,
                "end": temps_unix,
                "max_p": float(row["High"]),
                "min_p": float(row["Low"]),
                "text": "",
                "text_color": "#ffffff",
            }
        else:
            bloc_actuel["end"] = temps_unix
            bloc_actuel["max_p"] = max(bloc_actuel["max_p"], float(row["High"]))
            bloc_actuel["min_p"] = min(bloc_actuel["min_p"], float(row["Low"]))

    if bloc_actuel:
        blocs_sessions.append(bloc_actuel)

    return blocs_sessions


# =========================
#  Trend Quality
# =========================

def calculer_trend_quality(
    df,
    session_lookback=None,
    use_decay=True,
    timezone=None,
    weight_ny=50,
    weight_ldn=35,
    weight_tky=15,
    thresh_strong_bull=75,
    thresh_weak_bull=65,
    thresh_weak_bear=35,
    thresh_strong_bear=25
):
    if df is None or df.empty:
        return None

    if session_lookback is None:
        session_lookback = int(getattr(config, "TREND_SESSION_LOOKBACK", 6))
    if timezone is None:
        timezone = getattr(config, "TREND_TIMEZONE", "Europe/Zurich")

    df_local = df.copy()

    if df_local["time"].dt.tz is None:
        df_local["time_local"] = df_local["time"].dt.tz_localize("Etc/UTC").dt.tz_convert(timezone)
    else:
        df_local["time_local"] = df_local["time"].dt.tz_convert(timezone)

    df_local["date"] = df_local["time_local"].dt.date
    df_local["hour"] = df_local["time_local"].dt.hour

    def get_session_name(h):
        if 0 <= h < 8:
            return "TKY"
        elif 8 <= h < 14:
            return "LDN"
        else:
            return "NY"

    df_local["session"] = df_local["hour"].apply(get_session_name)

    session_stats = (
        df_local
        .groupby(["date", "session"])
        .agg({"High": "max", "Low": "min"})
        .reset_index()
    )

    tky_stats = (
        session_stats[session_stats["session"] == "TKY"]
        .sort_values("date")
        .tail(session_lookback)
    )
    ldn_stats = (
        session_stats[session_stats["session"] == "LDN"]
        .sort_values("date")
        .tail(session_lookback)
    )
    ny_stats = (
        session_stats[session_stats["session"] == "NY"]
        .sort_values("date")
        .tail(session_lookback)
    )

    def calc_score(df_sess):
        highs = df_sess["High"].tolist()
        lows = df_sess["Low"].tolist()
        sz = len(highs)
        if sz < 2:
            return 50.0

        tot_weight = 0.0
        bull_pts = 0.0

        for i in range(1, sz):
            w = (i + 1) if use_decay else 1.0
            tot_weight += (w * 2)

            if highs[i] > highs[i - 1]:
                bull_pts += w
            if lows[i] > lows[i - 1]:
                bull_pts += w

        return (bull_pts / tot_weight) * 100 if tot_weight > 0 else 50.0

    score_tky = calc_score(tky_stats)
    score_ldn = calc_score(ldn_stats)
    score_ny = calc_score(ny_stats)

    tot_w = weight_ny + weight_ldn + weight_tky
    if tot_w == 0:
        wn = wl = wt = 1.0 / 3.0
    else:
        wn = weight_ny / tot_w
        wl = weight_ldn / tot_w
        wt = weight_tky / tot_w

    trend_score = (score_ny * wn) + (score_ldn * wl) + (score_tky * wt)

    if trend_score >= thresh_strong_bull:
        text = f"Forte Haussière ({trend_score:.1f}%)"
        color = "#4CAF50"
    elif trend_score > thresh_weak_bull:
        text = f"Légère Haussière ({trend_score:.1f}%)"
        color = "#81C784"
    elif trend_score <= thresh_strong_bear:
        text = f"Forte Baissière ({trend_score:.1f}%)"
        color = "#FF5252"
    elif trend_score < thresh_weak_bear:
        text = f"Légère Baissière ({trend_score:.1f}%)"
        color = "#E57373"
    else:
        text = f"Consolidation ({trend_score:.1f}%)"
        color = "#9E9E9E"

    return {
        "score": float(trend_score),
        "text": text,
        "color": color,
        "lookback": int(session_lookback),
    }


# =========================
#  Candles pour le chart
# =========================

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