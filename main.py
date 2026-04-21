import os
import json
import webbrowser
import importlib
from strategies.asian_htf_reversal import run_strategy
strategy_trades = run_strategy(df)

# --- VIDER LA CONSOLE À CHAQUE LANCEMENT ---
os.system('cls' if os.name == 'nt' else 'clear')

# ─────────────────────────────────────────────────────────────
# 🛠️ CONFIGURATION GLOBALE
# ─────────────────────────────────────────────────────────────

# Source de données : 'HISTDATA', 'MASSIVE' ou 'MT5'
SOURCE_DONNEES = 'MT5'

# Stratégie active : clé du registre ci-dessous, ou None pour désactiver
STRATEGIE_ACTIVE = 'tokyo_liquidity'

# Registre des stratégies disponibles
# Ajouter ici chaque nouvelle stratégie sans toucher au reste du fichier
REGISTRE_STRATEGIES = {
    'tokyo_liquidity': 'strategies.tokyo_liquidity_demo',
    # 'london_breakout': 'strategies.london_breakout',
    # 'ny_open':         'strategies.ny_open',
}

# --- Paramètres pour HISTDATA (Fichier Local) ---
FICHIER_CSV = 'EURUSD-mars-2026.csv'

# --- Paramètres pour MASSIVE (API en direct) ---
MASSIVE_TICKER = "C:EURUSD"
MASSIVE_DEBUT  = "2026-01-15"
MASSIVE_FIN    = "2026-04-20"
MASSIVE_TF     = "minute"
MASSIVE_MULT   = 30

# --- Paramètres pour MT5 ---
MT5_SYMBOL = "EURUSD"
MT5_DEBUT  = "2026-01-15"
MT5_FIN    = "2026-04-21"
MT5_TF     = "M5"

# ─────────────────────────────────────────────────────────────
# CONFIGURATION DES CHEMINS SYSTÈMES
# ─────────────────────────────────────────────────────────────
DOSSIER_RACINE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE  = os.path.join(DOSSIER_RACINE, 'templates', 'chart_execution_template.html')
HTML_FILE      = os.path.join(DOSSIER_RACINE, 'output.html')

# ─────────────────────────────────────────────────────────────
# 1. RÉCUPÉRATION DES DONNÉES
# ─────────────────────────────────────────────────────────────
df = None

if SOURCE_DONNEES == 'HISTDATA':
    print("📡 SOURCE SÉLECTIONNÉE : HISTDATA (Fichier local)")
    from loaders.histdata import charger_donnees
    chemin_csv = os.path.join(DOSSIER_RACINE, 'data', FICHIER_CSV)
    df = charger_donnees(chemin_csv)

elif SOURCE_DONNEES == 'MASSIVE':
    print("📡 SOURCE SÉLECTIONNÉE : MASSIVE (API en direct)")
    from loaders.massive import charger_donnees
    df = charger_donnees(
        ticker=MASSIVE_TICKER,
        date_from=MASSIVE_DEBUT,
        date_to=MASSIVE_FIN,
        multiplier=MASSIVE_MULT,
        timespan=MASSIVE_TF
    )

elif SOURCE_DONNEES == 'MT5':
    print("📡 SOURCE SÉLECTIONNÉE : MT5")
    from loaders.mt5 import charger_donnees
    df = charger_donnees(
        symbol=MT5_SYMBOL,
        date_from=MT5_DEBUT,
        date_to=MT5_FIN,
        timeframe=MT5_TF
    )

else:
    print(f"❌ Source inconnue : {SOURCE_DONNEES}")
    exit()

if df is None or df.empty:
    print("❌ Aucune donnée récupérée. Arrêt.")
    exit()

# Formatage des bougies pour Javascript
candles = []
for row in df.itertuples(index=False):
    candles.append({
        'time':  int(row.time.timestamp()),
        'open':  float(row.Open),
        'high':  float(row.High),
        'low':   float(row.Low),
        'close': float(row.Close),
    })

donnees_javascript = json.dumps(candles, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────
# 2. CALCUL DES INDICATEURS
# ─────────────────────────────────────────────────────────────
print("⚙️  Calcul des indicateurs...")

# Sessions
try:
    from indicators.sessions_market import calculer_sessions
    sessions = calculer_sessions(df)
except Exception as e:
    print(f"⚠️ Erreur Sessions : {e}")
    sessions = []

sessions_javascript = json.dumps(sessions, ensure_ascii=False)

# Order Blocks
try:
    from indicators.order_blocks import calculer_order_blocks
    order_blocks = calculer_order_blocks(df, min_gap_pips=2.0, extension_bougies=30)
except Exception as e:
    print(f"⚠️ Erreur Order Blocks : {e}")
    order_blocks = []

ob_javascript = json.dumps(order_blocks, ensure_ascii=False)

# Trend Quality
try:
    from indicators.trend_quality import calculer_trend_quality
    trend_data = calculer_trend_quality(df)
    trend_javascript = json.dumps(trend_data, ensure_ascii=False) if trend_data else "null"
except Exception as e:
    print(f"⚠️ Erreur Trend Quality : {e}")
    trend_javascript = "null"

# ─────────────────────────────────────────────────────────────
# 3. EXÉCUTION DE LA STRATÉGIE (optionnel)
# ─────────────────────────────────────────────────────────────
strategy_trades = []

if STRATEGIE_ACTIVE is None:
    print("ℹ️  Aucune stratégie active (mode indicateurs uniquement).")

elif STRATEGIE_ACTIVE not in REGISTRE_STRATEGIES:
    print(f"⚠️  Stratégie '{STRATEGIE_ACTIVE}' introuvable dans le registre. Ignorée.")

else:
    module_path = REGISTRE_STRATEGIES[STRATEGIE_ACTIVE]
    print(f"🚀 Stratégie active : {STRATEGIE_ACTIVE} ({module_path})")
    try:
        module = importlib.import_module(module_path)
        strategy_trades = module.generer_strategie_tokyo_liquidity(df)
        print(f"📊 Trades générés : {len(strategy_trades)}")
    except Exception as e:
        print(f"⚠️  Erreur Stratégie '{STRATEGIE_ACTIVE}' : {e}")
        strategy_trades = []

strategy_javascript = json.dumps(strategy_trades, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────
# 4. GÉNÉRATION DE LA PAGE WEB
# ─────────────────────────────────────────────────────────────
print("📄 Lecture du template...")

with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
    html_content = f.read()

html_content = html_content.replace('{{donnees_javascript}}',   donnees_javascript)
html_content = html_content.replace('{{sessions_javascript}}',  sessions_javascript)
html_content = html_content.replace('{{ob_javascript}}',        ob_javascript)
html_content = html_content.replace('{{trend_javascript}}',     trend_javascript)
html_content = html_content.replace('{{strategy_javascript}}',  strategy_javascript)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Graphique prêt avec {len(df)} bougies ! ({HTML_FILE})")
webbrowser.open(f'file://{HTML_FILE}')