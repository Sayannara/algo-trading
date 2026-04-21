import pandas as pd

def obtenir_info_session(heure):
    """
    Définit le nom, la couleur de fond et la couleur de bordure des sessions.
    Fond léger (0.1) et couleurs bien distinctes (Violet, Orange, Bleu).
    Pas de bordure ('transparent').
    """
    if 0 <= heure < 8:
        return 'Tokyo', 'rgba(156, 39, 176, 0.1)', 'transparent'    # Violet
    elif 8 <= heure < 14:
        return 'London', 'rgba(255, 87, 34, 0.1)', 'transparent'    # Orange
    else:
        return 'New York', 'rgba(33, 150, 243, 0.1)', 'transparent' # Bleu

def calculer_sessions(df):
    blocs_sessions = []
    if df.empty:
        return blocs_sessions
        
    session_en_cours = None
    bloc_actuel = {}
    
    for index, row in df.iterrows():
        dt = row['time'] 
        nom_session, couleur_bg, couleur_border = obtenir_info_session(dt.hour)
        
        temps_unix = int(dt.timestamp())
        
        if nom_session != session_en_cours:
            if session_en_cours is not None:
                blocs_sessions.append(bloc_actuel)
            
            session_en_cours = nom_session
            bloc_actuel = {
                'title': nom_session,
                'color_bg': couleur_bg,
                'color_border': couleur_border,
                'border_style': 'solid', 
                'start': temps_unix,
                'end': temps_unix,
                'max_p': row['High'],
                'min_p': row['Low']
            }
        else:
            bloc_actuel['end'] = temps_unix
            bloc_actuel['max_p'] = max(bloc_actuel['max_p'], row['High'])
            bloc_actuel['min_p'] = min(bloc_actuel['min_p'], row['Low'])
            
    if bloc_actuel:
        blocs_sessions.append(bloc_actuel)
        
    return blocs_sessions