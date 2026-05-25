import streamlit as st
import requests
import time
import threading
import pandas as pd
from datetime import datetime, date, timedelta

from scanner.collector   import collect_all_parallel
from scanner.filters     import batch_filter_humans
from scanner.fingerprint import get_wallet_fingerprint, group_by_funder, similarity_score
from scanner.score       import calcular_score, score_label, score_color
from scanner             import cache as mint_cache

st.set_page_config(page_title="Solana Trader Scanner", page_icon="🔍", layout="wide")

st.markdown("""
<style>
  .stApp{background:#0f1117}
  h1{color:#14F195!important;font-family:monospace}
  h2,h3{color:#9945FF!important;font-family:monospace}
  .stTextInput>div>div>input{background:#1a1d2e;color:#fff;border:1px solid #2d2f45;font-family:monospace;font-size:13px}
  .stButton>button{background:linear-gradient(90deg,#9945FF,#14F195);color:white;border:none;border-radius:8px;padding:8px 20px;font-weight:bold;width:100%}
  .stButton>button:hover{opacity:.85}
  .score-bar{height:8px;border-radius:4px;background:#2d2f45;margin-top:4px}
  .score-fill{height:100%;border-radius:4px}
  .tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;margin:2px}
  .tag-green {background:#14F19522;color:#14F195;border:1px solid #14F19555}
  .tag-purple{background:#9945FF22;color:#9945FF;border:1px solid #9945FF55}
  .tag-orange{background:#FF914D22;color:#FF914D;border:1px solid #FF914D55}
  .tag-red   {background:#FF4D4D22;color:#FF4D4D;border:1px solid #FF4D4D55}
  .tag-blue  {background:#4D9FFF22;color:#4D9FFF;border:1px solid #4D9FFF55}
  .tag-yellow{background:#FFD70022;color:#FFD700;border:1px solid #FFD70055}
  .funder-box{background:#1a1d2e;border:1px solid #FFD700;border-radius:8px;padding:10px;margin:6px 0}
</style>
""", unsafe_allow_html=True)

KEY = "befa16a2-ae3a-4b39-a830-0f5631a4f2e2"
RPC = f"https://mainnet.helius-rpc.com/?api-key={KEY}"

# ── Helpers ────────────────────────────────────────────────
def get_token_meta(mint):
    try:
        r = requests.post(f"https://api.helius.xyz/v0/token-metadata?api-key={KEY}",
            json={"mintAccounts":[mint]}, timeout=10)
        if r.ok and r.json():
            m = r.json()[0]
            sym  = m.get("onChainMetadata",{}).get("metadata",{}).get("data",{}).get("symbol","")
            name = m.get("onChainMetadata",{}).get("metadata",{}).get("data",{}).get("name","")
            if sym: return sym, name
    except: pass
    return mint[:8]+"…", "Desconhecido"

def get_token_price(mint):
    try:
        r = requests.get(f"https://price.jup.ag/v4/price?ids={mint}", timeout=8)
        if r.ok:
            p = r.json().get("data",{}).get(mint,{}).get("price",0)
            return float(p) if p else 0.0
    except: return 0.0

def time_ago(ts):
    if not ts: return "—"
    d = int(time.time())-ts
    if d<3600:  return f"{d//60}min atrás"
    if d<86400: return f"{d//3600}h atrás"
    return f"{d//86400}d atrás"

def date_to_ts(d, end=False):
    if not d: return None
    h,m,s = (23,59,59) if end else (0,0,0)
    return int(datetime(d.year,d.month,d.day,h,m,s).timestamp())

