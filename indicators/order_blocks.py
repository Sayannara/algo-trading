import pandas as pd

def calculer_order_blocks(df, min_gap_pips=2.0, extension_bougies=30):
    """
    Détecte les Order Blocks liés à une Imbalance (FVG).
    :param min_gap_pips: Taille minimum de l'imbalance en pips (ex: 2.0 pour l'EURUSD = 0.00020)
    :param extension_bougies: Nombre de bougies sur lesquelles on étire le dessin du rectangle
    """
    zones_ob = []
    if len(df) < 3:
        return zones_ob
        
    # Conversion des pips en valeur de prix brute (Pour les paires Forex classiques comme l'EURUSD)
    min_gap = min_gap_pips * 0.001
    
    # On parcourt à partir de la 3ème bougie (index 2) pour chercher le gap entre la bougie 1 et 3
    for i in range(2, len(df)):
        high_1 = df.loc[i-2, 'High']
        low_1  = df.loc[i-2, 'Low']
        
        high_3 = df.loc[i, 'High']
        low_3  = df.loc[i, 'Low']
        
        # --- BULLISH FVG (Imbalance Haussière) ---
        if low_3 > high_1:
            gap = low_3 - high_1
            if gap >= min_gap:
                # Chercher l'Order Block : dernière bougie baissière (Close <= Open) avant le FVG
                idx_ob = i - 2
                while idx_ob >= 0 and df.loc[idx_ob, 'Close'] > df.loc[idx_ob, 'Open']:
                    idx_ob -= 1
                
                if idx_ob >= 0:
                    ob_time = int(df.loc[idx_ob, 'time'].timestamp())
                    # Étendre le rectangle vers le futur
                    end_time_idx = min(len(df) - 1, i + extension_bougies)
                    end_time = int(df.loc[end_time_idx, 'time'].timestamp())
                    
                    zones_ob.append({
                        'title': 'Bullish OB',
                        'start': ob_time,
                        'end': end_time,
                        'max_p': df.loc[idx_ob, 'High'],
                        'min_p': df.loc[idx_ob, 'Low'],
                        'color_bg': 'rgba(8, 153, 129, 0.15)', # Vert transparent
                        'color_border': 'rgba(8, 153, 129, 0.9)',
                        'border_style': 'solid'
                    })
                    
        # --- BEARISH FVG (Imbalance Baissière) ---
        elif high_3 < low_1:
            gap = low_1 - high_3
            if gap >= min_gap:
                # Chercher l'Order Block : dernière bougie haussière (Close >= Open) avant le FVG
                idx_ob = i - 2
                while idx_ob >= 0 and df.loc[idx_ob, 'Close'] < df.loc[idx_ob, 'Open']:
                    idx_ob -= 1
                    
                if idx_ob >= 0:
                    ob_time = int(df.loc[idx_ob, 'time'].timestamp())
                    # Étendre le rectangle vers le futur
                    end_time_idx = min(len(df) - 1, i + extension_bougies)
                    end_time = int(df.loc[end_time_idx, 'time'].timestamp())
                    
                    zones_ob.append({
                        'title': 'Bearish OB',
                        'start': ob_time,
                        'end': end_time,
                        'max_p': df.loc[idx_ob, 'High'],
                        'min_p': df.loc[idx_ob, 'Low'],
                        'color_bg': 'rgba(242, 54, 69, 0.15)', # Rouge transparent
                        'color_border': 'rgba(242, 54, 69, 0.9)'
                    })
                    
    return zones_ob