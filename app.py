import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, date

st.set_page_config(
    page_title="Solana Trader Scanner",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    h1 { color: #14F195 !important; font-family: monospace; }
    h2, h3 { color: #9945FF !important; font-family: monospace; }
    .stTextInput > div > div > input {
        background-color: #1a1d2e; color: #fff;
        border: 1px solid #2d2f45; font-family: monospace; font-size: 13px;
    }
    .token-card {
        background: #1a1d2e;
        border: 1px solid #2d2f45;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
    }
    .token-card-title {
        font-size: 16px; font-weight: bold;
        color: #9945FF; font-family: monospace;
        margin-bottom: 10px;
    }
    .btn-add > button {
        background: #14F195 !important; color: #0f1117 !important;
        border: none !important; border-radius: 8px !important;
        font-weight: bold !important;
    }
    .btn-remove > button {
        background: transparent !important; color: #FF4D4D !important;
        border: 1px solid #FF4D4D !important; border-radius: 8px !important;
        font-size: 12px !important;
    }
    .btn-scan > button {
        background: linear-gradient(90deg,#9945FF,#14F195) !important;
        color: white !important; border: none !important;
        border-radius: 8px !important; padding: 10px 30px !important;
        font-weight: bold !important; font-size: 16px !important;
        width: 100% !important;
    }
    .score-bar { height: 8px; border-radius: 4px; background: #2d2f45; margin-top: 4px; }
    .score-fill { height: 100%; border-radius: 4px; }
    .tag { display:inline-block; padding:2px 8px; border-radius:4px;
           font-size:11px; font-weight:bold; margin:2px; }
    .tag-green  { background:#14F19522; color:#14F195; border:1px solid #14F19555; }
    .tag-purple { background:#9945FF22; color:#9945FF; border:1px solid #9945FF55; }
    .tag-orange { background:#FF914D22; color:#FF914D; border:1px solid #FF914D55; }
    .tag-red    { background:#FF4D4D22; color:#FF4D4D; border:1px solid #FF4D4D55; }
    .tag-blue   { background:#4D9FFF22; color:#4D9FFF; border:1px solid #4D9FFF55; }
</style>
""", unsafe_allow_html=True)

# ── Constantes ──────────────────────────────────────────────
KEY  = "befa16a2-ae3a-4b39-a830-0f5631a4f2e2"
HAPI = "https://api.helius.xyz/v0"
RPC  = f"https://mainnet.helius-rpc.com/?api-key={KEY}"

SKIP_PROGRAMS = {
    "11111111111111111111111111111111",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJe1bRS",
    "ComputeBudget111111111111111111111111111111",
    "BPFLoaderUpgradeab1e11111111111111111111111",
    "NativeLoader1111111111111111111111111111111",
    "Vote111111111111111111111111111111111111111h",
    "So11111111111111111111111111111111111111112",
    "SysvarRent111111111111111111111111111111111",
    "SysvarC1ock11111111111111111111111111111111",
    "SysvarS1otHashes111111111111111111111111111",
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",
}

DEX_NAMES = {
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter v6",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter v4",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM",
    "27haf8L6oxUeXrHrgEgsexjSY5hbVUWEmvv9Nyxg8vQv": "Raydium CLMM",
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": "Orca",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc" : "Orca Whirlpool",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "Meteora DLMM",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "Raydium CPMM",
    "DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M": "Jupiter DCA",
    "opnb2LAfJYbRMAHHvqjCwQxanZn7n7YzmjMERkCDHMT" : "OpenBook",
}

rid = 0

def rpc_call(method, params):
    global rid; rid += 1
    r = requests.post(RPC,
        json={"jsonrpc":"2.0","id":rid,"method":method,"params":params},
        timeout=20)
    d = r.json()
    if "error" in d: raise Exception(d["error"]["message"])
    return d["result"]

def helius_txns(mint, before=None):
    url = f"{HAPI}/addresses/{mint}/transactions?api-key={KEY}&limit=100"
    if before: url += f"&before={before}"
    r = requests.get(url, timeout=25)
    if not r.ok: raise Exception(f"HTTP {r.status_code}")
    return r.json()

def get_token_price(mint):
    try:
        r = requests.get(f"https://price.jup.ag/v4/price?ids={mint}", timeout=8)
        if r.ok:
            p = r.json().get("data",{}).get(mint,{}).get("price",0)
            return float(p) if p else 0.0
    except: pass
    return 0.0

def get_token_name(mint):
    try:
        r = requests.post(f"{HAPI}/token-metadata?api-key={KEY}",
            json={"mintAccounts":[mint]}, timeout=10)
        if r.ok:
            data = r.json()
            if data:
                meta = data[0]
                sym  = meta.get("onChainMetadata",{}).get("metadata",{}).get("data",{}).get("symbol","")
                name = meta.get("onChainMetadata",{}).get("metadata",{}).get("data",{}).get("name","")
                if sym: return sym, name
    except: pass
    return mint[:8]+"…", "Desconhecido"

def is_real_wallet(addr):
    if addr in SKIP_PROGRAMS: return False
    try:
        info = rpc_call("getAccountInfo", [addr, {"encoding":"base64"}])
        if not info or not info.get("value"): return False
        acc = info["value"]
        if acc.get("executable", False): return False
        return acc.get("owner","") == "11111111111111111111111111111111"
    except: return True

def get_wallet_profile(addr):
    profile = {"sol_balance":0.0,"token_count":0,"age_days":None,
               "first_tx_date":None,"trades_30d":0,"dexes_used":set(),"avg_tx_per_day":0.0}
    try:
        bal = rpc_call("getBalance",[addr,{"commitment":"finalized"}])
        profile["sol_balance"] = bal.get("value",0)/1e9
    except: pass
    try:
        tok = rpc_call("getTokenAccountsByOwner",[addr,
            {"programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding":"base64","dataSlice":{"offset":0,"length":0}}])
        profile["token_count"] = len(tok.get("value",[]))
    except: pass
    try:
        sigs = rpc_call("getSignaturesForAddress",[addr,{"limit":50,"commitment":"finalized"}])
        if sigs:
            ts30 = int(time.time())-(30*86400)
            profile["trades_30d"] = len([s for s in sigs if s.get("blockTime",0)>=ts30])
            oldest_sig = sigs[-1].get("signature","")
            if oldest_sig:
                old = rpc_call("getSignaturesForAddress",
                    [addr,{"limit":1000,"before":oldest_sig,"commitment":"finalized"}])
                all_s = sigs+(old or [])
                oldest_ts = min((s.get("blockTime",0) for s in all_s if s.get("blockTime")),default=0)
                if oldest_ts:
                    age = (int(time.time())-oldest_ts)/86400
                    profile["age_days"] = round(age,1)
                    profile["first_tx_date"] = datetime.fromtimestamp(oldest_ts).strftime("%d/%m/%Y")
                    if age>0: profile["avg_tx_per_day"] = round(len(all_s)/age,2)
            for s in sigs[:15]:
                try:
                    tx = rpc_call("getTransaction",[s["signature"],
                        {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}])
                    if tx:
                        for acc in tx.get("transaction",{}).get("message",{}).get("accountKeys",[]):
                            pk = acc.get("pubkey","")
                            if pk in DEX_NAMES: profile["dexes_used"].add(DEX_NAMES[pk])
                except: pass
                time.sleep(0.08)
    except: pass
    return profile

def get_early_minutes(wallet, mint, launch_ts):
    if not launch_ts: return None
    try:
        sigs = rpc_call("getSignaturesForAddress",[wallet,{"limit":1000}])
        window_end = launch_ts+(48*3600)
        relevant = [s for s in (sigs or []) if launch_ts<=s.get("blockTime",0)<=window_end]
        if not relevant: return None
        earliest = min(relevant, key=lambda s: s.get("blockTime",9e9))
        return round((earliest["blockTime"]-launch_ts)/60, 1)
    except: return None

def estimate_pnl(wallet, mint, current_price, comp_info):
    if current_price<=0 or not comp_info: return None,None,None,None
    tokens_held = comp_info.get("amount",0)
    valor_atual = tokens_held*current_price
    custo_sol   = 0.0
    try:
        sigs = rpc_call("getSignaturesForAddress",[wallet,{"limit":100}])
        ts_first = comp_info.get("first",0)
        ts_last  = comp_info.get("last",0)
        relevant = [s for s in (sigs or []) if ts_first<=s.get("blockTime",0)<=ts_last][:15]
        for s in relevant:
            try:
                tx = rpc_call("getTransaction",[s["signature"],
                    {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}])
                if not tx: continue
                accs = [a.get("pubkey","") for a in
                        tx.get("transaction",{}).get("message",{}).get("accountKeys",[])]
                if mint not in accs: continue
                pre  = tx.get("meta",{}).get("preBalances",[])
                post = tx.get("meta",{}).get("postBalances",[])
                for i,acc in enumerate(accs):
                    if acc==wallet and i<len(pre) and i<len(post):
                        diff = (pre[i]-post[i])/1e9
                        if diff>0: custo_sol+=diff
            except: pass
            time.sleep(0.08)
    except: pass
    try:
        r = requests.get("https://price.jup.ag/v4/price?ids=So11111111111111111111111111111111111111112",timeout=5)
        sol_p = float(r.json().get("data",{}).get("So11111111111111111111111111111111111111112",{}).get("price",0)) if r.ok else 0
        custo_usd = custo_sol*sol_p if sol_p else 0
    except: custo_usd=0
    if custo_usd<=0: return None,round(valor_atual,2),None,None
    pnl_usd = valor_atual-custo_usd
    pnl_pct = pnl_usd/custo_usd*100
    return round(custo_usd,2),round(valor_atual,2),round(pnl_usd,2),round(pnl_pct,1)

def calcular_score(wallet, compradores_por_token, profile, early_mins_list, total_tokens, min_intersect):
    score = 0
    tokens_comprados = sum(1 for l in compradores_por_token if wallet in compradores_por_token[l])
    score += min(25, int((tokens_comprados/total_tokens)*25))
    score += min(20, int(profile.get("trades_30d",0)/5))
    score += min(20, int((profile.get("age_days",0) or 0)/30))
    score += min(10, int(profile.get("sol_balance",0)*2))
    score += min(10, int(profile.get("token_count",0)/5))
    for mins in early_mins_list:
        if mins is not None:
            if mins<=5:    score+=15; break
            elif mins<=30: score+=10; break
            elif mins<=120: score+=5; break
    return min(100,score)

def score_color(s):
    if s>=75: return "#14F195"
    if s>=50: return "#9945FF"
    if s>=25: return "#FF914D"
    return "#FF4D4D"

def score_label(s):
    if s>=75: return "🟢 ELITE",    "tag-green"
    if s>=50: return "🟣 SÓLIDO",   "tag-purple"
    if s>=25: return "🟠 INICIANTE","tag-orange"
    return      "🔴 FRACO",         "tag-red"

def extrair_compradores(mint, label, ts_from, ts_to, prog_text):
    compradores={}; before=None; total_tx=0; pagina=0; launch_ts=None
    while True:
        pagina+=1
        try: batch=helius_txns(mint,before)
        except Exception as e:
            time.sleep(3)
            try: batch=helius_txns(mint,before)
            except: break
        if not batch: break
        total_tx+=len(batch); parou=False
        for tx in batch:
            ts=tx.get("timestamp",0); fee_payer=tx.get("feePayer","")
            if ts_from and ts<ts_from: parou=True; break
            if ts_to and ts>ts_to: continue
            for tt in tx.get("tokenTransfers",[]):
                if tt.get("mint","")!=mint: continue
                dest=tt.get("toUserAccount",""); amount=float(tt.get("tokenAmount",0))
                if not dest or dest in SKIP_PROGRAMS or dest==mint: continue
                if dest!=fee_payer: continue
                if dest not in compradores:
                    compradores[dest]={"count":0,"amount":0.0,"first":ts,"last":ts}
                compradores[dest]["count"]+=1; compradores[dest]["amount"]+=amount
                if ts<compradores[dest]["first"]: compradores[dest]["first"]=ts
                if ts>compradores[dest]["last"]:  compradores[dest]["last"]=ts
        periodo=""
        if ts_from or ts_to:
            f=datetime.fromtimestamp(ts_from).strftime("%d/%m/%Y") if ts_from else "início"
            t=datetime.fromtimestamp(ts_to).strftime("%d/%m/%Y")   if ts_to   else "hoje"
            periodo=f" | {f} → {t}"
        prog_text.text(f"📦 {label} — Pág {pagina} | {total_tx} txns | {len(compradores)} traders{periodo}")
        if parou or len(batch)<100:
            if batch:
                oldest=min((tx.get("timestamp",0) for tx in batch if tx.get("timestamp")),default=0)
                launch_ts=oldest
            break
        before=batch[-1]["signature"]; time.sleep(0.3)
    return compradores, launch_ts

def time_ago(ts):
    if not ts: return "—"
    diff=int(time.time())-ts
    if diff<3600:  return f"{diff//60}min atrás"
    if diff<86400: return f"{diff//3600}h atrás"
    return f"{diff//86400}d atrás"

def date_to_ts(d):
    return int(datetime(d.year,d.month,d.day,0,0,0).timestamp()) if d else None

def date_to_ts_end(d):
    return int(datetime(d.year,d.month,d.day,23,59,59).timestamp()) if d else None

# ══════════════════════════════════════════════════════════
#  ESTADO — lista dinâmica de tokens
# ══════════════════════════════════════════════════════════
if "token_count" not in st.session_state:
    st.session_state.token_count = 3   # começa com 3

# ── HEADER ──────────────────────────────────────────────────
st.markdown("# 🔍 Solana Trader Scanner")
st.markdown("##### Encontre traders reais que compraram múltiplos tokens — com score, PnL e early buyer")
st.markdown("---")

# ── CONTROLES DE QUANTIDADE ─────────────────────────────────
ctrl1, ctrl2, ctrl3 = st.columns([2,1,1])
with ctrl1:
    st.markdown(f"**{st.session_state.token_count} token(s) adicionado(s)**")
with ctrl2:
    with st.container():
        if st.button("➕ Adicionar token", key="btn_add",
                     disabled=st.session_state.token_count >= 10):
            st.session_state.token_count += 1
            st.rerun()
with ctrl3:
    if st.button("➖ Remover último", key="btn_remove",
                 disabled=st.session_state.token_count <= 2):
        n = st.session_state.token_count
        # Limpa o estado do token removido
        for k in [f"mint{n}", f"from{n}", f"to{n}"]:
            if k in st.session_state: del st.session_state[k]
        st.session_state.token_count -= 1
        st.rerun()

st.caption("Mínimo: 2 tokens · Máximo: 10 tokens")
st.markdown("")

# ── TOKENS DINÂMICOS ─────────────────────────────────────────
n = st.session_state.token_count
# Renderiza em grade de 3 colunas
cols_per_row = 3
rows = []
for i in range(0, n, cols_per_row):
    rows.append(list(range(i+1, min(i+cols_per_row+1, n+1))))

for row in rows:
    cols = st.columns(len(row))
    for col_idx, num in enumerate(row):
        with cols[col_idx]:
            st.markdown(f"**Token {num}**")
            mint_val = st.text_input(
                f"Contrato",
                placeholder="Endereço do contrato...",
                key=f"mint{num}",
                label_visibility="collapsed"
            )
            st.caption("📅 Filtrar por data (opcional)")
            d1, d2 = st.columns(2)
            with d1:
                st.date_input("De", value=None,
                    min_value=date(2020,1,1), max_value=date.today(),
                    key=f"from{num}", label_visibility="visible")
            with d2:
                st.date_input("Até", value=None,
                    min_value=date(2020,1,1), max_value=date.today(),
                    key=f"to{num}", label_visibility="visible")
            if st.button("🔄 Limpar", key=f"reset{num}"):
                st.session_state[f"from{num}"] = None
                st.session_state[f"to{num}"]   = None
                st.rerun()
    st.markdown("---")

# ── OPÇÕES AVANÇADAS ─────────────────────────────────────────
with st.expander("⚙️ Opções avançadas"):
    oa1, oa2 = st.columns(2)
    with oa1:
        calc_pnl     = st.checkbox("Calcular PnL estimado (mais lento)", value=True)
        calc_early   = st.checkbox("Detectar early buyers", value=True)
        calc_profile = st.checkbox("Buscar perfil das wallets", value=True)
    with oa2:
        min_compras = st.number_input("Mínimo de compras por token", min_value=1, value=1)
        min_intersect = st.number_input(
            "Mínimo de tokens que a wallet deve ter comprado",
            min_value=2, max_value=n, value=n,
            help="Ex: se você tem 5 tokens e quer quem comprou pelo menos 3, coloque 3."
        )
        min_score = st.slider("Score mínimo", 0, 100, 0)

# ── BOTÃO SCAN ───────────────────────────────────────────────
run = st.button("🚀 Iniciar Scan", key="btn_scan")

if run:
    # Coleta inputs
    contratos = {}
    for num in range(1, n+1):
        mint_v = st.session_state.get(f"mint{num}", "").strip()
        from_v = st.session_state.get(f"from{num}", None)
        to_v   = st.session_state.get(f"to{num}",   None)
        contratos[f"Token {num}"] = (mint_v, date_to_ts(from_v), date_to_ts_end(to_v))

    erros = [l for l,(m,_,_) in contratos.items() if not m or len(m)<30]
    if erros:
        st.error(f"Preencha corretamente: {', '.join(erros)}")
        st.stop()

    if min_intersect > len(contratos):
        st.error("O mínimo de tokens comprados não pode ser maior que o número de tokens.")
        st.stop()

    st.markdown("---")
    st.markdown("## ⏳ Processando...")
    prog_bar  = st.progress(0)
    prog_text = st.empty()

    # Nomes e preços
    prog_text.text("Identificando tokens...")
    nomes={}; simbolos={}; precos={}
    for label,(mint,_,_) in contratos.items():
        sym,name = get_token_name(mint)
        nomes[label]=name; simbolos[label]=sym
        precos[label]=get_token_price(mint)
        prog_text.text(f"✓ {sym} — ${precos[label]:.8f}")

    # Coleta compradores
    compradores_por_token={}; launch_timestamps={}
    labels=list(contratos.keys())
    for i,(label,(mint,ts_from,ts_to)) in enumerate(contratos.items()):
        prog_bar.progress(int((i/len(labels))*50))
        comps,launch_ts = extrair_compradores(mint,f"{label} ({simbolos[label]})",ts_from,ts_to,prog_text)
        compradores_por_token[label] = {k:v for k,v in comps.items() if v["count"]>=min_compras}
        launch_timestamps[label] = launch_ts

    prog_bar.progress(55)

    # Interseção dinâmica: wallets que compraram >= min_intersect tokens
    prog_text.text("Calculando interseção dinâmica...")
    sets = {l: set(compradores_por_token[l].keys()) for l in labels}

    wallet_token_count = {}
    for l,s in sets.items():
        for w in s:
            wallet_token_count[w] = wallet_token_count.get(w,0)+1

    candidatos = [w for w,c in wallet_token_count.items() if c>=min_intersect]
    prog_text.text(f"Verificando {len(candidatos)} carteiras (mínimo {min_intersect} tokens)...")

    traders_confirmados = [a for a in candidatos if is_real_wallet(a)]
    prog_bar.progress(65)

    # Enriquecimento
    wallet_data={}
    for i,wallet in enumerate(traders_confirmados):
        prog_bar.progress(65+int((i/max(len(traders_confirmados),1))*30))
        prog_text.text(f"Analisando wallet {i+1}/{len(traders_confirmados)}: {wallet[:14]}…")
        entry={"wallet":wallet,"profile":{},"pnl":{},"early":{},"score":0,
               "tokens_comprados": wallet_token_count.get(wallet,0)}

        if calc_profile: entry["profile"] = get_wallet_profile(wallet)

        if calc_early:
            for label,(mint,_,_) in contratos.items():
                entry["early"][label] = get_early_minutes(wallet,mint,launch_timestamps.get(label))
                time.sleep(0.1)

        if calc_pnl:
            for label,(mint,_,_) in contratos.items():
                comp=compradores_por_token[label].get(wallet,{})
                entry["pnl"][label] = estimate_pnl(wallet,mint,precos[label],comp)

        early_mins=[entry["early"].get(l) for l in labels]
        entry["score"] = calcular_score(wallet,compradores_por_token,entry["profile"],
                                        early_mins,len(labels),min_intersect)
        wallet_data[wallet]=entry
        time.sleep(0.1)

    prog_bar.progress(100)
    prog_text.text("✅ Análise completa!")

    traders_filtrados = sorted(
        [w for w in traders_confirmados if wallet_data[w]["score"]>=min_score],
        key=lambda w: wallet_data[w]["score"], reverse=True
    )

    # ── MÉTRICAS ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Resultado")

    metric_cols = st.columns(len(labels)+2)
    total_txns=sum(sum(c.get("count",0) for c in compradores_por_token[l].values()) for l in labels)
    metric_cols[0].metric("Txns analisadas", f"{total_txns:,}")
    for i,l in enumerate(labels):
        metric_cols[i+1].metric(f"{simbolos[l]}", len(sets[l]))
    metric_cols[-1].metric(f"🎯 ≥{min_intersect} tokens", len(traders_filtrados))

    # ── TABELA RANKING ────────────────────────────────────────
    if traders_filtrados:
        st.markdown("---")
        st.markdown(f"### 🏆 Ranking de Traders ({len(traders_filtrados)} wallets)")

        rows_data=[]
        for wallet in traders_filtrados:
            d=wallet_data[wallet]
            sl,_=score_label(d["score"])
            row={"Score":d["score"],"Nível":sl,"Tokens Comprados":d["tokens_comprados"],
                 "Wallet":wallet,
                 "SOL":f"{d['profile'].get('sol_balance',0):.3f}",
                 "Trades 30d":d['profile'].get('trades_30d',0),
                 "Idade":f"{d['profile'].get('age_days','?')} dias",
                 "DEXes":", ".join(d['profile'].get('dexes_used',set())) or "—"}
            for l in labels:
                sym=simbolos[l]
                comp=compradores_por_token[l].get(wallet,{})
                row[f"{sym} Compras"]=comp.get("count",0) if comp else "—"
                mins=d["early"].get(l)
                row[f"{sym} Early"]=(f"⚡{mins:.0f}min" if mins is not None and mins<=60
                                     else f"{mins:.0f}min" if mins is not None else "—")
                _,v,p,pct=d["pnl"].get(l,(None,None,None,None))
                row[f"{sym} PnL"]=(f"{'+'if p>=0 else ''}{p:.2f}$ ({pct:+.1f}%)"
                                   if p is not None else "—")
            row["Solscan"]=f"https://solscan.io/account/{wallet}"
            row["Birdeye"]=f"https://birdeye.so/profile/{wallet}?chain=solana"
            rows_data.append(row)

        df=pd.DataFrame(rows_data)
        st.dataframe(df,
            column_config={
                "Score":   st.column_config.ProgressColumn("Score",min_value=0,max_value=100,format="%d"),
                "Wallet":  st.column_config.TextColumn("Wallet",width=200),
                "Solscan": st.column_config.LinkColumn("Solscan ↗"),
                "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
            },
            use_container_width=True, hide_index=True)

        csv=df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV completo",csv,"traders_analise.csv","text/csv")

        # ── CARDS DETALHADOS ──────────────────────────────────
        st.markdown("---")
        st.markdown("### 🃏 Análise detalhada por wallet")

        for wallet in traders_filtrados:
            d=wallet_data[wallet]; prof=d["profile"]
            sc=d["score"]; sl,_=score_label(sc)
            short=wallet[:6]+"…"+wallet[-6:]; color=score_color(sc)

            with st.expander(f"{sl}  |  Score {sc}/100  |  Comprou {d['tokens_comprados']}/{len(labels)} tokens  |  {short}"):
                st.markdown(f'<div class="score-bar"><div class="score-fill" style="width:{sc}%;background:{color}"></div></div>',unsafe_allow_html=True)
                st.code(wallet,language=None)

                pc1,pc2,pc3,pc4=st.columns(4)
                pc1.metric("SOL",f"{prof.get('sol_balance',0):.4f}")
                pc2.metric("Token Accounts",prof.get("token_count","—"))
                pc3.metric("Trades 30d",prof.get("trades_30d","—"))
                pc4.metric("Idade",f"{prof.get('age_days','?')} dias")

                if prof.get("first_tx_date"):
                    st.caption(f"Primeira tx: {prof['first_tx_date']}  |  Média: {prof.get('avg_tx_per_day',0)} txns/dia")

                dexes=prof.get("dexes_used",set())
                if dexes:
                    st.markdown("**DEXes:** "+" ".join(f'<span class="tag tag-blue">{dx}</span>' for dx in dexes),unsafe_allow_html=True)

                st.markdown("---")
                # Colunas por token (máx 5 por linha para não estourar)
                chunk=5
                for chunk_start in range(0,len(labels),chunk):
                    chunk_labels=labels[chunk_start:chunk_start+chunk]
                    tcols=st.columns(len(chunk_labels))
                    for ci,label in enumerate(chunk_labels):
                        sym=simbolos[label]
                        comp=compradores_por_token[label].get(wallet,{})
                        mins=d["early"].get(label)
                        _,v,p,pct=d["pnl"].get(label,(None,None,None,None))
                        with tcols[ci]:
                            st.markdown(f"**{sym}**")
                            if comp:
                                st.write(f"Compras: **{comp.get('count',0)}**")
                                st.write(f"Tokens: **{comp.get('amount',0):,.0f}**")
                                st.write(f"Última: **{time_ago(comp.get('last',0))}**")
                            else:
                                st.caption("Não comprou este token")
                            if mins is not None:
                                tag="tag-green" if mins<=30 else "tag-purple"
                                st.markdown(f'<span class="tag {tag}">⚡ {mins:.0f}min após launch</span>',unsafe_allow_html=True)
                            if p is not None:
                                c2=":green" if p>=0 else ":red"
                                st.markdown(f"PnL: **{c2}[{'+'if p>=0 else ''}{p:.2f}$ ({pct:+.1f}%)]**")
                            elif v is not None:
                                st.caption(f"Valor atual: ${v:.2f}")

                st.markdown(
                    f"[🔗 Solscan](https://solscan.io/account/{wallet}) · "
                    f"[🐦 Birdeye](https://birdeye.so/profile/{wallet}?chain=solana) · "
                    f"[📊 Step](https://step.finance/en/portfolio/{wallet})"
                )
    else:
        st.warning("Nenhum trader encontrado com os filtros selecionados.")
