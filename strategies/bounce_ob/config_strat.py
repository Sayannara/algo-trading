# =========================
# Paramètres stratégie
# =========================

# Timezone de référence
TRADING_TIMEZONE = "Europe/Zurich"

# Heures de trading autorisées pour chercher les sweeps
TRADING_START_HOUR = 8   # inclus
TRADING_END_HOUR = 18    # exclus

# Définition de la session Tokyo
TOKYO_START_HOUR = 0     # inclus
TOKYO_END_HOUR = 8       # exclus

# Seuils de trend quality
TREND_LONG_MIN = 60.0    # score > 60 -> BUY si sweep du bas
TREND_SHORT_MAX = 40.0   # score < 40 -> SELL si sweep du haut

# Limitation du nombre de signaux
ONE_SIGNAL_PER_DAY = True