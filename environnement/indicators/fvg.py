import pandas as pd
import numpy as np

def calculate_atr(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    return tr.rolling(window=period).mean()

def detect_fvg(df, config):
    if len(df) < 20:
        return []
        
    fvg_cfg = getattr(config, "FVG", {})
    type_mesure = fvg_cfg.get("type_mesure", "Ticks")
    min_valeur = fvg_cfg.get("min_valeur", 150.0)
    mintick = fvg_cfg.get("mintick", 0.00001)
    show_labels = fvg_cfg.get("show_labels", True)
    
    atr = calculate_atr(df, 14)
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
    
    def get_text(somme, close_val, atr_val):
        if not show_labels: return ""
        if type_mesure == "Ticks":
            val = somme / mintick
            return f"{val:.0f} ticks"
        elif type_mesure == "%":
            val = (somme / close_val) * 100
            return f"{val:.2f} %"
        else: # ATR
            val = somme / atr_val if atr_val else 0
            return f"{val:.2f} ATR"

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
                        "text": get_text(bull_sum, c_close, c_atr)
                    })
                # Le gap visuel se situe souvent à la bougie du milieu (i-1)
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
                        "text": get_text(bear_sum, c_close, c_atr)
                    })
                bear_start_idx = i - 1
                bear_top = c_low_2
                bear_bot = c_high
                bear_sum = gap
            
            bear_valide = check_validity(bear_sum, c_close, c_atr)
            last_bear_idx = i
            
    if last_bull_idx != -1 and bull_valide:
        fvgs.append({"direction": "bullish", "start_idx": bull_start_idx, "end_idx": last_bull_idx, "top": bull_top, "bot": bull_bot, "text": get_text(bull_sum, df['Close'].iloc[last_bull_idx], atr.iloc[last_bull_idx])})
    if last_bear_idx != -1 and bear_valide:
        fvgs.append({"direction": "bearish", "start_idx": bear_start_idx, "end_idx": last_bear_idx, "top": bear_top, "bot": bear_bot, "text": get_text(bear_sum, df['Close'].iloc[last_bear_idx], atr.iloc[last_bear_idx])})
        
    return fvgs
