# config.py — Configuration partagée
# ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════
# ENVIRONNEMENT
# ══════════════════════════════════════════════════════════════

TIMEZONE = 'Europe/Zurich'



SYMBOL    = "NZDJPY"
DATE_FROM = "2026-02-01"
DATE_TO   = "2026-05-01"
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
    "fvg_type_mesure": "Ticks", # Type de mesure pour la taille du FVG ("Ticks", "%" ou "ATR")
    "fvg_min_valeur": 200.0, # Taille minimale du FVG pour être considéré valide (selon le type_mesure)
    "fvg_mintick": 0.001, # Valeur d'un tick (ex: 0.00001 pour EURUSD, 0.001 pour les paires JPY)
    "show_fvg_labels": True, # Afficher le texte avec la taille du gap à l'intérieur du rectangle FVG

    # --- OB Settings ---
    "ob_extension_days": 3, # Nombre de jours pour prolonger visuellement le rectangle de l'Order Block vers la droite
    "show_ob_labels": True, # Afficher la méthode (ex: "M1", "M2", "M3") au milieu de l'Order Block

    # --- Activation des méthodes ---
    "method_1_enabled": True, # Activer la recherche de la bougie inverse simple (la plus basique)
    "method_2_enabled": True, # Activer la recherche d'accumulation (plusieurs bougies comprimées)
    "method_3_enabled": True, # Activer la recherche par swing structurel (le plus haut/bas d'une fenêtre)

    # --- Espace max toléré entre OB et FVG (en bougies) ---
    "max_gap_ob_fvg": 3, # Nombre maximum de bougies autorisées entre la fin de l'OB et le début effectif du gap FVG

    # --- Overlap max toléré entre OB et FVG (en ticks) ---
    "max_overlap_ob_fvg_ticks": 20, # Marge globale de chevauchement (overlap) tolérée entre l'OB et le FVG pour valider la paire.

    # --- Cascade de méthodes si overlap détecté ---
    "cascade_on_overlap": True, # Si la priorité haute (M3) échoue, l'algo essaie M2, puis M1 au lieu d'abandonner immédiatement

    # --- Méthode 1 : Bougie inverse simple (priorité basse) ---
    "method_1": {
        "max_search_candles": 5, # Remonte jusqu'à 5 bougies en arrière avant le gap pour trouver une bougie de couleur inverse
        "max_overlap_ticks": 80, # Marge tolérée (en ticks) entre la mèche de cette bougie inverse et le bord du gap FVG
    },

    # --- Méthode 2 : Accumulation (priorité moyenne) ---
    "method_2": {
        "min_candles": 3, # Nombre minimum de bougies qui doivent se succéder dans le bloc d'accumulation
        "atr_len": 14, # Période pour calculer l'ATR (volatilité moyenne) utilisé pour mesurer la compression
        "atr_mult": 1.2, # La hauteur totale de toutes les bougies accumulées ne doit pas dépasser 1.2 fois l'ATR
    },

    # --- Méthode 3 : Swing structurel (priorité haute) ---
    "method_3": {
        "swing_window": 10, # Fenêtre de recherche du swing : regarde le plus haut/plus bas des 10 dernières bougies avant le gap
        "max_atr_mult": 2.5, # Rejette le swing s'il est gigantesque (distance entre le plus haut et le plus bas > 2.5x l'ATR)
        "require_swing_below_fvg": True, # Pour un FVG haussier, s'assurer que le swing est logiquement en dessous du FVG
        "require_swing_above_fvg": True, # Pour un FVG baissier, s'assurer que le swing est logiquement au-dessus du FVG
    },

    # --- Visuels ---
    "visuals": {
        "show_method_label": True,

        "method_1": {
            "bullish_color": "#00E676",
            "bullish_opacity": 0.2,
            "bearish_color": "#FF1744",
            "bearish_opacity": 0.2,
        },

        "method_2": {
            "bullish_color": "#00E676",
            "bullish_opacity": 0.25,
            "bearish_color": "#FF1744",
            "bearish_opacity": 0.25,
        },

        "method_3": {
            "bullish_color": "#00E676",
            "bullish_opacity": 0.3,
            "bearish_color": "#FF1744",
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
