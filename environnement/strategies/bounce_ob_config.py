# Configuration pour la stratégie Bounce OB

CONFIG = {
    # Pénétration dans l'OB pour l'entrée (0.0 à 1.0)
    # 0.0 = Entrée immédiate dès qu'on touche l'OB (bord interne)
    # 0.5 = Entrée au milieu de l'OB (50%)
    # 1.0 = Entrée tout au fond de l'OB (bord externe, tout en haut pour un baissier)
    "entry_level": 1.0,
    
    # Marge pour le Stop Loss au-delà de l'OB (en ticks/pips selon l'actif)
    # Par défaut, 0.01 pour une paire JPY (1 tick = 0.01)
    "sl_margin_ticks": 200.0, 
    
    # Ratio Risk/Reward pour le Take Profit
    "tp_rr": 3.0,
    
    # Ratio Risk/Reward pour sécuriser à Break-Even (BE)
    "be_rr_trigger": 1.0,
}
