import os
import strategies.bounce_ob_config as bounce_config
from datetime import datetime
import pytz

# Session précédant l'entrée pour chaque session active
PREV_SESSION_MAP = {
    "London":   "Tokyo",
    "New York": "London",
    "Tokyo":    "New York",
}

def execute(df, candles, ob_fvg_data, tq_history, config, ctx=None):
    cfg        = bounce_config.CONFIG
    tp_rr      = cfg.get("tp_rr", 3.0)
    be_rr      = cfg.get("be_rr_trigger", 1.0)
    mintick    = config.OB_DETECTION.get("fvg_mintick", 0.01) if hasattr(config, "OB_DETECTION") else 0.01
    sl_margin  = cfg.get("sl_margin_ticks", 2.0) * mintick
    entry_level= cfg.get("entry_level", 0.5)

    markers, trade_boxes, trades_log = [], [], []
    stats = {"total":0,"win":0,"loss":0,"be":0,
             "long_total":0,"long_win":0,"long_loss":0,"long_be":0,
             "short_total":0,"short_win":0,"short_loss":0,"short_be":0,"pnl_rr":0.0}

    sessions_conf    = getattr(config, 'SESSIONS', {})
    tz = pytz.timezone(config.TIMEZONE)

    # ── Construction de l'historique de sessions en temps réel ──
    # On scanne toutes les bougies une fois pour construire un historique complet
    # de chaque session (high/low + ts_end) au fil du temps.
    from datetime import time as dtime

    def ts_to_local_time(ts):
        """Convertit un chart_ts (déjà décalé en local) vers un objet time local."""
        try:
            return datetime.utcfromtimestamp(ts).time()
        except:
            return None

    def session_name_at(ts):
        """Retourne le nom de la session active pour un chart_ts donné."""
        t = ts_to_local_time(ts)
        if not t: return "Hors session"
        for key, ses in sessions_conf.items():
            if not ses.get("enabled"): continue
            h0,m0 = map(int, ses["start"].split(":"))
            h1,m1 = map(int, ses["end"].split(":"))
            s, e = dtime(h0,m0), dtime(h1,m1)
            if e == dtime(0,0): ins = t >= s
            elif s < e:         ins = s <= t < e
            else:               ins = t >= s or t < e
            if ins: return ses["name"]
        return "Hors session"

    # Construire live_session_history : dict[ts] -> dict[session_name] -> {high, low, time_end}
    # (la session précédente COMPLÈTE juste avant chaque timestamp)
    live_prev_session: dict = {}   # session_name -> {'high', 'low', 'time_end'}
    current_session_data: dict = {}  # session_name -> {'high', 'low', 'time_end'}
    prev_session_name = None
    snapshot_by_ts: dict = {}  # chart_ts -> copy of live_prev_session at that point

    for ci, c in enumerate(candles):
        ts = c['time']
        cur_ses = session_name_at(ts)
        lo = df['Low'].iloc[ci]
        hi = df['High'].iloc[ci]

        # Détection changement de session
        if cur_ses != prev_session_name:
            # Fermer la session précédente si elle existe
            if prev_session_name and prev_session_name in current_session_data:
                live_prev_session[prev_session_name] = current_session_data[prev_session_name].copy()
                live_prev_session[prev_session_name]['time_end'] = ts - 1  # just before
            # Ouvrir nouvelle session
            if cur_ses != "Hors session":
                current_session_data[cur_ses] = {'high': hi, 'low': lo, 'time_end': ts}
            prev_session_name = cur_ses
        else:
            if cur_ses != "Hors session" and cur_ses in current_session_data:
                current_session_data[cur_ses]['high'] = max(current_session_data[cur_ses]['high'], hi)
                current_session_data[cur_ses]['low']  = min(current_session_data[cur_ses]['low'],  lo)
                current_session_data[cur_ses]['time_end'] = ts

        snapshot_by_ts[ts] = {k: v.copy() for k, v in live_prev_session.items()}

    # ── helpers ─────────────────────────────────────────────────

    def get_tq_at(ts):
        score = 50.0
        for e in tq_history:
            if e['time'] <= ts: score = e['score']
            else: break
        return score

    def ts_to_dt(ts):
        try: return datetime.utcfromtimestamp(ts)
        except: return None

    def session_at(ts):
        return session_name_at(ts)

    def get_prev_session_range(entry_ts, session_name):
        """Retourne (high, low) de la session précédente à l'instant entry_ts."""
        prev_name = PREV_SESSION_MAP.get(session_name)
        if not prev_name: return None, None
        # Chercher le snapshot le plus proche avant ou égal à entry_ts
        snap = snapshot_by_ts.get(entry_ts)
        if snap is None:
            # Trouver le ts le plus proche
            candidates_ts = [t for t in snapshot_by_ts if t <= entry_ts]
            if not candidates_ts: return None, None
            snap = snapshot_by_ts[max(candidates_ts)]
        prev = snap.get(prev_name)
        if not prev: return None, None
        return prev['high'], prev['low']

    def check_liquidity(entry_ts, is_long, session_name):
        prev_high, prev_low = get_prev_session_range(entry_ts, session_name)
        if prev_high is None:
            return False, False, PREV_SESSION_MAP.get(session_name,"?"), None, None

        window_candles = []
        for j in range(len(candles)-1, -1, -1):
            c_time = candles[j]['time']
            if c_time > entry_ts:
                continue
            if session_at(c_time) != session_name:
                break  # On sort de la session en cours
            window_candles.append(j)

        if not window_candles:
            return False, False, PREV_SESSION_MAP.get(session_name,"?"), prev_high, prev_low

        lows  = [df['Low'].iloc[j]  for j in window_candles]
        highs = [df['High'].iloc[j] for j in window_candles]
        min_l, max_h = min(lows), max(highs)

        if is_long:
            liq_in  = min_l < prev_low   # prix sous le low → liquidity sweep vers le bas
            liq_inv = max_h > prev_high  # prix au-dessus du high → sens inverse
        else:
            liq_in  = max_h > prev_high  # prix au-dessus high → sweep Short
            liq_inv = min_l < prev_low   # prix sous le low → sens inverse

        return liq_in, liq_inv, PREV_SESSION_MAP.get(session_name,"?"), prev_high, prev_low

    def fvg_new_extreme(fvg, all_data):
        dir_ = fvg['direction']
        fvg_start = fvg.get('start_time', 0)
        prev = [f['fvg'] for f in all_data
                if f.get('fvg',{}).get('direction')==dir_
                and f['fvg'].get('end_time',0) < fvg_start]
        if not prev: return True, "Premier FVG"
        last = sorted(prev, key=lambda x: x.get('end_time',0))[-1]
        if dir_=='bearish':
            ok = fvg['bot'] < last['bot']
            return ok, f"Bot {fvg['bot']:.3f} vs préc. {last['bot']:.3f}"
        else:
            ok = fvg['top'] > last['top']
            return ok, f"Top {fvg['top']:.3f} vs préc. {last['top']:.3f}"

    def ob_reuse_count(ob, candles, df):
        top,bot = ob['top'],ob['bot']
        ob_s, ob_e = ob.get('start_time',0), ob.get('end_time',0)
        touches, in_ob = 0, False
        for j,c in enumerate(candles):
            if c['time']<=ob_s or c['time']>ob_e: continue
            if df['Low'].iloc[j]<=top and df['High'].iloc[j]>=bot:
                if not in_ob: touches+=1; in_ob=True
            else: in_ob=False
        return max(0, touches-1)

    def competing_obs(entry_price, tp_price, is_long, all_data, cur_ob):
        out=[]
        for item in all_data:
            ob2=item.get('ob'); fvg2=item.get('fvg',{})
            if not ob2 or ob2 is cur_ob: continue
            d2=fvg2.get('direction','')
            if is_long and d2=='bearish' and entry_price < ob2['bot'] < tp_price:
                out.append(f"OB Baissier {ob2['bot']:.3f}–{ob2['top']:.3f}")
            elif not is_long and d2=='bullish' and tp_price < ob2['top'] < entry_price:
                out.append(f"OB Haussier {ob2['bot']:.3f}–{ob2['top']:.3f}")
        return out

    # ── boucle principale ────────────────────────────────────────

    for item in ob_fvg_data:
        ob = item.get('ob'); fvg = item.get('fvg')
        if not ob or not fvg: continue

        direction = fvg['direction']
        is_long   = direction == 'bullish'
        ob_top, ob_bot = ob['top'], ob['bot']

        entry_price      = (ob_top-(ob_top-ob_bot)*entry_level) if is_long else (ob_bot+(ob_top-ob_bot)*entry_level)
        initial_sl_price = (ob_bot-sl_margin) if is_long else (ob_top+sl_margin)
        sl_dist          = abs(entry_price - initial_sl_price)
        if sl_dist == 0: continue

        tp_price = entry_price + sl_dist*tp_rr if is_long else entry_price - sl_dist*tp_rr
        be_price = entry_price + sl_dist*be_rr  if is_long else entry_price - sl_dist*be_rr
        fvg_end_time = fvg.get('end_time', 0)

        start_search = 0
        for i,c in enumerate(candles):
            if c['time'] >= fvg_end_time: start_search=i; break

        if start_search < len(df):
            fo = df['Open'].iloc[start_search]
            if is_long and fo <= entry_price: continue
            if not is_long and fo >= entry_price: continue

        in_trade=False; trade_entry_time=None; current_sl=initial_sl_price
        tq_entry=None; ses_entry=None; entry_idx=None

        for i in range(start_search, len(df)):
            ct = candles[i]['time']
            if 'end_time' in ob and ct > ob['end_time'] and not in_trade: break
            lo, hi = df['Low'].iloc[i], df['High'].iloc[i]

            if not in_trade:
                if is_long and lo <= entry_price:
                    tq = get_tq_at(ct)
                    if tq > 55:
                        in_trade=True; trade_entry_time=ct
                        tq_entry=tq; ses_entry=session_at(ct); entry_idx=i
                        markers.append({"time":ct,"position":"belowBar","color":"#ffffff","shape":"arrowUp","text":"Entry"})
                    else: break
                elif not is_long and hi >= entry_price:
                    tq = get_tq_at(ct)
                    if tq < 45:
                        in_trade=True; trade_entry_time=ct
                        tq_entry=tq; ses_entry=session_at(ct); entry_idx=i
                        markers.append({"time":ct,"position":"aboveBar","color":"#ffffff","shape":"arrowDown","text":"Entry"})
                    else: break
            else:
                exit_time=ct; status=None
                if is_long:
                    if hi>=tp_price: status="win"
                    elif lo<=current_sl: status="loss" if current_sl==initial_sl_price else "be"
                    elif hi>=be_price: current_sl=entry_price
                else:
                    if lo<=tp_price: status="win"
                    elif hi>=current_sl: status="loss" if current_sl==initial_sl_price else "be"
                    elif lo<=be_price: current_sl=entry_price

                if status:
                    pnl = tp_rr if status=="win" else (-1.0 if status=="loss" else 0.0)
                    stats["total"]+=1; stats[status]+=1; stats["pnl_rr"]+=pnl
                    if is_long: stats["long_total"]+=1; stats[f"long_{status}"]+=1
                    else:       stats["short_total"]+=1; stats[f"short_{status}"]+=1

                    # métriques
                    liq_in, liq_inv, prev_ses_name, prev_h, prev_l = check_liquidity(
                        trade_entry_time, is_long, ses_entry or "")
                    fvg_ext, fvg_detail = fvg_new_extreme(fvg, ob_fvg_data)
                    comp_obs = competing_obs(entry_price, tp_price, is_long, ob_fvg_data, ob)
                    reuses   = ob_reuse_count(ob, candles, df)

                    trades_log.append({
                        "num": stats["total"],
                        "direction": "LONG" if is_long else "SHORT",
                        "status": status.upper(),
                        "pnl_rr": pnl,
                        "entry_price": entry_price, "sl_price": initial_sl_price,
                        "tp_price": tp_price, "sl_ticks": round(sl_dist/mintick),
                        "entry_dt": ts_to_dt(trade_entry_time),
                        "exit_dt":  ts_to_dt(exit_time),
                        "duration": i - entry_idx if entry_idx else 0,
                        "session":  ses_entry or "?",
                        "tq": round(tq_entry,1) if tq_entry else 50.0,
                        "fvg_dir": fvg['direction'],
                        "fvg_extreme": fvg_ext, "fvg_detail": fvg_detail,
                        "fvg_ticks": round(abs(fvg['top']-fvg['bot'])/mintick),
                        "ob_method": ob.get('method','?'),
                        "ob_reuses": reuses,
                        "liq_in": liq_in, "liq_inv": liq_inv,
                        "prev_ses": prev_ses_name,
                        "prev_high": prev_h, "prev_low": prev_l,
                        "comp_obs": comp_obs,
                    })

                    markers.append({"time":exit_time,
                        "position":"aboveBar" if not is_long else "belowBar",
                        "color":"#ffffff",
                        "shape":"arrowDown" if not is_long else "arrowUp",
                        "text":f"Exit ({status.upper()})"})
                    trade_boxes.append({
                        "time_entry":trade_entry_time,"time_right":exit_time,
                        "entry":entry_price,"sl":initial_sl_price,"is_long":is_long,
                        "max_rr":tp_rr,
                        "colors":{
                            "tp_fill":"rgba(0,150,136,0.3)" if status=="win" else "rgba(158,158,158,0.2)",
                            "sl_fill":"rgba(239,83,80,0.3)"}})
                    break

    _write_html(stats, trades_log, tp_rr, config.SYMBOL)
    _write_csv(trades_log)
    return {"markers": markers, "trade_boxes": trade_boxes}


