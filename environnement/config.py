# config.py — Configuration partagée
# ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════
# ENVIRONNEMENT
# ══════════════════════════════════════════════════════════════

TIMEZONE = 'Europe/Zurich'



SYMBOL    = "EURUSD"
DATE_FROM = "2025-02-01"
DATE_TO   = "2026-04-29"
TIMEFRAME = "M30"



# ══════════════════════════════════════════════════════════════
# INDICATEURS
# ══════════════════════════════════════════════════════════════

# ── Indicateurs actifs ────────────────────────────────────────
INDICATORS = {
    'sessions':       True,
    'trend_quality':  True,
    'trades':         False, 
    "trade_boxes":    False,
    'fvg':            False,
    'ob_fvg':         True,
}

# ── Sessions ──────────────────────────────────────────────────

SESSIONS = {
    'A': {
        'name':         'New York',
        'enabled':      True,
        'start':        '14:00',    # heure locale (TIMEZONE)
        'end':          '00:00',    # heure locale (TIMEZONE)
        'color':        '#00BCD4',  # couleur bordure
        'fill_alpha':   0.05       # transparence du fond (0.0 → 1.0)
    },
    'B': {
        'name':         'London',
        'enabled':      True,
        'start':        '09:00',
        'end':          '14:00',
        'color':        '#F44336',
        'fill_alpha':   0.05,
    },
    'C': {
        'name':         'Tokyo',
        'enabled':      True,
        'start':        '00:00',
        'end':          '09:00',
        'color':        '#CE93D8',
        'fill_alpha':   0.05,
    },
    'D': {
        'name':         'Sydney',
        'enabled':      False,
        'start':        '21:00',
        'end':          '06:00',
        'color':        '#FFEB3B',
        'fill_alpha':   0.05,
    },
}


# ── Trend quality  ──────────────────────────────────────────────────

TREND_QUALITY = {
    "enabled": True,
    "show_labels": False,
    "lookback_days": 12,
    "min_days": 4,
    "use_decay": True,
    "decay": 0.85,
    "label_position": "aboveBar",
    "label_shape": "circle",
    "sessions": {
        "tokyo":   {"start": "00:00", "end": "08:00"},
        "london":  {"start": "08:00", "end": "14:00"},
        "newyork": {"start": "14:00", "end": "22:00"},
    },
}

# ── Draw trade box  ──────────────────────────────────────────────────
MAX_RR = 4


# ── OB + FVG Detection  ──────────────────────────────────────────────
OB_DETECTION = {
    # --- FVG Settings ---
    "fvg_type_mesure": "Ticks",
    "fvg_min_valeur": 150.0,
    "fvg_mintick": 0.00001,
    "show_fvg_labels": True,

    # --- OB Settings ---
    "ob_extension_days": 3,
    "show_ob_labels": True,

    # --- Activation des méthodes ---
    "method_1_enabled": True,
    "method_2_enabled": True,
    "method_3_enabled": True,

    # --- Espace max toléré entre OB et FVG (en bougies) ---
    "max_gap_ob_fvg": 3,

    # --- Overlap max toléré entre OB et FVG (en ticks) ---
    "max_overlap_ob_fvg_ticks": 0,

    # --- Cascade de méthodes si overlap détecté ---
    "cascade_on_overlap": True,

    # --- Méthode 1 : Bougie inverse simple (priorité basse) ---
    "method_1": {
        "max_search_candles": 5,
        "max_overlap_ticks": 80, # Marge tolérée (en ticks) entre la bougie et le FVG
    },

    # --- Méthode 2 : Accumulation (priorité moyenne) ---
    "method_2": {
        "min_candles": 3,
        "atr_len": 14,
        "atr_mult": 1.2, # Multiplicateur de l'ATR pour la compression
    },

    # --- Méthode 3 : Swing structurel (priorité haute) ---
    "method_3": {
        "swing_window": 10,
        "max_atr_mult": 2.5, # Rejette le swing s'il est plus grand que 2.5x l'ATR
        "require_swing_below_fvg": True,
        "require_swing_above_fvg": True,
    },

    # --- Visuels ---
    "visuals": {
        "show_method_label": True,

        "method_1": {
            "bullish_color": "#2962FF",
            "bullish_opacity": 0.2,
            "bearish_color": "#FF1744",
            "bearish_opacity": 0.2,
        },

        "method_2": {
            "bullish_color": "#00BCD4",
            "bullish_opacity": 0.25,
            "bearish_color": "#FF6D00",
            "bearish_opacity": 0.25,
        },

        "method_3": {
            "bullish_color": "#00E676",
            "bullish_opacity": 0.3,
            "bearish_color": "#D500F9",
            "bearish_opacity": 0.3,
        },
    },

    # --- Debug ---
    "debug": {
        "show_detection_labels": True,
        "highlight_ob_candles": True,
    }
}

# ── FVG Simple  ──────────────────────────────────────────────
FVG = {
    "type_mesure": "Ticks", # "Ticks", "Pourcentage (%)", "ATR"
    "min_valeur": 150.0,
    "mintick": 0.00001,
    "show_labels": True,
}
