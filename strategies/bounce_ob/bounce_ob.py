import os
import json

from indicators import (
    get_mt5_data,
    detect_fvg_groups,
    attach_ict_ob_to_fvg,
    calculer_sessions,
    calculer_trend_quality,
    build_chart_data,
)

from strat import run_strategy, trades_to_dicts

def main():
    # 1. Exécution de la stratégie (trades, trend, zones)
    trades, trend_info, fvg_zones, ob_zones = run_strategy()

    # 2. Récupération des données complètes + sessions + candles
    df = get_mt5_data()
    if df is None:
        return

    session_zones = calculer_sessions(df)
    candles = build_chart_data(df)

    # 3. Zones rectangles pour overlay (sessions + FVG + OB)
    all_zones = session_zones + fvg_zones + ob_zones

    # 4. Préparation des markers de trades pour Lightweight Charts
    trade_dicts = trades_to_dicts(trades)
    markers = []

    for t in trade_dicts:
        if t["entry_time"] is not None:
            markers.append({
                "time": int(t["entry_time"]),
                "position": "belowBar" if t["direction"] == "long" else "aboveBar",
                "color": "#51cf66" if t["direction"] == "long" else "#ff6b6b",
                "shape": "arrowUp" if t["direction"] == "long" else "arrowDown",
                "text": "BUY" if t["direction"] == "long" else "SELL",
            })

        if t["exit_time"] is not None:
            markers.append({
                "time": int(t["exit_time"]),
                "position": "aboveBar" if t["direction"] == "long" else "belowBar",
                "color": "#74c0fc" if t["exit_reason"] == "TP" else "#ffa94d",
                "shape": "square",
                "text": t["exit_reason"] or "EXIT",
            })

    markers.sort(key=lambda m: m["time"])

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
    html = html.replace("{{trades_javascript}}", json.dumps(trade_dicts))
    html = html.replace("{{markers_javascript}}", json.dumps(markers))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 5. Résumé console
    total_trades = len(trades)
    tp_count = sum(1 for t in trades if t.exit_reason == "TP")
    sl_count = sum(1 for t in trades if t.exit_reason == "SL")
    other_exit = total_trades - tp_count - sl_count

    print(f"{len(candles)} bougies chargées")
    print(f"{len(session_zones)} blocs de session")
    print(f"{len(fvg_zones)} FVG utilisés pour OB")
    print(f"{len(ob_zones)} OB ICT")
    if trend_info is not None:
        print(f"Trend quality: {trend_info['text']} (score={trend_info['score']:.2f}%, lookback={trend_info['lookback']} jours)")
    else:
        print("Trend quality: N/A")

    print(f"Trades totaux: {total_trades}")
    print(f"TP: {tp_count} | SL: {sl_count} | Autres: {other_exit}")
    print(f"Fichier généré: {output_path}")


if __name__ == "__main__":
    main()