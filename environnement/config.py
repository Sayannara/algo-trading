# config.py — Configuration partagée
# ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════
# ENVIRONNEMENT
# ══════════════════════════════════════════════════════════════

SYMBOL    = "EURUSD"
DATE_FROM = "2026-04-01"
DATE_TO   = "2026-04-28"
TIMEFRAME = "M30"

SOURCE    = "MT5"   # "MT5" | "HISTDATA" | "MASSIVE"

# Indicateurs à charger (True = actif)
INDICATORS = {
    'sessions': True,
}


# ══════════════════════════════════════════════════════════════
# INDICATEURS
# ══════════════════════════════════════════════════════════════

# ── Sessions ──────────────────────────────────────────────────
TIMEZONE = 'Europe/Zurich'

SESSIONS = {
    'A': { 'name': 'New York', 'enabled': True,  'start': '14:00', 'end': '00:00', 'color': '#00BCD4' },
    'B': { 'name': 'London',   'enabled': True,  'start': '09:00', 'end': '14:00', 'color': '#F44336' },
    'C': { 'name': 'Tokyo',    'enabled': True,  'start': '00:00', 'end': '09:00', 'color': '#CE93D8' },
    'D': { 'name': 'Sydney',   'enabled': False, 'start': '21:00', 'end': '06:00', 'color': '#FFEB3B' },
}