def _fmt(v, dec=3):
    return f"{v:.{dec}f}" if v is not None else "—"

def _bool_cell(val, true_label="✅ Oui", false_label="❌ Non"):
    cls = "yes" if val else "no"
    return f'<span class="{cls}">{true_label if val else false_label}</span>'

def _status_badge(s):
    colors = {"WIN":"#00c853","LOSS":"#f44336","BE":"#ff9800"}
    return f'<span class="badge" style="background:{colors.get(s,"#999")}">{s}</span>'

def _write_csv(trades):
    import csv
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bounce_ob_trades.csv")
    if not trades: return
    keys = trades[0].keys()
    with open(path, "w", newline="", encoding="utf-8") as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(trades)

def _write_html(stats, trades, tp_rr, symbol):
    T = stats["total"]
    wr = round(stats["win"]/T*100,1) if T else 0
    net = stats["pnl_rr"]
    
    l_wr = round(stats['long_win']/stats['long_total']*100,1) if stats['long_total']>0 else 0
    s_wr = round(stats['short_win']/stats['short_total']*100,1) if stats['short_total']>0 else 0

    rows = ""
    for t in trades:
        ed = t['entry_dt'].strftime('%Y-%m-%d %H:%M') if t['entry_dt'] else '?'
        xd = t['exit_dt'].strftime('%Y-%m-%d %H:%M')  if t['exit_dt']  else '?'
        dir_cls = "long" if t["direction"]=="LONG" else "short"
        pnl_cls = "pos" if t["pnl_rr"]>0 else ("neg" if t["pnl_rr"]<0 else "neu")
        prev_range = f"{_fmt(t['prev_low'])}–{_fmt(t['prev_high'])}" if t['prev_high'] else "—"
        comp = "<br>".join(t['comp_obs']) if t['comp_obs'] else "—"
        rows += f"""
        <tr>
          <td class="center">{t['num']}</td>
          <td><span class="dir {dir_cls}">{t['direction']}</span></td>
          <td>{_status_badge(t['status'])}</td>
          <td>{ed}</td>
          <td class="center">{t['duration']}</td>
          <td class="center">{t['session']}</td>
          <td class="center">{t['tq']:.1f}%</td>
          <td class="center">{t['fvg_ticks']}</td>
          <td class="center">{_bool_cell(t['liq_in'], '✅ Prise', '❌ Non')}</td>
          <td class="center">{_bool_cell(t['liq_inv'], '⚠️ Oui', '✅ Non')}</td>
          <td class="center">{t['ob_method']}</td>
        </tr>"""

    # PnL Curve & Max Consecutive SL & Session Stats & Drawdown
    pnl_data = [0.0]
    cumulative = 0.0
    max_sl = 0
    cur_sl = 0
    
    # Drawdown calculation
    peak = 0.0
    max_dd = 0.0
    
    # Session stats
    ses_stats = {
        "London":   {"t":0, "w":0},
        "New York": {"t":0, "w":0},
        "Tokyo":    {"t":0, "w":0}
    }
    
    for t in trades:
        cumulative += t['pnl_rr']
        pnl_data.append(round(cumulative, 2))
        
        # Max DD
        if cumulative > peak: peak = cumulative
        dd = peak - cumulative
        if dd > max_dd: max_dd = dd

        # Session
        s_name = t['session']
        if s_name in ses_stats:
            ses_stats[s_name]["t"] += 1
            if t['status'] == 'WIN': ses_stats[s_name]["w"] += 1
        
        if t['status'] == 'LOSS':
            cur_sl += 1
            max_sl = max(max_sl, cur_sl)
        elif t['status'] == 'WIN':
            cur_sl = 0

    # Winrates sessions
    for k in ses_stats:
        total = ses_stats[k]["t"]
        win = ses_stats[k]["w"]
        ses_stats[k]["wr"] = round(win/total*100, 1) if total > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport Bounce OB</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f1117; color: #d1d4dc; font-family: 'Segoe UI', sans-serif; font-size: 13px; padding: 24px; }}
  h1 {{ font-size: 22px; color: #fff; margin-bottom: 4px; }}
  .subtitle {{ color: #6c7280; font-size: 13px; margin-bottom: 24px; }}
  .summary {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }}
  .card {{ background: #1a1e2b; border: 1px solid #2a2e3d; border-radius: 10px; padding: 16px 24px; min-width: 150px; }}
  .card .label {{ font-size: 11px; color: #6c7280; text-transform: uppercase; letter-spacing:.5px; margin-bottom:4px; }}
  .card .value {{ font-size: 26px; font-weight: 700; color: #fff; }}
  .card .value.pos {{ color: #00c853; }}
  .card .value.neg {{ color: #f44336; }}
  .card .value.neu {{ color: #ff9800; }}
  .section {{ font-size: 11px; color: #6c7280; text-transform: uppercase; letter-spacing:1px; margin: 20px 0 8px; }}
  .split {{ display:flex; gap:12px; margin-bottom:28px; flex-wrap:wrap; }}
  .split .card {{ flex:1; min-width:200px; }}
  .split .card .row {{ display:flex; justify-content:space-between; font-size:13px; padding:3px 0; border-bottom:1px solid #2a2e3d; }}
  .split .card .row:last-child {{ border:none; }}
  .split .card .row .k {{ color:#9ca3af; }}
  table {{ width:100%; border-collapse:collapse; }}
  thead th {{ background:#1a1e2b; color:#9ca3af; font-size:11px; text-transform:uppercase; letter-spacing:.5px; padding:10px 8px; text-align:left; border-bottom:2px solid #2a2e3d; position:sticky; top:0; z-index:10; white-space:nowrap; }}
  tbody tr {{ border-bottom:1px solid #1e2233; transition:background .15s; }}
  tbody tr:hover {{ background:#1a1e2b; }}
  td {{ padding:8px; vertical-align:middle; }}
  td.center {{ text-align:center; }}
  td small {{ color:#6c7280; font-size:11px; display:block; margin-top:2px; }}
  .dir {{ font-weight:700; font-size:12px; padding:2px 8px; border-radius:4px; }}
  .dir.long  {{ background:rgba(0,200,83,.15);  color:#00c853; }}
  .dir.short {{ background:rgba(244,67,54,.15); color:#f44336; }}
  .badge {{ font-size:11px; font-weight:700; padding:3px 8px; border-radius:12px; color:#fff; }}
  .pos {{ color:#00c853; font-weight:700; }}
  .neg {{ color:#f44336; font-weight:700; }}
  .neu {{ color:#ff9800; font-weight:700; }}
  .yes {{ color:#00c853; }}
  .no  {{ color:#f44336; }}
  .detail {{ max-width:200px; word-break:break-word; }}
  .table-wrap {{ overflow-x:auto; border-radius:10px; border:1px solid #2a2e3d; }}
  /* DataTables Dark Mode Fix */
  .dataTables_wrapper .dataTables_length, .dataTables_wrapper .dataTables_filter, .dataTables_wrapper .dataTables_info, .dataTables_wrapper .dataTables_processing, .dataTables_wrapper .dataTables_paginate {{ color: #9ca3af !important; }}
  .dataTables_wrapper .dataTables_length select, .dataTables_wrapper .dataTables_filter input {{ background-color: #1a1e2b !important; color: #fff !important; border: 1px solid #2a2e3d !important; border-radius: 4px; padding: 4px 8px; }}
  table.dataTable tbody tr {{ background-color: #0f1117 !important; color: #d1d4dc !important; }}
  table.dataTable tbody tr:hover {{ background-color: #1a1e2b !important; }}
  tfoot input {{ background: #1a1e2b; color: #fff; border: 1px solid #2a2e3d; padding: 4px; border-radius: 4px; font-size: 11px; }}
</style>
</head>
<body>
<h1>📊 Rapport Bounce OB — {symbol}</h1>
<p class="subtitle">
  {trades[0]['entry_dt'].strftime('%Y-%m-%d') if trades else '?'} →
  {trades[-1]['exit_dt'].strftime('%Y-%m-%d') if trades else '?'}
  &nbsp;·&nbsp; {T} trades
</p>

<div class="summary">
  <div class="card"><div class="label">Total Trades</div>
    <div class="value">{T}</div></div>
  <div class="card"><div class="label">PnL Net (RR)</div>
    <div class="value {'pos' if net>0 else 'neg' if net<0 else 'neu'}">{net:+.2f}</div></div>
  <div class="card"><div class="label">Win Rate</div>
    <div class="value">{wr}%</div></div>
  <div class="card"><div class="label">✅ Gagnants</div>
    <div class="value pos">{stats['win']}</div></div>
  <div class="card"><div class="label">❌ Pertes</div>
    <div class="value neg">{stats['loss']}</div></div>
  <div class="card"><div class="label">🔶 Break-Even</div>
    <div class="value neu">{stats['be']}</div></div>
  <div class="card"><div class="label">🔴 Max SL Consécutifs</div>
    <div class="value neg">{max_sl}</div></div>
  <div class="card"><div class="label">📉 Max Drawdown</div>
    <div class="value neg">-{max_dd:.1f} RR</div></div>
</div>

<div class="card" style="width:100%; height:300px; margin-bottom:28px; padding:15px;">
  <canvas id="pnlChart"></canvas>
</div>

<div class="split">
  <div class="card">
    <div class="label">Longs — {stats['long_total']} trades</div>
    <div class="row"><span class="k">✅ Win</span><span>{stats['long_win']}</span></div>
    <div class="row"><span class="k">❌ Loss</span><span>{stats['long_loss']}</span></div>
    <div class="row"><span class="k">🔶 BE</span><span>{stats['long_be']}</span></div>
    <div class="row" style="border-top:1px dashed #444; margin-top:5px; padding-top:5px;"><span class="k">Win Rate</span><span class="pos">{l_wr}%</span></div>
  </div>
  <div class="card">
    <div class="label">Shorts — {stats['short_total']} trades</div>
    <div class="row"><span class="k">✅ Win</span><span>{stats['short_win']}</span></div>
    <div class="row"><span class="k">❌ Loss</span><span>{stats['short_loss']}</span></div>
    <div class="row"><span class="k">🔶 BE</span><span>{stats['short_be']}</span></div>
    <div class="row" style="border-top:1px dashed #444; margin-top:5px; padding-top:5px;"><span class="k">Win Rate</span><span class="pos">{s_wr}%</span></div>
  </div>
</div>

<div class="section">Performance par Session</div>
<div class="summary">
  <div class="card">
    <div class="label">London</div>
    <div class="value" style="font-size:20px;">{ses_stats['London']['wr']}% <small style="display:inline; font-size:12px; color:#6c7280;">({ses_stats['London']['t']} trades)</small></div>
  </div>
  <div class="card">
    <div class="label">New York</div>
    <div class="value" style="font-size:20px;">{ses_stats['New York']['wr']}% <small style="display:inline; font-size:12px; color:#6c7280;">({ses_stats['New York']['t']} trades)</small></div>
  </div>
  <div class="card">
    <div class="label">Tokyo</div>
    <div class="value" style="font-size:20px;">{ses_stats['Tokyo']['wr']}% <small style="display:inline; font-size:12px; color:#6c7280;">({ses_stats['Tokyo']['t']} trades)</small></div>
  </div>
</div>

<div class="section">Détail par trade</div>
<div class="table-wrap" style="background:#1a1e2b; padding:15px;">
<table id="tradeTable" class="display nowrap">
<thead>
<tr>
  <th>#</th>
  <th>Direction</th>
  <th>Résultat</th>
  <th>Date Entrée</th>
  <th>Durée</th>
  <th>Session</th>
  <th>TQ</th>
  <th>Taille GAP</th>
  <th>Liq. Sens</th>
  <th>Liq. Inv.</th>
  <th>Méthode</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
<tfoot>
<tr>
  <th></th>
  <th><input type="text" placeholder="Filtrer.." style="width:100%"></th>
  <th><input type="text" placeholder="Filtrer.." style="width:100%"></th>
  <th><input type="text" placeholder="Filtrer.." style="width:100%"></th>
  <th></th>
  <th><input type="text" placeholder="Filtrer.." style="width:100%"></th>
  <th></th>
  <th></th>
  <th></th>
  <th></th>
  <th></th>
</tr>
</tfoot>
</table>
</div>

<script>
$(document).ready(function() {{
    var table = $('#tradeTable').DataTable({{
        "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.6/i18n/fr-FR.json" }},
        "pageLength": 25,
        "order": [[0, "desc"]],
        "dom": '<"top"fl>rt<"bottom"ip><"clear">'
    }});

    // Filtres par colonnes
    table.columns().every(function () {{
        var that = this;
        $('input', this.footer()).on('keyup change clear', function () {{
            if (that.search() !== this.value) {{
                that.search(this.value).draw();
            }}
        }});
    }});

    // Graphique PnL
    var ctx = document.getElementById('pnlChart').getContext('2d');
    new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: Array.from({{length: {len(pnl_data)}}}, (_, i) => i),
            datasets: [{{
                label: 'PnL Cumulé (RR)',
                data: {pnl_data},
                borderColor: '#00c853',
                backgroundColor: 'rgba(0, 200, 83, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 0
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                x: {{ display: false }},
                y: {{ 
                    grid: {{ color: '#2a2e3d' }},
                    ticks: {{ color: '#9ca3af' }}
                }}
            }},
            plugins: {{
                legend: {{ display: false }}
            }}
        }}
    }});
}});
</script>
</body>
</html>"""

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bounce_ob_result.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
