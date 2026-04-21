import pandas as pd

def calculer_trend_quality(
    df,
    session_lookback=6,
    use_decay=True,
    timezone="Europe/Zurich",
    weight_ny=50,
    weight_ldn=35,
    weight_tky=15,
    thresh_strong_bull=75,
    thresh_weak_bull=65,
    thresh_weak_bear=35,
    thresh_strong_bear=25
):
    if df.empty:
        return None

    # Création d'une copie avec le bon fuseau horaire
    df_local = df.copy()
    df_local['time_local'] = df_local['time'].dt.tz_convert(timezone)
    df_local['date'] = df_local['time_local'].dt.date
    df_local['hour'] = df_local['time_local'].dt.hour
    
    # Détection des sessions selon l'heure
    def get_session_name(h):
        if 0 <= h < 8: return 'TKY'
        elif 8 <= h < 14: return 'LDN'
        else: return 'NY'
        
    df_local['session'] = df_local['hour'].apply(get_session_name)
    
    # Grouper par Date et Session pour obtenir les Plus Hauts / Plus Bas par jour
    session_stats = df_local.groupby(['date', 'session']).agg({'High': 'max', 'Low': 'min'}).reset_index()
    
    # Extraction des X derniers jours pour chaque session (triés du plus ancien au plus récent)
    tky_stats = session_stats[session_stats['session'] == 'TKY'].sort_values('date').tail(session_lookback)
    ldn_stats = session_stats[session_stats['session'] == 'LDN'].sort_values('date').tail(session_lookback)
    ny_stats =  session_stats[session_stats['session'] == 'NY'].sort_values('date').tail(session_lookback)
    
    # Fonction de calcul du score interne
    def calc_score(df_sess):
        highs = df_sess['High'].tolist()
        lows = df_sess['Low'].tolist()
        sz = len(highs)
        if sz < 2: 
            return 50.0
        
        tot_weight = 0.0
        bull_pts = 0.0
        
        for i in range(1, sz):
            # Plus 'i' est grand (récent), plus le poids est fort si use_decay est True
            w = (i + 1) if use_decay else 1.0
            tot_weight += (w * 2)
            
            if highs[i] > highs[i-1]: bull_pts += w
            if lows[i] > lows[i-1]:   bull_pts += w
            
        return (bull_pts / tot_weight) * 100 if tot_weight > 0 else 50.0
        
    score_tky = calc_score(tky_stats)
    score_ldn = calc_score(ldn_stats)
    score_ny  = calc_score(ny_stats)
    
    # Normalisation des pondérations
    tot_w = weight_ny + weight_ldn + weight_tky
    wn = weight_ny / tot_w if tot_w else 0.333
    wl = weight_ldn / tot_w if tot_w else 0.333
    wt = weight_tky / tot_w if tot_w else 0.333
    
    trend_score = (score_ny * wn) + (score_ldn * wl) + (score_tky * wt)
    
    # Interprétation du score final
    if trend_score >= thresh_strong_bull:
        text = f"Forte Haussière ({trend_score:.1f}%)"
        color = "#4CAF50" # Vert TradingView
    elif trend_score > thresh_weak_bull:
        text = f"Légère Haussière ({trend_score:.1f}%)"
        color = "#81C784"
    elif trend_score <= thresh_strong_bear:
        text = f"Forte Baissière ({trend_score:.1f}%)"
        color = "#FF5252" # Rouge TradingView
    elif trend_score < thresh_weak_bear:
        text = f"Légère Baissière ({trend_score:.1f}%)"
        color = "#E57373"
    else:
        text = f"Consolidation ({trend_score:.1f}%)"
        color = "#9E9E9E"

    # On renvoie les infos pour le tableau de bord HTML
    return {
        "score": trend_score,
        "text": text,
        "color": color,
        "lookback": session_lookback
    }