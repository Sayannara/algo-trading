import os
import json
import webbrowser
from strategies.asian_htf_reversal import run_strategy

# --- VIDER LA CONSOLE À CHAQUE LANCEMENT ---
os.system('cls' if os.name == 'nt' else 'clear')

# ─────────────────────────────────────────────────────────────
# 🛠️ CONFIGURATION GLOBALE
# ─────────────────────────────────────────────────────────────

# Choisissez votre source de données parmi : 'HISTDATA', 'MASSIVE' ou 'MT5'
SOURCE_DONNEES = 'MT5'

# --- Paramètres pour HISTDATA (Fichier Local) ---
FICHIER_CSV = 'EURUSD-mars-2026.csv'

# --- Paramètres pour MASSIVE (API en direct) ---
MASSIVE_TICKER = "C:EURUSD"
MASSIVE_DEBUT = "2026-01-15"
MASSIVE_FIN = "2026-04-20"
MASSIVE_TF = "minute"
MASSIVE_MULT = 30

# --- Paramètres pour MT5 ---
MT5_SYMBOL = "EURUSD"
MT5_DEBUT = "2025-06-15"
MT5_FIN = "2026-04-21"
MT5_TF = "M5"

# ─────────────────────────────────────────────────────────────
# CONFIGURATION DES CHEMINS SYSTÈMES
# ─────────────────────────────────────────────────────────────
DOSSIER_RACINE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(DOSSIER_RACINE, 'templates', 'chart_execution_template.html')
HTML_FILE = os.path.join(DOSSIER_RACINE, 'output.html')

# ─────────────────────────────────────────────────────────────
# 1. RÉCUPÉRATION DES DONNÉES (Routage dynamique)
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
    print(f"❌ Source {SOURCE_DONNEES} inconnue.")
    exit()

# Vérification de sécurité
if df is None or df.empty:
    print("❌ Aucune donnée n'a été récupérée. Arrêt du script.")
    exit()

# Formatage des bougies pour Javascript
candles = []
for row in df.itertuples(index=False):
    candles.append({
        'time': int(row.time.timestamp()),
        'open': float(row.Open),
        'high': float(row.High),
        'low': float(row.Low),
        'close': float(row.Close),
    })

donnees_javascript = json.dumps(candles, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────
# 2. CALCUL DES INDICATEURS
# ─────────────────────────────────────────────────────────────
print("⚙️ Calcul des indicateurs...")

# 1. Sessions
try:
    from indicators.sessions_market import calculer_sessions
    sessions = calculer_sessions(df)
except Exception as e:
    print(f"⚠️ Erreur Sessions : {e}")
    sessions = []

sessions_javascript = json.dumps(sessions, ensure_ascii=False)

# 2. Order Blocks
try:
    from indicators.order_blocks import calculer_order_blocks
    order_blocks = calculer_order_blocks(df, min_gap_pips=2.0, extension_bougies=30)
except Exception as e:
    print(f"⚠️ Erreur Order Blocks : {e}")
    order_blocks = []

ob_javascript = json.dumps(order_blocks, ensure_ascii=False)

# 3. Trend Quality
try:
    from indicators.trend_quality import calculer_trend_quality
    trend_data = calculer_trend_quality(df)

    if trend_data is None:
        trend_javascript = "null"
    else:
        trend_javascript = json.dumps(trend_data, ensure_ascii=False)

except Exception as e:
    print(f"⚠️ Erreur Trend Quality : {e}")
    trend_data = None
    trend_javascript = "null"

# 4. Stratégie Asian HTF Reversal
try:
    strategy_trades = run_strategy(df, trend_data)
except Exception as e:
    print(f"⚠️ Erreur Stratégie Asian HTF Reversal : {e}")
    strategy_trades = []

# ─────────────────────────────────────────────────────────────
# RAPPORT CONSOLE UNIQUEMENT
# ─────────────────────────────────────────────────────────────
total_trades = len(strategy_trades)

longs = sum(1 for t in strategy_trades if t.get("type") == "long")
shorts = sum(1 for t in strategy_trades if t.get("type") == "short")

tp_count = sum(1 for t in strategy_trades if t.get("exit_reason") == "TP")
sl_count = sum(1 for t in strategy_trades if t.get("exit_reason") == "SL")
end_2300_count = sum(1 for t in strategy_trades if t.get("exit_reason") == "23:00")
data_end_count = sum(1 for t in strategy_trades if t.get("exit_reason") == "data_end")

def pct(count, total):
    return (count / total * 100) if total > 0 else 0.0

winrate = pct(tp_count, total_trades)

print("\n📊 RÉSUMÉ — Asian HTF Reversal")
print("─────────────────────────────────────────")
print(f"Total trades    : {total_trades}")
print(f"  ↗  Longs     : {longs}")
print(f"  ↘  Shorts    : {shorts}")
print("")
print("Sorties")
print(f"  ✅  TP        : {tp_count}  ({pct(tp_count, total_trades):.1f}%)")
print(f"  ❌  SL        : {sl_count}  ({pct(sl_count, total_trades):.1f}%)")
print(f"  🕒  23:00     : {end_2300_count}   ({pct(end_2300_count, total_trades):.1f}%)")
print(f"  📉  data_end  : {data_end_count}   ({pct(data_end_count, total_trades):.1f}%)")
print("")
print(f"Winrate         : {winrate:.1f}%")

strategy_javascript = json.dumps(strategy_trades, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────
# 3. GÉNÉRATION DE LA PAGE WEB
# ─────────────────────────────────────────────────────────────
print("📄 Lecture du template...")

with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Injection Javascript
html_content = html_content.replace('{{donnees_javascript}}', donnees_javascript)
html_content = html_content.replace('{{sessions_javascript}}', sessions_javascript)
html_content = html_content.replace('{{ob_javascript}}', ob_javascript)
html_content = html_content.replace('{{trend_javascript}}', trend_javascript)
html_content = html_content.replace('{{strategy_javascript}}', strategy_javascript)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Graphique prêt avec {len(df)} bougies ! ({HTML_FILE})")
webbrowser.open(f'file://{HTML_FILE}')