import os
import json

from indicators import build_chart_data
from strat import run_strategy


def main():
    result = run_strategy()

    df = result.get("df")
    trend_info = result.get("trend_info")
    daily_trend = result.get("daily_trend", [])
    markers = result.get("markers", [])

    trades = result.get("trades", [])
    fvg_zones = result.get("fvg_zones", [])
    ob_zones = result.get("ob_zones", [])

    if df is None:
        print("Aucune donnée disponible.")
        return

    candles = build_chart_data(df)

    # Si plus tard tu remets des zones, elles seront déjà prises en charge ici
    all_zones = []
    if fvg_zones:
        all_zones.extend(fvg_zones)
    if ob_zones:
        all_zones.extend(ob_zones)

    # Range journalier pour la heatmap, aligné sur l'axe temps
    daily_trend_ranges = []
    for d in daily_trend:
        day_str = d["date"]
        day_rows = df[df["time"].dt.strftime("%Y-%m-%d") == day_str]

        if day_rows.empty:
            continue

        start_ts = int(day_rows.iloc[0]["time"].timestamp())
        end_ts = int(day_rows.iloc[-1]["time"].timestamp())

        daily_trend_ranges.append({
            "date": day_str,
            "score": float(d["score"]),
            "start": start_ts,
            "end": end_ts,
        })

    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "template.html")
    output_path = os.path.join(current_dir, "output.html")

    if not os.path.exists(template_path):
        print(f"Template introuvable: {template_path}")
        return

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    summary = {
        "count": len(fvg_zones),
        "avg": 0.0,
        "median": 0.0,
        "unit": ""
    }

    html = html.replace("{{donnees_javascript}}", json.dumps(candles))
    html = html.replace("{{strategy_javascript}}", json.dumps(all_zones))
    html = html.replace("{{stats_javascript}}", json.dumps(summary))
    html = html.replace("{{trend_javascript}}", json.dumps(trend_info))
    html = html.replace("{{daily_trend_javascript}}", json.dumps(daily_trend_ranges))
    html = html.replace("{{markers_javascript}}", json.dumps(markers))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"{len(candles)} bougies chargées")
    print(f"{len(markers)} markers générés")
    print(f"{len(daily_trend_ranges)} scores journaliers de trend")
    print(f"Trades placeholder: {len(trades)}")
    print(f"FVG placeholder: {len(fvg_zones)}")
    print(f"OB placeholder: {len(ob_zones)}")
    print(f"Fichier généré: {output_path}")


if __name__ == "__main__":
    main()