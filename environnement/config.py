# config.py — Configuration partagée
# ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════
# ENVIRONNEMENT
# ══════════════════════════════════════════════════════════════

TIMEZONE = 'Europe/Zurich'

SYMBOL    = "EURUSD"
DATE_FROM = "2026-04-01"
DATE_TO   = "2026-04-28"
TIMEFRAME = "M30"
SOURCE    = "MT5"   # "MT5" | "HISTDATA" | "MASSIVE"



# ══════════════════════════════════════════════════════════════
# INDICATEURS
# ══════════════════════════════════════════════════════════════

# ── Sessions ──────────────────────────────────────────────────


# Indicateurs actifs
INDICATORS = {
    'sessions': True,
}


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
    'session_lookback': 6,
    'use_decay': True,
    'show_day_labels': False,
    'weights': {
        'New York': 50,
        'London': 35,
        'Tokyo': 15,
    },
    'thresholds': {
        'strong_bull': 75,
        'weak_bull': 65,
        'weak_bear': 35,
        'strong_bear': 25,
    },
}