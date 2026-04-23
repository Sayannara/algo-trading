from datetime import datetime
import MetaTrader5 as mt5

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M30

DATE_START = datetime(2026, 1, 1)
DATE_END = datetime(2026, 4, 23)

# FVG – paramètres de filtrage
TYPE_MESURE = "Ticks"  # "Ticks", "Pourcentage (%)", "ATR"
MIN_VALEUR_FOREX = 200.0
MIN_VALEUR_AUTRES = 1500.0

# News
FUSEAU_HORAIRE = "Europe/Zurich"
HEURES_NEWS_INPUT = "13:30-14:00/16:00-16:30"
MODE_AFFICHAGE = "Tout afficher (Marquer les News)"  # "Tout SANS les News" / "N'afficher QUE les News"

# Extensions visuelles
EXTEND_BOX_BARS = 1      # extension horizontale des FVG (en nombre de barres)
FALLBACK_MIN_TICK = 0.00001

# OB ICT
OB_LOOKBACK = 5          # nombre de bougies max à remonter pour trouver l’OB
MIN_OB_BODY = 0.00005    # taille min du corps de l’OB
OB_EXTEND_DAYS = 4       # durée des OB en jours

# Trend quality (tu pourras les exposer plus tard si besoin)
TREND_TIMEZONE = "Europe/Zurich"
TREND_SESSION_LOOKBACK = 6