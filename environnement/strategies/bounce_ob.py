def execute(df, candles, ob_fvg_data, tq_history, config):
    """
    Détecte le premier rebond sur un OB valide.
    Filtre par Trend Quality:
    - OB Haussier : TQ > 55
    - OB Baissier : TQ < 45
    """
    markers = []
    
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
        
        # On commence à chercher le premier impact après la formation de la paire
        # end_idx du FVG est l'index où le gap est confirmé
        start_search = fvg['end_idx'] + 1
        
        for i in range(start_search, len(df)):
            candle_time = candles[i]['time']
            
            # Ne pas chercher si on dépasse la durée de validité (extension) de l'OB
            if 'end_time' in ob and candle_time > ob['end_time']:
                break
                
            low = df['Low'].iloc[i]
            high = df['High'].iloc[i]
            
            if direction == 'bullish':
                # Le prix descend et touche le haut de l'OB
                if low <= ob_top:
                    tq = get_tq_score_at(candle_time)
                    if tq > 55:
                        print(f"DEBUG WIN CHECK: BULLISH Bounce at {candles[i]['time']} price {low} (Index {i})")
                        markers.append({
                            "time": candle_time,
                            "position": "belowBar",
                            "color": "#00E676", # Vert clair
                            "shape": "arrowUp",
                            "text": "Bounce OB"
                        })
                    break # On s'arrête à la PREMIÈRE touche quoi qu'il arrive
            
            elif direction == 'bearish':
                # Le prix monte et touche le bas de l'OB
                if high >= ob_bot:
                    tq = get_tq_score_at(candle_time)
                    if tq < 45:
                        print(f"DEBUG WIN CHECK: BEARISH Bounce at {candles[i]['time']} price {high} (Index {i})")
                        markers.append({
                            "time": candle_time,
                            "position": "aboveBar",
                            "color": "#FF1744", # Rouge vif
                            "shape": "arrowDown",
                            "text": "Bounce OB"
                        })
                    break # On s'arrête à la PREMIÈRE touche
                    
    return markers
