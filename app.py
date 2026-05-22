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
    .stButton > button {
        background: linear-gradient(90deg,#9945FF,#14F195);
        color: white; border: none; border-radius: 8px;
        padding: 10px 30px; font-weight: bold; font-size: 16px; width: 100%;
    }
    .stButton > button:hover { opacity: 0.85; }
    .score-bar { height: 8px; border-radius: 4px; background: #2d2f45; margin-top: 4px; }
    .score-fill { height: 100%; border-radius: 4px; }
    .tag { display:inline-block; padding:2px 8px; border-radius:4px;
           font-size:11px; font-weight:bold; margin:2px; }
    .tag-green  { background:#14F19522; color:#14F195; border:1px solid #14F19555; }
    .tag-purple { background:#9945FF22; color:#9945FF; border:1px solid #9945FF55; }
    .tag-orange { background:#FF914D22; color:#FF914D; border:1px solid #FF914D55; }
    .tag-red    { background:#FF4D4D22; color:#FF4D4D; border:1px solid #FF4D4D55; }
    .tag-blue   { background:#4D9FFF22; color:#4D9FFF; border:1px solid #4D9FFF55; }
    .wallet-header { font-family:monospace; font-size:13px; color:#14F195; }
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
    """Tenta buscar preço atual via Jupiter Price API."""
    try:
        r = requests.get(
            f"https://price.jup.ag/v4/price?ids={mint}",
            timeout=8)
        if r.ok:
            data = r.json()
            price = data.get("data",{}).get(mint,{}).get("price", 0)
            return float(price) if price else 0.0
    except: pass
    return 0.0

def get_token_name(mint):
    try:
        r = requests.post(
            f"https://api.helius.xyz/v0/token-metadata?api-key={KEY}",
            json={"mintAccounts": [mint]}, timeout=10)
        if r.ok:
            data = r.json()
            if data:
                meta = data[0]
                sym  = meta.get("onChainMetadata",{}).get("metadata",{}).get("data",{}).get("symbol","")
                name = meta.get("onChainMetadata",{}).get("metadata",{}).get("data",{}).get("name","")
                if sym: return sym, name
    except: pass
    return mint[:8]+"…", "Token desconhecido"

def is_real_wallet(addr):
    if addr in SKIP_PROGRAMS: return False
    try:
        info = rpc_call("getAccountInfo", [addr, {"encoding": "base64"}])
        if not info or not info.get("value"): return False
        acc = info["value"]
        if acc.get("executable", False): return False
        return acc.get("owner","") == "11111111111111111111111111111111"
    except:
        return True

def get_wallet_profile(addr):
    """
    Busca perfil completo da wallet:
    - Saldo SOL
    - Número de token accounts
    - Idade da wallet (primeira transação)
    - DEXes usados
    - Frequência de trades (últimos 30 dias)
    """
    profile = {
        "sol_balance": 0.0,
        "token_count": 0,
        "age_days": None,
        "first_tx_date": None,
        "trades_30d": 0,
        "dexes_used": set(),
        "avg_tx_per_day": 0.0,
    }
    try:
        bal = rpc_call("getBalance", [addr, {"commitment":"finalized"}])
        profile["sol_balance"] = bal.get("value", 0) / 1e9
    except: pass

    try:
        tok = rpc_call("getTokenAccountsByOwner", [addr,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "base64", "dataSlice": {"offset":0,"length":0}}])
        profile["token_count"] = len(tok.get("value", []))
    except: pass

    try:
        # Última página de assinaturas para pegar a mais antiga
        sigs_recent = rpc_call("getSignaturesForAddress", [addr, {"limit": 50, "commitment":"finalized"}])
        if sigs_recent:
            ts_30d = int(time.time()) - (30 * 86400)
            trades_30d = [s for s in sigs_recent if s.get("blockTime",0) >= ts_30d]
            profile["trades_30d"] = len(trades_30d)

            # Tenta pegar assinaturas mais antigas para estimar idade
            oldest_sig = sigs_recent[-1].get("signature","")
            if oldest_sig:
                sigs_old = rpc_call("getSignaturesForAddress",
                    [addr, {"limit": 1000, "before": oldest_sig, "commitment":"finalized"}])
                all_sigs = sigs_recent + (sigs_old or [])
                oldest_ts = min((s.get("blockTime",0) for s in all_sigs if s.get("blockTime")), default=0)
                if oldest_ts:
                    age = (int(time.time()) - oldest_ts) / 86400
                    profile["age_days"] = round(age, 1)
                    profile["first_tx_date"] = datetime.fromtimestamp(oldest_ts).strftime("%d/%m/%Y")
                    if age > 0:
                        profile["avg_tx_per_day"] = round(len(all_sigs) / age, 2)

        # DEXes usados (amostra das últimas 20 txns)
        sample = sigs_recent[:20]
        for s in sample:
            try:
                tx = rpc_call("getTransaction", [s["signature"],
                    {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}])
                if tx:
                    for acc in tx.get("transaction",{}).get("message",{}).get("accountKeys",[]):
                        pk = acc.get("pubkey","")
                        if pk in DEX_NAMES:
                            profile["dexes_used"].add(DEX_NAMES[pk])
            except: pass
            time.sleep(0.1)
    except: pass

    return profile

def get_early_buyer_rank(wallet, mint, launch_ts):
    """
    Verifica se a wallet foi early buyer:
    Retorna minutos após o lançamento que a wallet comprou pela 1ª vez.
    """
    if not launch_ts: return None
    try:
        sigs = rpc_call("getSignaturesForAddress", [wallet, {"limit": 1000}])
        # Filtra txns próximas ao lançamento (primeiras 48h)
        window_end = launch_ts + (48 * 3600)
        relevant = [s for s in (sigs or [])
                    if launch_ts <= s.get("blockTime",0) <= window_end]
        if not relevant: return None
        earliest = min(relevant, key=lambda s: s.get("blockTime", 9e9))
        minutes_after = (earliest["blockTime"] - launch_ts) / 60
        return round(minutes_after, 1)
    except:
        return None

def estimate_pnl(wallet, mint, current_price, compra_info):
    """
    Estima PnL:
    - Busca transferências SOL/USDC que saíram da wallet nas txns de compra
    - Compara com valor atual dos tokens
    Retorna: (custo_estimado_usd, valor_atual_usd, pnl_usd, pnl_pct)
    """
    if current_price <= 0 or not compra_info:
        return None, None, None, None

    # Valor atual dos tokens
    tokens_held = compra_info.get("amount", 0)
    valor_atual = tokens_held * current_price

    # Custo estimado: busca nativeTransfers de saída nas txns de compra
    custo_sol = 0.0
    try:
        sigs = rpc_call("getSignaturesForAddress", [wallet, {"limit": 100}])
        ts_first = compra_info.get("first", 0)
        ts_last  = compra_info.get("last", 0)
        relevant = [s for s in (sigs or [])
                    if ts_first <= s.get("blockTime",0) <= ts_last][:20]

        for s in relevant:
            try:
                tx = rpc_call("getTransaction", [s["signature"],
                    {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}])
                if not tx: continue
                # Verifica se envolveu o mint
                accs = [a.get("pubkey","") for a in
                        tx.get("transaction",{}).get("message",{}).get("accountKeys",[])]
                if mint not in accs: continue
                # Soma variação negativa de SOL (custo pago)
                pre  = tx.get("meta",{}).get("preBalances",[])
                post = tx.get("meta",{}).get("postBalances",[])
                for i, acc in enumerate(accs):
                    if acc == wallet and i < len(pre) and i < len(post):
                        diff = (pre[i] - post[i]) / 1e9
                        if diff > 0: custo_sol += diff
            except: pass
            time.sleep(0.08)
    except: pass

    # Converte SOL para USD (preço aproximado via Jupiter)
    try:
        r = requests.get("https://price.jup.ag/v4/price?ids=So11111111111111111111111111111111111111112", timeout=5)
        sol_price = r.json().get("data",{}).get("So11111111111111111111111111111111111111112",{}).get("price",0) if r.ok else 0
        custo_usd = custo_sol * float(sol_price) if sol_price else 0
    except:
        custo_usd = 0

    if custo_usd <= 0:
        return None, round(valor_atual, 2), None, None

    pnl_usd = valor_atual - custo_usd
    pnl_pct = (pnl_usd / custo_usd * 100) if custo_usd > 0 else 0
    return round(custo_usd, 2), round(valor_atual, 2), round(pnl_usd, 2), round(pnl_pct, 1)

def calcular_score(wallet, compras_por_token, profile, early_minutes_list, total_tokens):
    """
    Score 0-100 baseado em:
    - Quantos tokens comprou (máx 25 pts)
    - Frequência de trades 30d (máx 20 pts)
    - Idade da wallet em dias (máx 20 pts)
    - SOL balance (máx 10 pts)
    - Token accounts (máx 10 pts)
    - Early buyer em algum token (máx 15 pts)
    """
    score = 0

    # Tokens comprados (25 pts)
    tokens_comprados = sum(1 for l in compras_por_token if wallet in compras_por_token[l])
    score += min(25, int((tokens_comprados / total_tokens) * 25))

    # Frequência 30d (20 pts)
    t30 = profile.get("trades_30d", 0)
    score += min(20, int(t30 / 5))

    # Idade (20 pts) — carteiras mais velhas são mais confiáveis
    age = profile.get("age_days", 0) or 0
    score += min(20, int(age / 30))

    # SOL balance (10 pts)
    sol = profile.get("sol_balance", 0)
    score += min(10, int(sol * 2))

    # Token accounts (10 pts)
    tkc = profile.get("token_count", 0)
    score += min(10, int(tkc / 5))

    # Early buyer (15 pts)
    for mins in early_minutes_list:
        if mins is not None:
            if mins <= 5:    score += 15; break
            elif mins <= 30: score += 10; break
            elif mins <= 120: score += 5; break

    return min(100, score)

def score_color(s):
    if s >= 75: return "#14F195"
    if s >= 50: return "#9945FF"
    if s >= 25: return "#FF914D"
    return "#FF4D4D"

def score_label(s):
    if s >= 75: return ("🟢 ELITE", "tag-green")
    if s >= 50: return ("🟣 SÓLIDO", "tag-purple")
    if s >= 25: return ("🟠 INICIANTE", "tag-orange")
    return ("🔴 FRACO", "tag-red")

def extrair_compradores(mint, label, ts_from, ts_to, prog_text):
    compradores = {}
    before = None
    total_tx = 0
    pagina = 0
    launch_ts = None  # timestamp da 1ª transação do token

    while True:
        pagina += 1
        try:
            batch = helius_txns(mint, before)
        except Exception as e:
            time.sleep(3)
            try:   batch = helius_txns(mint, before)
            except: break

        if not batch: break

        # A última página contém as txns mais antigas = lançamento
        total_tx += len(batch)
        parou = False

        for tx in batch:
            ts        = tx.get("timestamp", 0)
            fee_payer = tx.get("feePayer", "")
            if ts_from and ts < ts_from: parou = True; break
            if ts_to and ts > ts_to: continue

            for tt in tx.get("tokenTransfers", []):
                if tt.get("mint","") != mint: continue
                dest   = tt.get("toUserAccount","")
                amount = float(tt.get("tokenAmount", 0))
                if not dest or dest in SKIP_PROGRAMS or dest == mint: continue
                if dest != fee_payer: continue
                if dest not in compradores:
                    compradores[dest] = {"count":0,"amount":0.0,"first":ts,"last":ts}
                compradores[dest]["count"]  += 1
                compradores[dest]["amount"] += amount
                if ts < compradores[dest]["first"]: compradores[dest]["first"] = ts
                if ts > compradores[dest]["last"]:  compradores[dest]["last"]  = ts

        periodo = ""
        if ts_from or ts_to:
            f = datetime.fromtimestamp(ts_from).strftime("%d/%m/%Y") if ts_from else "início"
            t = datetime.fromtimestamp(ts_to).strftime("%d/%m/%Y")   if ts_to   else "hoje"
            periodo = f" | {f} → {t}"

        prog_text.text(
            f"📦 {label} — Pág {pagina} | {total_tx} txns | "
            f"{len(compradores)} traders únicos{periodo}"
        )

        if parou or len(batch) < 100:
            # Salva timestamp de lançamento (txn mais antiga)
            if batch:
                oldest = min(tx.get("timestamp",0) for tx in batch if tx.get("timestamp"))
                launch_ts = oldest
            break

        before = batch[-1]["signature"]
        time.sleep(0.3)

    return compradores, launch_ts

def time_ago(ts):
    if not ts: return "—"
    diff = int(time.time()) - ts
    if diff < 3600:  return f"{diff//60}min atrás"
    if diff < 86400: return f"{diff//3600}h atrás"
    return f"{diff//86400}d atrás"

def date_to_ts(d):
    if d is None: return None
    return int(datetime(d.year, d.month, d.day, 0,0,0).timestamp())

def date_to_ts_end(d):
    if d is None: return None
    return int(datetime(d.year, d.month, d.day, 23,59,59).timestamp())

# ══════════════════════════════════════════════════════════
#  INTERFACE
# ══════════════════════════════════════════════════════════
st.markdown("# 🔍 Solana Trader Scanner")
st.markdown("##### Encontre traders reais que compraram múltiplos tokens — com score, PnL e análise de early buyer")
st.markdown("---")

col1, col2, col3 = st.columns(3)

def token_block(col, num):
    with col:
        st.markdown(f"### Token {num}")
        mint = st.text_input(f"Contrato do Token {num}",
            placeholder="Cole o endereço do contrato...", key=f"mint{num}")
        st.caption("⬇ Filtrar por data (opcional — deixe em branco para varrer tudo)")
        dc1, dc2 = st.columns(2)
        with dc1:
            date_from = st.date_input("De", value=None,
                min_value=date(2020,1,1), max_value=date.today(), key=f"from{num}")
        with dc2:
            date_to_val = st.date_input("Até", value=None,
                min_value=date(2020,1,1), max_value=date.today(), key=f"to{num}")
        if st.button(f"🔄 Limpar datas", key=f"reset{num}"):
            st.session_state[f"from{num}"] = None
            st.session_state[f"to{num}"]   = None
            st.rerun()
        return mint, date_from, date_to_val

mint1, from1, to1 = token_block(col1, 1)
mint2, from2, to2 = token_block(col2, 2)
mint3, from3, to3 = token_block(col3, 3)

st.markdown("")

# Opções avançadas
with st.expander("⚙️ Opções avançadas"):
    calc_pnl   = st.checkbox("Calcular PnL estimado (mais lento)", value=True)
    calc_early = st.checkbox("Detectar early buyers", value=True)
    calc_profile = st.checkbox("Buscar perfil completo das wallets", value=True)
    min_tokens_col, min_score_col = st.columns(2)
    with min_tokens_col:
        min_compras = st.number_input("Mínimo de compras por token", min_value=1, value=1)
    with min_score_col:
        min_score = st.slider("Score mínimo para exibir", 0, 100, 0)

run = st.button("🚀 Iniciar Scan")

if run:
    contratos = {
        "Token 1": (mint1.strip(), date_to_ts(from1), date_to_ts_end(to1)),
        "Token 2": (mint2.strip(), date_to_ts(from2), date_to_ts_end(to2)),
        "Token 3": (mint3.strip(), date_to_ts(from3), date_to_ts_end(to3)),
    }

    erros = [l for l,(m,_,_) in contratos.items() if not m or len(m) < 30]
    if erros:
        st.error(f"Preencha os contratos: {', '.join(erros)}")
        st.stop()

    st.markdown("---")
    st.markdown("## ⏳ Processando...")
    prog_bar  = st.progress(0)
    prog_text = st.empty()

    # Nomes e preços
    prog_text.text("Identificando tokens e buscando preços...")
    nomes = {}; simbolos = {}; precos = {}
    for label, (mint,_,_) in contratos.items():
        sym, name = get_token_name(mint)
        nomes[label]   = name
        simbolos[label] = sym
        precos[label]  = get_token_price(mint)
        prog_text.text(f"Token identificado: {sym} — preço atual: ${precos[label]:.8f}")

    # Coleta compradores
    compradores_por_token = {}
    launch_timestamps     = {}
    labels = list(contratos.keys())

    for i, (label, (mint, ts_from, ts_to)) in enumerate(contratos.items()):
        prog_bar.progress(int((i/3)*50))
        prog_text.text(f"Varrendo {label} ({simbolos[label]})...")
        comps, launch_ts = extrair_compradores(mint, f"{label} ({simbolos[label]})", ts_from, ts_to, prog_text)
        # Aplica filtro de mínimo de compras
        compradores_por_token[label] = {k:v for k,v in comps.items() if v["count"] >= min_compras}
        launch_timestamps[label] = launch_ts

    prog_bar.progress(55)
    prog_text.text("Calculando interseção...")

    sets       = [set(compradores_por_token[l].keys()) for l in labels]
    intersecao = sets[0] & sets[1] & sets[2]

    prog_text.text(f"Verificando {len(intersecao)} carteiras...")
    traders_confirmados = [a for a in intersecao if is_real_wallet(a)]

    prog_bar.progress(65)

    # ── Enriquecimento por wallet ───────────────────────────
    wallet_data = {}

    for i, wallet in enumerate(traders_confirmados):
        prog_bar.progress(65 + int((i / max(len(traders_confirmados),1)) * 30))
        prog_text.text(f"Enriquecendo wallet {i+1}/{len(traders_confirmados)}: {wallet[:14]}…")

        entry = {
            "wallet":   wallet,
            "profile":  {},
            "pnl":      {},   # label -> (custo, valor_atual, pnl_usd, pnl_pct)
            "early":    {},   # label -> minutes
            "score":    0,
        }

        # Perfil
        if calc_profile:
            entry["profile"] = get_wallet_profile(wallet)

        # Early buyer
        if calc_early:
            for label, (mint,_,_) in contratos.items():
                mins = get_early_buyer_rank(wallet, mint, launch_timestamps.get(label))
                entry["early"][label] = mins
                time.sleep(0.1)

        # PnL
        if calc_pnl:
            for label, (mint,_,_) in contratos.items():
                price = precos[label]
                comp  = compradores_por_token[label].get(wallet, {})
                c, v, p, pct = estimate_pnl(wallet, mint, price, comp)
                entry["pnl"][label] = (c, v, p, pct)

        # Score
        early_mins = [entry["early"].get(l) for l in labels]
        entry["score"] = calcular_score(
            wallet, compradores_por_token, entry["profile"], early_mins, len(labels)
        )

        wallet_data[wallet] = entry
        time.sleep(0.1)

    prog_bar.progress(100)
    prog_text.text("✅ Análise completa!")

    # Filtra por score mínimo
    traders_filtrados = [w for w in traders_confirmados
                         if wallet_data[w]["score"] >= min_score]

    # ── MÉTRICAS GERAIS ─────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Resultado")

    m1, m2, m3, m4, m5 = st.columns(5)
    total_txns = sum(
        sum(c.get("count",0) for c in compradores_por_token[l].values())
        for l in labels
    )
    m1.metric("Txns analisadas",      f"{total_txns:,}")
    m2.metric(f"{simbolos['Token 1']} traders", len(sets[0]))
    m3.metric(f"{simbolos['Token 2']} traders", len(sets[1]))
    m4.metric(f"{simbolos['Token 3']} traders", len(sets[2]))
    m5.metric("🎯 Compraram as 3",   len(traders_filtrados))

    # Ordena por score
    traders_filtrados.sort(key=lambda w: wallet_data[w]["score"], reverse=True)

    # ── TABELA RESUMO ───────────────────────────────────────
    if traders_filtrados:
        st.markdown("---")
        st.markdown(f"### 🏆 Ranking de Traders — {len(traders_filtrados)} wallets")

        rows = []
        for wallet in traders_filtrados:
            d   = wallet_data[wallet]
            sl, sc = score_label(d["score"])
            row = {
                "Score":  d["score"],
                "Nível":  sl,
                "Wallet": wallet,
                "SOL":    f"{d['profile'].get('sol_balance',0):.3f}",
                "Tokens Hold": d['profile'].get('token_count',0),
                "Trades 30d":  d['profile'].get('trades_30d',0),
                "Idade":       f"{d['profile'].get('age_days','?')} dias",
                "DEXes":       ", ".join(d['profile'].get('dexes_used', set())) or "—",
            }
            for label in labels:
                sym  = simbolos[label]
                comp = compradores_por_token[label].get(wallet,{})
                row[f"{sym} Compras"] = comp.get("count",0)
                row[f"{sym} Tokens"]  = f"{comp.get('amount',0):,.0f}"

                # Early
                mins = d["early"].get(label)
                row[f"{sym} Early"] = (
                    f"⚡ {mins:.0f}min" if mins is not None and mins <= 60
                    else f"{mins:.0f}min" if mins is not None
                    else "—"
                )

                # PnL
                pnl_data = d["pnl"].get(label, (None,None,None,None))
                _, v, p, pct = pnl_data
                if p is not None:
                    row[f"{sym} PnL"] = f"{'+'if p>=0 else ''}{p:.2f} USD ({pct:+.1f}%)"
                else:
                    row[f"{sym} PnL"] = "—"

            row["Solscan"] = f"https://solscan.io/account/{wallet}"
            row["Birdeye"] = f"https://birdeye.so/profile/{wallet}?chain=solana"
            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            column_config={
                "Score":   st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
                "Wallet":  st.column_config.TextColumn("Wallet", width=200),
                "Solscan": st.column_config.LinkColumn("Solscan ↗"),
                "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
            },
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV completo", csv, "traders_analise.csv", "text/csv")

        # ── CARDS DETALHADOS ────────────────────────────────
        st.markdown("---")
        st.markdown("### 🃏 Análise detalhada por wallet")

        for wallet in traders_filtrados:
            d    = wallet_data[wallet]
            prof = d["profile"]
            sc   = d["score"]
            sl, stag = score_label(sc)
            short = wallet[:6]+"…"+wallet[-6:]
            color = score_color(sc)

            with st.expander(f"{sl}  |  Score {sc}/100  |  {short}"):

                # Score bar
                st.markdown(
                    f'<div class="score-bar"><div class="score-fill" '
                    f'style="width:{sc}%;background:{color}"></div></div>',
                    unsafe_allow_html=True
                )
                st.markdown(f"**Score:** `{sc}/100`")
                st.code(wallet, language=None)

                # Perfil
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("SOL Balance",   f"{prof.get('sol_balance',0):.4f} SOL")
                pc2.metric("Token Accounts", prof.get("token_count","—"))
                pc3.metric("Trades (30d)",   prof.get("trades_30d","—"))
                pc4.metric("Idade Wallet",   f"{prof.get('age_days','?')} dias")

                if prof.get("first_tx_date"):
                    st.caption(f"Primeira transação: {prof['first_tx_date']}  |  Média: {prof.get('avg_tx_per_day',0)} txns/dia")

                dexes = prof.get("dexes_used", set())
                if dexes:
                    st.markdown("**DEXes usados:** " +
                        " ".join(f'<span class="tag tag-blue">{d}</span>' for d in dexes),
                        unsafe_allow_html=True)

                st.markdown("---")

                # Por token
                tcols = st.columns(len(labels))
                for i, label in enumerate(labels):
                    sym  = simbolos[label]
                    comp = compradores_por_token[label].get(wallet, {})
                    mins = d["early"].get(label)
                    pnl_data = d["pnl"].get(label, (None,None,None,None))
                    custo, valor, pnl_usd, pnl_pct = pnl_data

                    with tcols[i]:
                        st.markdown(f"**{sym}** — {nomes[label]}")
                        st.write(f"Compras: **{comp.get('count',0)}**")
                        st.write(f"Tokens: **{comp.get('amount',0):,.0f}**")
                        st.write(f"Última: **{time_ago(comp.get('last',0))}**")

                        # Early buyer
                        if mins is not None:
                            if mins <= 5:
                                st.markdown('<span class="tag tag-green">⚡ TOP EARLY &lt;5min</span>', unsafe_allow_html=True)
                            elif mins <= 30:
                                st.markdown(f'<span class="tag tag-green">⚡ Early {mins:.0f}min</span>', unsafe_allow_html=True)
                            elif mins <= 120:
                                st.markdown(f'<span class="tag tag-purple">Early {mins:.0f}min</span>', unsafe_allow_html=True)
                            else:
                                st.caption(f"Entrou {mins:.0f}min após lançamento")
                        else:
                            st.caption("Early: —")

                        # PnL
                        if pnl_usd is not None:
                            pnl_color = "green" if pnl_usd >= 0 else "red"
                            st.markdown(
                                f"PnL: **:{pnl_color}[{'+'if pnl_usd>=0 else ''}"
                                f"${pnl_usd:.2f} ({pnl_pct:+.1f}%)]**"
                            )
                            if custo:
                                st.caption(f"Custo est.: ${custo:.2f} → Atual: ${valor:.2f}")
                        elif valor is not None:
                            st.caption(f"Valor atual: ${valor:.2f}")

                        st.caption(f"Preço atual: ${precos[label]:.8f}")

                st.markdown(
                    f"[🔗 Solscan](https://solscan.io/account/{wallet}) · "
                    f"[🐦 Birdeye](https://birdeye.so/profile/{wallet}?chain=solana) · "
                    f"[📊 Step](https://step.finance/en/portfolio/{wallet})"
                )

        # ── BÔNUS 2 das 3 ───────────────────────────────────
        bonus_set = ((sets[0]&sets[1]) | (sets[0]&sets[2]) | (sets[1]&sets[2])) - (sets[0]&sets[1]&sets[2])
        if bonus_set:
            st.markdown("---")
            st.markdown(f"### ⭐ Traders que compraram 2 das 3 ({min(len(bonus_set),50)} mostrados)")
            bonus_traders = [a for a in list(bonus_set)[:50] if is_real_wallet(a)]
            if bonus_traders:
                bonus_rows = []
                for wallet in bonus_traders:
                    moedas = [simbolos[l] for j,l in enumerate(labels) if wallet in sets[j]]
                    bonus_rows.append({
                        "Wallet":  wallet,
                        "Comprou": " + ".join(moedas),
                        "Solscan": f"https://solscan.io/account/{wallet}",
                        "Birdeye": f"https://birdeye.so/profile/{wallet}?chain=solana",
                    })
                df2 = pd.DataFrame(bonus_rows)
                st.dataframe(df2,
                    column_config={
                        "Solscan": st.column_config.LinkColumn("Solscan ↗"),
                        "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
                    },
                    use_container_width=True, hide_index=True)
                csv2 = df2.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Baixar CSV bônus", csv2, "traders_2_tokens.csv", "text/csv")

    else:
        st.warning("Nenhum trader encontrado com os filtros selecionados.")
