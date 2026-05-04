import os
import strategies.bounce_ob_config as bounce_config

def execute(df, candles, ob_fvg_data, tq_history, config):
    cfg = bounce_config.CONFIG
    markers = []
    trade_boxes = []
    stats = {
        "total": 0, "win": 0, "loss": 0, "be": 0,
        "long_total": 0, "long_win": 0, "long_loss": 0, "long_be": 0,
        "short_total": 0, "short_win": 0, "short_loss": 0, "short_be": 0,
    }
    
    def get_tq_score_at(timestamp):
        score = 50.0
        for entry in tq_history:
            if entry['time'] <= timestamp:
                score = entry['score']
            else:
                break
        return score

    for item in ob_fvg_data:
        ob = item.get('ob')
        fvg = item.get('fvg')
        
        if not ob or not fvg:
            continue
            
        direction = fvg['direction']
        ob_top = ob['top']
        ob_bot = ob['bot']
        
        entry_level = cfg.get("entry_level", 0.5)
        mintick = config.OB_DETECTION.get("fvg_mintick", 0.01) if hasattr(config, "OB_DETECTION") else 0.01
        sl_margin = cfg.get("sl_margin_ticks", 2.0) * mintick

        if direction == 'bullish':
            entry_price = ob_top - (ob_top - ob_bot) * entry_level
            initial_sl_price = ob_bot - sl_margin
        else:
            entry_price = ob_bot + (ob_top - ob_bot) * entry_level
            initial_sl_price = ob_top + sl_margin
            
        print(f"DEBUG {direction}: ob_bot={ob_bot}, ob_top={ob_top}, entry_level={entry_level} -> entry_price={entry_price}")

        sl_dist = abs(entry_price - initial_sl_price)
        if sl_dist == 0: continue
        
        tp_price = entry_price + sl_dist * cfg.get("tp_rr", 2.0) if direction == 'bullish' else entry_price - sl_dist * cfg.get("tp_rr", 2.0)
        be_price = entry_price + sl_dist * cfg.get("be_rr_trigger", 1.0) if direction == 'bullish' else entry_price - sl_dist * cfg.get("be_rr_trigger", 1.0)
        # On ne doit chercher qu'à partir du moment où le FVG HTF est complètement formé
        fvg_end_time = fvg.get('end_time', 0)
        
        in_trade = False
        trade_entry_time = None
        is_long = (direction == 'bullish')
        current_sl_price = initial_sl_price
        
        # Trouver l'index de départ dans le LTF
        start_search = 0
        for i, c in enumerate(candles):
            if c['time'] >= fvg_end_time:
                start_search = i
                break
                
        # Vérification stricte au moment exact où l'OB est formé
        if start_search < len(df):
            first_open = df['Open'].iloc[start_search]
            if direction == 'bullish' and first_open <= entry_price:
                continue
            elif direction == 'bearish' and first_open >= entry_price:
                continue
        
        for i in range(start_search, len(df)):
            candle_time = candles[i]['time']
            if 'end_time' in ob and candle_time > ob['end_time'] and not in_trade:
                break
                
            low = df['Low'].iloc[i]
            high = df['High'].iloc[i]
            
            if not in_trade:
                if is_long and low <= entry_price:
                    tq = get_tq_score_at(candle_time)
                    if tq > 55:
                        in_trade = True
                        trade_entry_time = candle_time
                        markers.append({
                            "time": candle_time, "position": "belowBar", "color": "#ffffff", "shape": "arrowUp", "text": "Entry"
                        })
                    else:
                        break # TQ invalide, on annule l'OB
                elif not is_long and high >= entry_price:
                    tq = get_tq_score_at(candle_time)
                    if tq < 45:
                        in_trade = True
                        trade_entry_time = candle_time
                        markers.append({
                            "time": candle_time, "position": "aboveBar", "color": "#ffffff", "shape": "arrowDown", "text": "Entry"
                        })
                    else:
                        break # TQ invalide
            else:
                # Gestion du trade
                exit_time = candle_time
                status = None
                
                if is_long:
                    if high >= tp_price:
                        status = "win"
                    elif low <= current_sl_price:
                        status = "loss" if current_sl_price == initial_sl_price else "be"
                    elif high >= be_price:
                        current_sl_price = entry_price
                else:
                    if low <= tp_price:
                        status = "win"
                    elif high >= current_sl_price:
                        status = "loss" if current_sl_price == initial_sl_price else "be"
                    elif low <= be_price:
                        current_sl_price = entry_price
                        
                if status:
                    stats["total"] += 1
                    stats[status] += 1
                    if is_long:
                        stats["long_total"] += 1
                        stats[f"long_{status}"] += 1
                    else:
                        stats["short_total"] += 1
                        stats[f"short_{status}"] += 1
                        
                    # Ajout marqueur de sortie
                    markers.append({
                        "time": exit_time,
                        "position": "aboveBar" if not is_long else "belowBar",
                        "color": "#ffffff",
                        "shape": "arrowDown" if not is_long else "arrowUp",
                        "text": f"Exit ({status.upper()})"
                    })
                        
                    trade_boxes.append({
                        "time_entry": trade_entry_time,
                        "time_right": exit_time,
                        "entry": entry_price,
                        "sl": initial_sl_price, # On affiche le SL initial pour la boîte
                        "is_long": is_long,
                        "max_rr": cfg.get("tp_rr", 2.0),
                        "colors": {
                            "tp_fill": "rgba(0,150,136,0.3)" if status == "win" else "rgba(158,158,158,0.2)",
                            "sl_fill": "rgba(239,83,80,0.3)",
                        }
                    })
                    break # Sortie du trade, on passe à l'OB suivant

    # Export stats
    result_text = f"=== RESUME BOUNCE OB ===\n"
    result_text += f"Total trades: {stats['total']}\n"
    result_text += f"Win: {stats['win']} | Loss: {stats['loss']} | BE: {stats['be']}\n\n"
    result_text += f"--- LONGS ({stats['long_total']}) ---\n"
    result_text += f"Win: {stats['long_win']} | Loss: {stats['long_loss']} | BE: {stats['long_be']}\n\n"
    result_text += f"--- SHORTS ({stats['short_total']}) ---\n"
    result_text += f"Win: {stats['short_win']} | Loss: {stats['short_loss']} | BE: {stats['short_be']}\n"
    
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bounce_ob_result.txt"), "w", encoding="utf-8") as f:
        f.write(result_text)

    return {"markers": markers, "trade_boxes": trade_boxes}
