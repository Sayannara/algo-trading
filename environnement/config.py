# config.py — Configuration partagée
# ─────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════
# ENVIRONNEMENT GLOBAL
# ══════════════════════════════════════════════════════════════

TIMEZONE  = 'Europe/Zurich'
SYMBOL    = "NZDJPY"
DATE_FROM = "2025-02-01"
DATE_TO   = "2027-01-01"

# ══════════════════════════════════════════════════════════════
# CONFIGURATION LTF (Execution)
# ══════════════════════════════════════════════════════════════
LTF = {
    "TIMEFRAME": "M5",
    
    "INDICATORS": {
        'sessions':       True,
        'trend_quality':  True,
        'trades':         False, 
        'trade_boxes':    False,
        'fvg':            False,
        'ob_fvg':         False, # Calcul d'OB désactivé car on prend ceux du HTF
        'import_htf_ob':  True,  # Import de la source HTF
    },
    
    "STRATEGIES": {
        'bounce_ob': True,
    },
    
    "MAX_RR": 4,
    
    "SESSIONS": {   'A': {   'color': '#00BCD4',
             'enabled': True,
             'end': '00:00',
             'fill_alpha': 0.0,
             'name': 'New York',
             'start': '14:00'},
    'B': {'color': '#F44336', 'enabled': True, 'end': '14:00', 'fill_alpha': 0.0, 'name': 'London', 'start': '09:00'},
    'C': {'color': '#CE93D8', 'enabled': True, 'end': '09:00', 'fill_alpha': 0.0, 'name': 'Tokyo', 'start': '00:00'},
    'D': {'color': '#FFEB3B', 'enabled': False, 'end': '06:00', 'fill_alpha': 0.0, 'name': 'Sydney', 'start': '21:00'}},
    "TREND_QUALITY": {   'decay': 0.85,
    'enabled': True,
    'label_position': 'aboveBar',
    'label_shape': 'circle',
    'lookback_days': 12,
    'min_days': 4,
    'sessions': {   'london': {'end': '14:00', 'start': '08:00'},
                    'newyork': {'end': '22:00', 'start': '14:00'},
                    'tokyo': {'end': '08:00', 'start': '00:00'}},
    'show_labels': False,
    'use_decay': True},
    "OB_DETECTION": {   'cascade_on_overlap': True,
    'debug': {'highlight_ob_candles': True, 'show_detection_labels': True},
    'fvg_min_valeur': 200.0,
    'fvg_mintick': 0.001,
    'fvg_type_mesure': 'Ticks',
    'max_gap_ob_fvg': 3,
    'max_overlap_ob_fvg_ticks': 20,
    'method_1': {'max_overlap_ticks': 80, 'max_search_candles': 5},
    'method_1_enabled': True,
    'method_2': {'atr_len': 14, 'atr_mult': 1.2, 'min_candles': 3},
    'method_2_enabled': True,
    'method_3': {   'max_atr_mult': 2.5,
                    'require_swing_above_fvg': True,
                    'require_swing_below_fvg': True,
                    'swing_window': 10},
    'method_3_enabled': True,
    'ob_extension_days': 3,
    'show_fvg_labels': True,
    'show_ob_labels': True,
    'visuals': {   'method_1': {   'bearish_color': '#FF1744',
                                   'bearish_opacity': 0.0,
                                   'bullish_color': '#00E676',
                                   'bullish_opacity': 0.0},
                   'method_2': {   'bearish_color': '#FF1744',
                                   'bearish_opacity': 0.0,
                                   'bullish_color': '#00E676',
                                   'bullish_opacity': 0.0},
                   'method_3': {   'bearish_color': '#FF1744',
                                   'bearish_opacity': 0.0,
                                   'bullish_color': '#00E676',
                                   'bullish_opacity': 0.0},
                   'show_method_label': True}},
    "FVG": {'min_valeur': 150.0, 'mintick': 1e-05, 'show_labels': True, 'type_mesure': 'Ticks'}
}

# ══════════════════════════════════════════════════════════════
# CONFIGURATION HTF (Contexte)
# ══════════════════════════════════════════════════════════════
HTF = {
    "ENABLED": True,
    "TIMEFRAME": "M30",
    
    "INDICATORS": {
        'sessions':       True,
        'trend_quality':  True,
        'trades':         False, 
        'trade_boxes':    False,
        'fvg':            False,
        'ob_fvg':         True,  # Calcul d'OB activé sur le HTF
        'import_htf_ob':  False,
    },
    
    "STRATEGIES": {
        'bounce_ob': False, # Pas exécuté sur le HTF pur
    },
    
    "MAX_RR": 4,
    
    "SESSIONS": {   'A': {   'color': '#00BCD4',
             'enabled': True,
             'end': '00:00',
             'fill_alpha': 0.05,
             'name': 'New York',
             'start': '14:00'},
    'B': {'color': '#F44336', 'enabled': True, 'end': '14:00', 'fill_alpha': 0.05, 'name': 'London', 'start': '09:00'},
    'C': {'color': '#CE93D8', 'enabled': True, 'end': '09:00', 'fill_alpha': 0.05, 'name': 'Tokyo', 'start': '00:00'},
    'D': {'color': '#FFEB3B', 'enabled': False, 'end': '06:00', 'fill_alpha': 0.05, 'name': 'Sydney', 'start': '21:00'}},
    "TREND_QUALITY": {   'decay': 0.85,
    'enabled': True,
    'label_position': 'aboveBar',
    'label_shape': 'circle',
    'lookback_days': 12,
    'min_days': 4,
    'sessions': {   'london': {'end': '14:00', 'start': '08:00'},
                    'newyork': {'end': '22:00', 'start': '14:00'},
                    'tokyo': {'end': '08:00', 'start': '00:00'}},
    'show_labels': False,
    'use_decay': True},
    "OB_DETECTION": {   'cascade_on_overlap': True,
    'debug': {'highlight_ob_candles': True, 'show_detection_labels': True},
    'fvg_min_valeur': 200.0,
    'fvg_mintick': 0.001,
    'fvg_type_mesure': 'Ticks',
    'max_gap_ob_fvg': 3,
    'max_overlap_ob_fvg_ticks': 20,
    'method_1': {'max_overlap_ticks': 80, 'max_search_candles': 5},
    'method_1_enabled': True,
    'method_2': {'atr_len': 14, 'atr_mult': 1.2, 'min_candles': 3},
    'method_2_enabled': True,
    'method_3': {   'max_atr_mult': 2.5,
                    'require_swing_above_fvg': True,
                    'require_swing_below_fvg': True,
                    'swing_window': 10},
    'method_3_enabled': True,
    'ob_extension_days': 3,
    'show_fvg_labels': True,
    'show_ob_labels': True,
    'visuals': {   'method_1': {   'bearish_color': '#B71C1C',
                                   'bearish_opacity': 0.3,
                                   'bullish_color': '#1B5E20',
                                   'bullish_opacity': 0.3},
                   'method_2': {   'bearish_color': '#B71C1C',
                                   'bearish_opacity': 0.3,
                                   'bullish_color': '#1B5E20',
                                   'bullish_opacity': 0.3},
                   'method_3': {   'bearish_color': '#B71C1C',
                                   'bearish_opacity': 0.3,
                                   'bullish_color': '#1B5E20',
                                   'bullish_opacity': 0.3},
                   'show_method_label': True}},
    "FVG": {'min_valeur': 150.0, 'mintick': 1e-05, 'show_labels': True, 'type_mesure': 'Ticks'}
}
