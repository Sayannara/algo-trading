STRATEGY_CONFIG = {
    # ─────────────────────────────────────────────
    # FILTRE DE TENDANCE
    # ─────────────────────────────────────────────

    # Trend > 60 => setups Buy uniquement
    "trend_buy_threshold": 60,

    # Trend < 40 => setups Sell uniquement
    "trend_sell_threshold": 40,

    # Autorise ou non les trades en zone neutre
    "allow_neutral_trades": False,

    # ─────────────────────────────────────────────
    # CONDITIONS DE DÉTECTION
    # ─────────────────────────────────────────────

    # Historique minimum avant de lancer la stratégie
    "min_bars": 50,

    # Fenêtre HTF pour détecter le sweep de liquidité
    "htf_lookback": 20,

    # Taille minimale du corps de bougie pour valider l'impulsion LTF
    "ltf_impulse_threshold": 0.0003,

    # ─────────────────────────────────────────────
    # GESTION DU TRADE
    # ─────────────────────────────────────────────

    # Objectif en multiple du risque
    "rr": 2.0,

    # Buffer au-delà du niveau de liquidité pour placer le SL
    "buffer": 0.00015,

    # Heure limite de clôture forcée du trade (format HH:MM)
    "force_exit_time": "23:00",

    # Si True, en cas de TP et SL touchés sur la même bougie,
    # on considère le SL comme prioritaire (hypothèse prudente)
    "sl_priority_if_both_hit": True,

    # ─────────────────────────────────────────────
    # OUTILS
    # ─────────────────────────────────────────────

    "debug": False,
}