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
    .stButton > button:hover { opacity: 0.85; }
    .date-box {
        background: #1a1d2e;
        border: 1px solid #2d2f45;
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 6px;
    }
    .date-label {
        font-size: 11px;
        color: #888;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
        font-family: monospace;
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

def extrair_compradores(mint, label, ts_from, ts_to, prog_text):
    """
    ts_from / ts_to: unix timestamps (int) ou None = sem limite
    Para de paginar quando a transação for mais antiga que ts_from.
    """
    compradores = {}
    before      = None
    total_tx    = 0
    pagina      = 0
    parou_por_data = False

    while True:
        pagina += 1
        try:
            batch = helius_txns(mint, before)
        except Exception as e:
            prog_text.warning(f"Erro pág {pagina}: {e} — aguardando 3s...")
            time.sleep(3)
            try:   batch = helius_txns(mint, before)
            except: break

        if not batch:
            break

        total_tx += len(batch)
        encontrados = 0

        for tx in batch:
            ts        = tx.get("timestamp", 0)
            fee_payer = tx.get("feePayer", "")

            # Se a transação é mais antiga que o início do timeframe → para
            if ts_from and ts < ts_from:
                parou_por_data = True
                break

            # Se a transação é mais recente que o fim do timeframe → pula
            if ts_to and ts > ts_to:
                continue

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
                encontrados += 1

        # Monta string do período para o log
        periodo = ""
        if ts_from or ts_to:
            f = datetime.fromtimestamp(ts_from).strftime("%d/%m/%Y") if ts_from else "início"
            t = datetime.fromtimestamp(ts_to).strftime("%d/%m/%Y")   if ts_to   else "hoje"
            periodo = f" | período: {f} → {t}"

        prog_text.text(
            f"📦 {label} — Pág {pagina} | {total_tx} txns analisadas | "
            f"{len(compradores)} traders{periodo}"
        )

        if parou_por_data:
            prog_text.text(f"📦 {label} — Limite de data atingido na pág {pagina}. ✅")
            break

        if len(batch) < 100:
            break

        before = batch[-1]["signature"]
        time.sleep(0.3)

    return compradores

def time_ago(ts):
    if not ts: return "—"
    diff = int(time.time()) - ts
    if diff < 3600:  return f"{diff//60}min atrás"
    if diff < 86400: return f"{diff//3600}h atrás"
    return f"{diff//86400}d atrás"

def date_to_ts(d):
    """Converte date → unix timestamp (início do dia, UTC)."""
    if d is None: return None
    return int(datetime(d.year, d.month, d.day, 0, 0, 0).timestamp())

def date_to_ts_end(d):
    """Converte date → unix timestamp (fim do dia, UTC)."""
    if d is None: return None
    return int(datetime(d.year, d.month, d.day, 23, 59, 59).timestamp())

# ── HEADER ──────────────────────────────────────────────────
st.markdown("# 🔍 Solana Trader Scanner")
st.markdown("##### Encontre wallets que compraram múltiplos tokens — apenas traders reais")
st.markdown("---")

# ── INPUTS DOS 3 TOKENS ─────────────────────────────────────
col1, col2, col3 = st.columns(3)

def token_block(col, num):
    with col:
        st.markdown(f"### Token {num}")
        mint = st.text_input(
            f"Contrato do Token {num}",
            placeholder="Cole o endereço do contrato...",
            key=f"mint{num}"
        )
        st.markdown(
            '<div class="date-label">⬇ FILTRAR POR DATA (opcional — deixe em branco para varrer tudo)</div>',
            unsafe_allow_html=True
        )
        dc1, dc2 = st.columns(2)
        with dc1:
            date_from = st.date_input(
                "De",
                value=None,
                min_value=date(2020, 1, 1),
                max_value=date.today(),
                key=f"from{num}",
                help="Data de início (inclusive). Deixe em branco para sem limite."
            )
        with dc2:
            date_to = st.date_input(
                "Até",
                value=None,
                min_value=date(2020, 1, 1),
                max_value=date.today(),
                key=f"to{num}",
                help="Data de fim (inclusive). Deixe em branco para hoje."
            )

        # Botão Reset para limpar as datas
        if st.button(f"🔄 Limpar datas", key=f"reset{num}"):
            st.session_state[f"from{num}"] = None
            st.session_state[f"to{num}"]   = None
            st.rerun()

        return mint, date_from, date_to

mint1, from1, to1 = token_block(col1, 1)
mint2, from2, to2 = token_block(col2, 2)
mint3, from3, to3 = token_block(col3, 3)

st.markdown("")
run = st.button("🚀 Iniciar Scan")

if run:
    contratos = {
        "Token 1": (mint1.strip(), date_to_ts(from1), date_to_ts_end(to1)),
        "Token 2": (mint2.strip(), date_to_ts(from2), date_to_ts_end(to2)),
        "Token 3": (mint3.strip(), date_to_ts(from3), date_to_ts_end(to3)),
    }

    # Validação
    erros = [l for l,(m,_,_) in contratos.items() if not m or len(m) < 30]
    if erros:
        st.error(f"Preencha os contratos: {', '.join(erros)}")
        st.stop()

    st.markdown("---")
    st.markdown("## ⏳ Processando...")

    prog_bar  = st.progress(0)
    prog_text = st.empty()

    # Nomes
    prog_text.text("Identificando tokens...")
    nomes = {}; simbolos = {}
    for label, (mint, _, _) in contratos.items():
        sym, name = get_token_name(mint)
        nomes[label]    = name
        simbolos[label] = sym

    # Coleta
    compradores_por_token = {}
    labels = list(contratos.keys())

    for i, (label, (mint, ts_from, ts_to)) in enumerate(contratos.items()):
        prog_bar.progress(int((i / 3) * 85))
        f_str = datetime.fromtimestamp(ts_from).strftime("%d/%m/%Y") if ts_from else "início"
        t_str = datetime.fromtimestamp(ts_to).strftime("%d/%m/%Y")   if ts_to   else "hoje"
        prog_text.text(f"Varrendo {label} ({simbolos[label]}) — {f_str} → {t_str}...")
        compradores_por_token[label] = extrair_compradores(
            mint, f"{label} ({simbolos[label]})", ts_from, ts_to, prog_text
        )

    prog_bar.progress(90)
    prog_text.text("Calculando interseção e verificando carteiras reais...")

    sets       = [set(compradores_por_token[l].keys()) for l in labels]
    intersecao = sets[0] & sets[1] & sets[2]

    traders_confirmados = []
    for addr in intersecao:
        if is_real_wallet(addr):
            traders_confirmados.append(addr)
        time.sleep(0.12)

    prog_bar.progress(100)
    prog_text.text("✅ Scan concluído!")

    # ── MÉTRICAS ────────────────────────────────────────────
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
    c1.metric("🎯 Compraram as 3 moedas", len(traders_confirmados))
    bonus_set = ((sets[0]&sets[1]) | (sets[0]&sets[2]) | (sets[1]&sets[2])) - (sets[0]&sets[1]&sets[2])
    c2.metric("⭐ Compraram 2 das 3", len(bonus_set))

    # ── TABELA PRINCIPAL ────────────────────────────────────
    if traders_confirmados:
        st.markdown("---")
        st.markdown(f"### 🎯 Wallets que compraram as 3 tokens ({len(traders_confirmados)})")

        rows = []
        for wallet in traders_confirmados:
            row = {"Wallet": wallet}
            for label in labels:
                info = compradores_por_token[label].get(wallet, {})
                sym  = simbolos[label]
                row[f"{sym} Compras"] = info.get("count", 0)
                row[f"{sym} Tokens"]  = f"{info.get('amount',0):,.0f}"
                row[f"{sym} Última"]  = time_ago(info.get("last", 0))
            row["Solscan"] = f"https://solscan.io/account/{wallet}"
            row["Birdeye"] = f"https://birdeye.so/profile/{wallet}?chain=solana"
            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            column_config={
                "Wallet":  st.column_config.TextColumn("Wallet", width=220),
                "Solscan": st.column_config.LinkColumn("Solscan ↗"),
                "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
            },
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV", csv, "traders_3_tokens.csv", "text/csv")

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
                st.markdown(
                    f"[🔗 Solscan](https://solscan.io/account/{wallet}) · "
                    f"[🐦 Birdeye](https://birdeye.so/profile/{wallet}?chain=solana)"
                )
    else:
        st.warning("Nenhuma wallet de trader real comprou as 3 tokens no período selecionado.")

    # ── BÔNUS 2 das 3 ───────────────────────────────────────
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
            st.dataframe(
                df2,
                column_config={
                    "Solscan": st.column_config.LinkColumn("Solscan ↗"),
                    "Birdeye": st.column_config.LinkColumn("Birdeye ↗"),
                },
                use_container_width=True,
                hide_index=True,
            )
            csv2 = df2.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Baixar CSV bônus", csv2, "traders_2_tokens.csv", "text/csv")
