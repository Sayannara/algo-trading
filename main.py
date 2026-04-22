import os
import json
import webbrowser
import importlib

# --- VIDER LA CONSOLE À CHAQUE LANCEMENT ---
os.system('cls' if os.name == 'nt' else 'clear')

# ─────────────────────────────────────────────────────────────
# 🛠️ CONFIGURATION GLOBALE
# ─────────────────────────────────────────────────────────────

# Source de données : 'HISTDATA', 'MASSIVE' ou 'MT5'
SOURCE_DONNEES = 'MT5'

# ─────────────────────────────────────────────────────────────
# 🎯 STRATÉGIE ACTIVE
# Mettre None pour désactiver (mode graphique uniquement)
# ─────────────────────────────────────────────────────────────
STRATEGIE_ACTIVE = 'None'

REGISTRE_STRATEGIES = {
    'tokyo_liquidity':    'strategies.tokyo_liquidity_demo',
    'asian_htf_reversal': 'strategies.asian_htf_reversal',
    'bounce_ob':          'strategies.bounce_ob',
    'demo':               'strategies.demo',
}

# --- Paramètres HISTDATA ---
FICHIER_CSV = 'EURUSD-mars-2026.csv'

# --- Paramètres MASSIVE ---
MASSIVE_TICKER = "C:EURUSD"
MASSIVE_DEBUT  = "2026-01-15"
MASSIVE_FIN    = "2026-04-20"
MASSIVE_TF     = "minute"
MASSIVE_MULT   = 30

# --- Paramètres MT5 ---
MT5_SYMBOL = "EURUSD"
MT5_DEBUT  = "2025-06-15"
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

candles = [
    {
        'time':  int(row.time.timestamp()),
        'open':  float(row.Open),
        'high':  float(row.High),
        'low':   float(row.Low),
        'close': float(row.Close),
    }
    for row in df.itertuples(index=False)
]
donnees_javascript = json.dumps(candles, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────
# 2. EXÉCUTION DE LA STRATÉGIE (optionnel)
# ─────────────────────────────────────────────────────────────
strategy_trades = []

if STRATEGIE_ACTIVE is None:
    print("ℹ️  Mode graphique uniquement — aucune stratégie active.")

elif STRATEGIE_ACTIVE not in REGISTRE_STRATEGIES:
    print(f"⚠️  Stratégie '{STRATEGIE_ACTIVE}' introuvable dans le registre.")

else:
    module_path = REGISTRE_STRATEGIES[STRATEGIE_ACTIVE]
    print(f"🚀 Stratégie active : {STRATEGIE_ACTIVE} ({module_path})")
    try:
        module = importlib.import_module(module_path)
        strategy_trades = module.run(df)
        print(f"📊 Trades générés : {len(strategy_trades)}")
    except Exception as e:
        print(f"⚠️  Erreur Stratégie '{STRATEGIE_ACTIVE}' : {e}")
        strategy_trades = []

# Résumé console
if strategy_trades:
    total   = len(strategy_trades)
    longs   = sum(1 for t in strategy_trades if t.get("direction") == "long")
    shorts  = total - longs
    tp      = sum(1 for t in strategy_trades if t.get("exit_reason") == "TP")
    sl      = sum(1 for t in strategy_trades if t.get("exit_reason") == "SL")
    autres  = total - tp - sl
    winrate = round(tp / total * 100, 1)

    print("")
    print("─" * 43)
    print(f"  📊 RÉSUMÉ — {STRATEGIE_ACTIVE}")
    print("─" * 43)
    print(f"  Total trades  : {total}")
    print(f"  ↗  Longs      : {longs}")
    print(f"  ↘  Shorts     : {shorts}")
    print(f"  ✅ TP          : {tp}  ({round(tp/total*100,1)}%)")
    print(f"  ❌ SL          : {sl}  ({round(sl/total*100,1)}%)")
    print(f"  ⏱  Autres      : {autres}")
    print(f"  Winrate       : {winrate}%")
    print("─" * 43)
    print("")

strategy_javascript = json.dumps(strategy_trades, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────
# 3. GÉNÉRATION DE LA PAGE WEB
# ─────────────────────────────────────────────────────────────
print("📄 Lecture du template...")

with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
    html_content = f.read()

html_content = html_content.replace('{{donnees_javascript}}',  donnees_javascript)
html_content = html_content.replace('{{strategy_javascript}}', strategy_javascript)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Graphique prêt avec {len(df)} bougies ! ({HTML_FILE})")
webbrowser.open(f'file://{HTML_FILE}')