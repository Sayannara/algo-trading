import pandas as pd

def calculer_order_blocks(df, min_gap_pips=2.0, extension_bougies=30):
    """
    Détecte les Order Blocks liés à une Imbalance (FVG) 
    ET les Order Blocks liés à des Vrais GAPs.
    Esthétique : Tous les OBs sont dessinés sans fond, uniquement avec une bordure.
    Les GAPs en eux-mêmes ne sont plus dessinés en couleur.
    """
    zones_ob = []
    if len(df) < 3:
        return zones_ob
        
    min_gap = min_gap_pips * 0.002
    
    for i in range(2, len(df)):
        
        # ---------------------------------------------------------
        # PARTIE 1 : ORDER BLOCKS ISSUS DE VRAIS GAPS DE SESSION
        # ---------------------------------------------------------
        close_prev = df.loc[i-1, 'Close']
        open_curr  = df.loc[i, 'Open']
        
        is_bullish_gap = (open_curr > close_prev) and ((open_curr - close_prev) >= min_gap)
        is_bearish_gap = (open_curr < close_prev) and ((close_prev - open_curr) >= min_gap)

        if is_bullish_gap:
            idx_ob = i - 1
            max_lookback = max(0, i - 4) # Recul max de 4 bougies
            found_opposite = False
            
            # Chercher la dernière bougie rouge (Close <= Open)
            while idx_ob >= max_lookback:
                if df.loc[idx_ob, 'Close'] <= df.loc[idx_ob, 'Open']:
                    found_opposite = True
                    break
                idx_ob -= 1
            
            # Fallback : l'OB est la bougie i-1 même si elle est de la même couleur
            if not found_opposite:
                idx_ob = i - 1
                
            ob_time = int(df.loc[idx_ob, 'time'].timestamp())
            end_time_idx = min(len(df) - 1, i + extension_bougies)
            end_time = int(df.loc[end_time_idx, 'time'].timestamp())
            
            zones_ob.append({
                'title': 'Bullish OB (GAP)',
                'start': ob_time,
                'end': end_time,
                'max_p': df.loc[idx_ob, 'High'],
                'min_p': df.loc[idx_ob, 'Low'],
                'color_bg': 'transparent',               # Pas de fond
                'color_border': 'rgba(8, 153, 129, 0.9)', # Bordure verte
                'border_style': 'solid'
            })
            
        elif is_bearish_gap:
            idx_ob = i - 1
            max_lookback = max(0, i - 4) # Recul max de 4 bougies
            found_opposite = False
            
            # Chercher la dernière bougie verte (Close >= Open)
            while idx_ob >= max_lookback:
                if df.loc[idx_ob, 'Close'] >= df.loc[idx_ob, 'Open']:
                    found_opposite = True
                    break
                idx_ob -= 1
            
            # Fallback : l'OB est la bougie i-1 même si elle est de la même couleur
            if not found_opposite:
                idx_ob = i - 1
                
            ob_time = int(df.loc[idx_ob, 'time'].timestamp())
            end_time_idx = min(len(df) - 1, i + extension_bougies)
            end_time = int(df.loc[end_time_idx, 'time'].timestamp())
            
            zones_ob.append({
                'title': 'Bearish OB (GAP)',
                'start': ob_time,
                'end': end_time,
                'max_p': df.loc[idx_ob, 'High'],
                'min_p': df.loc[idx_ob, 'Low'],
                'color_bg': 'transparent',                # Pas de fond
                'color_border': 'rgba(242, 54, 69, 0.9)', # Bordure rouge
                'border_style': 'solid'
            })

        # ---------------------------------------------------------
        # PARTIE 2 : ORDER BLOCKS CLASSIQUES LIÉS AUX IMBALANCES (FVG)
        # ---------------------------------------------------------
        high_1 = df.loc[i-2, 'High']
        low_1  = df.loc[i-2, 'Low']
        high_3 = df.loc[i, 'High']
        low_3  = df.loc[i, 'Low']
        
        # Bullish FVG -> OB Vert
        if low_3 > high_1 and ((low_3 - high_1) >= min_gap):
            idx_ob = i - 2
            while idx_ob >= 0 and df.loc[idx_ob, 'Close'] > df.loc[idx_ob, 'Open']:
                idx_ob -= 1
            
            if idx_ob >= 0:
                ob_time = int(df.loc[idx_ob, 'time'].timestamp())
                end_time_idx = min(len(df) - 1, i + extension_bougies)
                end_time = int(df.loc[end_time_idx, 'time'].timestamp())
                
                zones_ob.append({
                    'title': 'Bullish OB',
                    'start': ob_time,
                    'end': end_time,
                    'max_p': df.loc[idx_ob, 'High'],
                    'min_p': df.loc[idx_ob, 'Low'],
                    'color_bg': 'transparent',               # Pas de fond
                    'color_border': 'rgba(8, 153, 129, 0.9)', # Bordure verte
                    'border_style': 'solid'
                })
                
        # Bearish FVG -> OB Rouge
        elif high_3 < low_1 and ((low_1 - high_3) >= min_gap):
            idx_ob = i - 2
            while idx_ob >= 0 and df.loc[idx_ob, 'Close'] < df.loc[idx_ob, 'Open']:
                idx_ob -= 1
                
            if idx_ob >= 0:
                ob_time = int(df.loc[idx_ob, 'time'].timestamp())
                end_time_idx = min(len(df) - 1, i + extension_bougies)
                end_time = int(df.loc[end_time_idx, 'time'].timestamp())
                
                zones_ob.append({
                    'title': 'Bearish OB',
                    'start': ob_time,
                    'end': end_time,
                    'max_p': df.loc[idx_ob, 'High'],
                    'min_p': df.loc[idx_ob, 'Low'],
                    'color_bg': 'transparent',                # Pas de fond
                    'color_border': 'rgba(242, 54, 69, 0.9)', # Bordure rouge
                    'border_style': 'solid'
                })
                    
    return zones_ob