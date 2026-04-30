# config.py — Configuration partagée
# ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════
# ENVIRONNEMENT
# ══════════════════════════════════════════════════════════════

TIMEZONE = 'Europe/Zurich'

SYMBOL    = "AUDUSD"
DATE_FROM = "2026-04-01"
DATE_TO   = "2026-04-28"
TIMEFRAME = "M30"
SOURCE    = "MT5"   # "MT5" | "HISTDATA" | "MASSIVE"



# ══════════════════════════════════════════════════════════════
# INDICATEURS
# ══════════════════════════════════════════════════════════════

# ── Indicateurs actifs ────────────────────────────────────────
INDICATORS = {
    'sessions':       True,
    'trend_quality':  True,
    'trades':         True, 
}

# ── Sessions ──────────────────────────────────────────────────

SESSIONS = {
    'A': {
        'name':         'New York',
        'enabled':      True,
        'start':        '14:00',    # heure locale (TIMEZONE)
        'end':          '00:00',    # heure locale (TIMEZONE)
        'color':        '#00BCD4',  # couleur bordure
        'fill_alpha':   0.12,       # transparence du fond (0.0 → 1.0)
    },
    'B': {
        'name':         'London',
        'enabled':      True,
        'start':        '09:00',
        'end':          '14:00',
        'color':        '#F44336',
        'fill_alpha':   0.12,
    },
    'C': {
        'name':         'Tokyo',
        'enabled':      True,
        'start':        '00:00',
        'end':          '09:00',
        'color':        '#CE93D8',
        'fill_alpha':   0.12,
    },
    'D': {
        'name':         'Sydney',
        'enabled':      False,
        'start':        '21:00',
        'end':          '06:00',
        'color':        '#FFEB3B',
        'fill_alpha':   0.12,
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