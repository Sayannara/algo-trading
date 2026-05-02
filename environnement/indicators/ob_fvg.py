import pandas as pd
import numpy as np

def calculate_atr(df, period=14):
    """Calcule l'Average True Range (ATR)"""
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    return tr.rolling(window=period).mean()

def detect_ob_fvg(df, config):
    """
    Détecte les Fair Value Gaps (FVG) et les Order Blocks (OB) associés.
    Retourne une liste de dictionnaires contenant les coordonnées précises.
    """
    if len(df) < 20:
        return []
        
    ob_cfg = getattr(config, "OB_DETECTION", {})
    
    m1_enabled = ob_cfg.get("method_1_enabled", True)
    m2_enabled = ob_cfg.get("method_2_enabled", True)
    m3_enabled = ob_cfg.get("method_3_enabled", True)
    
    max_gap = ob_cfg.get("max_gap_ob_fvg", 3)
    max_overlap = ob_cfg.get("max_overlap_ob_fvg_ticks", 0)
    cascade = ob_cfg.get("cascade_on_overlap", True)
    
    m1_cfg = ob_cfg.get("method_1", {})
    m1_max_search = m1_cfg.get("max_search_candles", 5)
    m1_max_overlap = m1_cfg.get("max_overlap_ticks", 50)
    
    m2_cfg = ob_cfg.get("method_2", {})
    m2_min_candles = m2_cfg.get("min_candles", 3)
    m2_atr_len = m2_cfg.get("atr_len", 14)
    m2_atr_mult = m2_cfg.get("atr_mult", 1.2)
    
    m3_cfg = ob_cfg.get("method_3", {})
    m3_window = m3_cfg.get("swing_window", 10)
    m3_max_atr_mult = m3_cfg.get("max_atr_mult", 2.5)
    m3_req_below = m3_cfg.get("require_swing_below_fvg", True)
    m3_req_above = m3_cfg.get("require_swing_above_fvg", True)
    
    # Paramètres FVG
    type_mesure = ob_cfg.get("fvg_type_mesure", "Ticks")
    min_valeur = ob_cfg.get("fvg_min_valeur", 150.0)
    mintick = ob_cfg.get("fvg_mintick", 0.00001)
    show_fvg_labels = ob_cfg.get("show_fvg_labels", True)
    show_ob_labels = ob_cfg.get("show_ob_labels", True)
    
    # Calcul ATR pour la méthode 2 et FVG
    atr = calculate_atr(df, m2_atr_len)
    
    fvgs = []
    
    last_bull_idx = -1
    bull_top = 0.0
    bull_bot = float('inf')
    bull_start_idx = -1
    bull_sum = 0.0
    bull_valide = False
    
    last_bear_idx = -1
    bear_top = 0.0
    bear_bot = -float('inf')
    bear_start_idx = -1
    bear_sum = 0.0
    bear_valide = False
    
    def check_validity(somme, close_val, atr_val):
        if type_mesure == "Ticks":
            val = somme / mintick
        elif type_mesure == "%":
            val = (somme / close_val) * 100
        else: # ATR
            val = somme / atr_val if atr_val else 0
        return val >= min_valeur
        
    def get_fvg_text(somme, close_val, atr_val):
        if not show_fvg_labels: return ""
        if type_mesure == "Ticks":
            val = somme / mintick
            return f"{val:.0f} ticks"
        elif type_mesure == "%":
            val = (somme / close_val) * 100
            return f"{val:.2f} %"
        else: # ATR
            val = somme / atr_val if atr_val else 0
            return f"{val:.2f} ATR"

    # ==========================================
    # 1. DÉTECTION ET FUSION DES FVGS
    # ==========================================
    for i in range(2, len(df)):
        c_low = df['Low'].iloc[i]
        c_high = df['High'].iloc[i]
        c_close = df['Close'].iloc[i]
        c_low_2 = df['Low'].iloc[i-2]
        c_high_2 = df['High'].iloc[i-2]
        c_atr = atr.iloc[i]
        
        # Bullish FVG
        if c_low > c_high_2:
            gap = c_low - c_high_2
            if i == last_bull_idx + 1:
                bull_top = max(bull_top, c_low)
                bull_bot = min(bull_bot, c_high_2)
                bull_sum += gap
            else:
                if last_bull_idx != -1 and bull_valide:
                    fvgs.append({
                        "direction": "bullish", 
                        "start_idx": bull_start_idx, 
                        "end_idx": last_bull_idx, 
                        "top": bull_top, 
                        "bot": bull_bot,
                        "text": get_fvg_text(bull_sum, c_close, c_atr)
                    })
                bull_start_idx = i - 1
                bull_top = c_low
                bull_bot = c_high_2
                bull_sum = gap
            
            bull_valide = check_validity(bull_sum, c_close, c_atr)
            last_bull_idx = i
            
        # Bearish FVG
        elif c_high < c_low_2:
            gap = c_low_2 - c_high
            if i == last_bear_idx + 1:
                bear_top = max(bear_top, c_low_2)
                bear_bot = min(bear_bot, c_high)
                bear_sum += gap
            else:
                if last_bear_idx != -1 and bear_valide:
                    fvgs.append({
                        "direction": "bearish", 
                        "start_idx": bear_start_idx, 
                        "end_idx": last_bear_idx, 
                        "top": bear_top, 
                        "bot": bear_bot,
                        "text": get_fvg_text(bear_sum, c_close, c_atr)
                    })
                bear_start_idx = i - 1
                bear_top = c_low_2
                bear_bot = c_high
                bear_sum = gap
            
            bear_valide = check_validity(bear_sum, c_close, c_atr)
            last_bear_idx = i
            
    if last_bull_idx != -1 and bull_valide:
        fvgs.append({"direction": "bullish", "start_idx": bull_start_idx, "end_idx": last_bull_idx, "top": bull_top, "bot": bull_bot, "text": get_fvg_text(bull_sum, df['Close'].iloc[last_bull_idx], atr.iloc[last_bull_idx])})
    if last_bear_idx != -1 and bear_valide:
        fvgs.append({"direction": "bearish", "start_idx": bear_start_idx, "end_idx": last_bear_idx, "top": bear_top, "bot": bear_bot, "text": get_fvg_text(bear_sum, df['Close'].iloc[last_bear_idx], atr.iloc[last_bear_idx])})
        
    results = []
    
    def get_overlap(ob_top, ob_bot, fvg_top, fvg_bot, direction):
        # Renvoie la quantité de chevauchement. 0 = aucun.
        if direction == 'bullish':
            return max(0, ob_top - fvg_bot) # Si le haut de l'OB dépasse le bas du FVG
        else:
            return max(0, fvg_top - ob_bot) # Si le bas de l'OB dépasse le haut du FVG

    # ==========================================
    # 2. RECHERCHE DES OBs POUR CHAQUE FVG
    # ==========================================
    for fvg in fvgs:
        dir_ = fvg['direction']
        fvg_start = fvg['start_idx'] # C'est la bougie [i-2] qui crée la base du gap
        fvg_top = fvg['top']
        fvg_bot = fvg['bot']
        
        ob_found = False
        ob_data = None
        
        # On commence à chercher l'OB à partir de la bougie AVANT la base du FVG
        search_start = fvg_start - 1 
        if search_start < 0:
            continue
            
        methods_to_try = []
        if m3_enabled: methods_to_try.append(3)
        if m2_enabled: methods_to_try.append(2)
        if m1_enabled: methods_to_try.append(1)
        
        for method in methods_to_try:
            if ob_found and not cascade:
                break
                
            temp_ob = None
            
            # --- MÉTHODE 3 : SWING ---
            if method == 3:
                w_start = max(0, search_start - m3_window + 1)
                window_df = df.iloc[w_start:search_start+1]
                if len(window_df) >= 3:
                    temp_top = window_df['High'].max()
                    temp_bot = window_df['Low'].min()
                    
                    b_height = temp_top - temp_bot
                    current_atr = atr.iloc[search_start]
                    
                    # Rejet si le swing est trop grand en hauteur
                    if pd.notna(current_atr) and current_atr > 0 and (b_height > current_atr * m3_max_atr_mult):
                        temp_ob = None
                    else:
                        temp_ob = {"top": temp_top, "bot": temp_bot, "start_idx": w_start, "end_idx": search_start, "method": 3}
                        
                        if dir_ == 'bullish' and m3_req_below and (temp_top > fvg_top):
                            temp_ob = None # Invalide si pas majoritairement sous FVG
                        elif dir_ == 'bearish' and m3_req_above and (temp_bot < fvg_bot):
                            temp_ob = None # Invalide si pas majoritairement sur FVG
            
            # --- MÉTHODE 2 : ACCUMULATION ---
            elif method == 2:
                accum_start = -1
                accum_end = search_start
                # On remonte en grandissant le bloc
                for length in range(m2_min_candles, search_start + 2):
                    start_idx = search_start - length + 1
                    if start_idx < 0: break
                    
                    block = df.iloc[start_idx:search_start+1]
                    b_high = block['High'].max()
                    b_low = block['Low'].min()
                    b_height = b_high - b_low
                    
                    current_atr = atr.iloc[search_start]
                    
                    if pd.notna(current_atr) and b_height < (current_atr * m2_atr_mult):
                        accum_start = start_idx
                        temp_top = b_high
                        temp_bot = b_low
                    else:
                        break # Le bloc n'est plus en compression, on s'arrête
                
                if accum_start != -1 and (accum_end - accum_start + 1) >= m2_min_candles:
                    temp_ob = {"top": temp_top, "bot": temp_bot, "start_idx": accum_start, "end_idx": accum_end, "method": 2}

            # --- MÉTHODE 1 : BOUGIE INVERSE ---
            elif method == 1:
                # Recherche en arrière sur un maximum de bougies défini par paramètre
                for k in range(search_start, max(-1, search_start - m1_max_search), -1):
                    o = df['Open'].iloc[k]
                    c = df['Close'].iloc[k]
                    h = df['High'].iloc[k]
                    l = df['Low'].iloc[k]
                    
                    is_bearish = c < o
                    is_bullish = c > o
                    
                    overlap_val = get_overlap(h, l, fvg_top, fvg_bot, dir_)
                    overlap_ticks = overlap_val / mintick
                    
                    if dir_ == 'bullish' and is_bearish:
                        if overlap_ticks > m1_max_overlap:
                            continue # On cherche plus loin une bougie dans la marge tolérée
                        temp_ob = {"top": h, "bot": l, "start_idx": k, "end_idx": k, "method": 1}
                        break
                    elif dir_ == 'bearish' and is_bullish:
                        if overlap_ticks > m1_max_overlap:
                            continue
                        temp_ob = {"top": h, "bot": l, "start_idx": k, "end_idx": k, "method": 1}
                        break
            
            # --- VÉRIFICATION CHEVAUCHEMENT (OVERLAP) ---
            if temp_ob:
                overlap_amt = get_overlap(temp_ob['top'], temp_ob['bot'], fvg_top, fvg_bot, dir_)
                overlap_ticks = overlap_amt / mintick
                
                tol_overlap = m1_max_overlap if method == 1 else max_overlap
                
                if overlap_ticks <= tol_overlap:
                    ob_data = temp_ob
                    ob_found = True
                    break # On a trouvé un OB valide avec cette méthode prioritaire
                elif cascade:
                    continue # Overlap trop grand, on descend en cascade à la méthode suivante
        
        # --- VÉRIFICATION ESPACE OB-FVG ---
        if ob_found and ob_data:
            gap_distance = fvg_start - ob_data['end_idx'] - 1
            if gap_distance <= max_gap:
                ob_data['text'] = f"M{ob_data['method']}" if show_ob_labels else ""
                results.append({
                    "fvg": fvg,
                    "ob": ob_data
                })
            else:
                results.append({"fvg": fvg, "ob": None})
        else:
            results.append({"fvg": fvg, "ob": None})
                
    return results
