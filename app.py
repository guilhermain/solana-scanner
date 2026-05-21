import streamlit as st
import requests
import time
import pandas as pd

# ── Configuração da página ──────────────────────────────────
st.set_page_config(
    page_title="Solana Trader Scanner",
    page_icon="🔍",
    layout="wide"
)

# ── CSS customizado ─────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .stApp { background-color: #0f1117; }
    h1 { color: #14F195 !important; font-family: monospace; }
    h2, h3 { color: #9945FF !important; font-family: monospace; }
    .metric-card {
        background: #1a1d2e;
        border: 1px solid #2d2f45;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .wallet-card {
        background: #1a1d2e;
        border: 1px solid #14F195;
        border-radius: 8px;
        padding: 15px;
        margin: 8px 0;
        font-family: monospace;
    }
    .tag {
        background: #14F195;
        color: #0f1117;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        margin-right: 4px;
    }
    .tag-purple {
        background: #9945FF;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        margin-right: 4px;
    }
    .stTextInput > div > div > input {
        background-color: #1a1d2e;
        color: #ffffff;
        border: 1px solid #2d2f45;
        font-family: monospace;
        font-size: 13px;
    }
    .stButton > button {
        background: linear-gradient(90deg, #9945FF, #14F195);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 30px;
        font-weight: bold;
        font-size: 16px;
        width: 100%;
    }
    .stButton > button:hover {
        opacity: 0.85;
        border: none;
    }
    div[data-testid="stProgress"] > div {
        background-color: #14F195;
    }
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
                if sym: return f"{sym}", f"{name}"
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

def extrair_compradores(mint, label, log_area, prog_bar, prog_text):
    compradores = {}
    before      = None
    total_tx    = 0
    pagina      = 0

    while True:
        pagina += 1
        try:
            batch = helius_txns(mint, before)
        except Exception as e:
            log_area.warning(f"Erro pág {pagina}: {e} — tentando novamente...")
            time.sleep(3)
            try: batch = helius_txns(mint, before)
            except: break

        if not batch: break

        total_tx += len(batch)

        for tx in batch:
            ts        = tx.get("timestamp", 0)
            fee_payer = tx.get("feePayer", "")
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

        prog_text.text(f"📦 {label} — Página {pagina} | {total_tx} transações | {len(compradores)} traders encontrados")

        if len(batch) < 100: break
        before = batch[-1]["signature"]
        time.sleep(0.3)

    return compradores

def time_ago(ts):
    if not ts: return "—"
    diff = int(time.time()) - ts
    if diff < 3600:  return f"{diff//60}min atrás"
    if diff < 86400: return f"{diff//3600}h atrás"
    return f"{diff//86400}d atrás"

# ── INTERFACE ───────────────────────────────────────────────
st.markdown("# 🔍 Solana Trader Scanner")
st.markdown("##### Encontre wallets que compraram múltiplos tokens — apenas traders reais")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Token 1")
    mint1 = st.text_input("Contrato da Moeda 1", placeholder="Cole o endereço do contrato...", key="m1")

with col2:
    st.markdown("### Token 2")
    mint2 = st.text_input("Contrato da Moeda 2", placeholder="Cole o endereço do contrato...", key="m2")

with col3:
    st.markdown("### Token 3")
    mint3 = st.text_input("Contrato da Moeda 3", placeholder="Cole o endereço do contrato...", key="m3")

st.markdown("")
run = st.button("🚀 Iniciar Scan")

if run:
    contratos = {"Token 1": mint1.strip(), "Token 2": mint2.strip(), "Token 3": mint3.strip()}

    # Validação
    erros = [l for l, m in contratos.items() if not m or len(m) < 30]
    if erros:
        st.error(f"Preencha os contratos: {', '.join(erros)}")
        st.stop()

    st.markdown("---")
    st.markdown("## ⏳ Processando...")

    # Progresso
    prog_bar  = st.progress(0)
    prog_text = st.empty()
    log_area  = st.empty()

    # Nomes dos tokens
    prog_text.text("Identificando tokens...")
    nomes = {}
    simbolos = {}
    for label, mint in contratos.items():
        sym, name = get_token_name(mint)
        nomes[label]    = name
        simbolos[label] = sym

    # Coleta
    compradores_por_token = {}
    labels = list(contratos.keys())

    for i, (label, mint) in enumerate(contratos.items()):
        log_area.info(f"Varrendo {label} ({simbolos[label]})...")
        prog_bar.progress((i * 30) // 100)
        compradores_por_token[label] = extrair_compradores(
            mint, f"{label} ({simbolos[label]})", log_area, prog_bar, prog_text
        )

    prog_bar.progress(90)
    prog_text.text("Calculando interseção e verificando carteiras...")

    sets = [set(compradores_por_token[l].keys()) for l in labels]
    intersecao = sets[0] & sets[1] & sets[2]

    log_area.info(f"Interseção bruta: {len(intersecao)} endereços — verificando se são carteiras reais...")

    traders_confirmados = []
    for addr in intersecao:
        if is_real_wallet(addr):
            traders_confirmados.append(addr)
        time.sleep(0.12)

    prog_bar.progress(100)
    prog_text.text("✅ Scan concluído!")
    log_area.empty()

    # ── MÉTRICAS ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Resultado")

    m1, m2, m3, m4 = st.columns(4)
    total_txns = sum(
        sum(c.get("count",0) for c in compradores_por_token[l].values())
        for l in labels
    )
    m1.metric("Transações analisadas", f"{total_txns:,}")
    m2.metric(f"Traders {simbolos['Token 1']}", len(sets[0]))
    m3.metric(f"Traders {simbolos['Token 2']}", len(sets[1]))
    m4.metric(f"Traders {simbolos['Token 3']}", len(sets[2]))

    st.markdown("")
    c1, c2 = st.columns(2)
    c1.metric("🎯 Compraram as 3 moedas", len(traders_confirmados),
              help="Wallets de traders reais que compraram os 3 tokens")
    bonus_set = ((sets[0]&sets[1]) | (sets[0]&sets[2]) | (sets[1]&sets[2])) - (sets[0]&sets[1]&sets[2])
    c2.metric("⭐ Compraram 2 das 3", len(bonus_set))

    # ── TABELA DE RESULTADOS ───────────────────────────────
    if traders_confirmados:
        st.markdown("---")
        st.markdown(f"### 🎯 Wallets que compraram as 3 moedas ({len(traders_confirmados)})")

        rows = []
        for wallet in traders_confirmados:
            row = {"Wallet": wallet}
            for label in labels:
                info = compradores_por_token[label].get(wallet, {})
                sym  = simbolos[label]
                row[f"{sym} — Compras"]  = info.get("count", 0)
                row[f"{sym} — Tokens"]   = f"{info.get('amount',0):,.0f}"
                row[f"{sym} — Última"]   = time_ago(info.get("last", 0))
            row["Solscan"] = f"https://solscan.io/account/{wallet}"
            row["Birdeye"] = f"https://birdeye.so/profile/{wallet}?chain=solana"
            rows.append(row)

        df = pd.DataFrame(rows)

        # Tabela interativa
        st.dataframe(
            df,
            column_config={
                "Wallet": st.column_config.TextColumn("Wallet", width=200),
                "Solscan": st.column_config.LinkColumn("Solscan ↗"),
                "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
            },
            use_container_width=True,
            hide_index=True,
        )

        # Download CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Baixar resultado em CSV",
            data=csv,
            file_name="traders_3_moedas.csv",
            mime="text/csv",
        )

        # Cards individuais
        st.markdown("---")
        st.markdown("### 🃏 Detalhe por wallet")
        for wallet in traders_confirmados:
            short = wallet[:6] + "…" + wallet[-6:]
            with st.expander(f"🟢 {short}  —  {wallet}"):
                cols = st.columns(3)
                for i, label in enumerate(labels):
                    info = compradores_por_token[label].get(wallet, {})
                    sym  = simbolos[label]
                    with cols[i]:
                        st.markdown(f"**{sym}**")
                        st.write(f"Compras: **{info.get('count',0)}**")
                        st.write(f"Tokens: **{info.get('amount',0):,.0f}**")
                        st.write(f"Última: **{time_ago(info.get('last',0))}**")
                st.markdown(f"[🔗 Solscan](https://solscan.io/account/{wallet}) · "
                            f"[🐦 Birdeye](https://birdeye.so/profile/{wallet}?chain=solana)")
    else:
        st.warning("Nenhuma wallet de trader real comprou as 3 moedas. Verifique os contratos.")

    # ── BÔNUS: 2 das 3 ─────────────────────────────────────
    if bonus_set:
        st.markdown("---")
        st.markdown(f"### ⭐ Traders que compraram 2 das 3 moedas ({min(len(bonus_set),50)} mostrados)")
        bonus_traders = [a for a in list(bonus_set)[:50] if is_real_wallet(a)]

        bonus_rows = []
        for wallet in bonus_traders:
            moedas_compradas = [simbolos[l] for j,l in enumerate(labels) if wallet in sets[j]]
            bonus_rows.append({
                "Wallet":   wallet,
                "Comprou":  " + ".join(moedas_compradas),
                "Solscan":  f"https://solscan.io/account/{wallet}",
                "Birdeye":  f"https://birdeye.so/profile/{wallet}?chain=solana",
            })

        if bonus_rows:
            df_bonus = pd.DataFrame(bonus_rows)
            st.dataframe(
                df_bonus,
                column_config={
                    "Solscan": st.column_config.LinkColumn("Solscan ↗"),
                    "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
                },
                use_container_width=True,
                hide_index=True,
            )
            csv2 = df_bonus.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Baixar bônus CSV", csv2, "traders_2_moedas.csv", "text/csv")