def str_to_ts(date_str, time_str):
    """Converte 'YYYY-MM-DD' + 'HH:MM' → unix timestamp."""
    try:
        return int(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").timestamp())
    except: return None

# ── Estado: lista dinâmica de tokens ───────────────────────
if "n_tokens" not in st.session_state:
    st.session_state.n_tokens = 2

# ── HEADER ─────────────────────────────────────────────────
st.markdown("# 🔍 Solana Trader Scanner")
st.markdown("##### Triangule traders de grupos de Telegram — paralelo, preciso, sem falsos positivos")

# Cache status
cached = mint_cache.list_cached()
if cached:
    st.info(f"💾 Cache ativo: {len(cached)} token(s) já coletados — não serão rebuscados. "
            f"[Limpar cache]")
    if st.button("🗑 Limpar cache"):
        mint_cache.clear()
        st.rerun()

st.markdown("---")

# ── Controles de quantidade ────────────────────────────────
c1,c2,c3 = st.columns([3,1,1])
with c1: st.markdown(f"**{st.session_state.n_tokens} token(s)**")
with c2:
    if st.button("➕ Adicionar token", disabled=st.session_state.n_tokens>=10):
        st.session_state.n_tokens+=1; st.rerun()
with c3:
    if st.button("➖ Remover último", disabled=st.session_state.n_tokens<=2):
        n=st.session_state.n_tokens
        for k in [f"mint{n}",f"from{n}",f"to{n}",f"sig_date{n}",f"sig_time{n}",f"sig_win{n}"]:
            st.session_state.pop(k,None)
        st.session_state.n_tokens-=1; st.rerun()

st.caption("Mínimo: 2 tokens · Máximo: 10 tokens · Coleta em paralelo")
st.markdown("")

# ── Cards de tokens ────────────────────────────────────────
n = st.session_state.n_tokens
for row_start in range(0, n, 3):
    cols = st.columns(min(3, n-row_start))
    for ci, num in enumerate(range(row_start+1, min(row_start+4, n+1))):
        with cols[ci]:
            with st.container(border=True):
                st.markdown(f"**Token {num}**")

                mint_val = st.text_input("Contrato", placeholder="Endereço do contrato...",
                    key=f"mint{num}", label_visibility="collapsed")

                # Mostra nome do token em cache
                if mint_val and len(mint_val)>=30:
                    cached_data = mint_cache.get(mint_val)
                    if cached_data:
                        sym = cached_data.get("symbol","")
                        st.markdown(f'<span class="tag tag-green">💾 Cache: {sym}</span>',
                            unsafe_allow_html=True)

                st.caption("📅 Janela de data (opcional)")
                da,db = st.columns(2)
                with da: st.date_input("De",   value=None, key=f"from{num}",
                    min_value=date(2020,1,1), max_value=date.today())
                with db: st.date_input("Até",  value=None, key=f"to{num}",
                    min_value=date(2020,1,1), max_value=date.today())

                st.caption("📡 Sinal do Telegram (opcional — filtra por horário)")
                sa,sb = st.columns(2)
                with sa: st.date_input("Data do sinal", value=None, key=f"sig_date{num}",
                    min_value=date(2020,1,1), max_value=date.today())
                with sb: st.text_input("Hora (HH:MM)", placeholder="14:30",
                    key=f"sig_time{num}")

                st.number_input("Janela após sinal (min)", min_value=5, max_value=1440,
                    value=120, key=f"sig_win{num}",
                    help="Busca compradores até X minutos após o sinal do Telegram")

                if st.button("🔄 Limpar", key=f"reset{num}"):
                    for k in [f"from{num}",f"to{num}",f"sig_date{num}",
                              f"sig_time{num}",f"sig_win{num}"]:
                        st.session_state.pop(k,None)
                    st.rerun()

st.markdown("---")

# ── Opções avançadas ───────────────────────────────────────
with st.expander("⚙️ Opções avançadas"):
    oa1,oa2,oa3 = st.columns(3)
    with oa1:
        calc_fp      = st.checkbox("Fingerprint comportamental", value=True)
        calc_pnl     = st.checkbox("PnL estimado (lento)", value=False)
        calc_funder  = st.checkbox("Detectar wallets do mesmo dono", value=True)
    with oa2:
        min_buys    = st.number_input("Mínimo de compras por token", 1, 20, 1)
        min_intersect = st.number_input("Mínimo de tokens comprados", 2, n, 2)
        min_score   = st.slider("Score mínimo para exibir", 0, 100, 0)
    with oa3:
        use_cache = st.checkbox("Usar cache (não rebuscar tokens já coletados)", value=True)
        show_sim  = st.checkbox("Mostrar similaridade entre wallets", value=True)

run = st.button("🚀 Iniciar Scan", key="btn_run")

if run:
    # ── Valida inputs ──────────────────────────────────────
    token_configs = []
    erros = []
    for num in range(1, n+1):
        mint_v = st.session_state.get(f"mint{num}","").strip()
        if not mint_v or len(mint_v)<30:
            erros.append(f"Token {num}"); continue

        from_v   = st.session_state.get(f"from{num}")
        to_v     = st.session_state.get(f"to{num}")
        sig_d    = st.session_state.get(f"sig_date{num}")
        sig_t    = st.session_state.get(f"sig_time{num}","")
        sig_win  = st.session_state.get(f"sig_win{num}", 120)

        signal_ts = str_to_ts(str(sig_d), sig_t) if sig_d and sig_t else None

        token_configs.append({
            "label":         f"Token {num}",
            "mint":          mint_v,
            "ts_from":       date_to_ts(from_v),
            "ts_to":         date_to_ts(to_v, end=True),
            "signal_ts":     signal_ts,
            "signal_window": int(sig_win) if sig_win else 120,
        })

    if erros:
        st.error(f"Preencha os contratos: {', '.join(erros)}")
        st.stop()

    if min_intersect > len(token_configs):
        st.error("Mínimo de tokens comprados não pode ser maior que o número de tokens.")
        st.stop()

    st.markdown("---")
    st.markdown("## ⏳ Processando em paralelo...")

    prog_bar  = st.progress(0)
    prog_text = st.empty()
    log_area  = st.container()

    # ── Nomes e preços ─────────────────────────────────────
    prog_text.text("Identificando tokens e preços...")
    simbolos={}; nomes={}; precos={}
    for tc in token_configs:
        # Verifica cache
        cached_data = mint_cache.get(tc["mint"]) if use_cache else None
        if cached_data:
            simbolos[tc["label"]] = cached_data.get("symbol", tc["mint"][:8])
            nomes[tc["label"]]    = cached_data.get("name", "")
            precos[tc["label"]]   = cached_data.get("price", 0.0)
        else:
            sym,name = get_token_meta(tc["mint"])
            price    = get_token_price(tc["mint"])
            simbolos[tc["label"]] = sym
            nomes[tc["label"]]    = name
            precos[tc["label"]]   = price

    prog_bar.progress(5)

    # ── Coleta paralela ────────────────────────────────────
    prog_text.text("🚀 Coletando compradores em paralelo (todos os tokens ao mesmo tempo)...")

    # Tokens que precisam ser coletados (não estão em cache)
    to_collect = []
    compradores_por_token = {}
    launch_timestamps     = {}

    for tc in token_configs:
        cached_data = mint_cache.get(tc["mint"]) if use_cache else None
        if cached_data and "compradores" in cached_data:
            compradores_por_token[tc["label"]] = cached_data["compradores"]
            launch_timestamps[tc["label"]]     = cached_data.get("launch_ts")
            with log_area:
                st.success(f"💾 {tc['label']} ({simbolos[tc['label']]}) — carregado do cache "
                           f"({len(cached_data['compradores'])} compradores)")
        else:
            to_collect.append(tc)

    if to_collect:
        # Log queues por token (thread-safe via lista)
        log_queues = {tc["label"]: [] for tc in to_collect}

        # Roda coleta paralela
        results = collect_all_parallel(
            tokens    = to_collect,
            hapi_key  = KEY,
            log_queues= log_queues,
            min_buys  = min_buys,
        )

        # Exibe logs e salva resultados
        for tc in to_collect:
            label = tc["label"]
            comps, launch_ts = results.get(label, ({}, None))
            compradores_por_token[label] = comps
            launch_timestamps[label]     = launch_ts

            # Salva no cache
            if use_cache:
                mint_cache.set(tc["mint"], {
                    "symbol":      simbolos[label],
                    "name":        nomes[label],
                    "price":       precos[label],
                    "compradores": comps,
                    "launch_ts":   launch_ts,
                })

            with log_area:
                with st.expander(f"📦 Log — {label} ({simbolos[label]}) — {len(comps)} compradores"):
                    for msg in log_queues.get(label,[]):
                        st.text(msg)

    prog_bar.progress(55)

    # ── Interseção dinâmica ────────────────────────────────
    prog_text.text("Calculando interseção...")
    labels = [tc["label"] for tc in token_configs]
    sets   = {l: set(compradores_por_token.get(l,{}).keys()) for l in labels}

    wallet_token_count = {}
    for l,s in sets.items():
        for w in s:
            wallet_token_count[w] = wallet_token_count.get(w,0)+1

    candidatos = [w for w,c in wallet_token_count.items() if c>=min_intersect]
    prog_text.text(f"Filtrando {len(candidatos)} candidatos — removendo programas, PDAs e routers...")

    # ── Filtro em lote (getMultipleAccounts) ──────────────
    def progress_cb(done, total, addr):
        prog_bar.progress(55 + int((done/max(total,1))*20))
        prog_text.text(f"Filtrando wallets: {done}/{total} — {addr[:14]}…")

    traders_confirmados = batch_filter_humans(candidatos, RPC, progress_cb)
    prog_bar.progress(75)
    prog_text.text(f"{len(traders_confirmados)} traders reais confirmados — gerando fingerprints...")

    # ── Fingerprint e score ────────────────────────────────
    wallet_data = {}
    for i,wallet in enumerate(traders_confirmados):
        prog_bar.progress(75+int((i/max(len(traders_confirmados),1))*20))
        prog_text.text(f"Analisando {i+1}/{len(traders_confirmados)}: {wallet[:14]}…")

        fp = get_wallet_fingerprint(wallet, RPC, compradores_por_token) if calc_fp else {}

        # Early minutes por token
        for tc in token_configs:
            label = tc["label"]
            comp  = compradores_por_token.get(label,{}).get(wallet,{})
            launch_ts = launch_timestamps.get(label)
            if comp and launch_ts and comp.get("first"):
                mins = (comp["first"] - launch_ts) / 60
                comp["early_minutes"] = round(mins,1) if mins>=0 else None
            else:
                comp["early_minutes"] = None

        sc = calcular_score(wallet, compradores_por_token, fp,
                            len(labels), min_intersect)

        wallet_data[wallet] = {
            "fp":     fp,
            "score":  sc,
            "tokens": wallet_token_count.get(wallet,0),
        }
        time.sleep(0.05)

    prog_bar.progress(100)
    prog_text.text("✅ Análise completa!")

    # Filtra por score mínimo e ordena
    traders_filtrados = sorted(
        [w for w in traders_confirmados if wallet_data[w]["score"]>=min_score],
        key=lambda w: wallet_data[w]["score"], reverse=True
    )

    # ── Detecta grupos com mesmo funder ───────────────────
    funder_groups = {}
    if calc_funder and traders_filtrados:
        fps_list = [{"addr":w, **wallet_data[w]["fp"]} for w in traders_filtrados]
        funder_groups = group_by_funder(fps_list)

    # ══════════════════════════════════════════════════════
    #  RESULTADO
    # ══════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 📊 Resultado")

    # Métricas
    mcols = st.columns(len(labels)+3)
    total_txns = sum(sum(c.get("count",0) for c in compradores_por_token.get(l,{}).values()) for l in labels)
    mcols[0].metric("Txns analisadas", f"{total_txns:,}")
    for i,l in enumerate(labels):
        mcols[i+1].metric(simbolos[l], len(sets[l]))
    mcols[-2].metric(f"≥{min_intersect} tokens", len(traders_confirmados))
    mcols[-1].metric("🎯 No ranking", len(traders_filtrados))

    # Alerta de grupos com mesmo funder
    if funder_groups:
        st.markdown("---")
        st.markdown("### 🔗 Wallets do mesmo dono detectadas")
        for funder, wallets in funder_groups.items():
            st.markdown(
                f'<div class="funder-box">'
                f'<span class="tag tag-yellow">MESMO DONO</span> '
                f'Funder: <code>{funder[:20]}…</code><br>'
                + "".join(f'<code style="margin:2px;display:inline-block">{w}</code><br>' for w in wallets)
                + f'<a href="https://solscan.io/account/{funder}" target="_blank" '
                  f'style="color:#FFD700;font-size:11px">Ver funder no Solscan ↗</a>'
                f'</div>',
                unsafe_allow_html=True
            )

    if not traders_filtrados:
        st.warning("Nenhum trader encontrado. Tente reduzir o score mínimo ou o mínimo de tokens comprados.")
        st.stop()

    # ── Tabela ranking ─────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 🏆 Ranking de Traders — {len(traders_filtrados)} wallets")

    rows=[]
    for wallet in traders_filtrados:
        d  = wallet_data[wallet]
        fp = d["fp"]
        sl,_ = score_label(d["score"])
        row = {
            "Score":          d["score"],
            "Nível":          sl,
            "Tokens":         f"{d['tokens']}/{len(labels)}",
            "Wallet":         wallet,
            "SOL":            f"{fp.get('sol_balance',0):.3f}",
            "Token Accounts": fp.get("token_accounts","—"),
            "Trades 30d":     fp.get("trades_30d","—"),
            "Idade":          f"{fp.get('age_days','nova')} dias" if fp.get("age_days") else "nova",
            "DEX Preferido":  fp.get("dex_preferred","—"),
            "Pos. Média SOL": f"{fp.get('avg_position_sol',0):.4f}",
        }
        for l in labels:
            sym  = simbolos[l]
            comp = compradores_por_token.get(l,{}).get(wallet,{})
            em   = comp.get("early_minutes")
            row[f"{sym} Early"] = (f"⚡{em:.0f}min" if em is not None and em<=60
                                   else f"{em:.0f}min" if em is not None else "—")
            row[f"{sym} Compras"] = comp.get("count",0) if comp else 0
        row["Solscan"] = f"https://solscan.io/account/{wallet}"
        row["Birdeye"] = f"https://birdeye.so/profile/{wallet}?chain=solana"
        rows.append(row)

    df=pd.DataFrame(rows)
    st.dataframe(df,
        column_config={
            "Score":   st.column_config.ProgressColumn("Score",min_value=0,max_value=100,format="%d"),
            "Wallet":  st.column_config.TextColumn("Wallet",width=210),
            "Solscan": st.column_config.LinkColumn("Solscan ↗"),
            "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
        },
        use_container_width=True, hide_index=True)

    csv=df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV completo", csv, "traders_analise.csv", "text/csv")

    # ── Cards detalhados ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 🃏 Perfil detalhado por wallet")

    for wallet in traders_filtrados:
        d  = wallet_data[wallet]
        fp = d["fp"]
        sc = d["score"]
        sl,_ = score_label(sc)
        color = score_color(sc)
        short = wallet[:6]+"…"+wallet[-6:]

        # Verifica se pertence a um grupo de mesmo funder
        in_group = any(wallet in wlist for wlist in funder_groups.values())
        group_tag = '<span class="tag tag-yellow">🔗 MESMO DONO</span>' if in_group else ""

        with st.expander(f"{sl} | Score {sc}/100 | {d['tokens']}/{len(labels)} tokens | {short}"):
            st.markdown(
                f'<div class="score-bar"><div class="score-fill" '
                f'style="width:{sc}%;background:{color}"></div></div>',
                unsafe_allow_html=True)

            st.code(wallet, language=None)
            if in_group:
                st.markdown(group_tag, unsafe_allow_html=True)

            # Métricas do perfil
            p1,p2,p3,p4,p5 = st.columns(5)
            p1.metric("SOL",           f"{fp.get('sol_balance',0):.4f}")
            p2.metric("Token Accounts", fp.get("token_accounts","—"))
            p3.metric("Trades 30d",    fp.get("trades_30d","—"))
            p4.metric("Pos. média",    f"{fp.get('avg_position_sol',0):.3f} SOL")
            p5.metric("Idade",         f"{fp.get('age_days','nova')} dias" if fp.get("age_days") else "nova")

            if fp.get("first_tx_date"):
                st.caption(f"Primeira tx: {fp['first_tx_date']} · {fp.get('avg_tx_day',0)} txns/dia")

            dexes = fp.get("dexes_used",set())
            if dexes:
                preferred = fp.get("dex_preferred","")
                dex_html = " ".join(
                    f'<span class="tag {"tag-green" if d==preferred else "tag-blue"}">'
                    f'{"⭐ " if d==preferred else ""}{d}</span>'
                    for d in dexes)
                st.markdown(f"**DEXes:** {dex_html}", unsafe_allow_html=True)

            if fp.get("funded_by"):
                st.markdown(
                    f'**Financiado por:** <a href="https://solscan.io/account/{fp["funded_by"]}" '
                    f'target="_blank" style="color:#FFD700;font-family:monospace">'
                    f'{fp["funded_by"][:20]}…</a>',
                    unsafe_allow_html=True)

            st.markdown("---")

            # Por token
            chunk=4
            for cs in range(0,len(labels),chunk):
                chunk_labels=labels[cs:cs+chunk]
                tcols=st.columns(len(chunk_labels))
                for ci,label in enumerate(chunk_labels):
                    sym  = simbolos[label]
                    comp = compradores_por_token.get(label,{}).get(wallet,{})
                    em   = comp.get("early_minutes") if comp else None
                    with tcols[ci]:
                        st.markdown(f"**{sym}**")
                        if comp:
                            st.write(f"Compras: **{comp.get('count',0)}**")
                            st.write(f"Tokens: **{comp.get('amount',0):,.0f}**")
                            st.write(f"Última: **{time_ago(comp.get('last',0))}**")
                            sol = comp.get("sol_spent",0)
                            if sol>0: st.write(f"SOL gasto: **{sol:.3f}**")
                            if em is not None:
                                tag = "tag-green" if em<=30 else "tag-purple" if em<=120 else "tag-orange"
                                st.markdown(f'<span class="tag {tag}">⚡ {em:.0f}min após launch</span>',
                                    unsafe_allow_html=True)
                        else:
                            st.caption("Não comprou este token")

            # Similaridade com outras wallets
            if show_sim and len(traders_filtrados)>1:
                st.markdown("---")
                st.caption("**Similaridade com outras wallets do ranking:**")
                fp1 = {"addr":wallet, **fp}
                sim_scores = []
                for other in traders_filtrados:
                    if other==wallet: continue
                    fp2 = {"addr":other, **wallet_data[other]["fp"]}
                    sim = similarity_score(fp1, fp2)
                    if sim>=40:
                        sim_scores.append((other, sim))
                sim_scores.sort(key=lambda x:-x[1])
                if sim_scores:
                    for other,sim in sim_scores[:3]:
                        color2 = "#14F195" if sim>=70 else "#FF914D"
                        st.markdown(
                            f'<span style="font-family:monospace;font-size:11px">'
                            f'{other[:10]}… — '
                            f'<span style="color:{color2};font-weight:bold">{sim}% similar</span>'
                            f'</span>',
                            unsafe_allow_html=True)
                else:
                    st.caption("Nenhuma similaridade acima de 40% com outras wallets.")

            st.markdown(
                f"[🔗 Solscan](https://solscan.io/account/{wallet}) · "
                f"[🐦 Birdeye](https://birdeye.so/profile/{wallet}?chain=solana) · "
                f"[📊 Step](https://step.finance/en/portfolio/{wallet})"
            )
