import pandas as pd

def charger_donnees(chemin_csv):
    """
    Charge et standardise un fichier CSV provenant de HistData.
    Format attendu : YYYYMMDD HHMMSS;Open;High;Low;Close;Volume
    """
    print(f"📥 Lecture des données depuis : {chemin_csv}")
    
    # 1) Lire le CSV local (séparateur point-virgule, sans en-tête)
    df = pd.read_csv(
        chemin_csv, 
        sep=';', 
        header=None, 
        names=['datetime', 'Open', 'High', 'Low', 'Close', 'Volume'],
        encoding='utf-8-sig'
    )

    # 2) Parse direct du format exact (ex: "20260301 170000")
    df['time'] = pd.to_datetime(
        df['datetime'].astype(str).str.strip(),
        format='%Y%m%d %H%M%S',
        errors='coerce'
    )

    # Force l'UTC pour que le graphique s'affiche correctement
    df['time'] = df['time'].dt.tz_localize('UTC')

    # Sécurisation des prix
    for col in ['Open', 'High', 'Low', 'Close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3) Nettoyage minimal strict
    df = df.dropna(subset=['time', 'Open', 'High', 'Low', 'Close']).copy()
    df = df.sort_values('time').drop_duplicates(subset=['time']).reset_index(drop=True)
    
    print(f"✅ {len(df)} bougies validées.")
    return df