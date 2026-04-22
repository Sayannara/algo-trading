STRATEGY_CONFIG = {
    # ─────────────────────────────────────────────
    # FILTRE DE TENDANCE
    # ─────────────────────────────────────────────
    "trend_buy_threshold": 60,
    "trend_sell_threshold": 40,
    "allow_neutral_trades": False,

    # ─────────────────────────────────────────────
    # CONDITIONS DE DÉTECTION
    # ─────────────────────────────────────────────
    "min_bars": 50,
    "ltf_impulse_threshold": 0.0003,

    # Session Tokyo précédente à utiliser comme référence de liquidité
    "tokyo_start_hour": 0,
    "tokyo_end_hour": 9,

    # Fenêtre autorisée pour chercher un setup
    "trading_start_hour": 14,
    "trading_end_hour": 18,

    # ─────────────────────────────────────────────
    # GESTION DU TRADE
    # ─────────────────────────────────────────────
    "rr": 2.0,
    "buffer": 0.00015,
    "force_exit_time": "23:00",
    "sl_priority_if_both_hit": True,

    # ─────────────────────────────────────────────
    # OUTILS
    # ─────────────────────────────────────────────
    "debug": False,
}