import requests
import pandas as pd

# --- CLÉ API MASSIVE EN DUR POUR LES TESTS ---
CLE_API_MASSIVE = "CMLSLaQhzseyp7dt7jDA8J6AAAePSH7T"

# Massive utilise l'architecture Polygon.io pour la data
BASE_URL = "https://api.polygon.io" 

def charger_donnees(
    ticker="C:EURUSD",
    date_from="2026-03-15",
    date_to="2026-03-28",
    multiplier=5,      
    timespan="minute", 
    limit=50000
):
    """
    Charge des bougies OHLC directement depuis l'API REST de Massive/Polygon.
    """
    print(f"📥 Téléchargement API : {ticker} ({multiplier} {timespan}) du {date_from} au {date_to}...")

    # Construction de l'URL d'agrégation V2
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{date_from}/{date_to}"

    # Paramètres de la requête GET
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": limit,
        "apiKey": CLE_API_MASSIVE
    }

    all_results = []

    # Boucle de pagination (si la requête dépasse la limite de 50 000 bougies)
    while url:
        # Si 'apiKey' est déjà dans l'URL (cas du next_url), on ne repasse pas l'objet params
        response = requests.get(url, params=params if "apiKey=" not in url else None, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erreur API ({response.status_code}): {response.text}")
            return pd.DataFrame()

        data = response.json()
        results = data.get("results", [])
        all_results.extend(results)

        # Vérification s'il y a une page suivante
        next_url = data.get("next_url")
        if next_url:
            # Assure que la clé API reste attachée à l'URL suivante
            if "apiKey=" not in next_url:
                sep = "&" if "?" in next_url else "?"
                next_url = f"{next_url}{sep}apiKey={CLE_API_MASSIVE}"
        
        url = next_url
        params = None # Pour les boucles suivantes, les paramètres sont dans next_url

    if not all_results:
        print("⚠️ Aucune donnée renvoyée par l'API pour cette période.")
        return pd.DataFrame()

    # --- FORMATAGE POUR LE GRAPHique ---
    df = pd.DataFrame(all_results)

    # Renommage des colonnes (o=open, h=high, l=low, c=close, t=time, v=volume)
    df = df.rename(columns={
        "t": "time_ms",
        "o": "Open",
        "h": "High",
        "l": "Low",
        "c": "Close",
        "v": "Volume"
    })

    # Conversion du temps (Millisecondes Unix -> Datetime UTC)
    df["time"] = pd.to_datetime(df["time_ms"], unit="ms", utc=True)

    # Sécurisation des valeurs numériques
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Nettoyage (suppression des bougies incomplètes) et tri chronologique
    df = df.dropna(subset=["time", "Open", "High", "Low", "Close"]).copy()
    df = df.sort_values("time").drop_duplicates(subset=["time"]).reset_index(drop=True)

    print(f"✅ {len(df)} bougies téléchargées depuis Massive avec succès.")
    return df