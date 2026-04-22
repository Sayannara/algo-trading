# ============================================================================
# BOUNCE_OB - CONFIGURATION
# ============================================================================
# Tous les paramètres modifiables de la stratégie sont centralisés ici
# pour éviter de toucher au coeur de la logique dans bounce_ob.py.
# ============================================================================

# Timeframe HTF utilisé pour détecter les order blocks.
# Ici on veut travailler en 30 minutes.
HTF_TIMEFRAME = "30min"

# Durée de vie maximale d'un OB, en heures.
# Exemple: 24 * 7 = 7 jours.
# Pendant cette période, l'OB reste affichable / tradable.
OB_EXTENSION_HOURS = 24 * 7

# Taille minimale du gap associé à l'OB, en pips.
# Seuls les OB avec un gap suffisamment important seront retenus.
MIN_GAP_PIPS = 8.0

# Taille minimale du corps de la bougie OB, en pips.
# Permet d'éviter de retenir des bougies trop petites ou insignifiantes.
MIN_OB_BODY_PIPS = 4.0

# Délai minimum entre la création de l'OB et le premier retest, en heures.
# Exemple: 24 = le premier retest ne sera pris en compte qu'au moins 1 jour plus tard.
FIRST_RETEST_DELAY_HOURS = 24

# Délai minimum entre le premier retest rejeté et le retest d'entrée, en heures.
# Exemple: 24 = après un premier rejet valide, on attend au moins encore 1 jour
# avant d'autoriser une entrée sur le retour suivant.
ENTRY_RETEST_DELAY_HOURS = 24

# Distance minimale de clôture en dehors de l'OB pour considérer
# qu'il y a bien eu un rejet, en pips.
# Plus cette valeur est grande, plus le rejet demandé est fort.
REJECTION_CLOSE_BUFFER_PIPS = 2.0

# Buffer ajouté au stop loss au-dessus / au-dessous de l'OB, en pips.
# Permet d'éviter un SL exactement posé sur la borne de la zone.
SL_BUFFER_PIPS = 1.5

# Début de la session de Tokyo (heure locale du dataset / système utilisé).
TOKYO_START_HOUR = 0

# Fin de la session de Tokyo.
# Exemple: 9 = session de 00:00 à 09:00.
TOKYO_END_HOUR = 9

# Taille d'un pip pour l'instrument.
# 0.0001 convient pour la plupart des paires Forex classiques.
# A adapter si tu testes des actifs avec une autre convention.
PIP_SIZE = 0.0001

# Si True, la stratégie interdit plusieurs trades simultanés.
# Un nouveau trade ne pourra être pris qu'après la clôture du précédent.
ALLOW_ONLY_ONE_TRADE_AT_A_TIME = True