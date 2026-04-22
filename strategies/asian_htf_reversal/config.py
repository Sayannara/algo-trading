STRATEGY_CONFIG = {
    # Seuil minimum de quality trend pour autoriser uniquement des setups acheteurs.
    # Si la valeur du trend est strictement supérieure à ce seuil, la stratégie cherche des longs.
    "trend_buy_threshold": 60,

    # Seuil maximum de quality trend pour autoriser uniquement des setups vendeurs.
    # Si la valeur du trend est strictement inférieure à ce seuil, la stratégie cherche des shorts.
    "trend_sell_threshold": 40,

    # Nombre minimum de bougies requis avant d'autoriser l'analyse de la stratégie.
    # Sert à éviter de travailler sur un historique trop court.
    "min_bars": 50,

    # Nombre de bougies utilisées pour définir le contexte HTF récent
    # et calculer les niveaux de liquidité à surveiller.
    "htf_lookback": 20,

    # Taille minimale du corps de bougie pour considérer qu'il y a une impulsion LTF valide.
    # Valeur exprimée en prix brut, donc à adapter selon l'instrument.
    "ltf_impulse_threshold": 0.0003,

    # Risk/Reward cible utilisé pour calculer le take profit à partir du risque initial.
    # Exemple : 2.0 signifie un objectif à 2R.
    "rr": 2.0,

    # Marge de sécurité ajoutée au-dessus ou au-dessous du niveau de liquidité
    # pour placer le stop loss un peu au-delà du sweep.
    "buffer": 0.00015,

    # Si True, la stratégie peut quand même chercher des trades lorsque le trend
    # est entre les deux seuils. Si False, aucun trade n'est pris en zone neutre.
    "allow_neutral_trades": False,

    # Active les logs de debug internes de la stratégie si tu en ajoutes plus tard.
    # À laisser sur False en usage normal.
    "debug": False,
}