import pandas as pd

def obtenir_info_session(heure):
    if 0 <= heure < 8:
        return 'Tokyo', 'rgba(206, 147, 216, 0.15)', 'rgba(206, 147, 216, 0.8)'
    elif 8 <= heure < 14:
        return 'London', 'rgba(244, 67, 54, 0.15)', 'rgba(244, 67, 54, 0.8)'
    else:
        return 'New York', 'rgba(0, 188, 212, 0.15)', 'rgba(0, 188, 212, 0.8)'

def calculer_sessions(df):
    blocs_sessions = []
    if df.empty:
        return blocs_sessions
        
    session_en_cours = None
    bloc_actuel = {}
    
    for index, row in df.iterrows():
        dt = row['time'] 
        nom_session, couleur_bg, couleur_border = obtenir_info_session(dt.hour)
        
        # CHANGEMENT CRUCIAL : On utilise le timestamp UNIX au lieu du texte
        temps_unix = int(dt.timestamp())
        
        if nom_session != session_en_cours:
            if session_en_cours is not None:
                blocs_sessions.append(bloc_actuel)
            
            session_en_cours = nom_session
            bloc_actuel = {
                'title': nom_session,
                'color_bg': couleur_bg,
                'color_border': couleur_border,
                'border_style': 'dashed',
                'start': temps_unix,
                'end': temps_unix,
                'max_p': row['High'],  # Majuscule (venant de notre loader)
                'min_p': row['Low']
            }
        else:
            bloc_actuel['end'] = temps_unix
            bloc_actuel['max_p'] = max(bloc_actuel['max_p'], row['High'])
            bloc_actuel['min_p'] = min(bloc_actuel['min_p'], row['Low'])
            
    if bloc_actuel:
        blocs_sessions.append(bloc_actuel)
        
    return blocs_sessions