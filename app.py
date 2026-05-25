import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

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
  .tag-green{background:#14F19522;color:#14F195;border:1px solid #14F19555}
  .tag-purple{background:#9945FF22;color:#9945FF;border:1px solid #9945FF55}
  .tag-orange{background:#FF914D22;color:#FF914D;border:1px solid #FF914D55}
  .tag-red{background:#FF4D4D22;color:#FF4D4D;border:1px solid #FF4D4D55}
  .tag-blue{background:#4D9FFF22;color:#4D9FFF;border:1px solid #4D9FFF55}
  .tag-yellow{background:#FFD70022;color:#FFD700;border:1px solid #FFD70055}
  .funder-box{background:#1a1d2e;border:1px solid #FFD700;border-radius:8px;padding:10px;margin:6px 0}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════
KEY = "befa16a2-ae3a-4b39-a830-0f5631a4f2e2"
RPC = f"https://mainnet.helius-rpc.com/?api-key={KEY}"
HAPI = "https://api.helius.xyz/v0"

SYSTEM_PROGRAM = "11111111111111111111111111111111"

SKIP = {
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
    "SysvarEpochSchedu1e111111111111111111111111",
    "SysvarRecentB1ockHashes11111111111111111111",
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "27haf8L6oxUeXrHrgEgsexjSY5hbVUWEmvv9Nyxg8vQv",
    "5quBtoiQqxF9Jv6KYKctB59NT3gtJD2Y65kdnB1Uev3h",
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
    "DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M",
    "opnb2LAfJYbRMAHHvqjCwQxanZn7n7YzmjMERkCDHMT",
    "srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX",
    "routeUGWgWzqBWFcrCfv8tritsqukccJPu3q5GPP3xS",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",
    "MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2pgJqp",
    "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K",
    "worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth",
    "namesLPAMHSKApHKFZ8Rm2janYTMTB98M5n8B8voseb",
    "SSwpkEEcbUqx4vtoEByFjSkhKdCT862DNVb52nZg1UZ",
    "GFXsSL5sSaDfNFQUYsHekbWBW1TsFdjDYzACh62tEHxn",
    "BSwp6bEBihVLdqkRKGcCftHRHgFqp41KxdJLTTra7aq1",
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

# ══════════════════════════════════════════════════════════
#  CACHE DE SESSÃO
# ══════════════════════════════════════════════════════════
if "mint_cache" not in st.session_state:
    st.session_state.mint_cache = {}

def cache_get(mint):
    return st.session_state.mint_cache.get(mint)

def cache_set(mint, data):
    st.session_state.mint_cache[mint] = data

def cache_clear():
    st.session_state.mint_cache = {}

def cache_list():
    return list(st.session_state.mint_cache.keys())

# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════
def time_ago(ts):
    if not ts: return "—"
    d = int(time.time()) - ts
    if d < 3600:  return f"{d//60}min atrás"
    if d < 86400: return f"{d//3600}h atrás"
    return f"{d//86400}d atrás"

def date_to_ts(d, end=False):
    if not d: return None
    h, m, s = (23,59,59) if end else (0,0,0)
    return int(datetime(d.year, d.month, d.day, h, m, s).timestamp())

def str_to_ts(date_str, time_str):
    try:
        return int(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").timestamp())
    except: return None

def get_token_meta(mint):
    try:
        r = requests.post(f"{HAPI}/token-metadata?api-key={KEY}",
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

# ══════════════════════════════════════════════════════════
#  COLETA DE COMPRADORES (1 token)
# ══════════════════════════════════════════════════════════
def collect_buyers(mint, ts_from=None, ts_to=None,
                   signal_ts=None, signal_window=120,
                   min_buys=1, log_cb=None):
    compradores = {}
    before = None
    total_tx = 0
    pagina = 0
    launch_ts = None

    # Janela temporal efetiva
    eff_from = ts_from
    eff_to   = ts_to
    if signal_ts:
        sig_start = signal_ts - 30*60
        sig_end   = signal_ts + signal_window*60
        eff_from  = max(ts_from, sig_start) if ts_from else sig_start
        eff_to    = min(ts_to,   sig_end)   if ts_to   else sig_end

    while True:
        pagina += 1
        for attempt in range(2):
            try:
                url = f"{HAPI}/addresses/{mint}/transactions?api-key={KEY}&limit=100"
                if before: url += f"&before={before}"
                r = requests.get(url, timeout=25)
                if not r.ok: raise Exception(f"HTTP {r.status_code}")
                batch = r.json() or []
                break
            except Exception as e:
                if attempt == 0: time.sleep(2)
                else:
                    if log_cb: log_cb(f"  ✗ Pág {pagina}: {e}")
                    return {k:v for k,v in compradores.items() if v["count"]>=min_buys}, launch_ts

        if not batch: break
        total_tx += len(batch)
        parou = False

        for tx in batch:
            ts        = tx.get("timestamp", 0)
            fee_payer = tx.get("feePayer", "")

            if eff_from and ts < eff_from: parou = True; break
            if eff_to   and ts > eff_to:   continue

            if launch_ts is None or ts < launch_ts:
                launch_ts = ts

            for tt in tx.get("tokenTransfers", []):
                if tt.get("mint","") != mint: continue
                dest   = tt.get("toUserAccount","")
                amount = float(tt.get("tokenAmount",0))
                if not dest or dest in SKIP or dest == mint: continue
                if dest != fee_payer: continue

                if dest not in compradores:
                    compradores[dest] = {"count":0,"amount":0.0,"first":ts,"last":ts,
                                         "sol_spent":0.0,"buy_times":[]}
                compradores[dest]["count"]  += 1
                compradores[dest]["amount"] += amount
                compradores[dest]["buy_times"].append(ts)
                if ts < compradores[dest]["first"]: compradores[dest]["first"] = ts
                if ts > compradores[dest]["last"]:  compradores[dest]["last"]  = ts

            if fee_payer and fee_payer in compradores:
                for nt in tx.get("nativeTransfers",[]):
                    if nt.get("fromUserAccount") == fee_payer:
                        compradores[fee_payer]["sol_spent"] += nt.get("amount",0)/1e9

        periodo = ""
        if eff_from or eff_to:
            f = datetime.fromtimestamp(eff_from).strftime("%d/%m %H:%M") if eff_from else "início"
            t = datetime.fromtimestamp(eff_to).strftime("%d/%m %H:%M")   if eff_to   else "agora"
            periodo = f" | {f}→{t}"
        if log_cb:
            log_cb(f"  Pág {pagina:03d} | {total_tx} txns | {len(compradores)} compradores{periodo}")

        if parou or len(batch) < 100: break
        before = batch[-1]["signature"]
        time.sleep(0.25)

    return {k:v for k,v in compradores.items() if v["count"]>=min_buys}, launch_ts

# ══════════════════════════════════════════════════════════
#  COLETA PARALELA (múltiplos tokens)
# ══════════════════════════════════════════════════════════
def collect_all_parallel(token_configs, log_queues, min_buys=1):
    results = {}

    def worker(tc):
        label = tc["label"]
        lq    = log_queues.setdefault(label, [])
        comps, launch_ts = collect_buyers(
            mint           = tc["mint"],
            ts_from        = tc.get("ts_from"),
            ts_to          = tc.get("ts_to"),
            signal_ts      = tc.get("signal_ts"),
            signal_window  = tc.get("signal_window", 120),
            min_buys       = min_buys,
            log_cb         = lq.append,
        )
        return label, comps, launch_ts

    with ThreadPoolExecutor(max_workers=min(len(token_configs), 5)) as ex:
        futures = {ex.submit(worker, tc): tc["label"] for tc in token_configs}
        for fut in as_completed(futures):
            try:
                label, comps, launch_ts = fut.result()
                results[label] = (comps, launch_ts)
            except Exception as e:
                label = futures[fut]
                results[label] = ({}, None)
                log_queues.setdefault(label,[]).append(f"✗ Erro fatal: {e}")

    return results

# ══════════════════════════════════════════════════════════
#  FILTRO HUMANO — lote de 100 via getMultipleAccounts
# ══════════════════════════════════════════════════════════
def batch_filter_humans(addresses, progress_cb=None):
    humans = []
    batch_size = 100

    for i in range(0, len(addresses), batch_size):
        batch = [a for a in addresses[i:i+batch_size] if a not in SKIP]
        if not batch: continue
        if progress_cb: progress_cb(i, len(addresses), batch[0])

        try:
            r = requests.post(RPC,
                json={"jsonrpc":"2.0","id":i,"method":"getMultipleAccounts",
                      "params":[batch,{"encoding":"base64"}]},
                timeout=15)
            if not r.ok:
                humans.extend(batch); continue

            values = r.json().get("result",{}).get("value",[])
            for addr, val in zip(batch, values):
                if val is None:
                    humans.append(addr); continue  # conta nova → inclui
                if val.get("executable", False): continue
                if val.get("owner","") != SYSTEM_PROGRAM: continue
                humans.append(addr)
        except:
            humans.extend(batch)

        time.sleep(0.15)

    return humans

# ══════════════════════════════════════════════════════════
#  FINGERPRINT COMPORTAMENTAL
# ══════════════════════════════════════════════════════════
def get_fingerprint(addr, compradores_por_token):
    fp = {"sol_balance":0.0,"token_accounts":0,"trades_30d":0,
          "age_days":None,"first_tx_date":None,"avg_tx_day":0.0,
          "dex_preferred":None,"dexes_used":set(),
          "avg_position_sol":0.0,"trade_hours":[],"funded_by":None}
    try:
        r = requests.post(RPC, json={"jsonrpc":"2.0","id":1,"method":"getBalance",
            "params":[addr,{"commitment":"finalized"}]}, timeout=8)
        fp["sol_balance"] = r.json().get("result",{}).get("value",0)/1e9
    except: pass

    try:
        r = requests.post(RPC, json={"jsonrpc":"2.0","id":2,
            "method":"getTokenAccountsByOwner",
            "params":[addr,{"programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                      {"encoding":"base64","dataSlice":{"offset":0,"length":0}}]}, timeout=8)
        fp["token_accounts"] = len(r.json().get("result",{}).get("value",[]))
    except: pass

    try:
        r = requests.post(RPC, json={"jsonrpc":"2.0","id":3,
            "method":"getSignaturesForAddress",
            "params":[addr,{"limit":1000,"commitment":"finalized"}]}, timeout=15)
        sigs = r.json().get("result",[])
        if sigs:
            ts30 = int(time.time())-30*86400
            fp["trades_30d"] = len([s for s in sigs if s.get("blockTime",0)>=ts30])
            all_ts = [s.get("blockTime",0) for s in sigs if s.get("blockTime")]
            if all_ts:
                oldest = min(all_ts)
                age = (int(time.time())-oldest)/86400
                fp["age_days"]     = round(age,1)
                fp["first_tx_date"]= datetime.fromtimestamp(oldest).strftime("%d/%m/%Y")
                if age>0: fp["avg_tx_day"] = round(len(sigs)/age,2)

            dex_counter = Counter()
            for s in sigs[:15]:
                try:
                    r2 = requests.post(RPC, json={"jsonrpc":"2.0","id":4,
                        "method":"getTransaction",
                        "params":[s["signature"],
                          {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}]}, timeout=10)
                    tx = r2.json().get("result")
                    if tx:
                        for acc in tx.get("transaction",{}).get("message",{}).get("accountKeys",[]):
                            pk = acc.get("pubkey","")
                            if pk in DEX_NAMES:
                                dex_counter[DEX_NAMES[pk]] += 1
                                fp["dexes_used"].add(DEX_NAMES[pk])
                except: pass
                time.sleep(0.07)

            if dex_counter:
                fp["dex_preferred"] = dex_counter.most_common(1)[0][0]

            # Funded by (txn mais antiga)
            oldest_sig = sigs[-1].get("signature","")
            if oldest_sig:
                try:
                    r3 = requests.post(RPC, json={"jsonrpc":"2.0","id":5,
                        "method":"getTransaction",
                        "params":[oldest_sig,
                          {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}]}, timeout=10)
                    tx = r3.json().get("result")
                    if tx:
                        accs = [a.get("pubkey","") for a in
                                tx.get("transaction",{}).get("message",{}).get("accountKeys",[])]
                        pre  = tx.get("meta",{}).get("preBalances",[])
                        post = tx.get("meta",{}).get("postBalances",[])
                        for i2,acc in enumerate(accs):
                            if acc==addr and i2<len(pre) and i2<len(post) and post[i2]>pre[i2]:
                                for j,acc2 in enumerate(accs):
                                    if acc2!=addr and j<len(pre) and j<len(post) and pre[j]>post[j]:
                                        fp["funded_by"]=acc2; break
                                break
                except: pass
    except: pass

    # Horários e posição média
    all_times=[]; all_sol=[]
    for l,cm in compradores_por_token.items():
        comp=cm.get(addr,{})
        if comp:
            all_times.extend(comp.get("buy_times",[]))
            s=comp.get("sol_spent",0)
            if s>0: all_sol.append(s)
    fp["trade_hours"]=[datetime.fromtimestamp(ts).hour for ts in all_times]
    if all_sol: fp["avg_position_sol"]=round(sum(all_sol)/len(all_sol),4)

    return fp

# ══════════════════════════════════════════════════════════
#  SCORE
# ══════════════════════════════════════════════════════════
def calc_score(wallet, compradores_por_token, fp, total_tokens):
    s=0
    tokens_bought=sum(1 for l in compradores_por_token if wallet in compradores_por_token[l])
    s+=min(25,int((tokens_bought/total_tokens)*25))
    t30=fp.get("trades_30d",0)
    if t30>=100: s+=20
    elif t30>=50: s+=15
    elif t30>=20: s+=10
    elif t30>=5:  s+=5
    sol=fp.get("sol_balance",0)
    if sol>=10: s+=10
    elif sol>=1: s+=7
    elif sol>=0.1: s+=4
    elif sol>0: s+=2
    tkc=fp.get("token_accounts",0)
    if tkc>=20: s+=10
    elif tkc>=10: s+=7
    elif tkc>=3: s+=4
    elif tkc>=1: s+=2
    for l,cm in compradores_por_token.items():
        comp=cm.get(wallet,{})
        em=comp.get("early_minutes")
        if em is not None:
            if em<=5: s+=20; break
            elif em<=15: s+=15; break
            elif em<=60: s+=10; break
            elif em<=240: s+=5; break
    if fp.get("dex_preferred"): s+=5
    pos=fp.get("avg_position_sol",0)
    if pos>=1: s+=10
    elif pos>=0.1: s+=6
    elif pos>0: s+=3
    return min(100,s)

def score_label(s):
    if s>=75: return "🟢 ELITE",    "green"
    if s>=50: return "🟣 SÓLIDO",   "purple"
    if s>=25: return "🟠 INICIANTE","orange"
    return           "🔴 FRACO",    "red"

def score_color(s):
    if s>=75: return "#14F195"
    if s>=50: return "#9945FF"
    if s>=25: return "#FF914D"
    return          "#FF4D4D"

def sim_score(fp1, fp2):
    s=0
    if fp1.get("dex_preferred") and fp1["dex_preferred"]==fp2.get("dex_preferred"): s+=25
    p1=fp1.get("avg_position_sol",0); p2=fp2.get("avg_position_sol",0)
    if p1>0 and p2>0:
        r=min(p1,p2)/max(p1,p2)
        if r>=0.7: s+=25
        elif r>=0.4: s+=10
    h1=fp1.get("trade_hours",[]); h2=fp2.get("trade_hours",[])
    if h1 and h2:
        diff=abs(sum(h1)/len(h1)-sum(h2)/len(h2))
        if diff<=2: s+=20
        elif diff<=4: s+=10
    f1=fp1.get("funded_by"); f2=fp2.get("funded_by")
    if f1 and f1==f2 and f1!=SYSTEM_PROGRAM: s+=30
    return min(100,s)

# ══════════════════════════════════════════════════════════
#  ESTADO
# ══════════════════════════════════════════════════════════
if "n_tokens" not in st.session_state:
    st.session_state.n_tokens = 2

# ══════════════════════════════════════════════════════════
#  INTERFACE
# ══════════════════════════════════════════════════════════
st.markdown("# 🔍 Solana Trader Scanner")
st.markdown("##### Triangule traders de grupos de Telegram — paralelo, preciso, sem falsos positivos")

cached_mints = cache_list()
if cached_mints:
    col_cache1, col_cache2 = st.columns([4,1])
    with col_cache1:
        st.info(f"💾 Cache ativo: {len(cached_mints)} token(s) já coletados — não serão rebuscados")
    with col_cache2:
        if st.button("🗑 Limpar cache"): cache_clear(); st.rerun()

st.markdown("---")

# Controles de quantidade
c1,c2,c3 = st.columns([3,1,1])
with c1: st.markdown(f"**{st.session_state.n_tokens} token(s) adicionado(s)**  ·  Mínimo: 2  ·  Máximo: 10  ·  Coleta em paralelo")
with c2:
    if st.button("➕ Adicionar token", disabled=st.session_state.n_tokens>=10):
        st.session_state.n_tokens+=1; st.rerun()
with c3:
    if st.button("➖ Remover último", disabled=st.session_state.n_tokens<=2):
        n=st.session_state.n_tokens
        for k in [f"mint{n}",f"from{n}",f"to{n}",f"sig_date{n}",f"sig_time{n}",f"sig_win{n}"]:
            st.session_state.pop(k,None)
        st.session_state.n_tokens-=1; st.rerun()

st.markdown("")

# Cards dos tokens
n = st.session_state.n_tokens
for row_start in range(0, n, 3):
    cols = st.columns(min(3, n-row_start))
    for ci, num in enumerate(range(row_start+1, min(row_start+4, n+1))):
        with cols[ci]:
            with st.container(border=True):
                st.markdown(f"**Token {num}**")
                mint_v = st.text_input("Contrato", placeholder="Endereço do contrato...",
                    key=f"mint{num}", label_visibility="collapsed")

                cached = cache_get(mint_v) if mint_v and len(mint_v)>=30 else None
                if cached:
                    st.markdown(f'<span class="tag tag-green">💾 {cached.get("symbol","")}</span>',
                        unsafe_allow_html=True)

                st.caption("📅 Janela de data (opcional)")
                da,db = st.columns(2)
                with da: st.date_input("De",  value=None, key=f"from{num}",
                    min_value=date(2020,1,1), max_value=date.today())
                with db: st.date_input("Até", value=None, key=f"to{num}",
                    min_value=date(2020,1,1), max_value=date.today())

                st.caption("📡 Sinal do Telegram (opcional)")
                sa,sb = st.columns(2)
                with sa: st.date_input("Data do sinal", value=None, key=f"sig_date{num}",
                    min_value=date(2020,1,1), max_value=date.today())
                with sb: st.text_input("Hora (HH:MM)", placeholder="14:30", key=f"sig_time{num}")

                st.number_input("Janela após sinal (min)", min_value=5, max_value=1440,
                    value=120, key=f"sig_win{num}")

                if st.button("🔄 Limpar", key=f"reset{num}"):
                    for k in [f"from{num}",f"to{num}",f"sig_date{num}",f"sig_time{num}"]:
                        st.session_state.pop(k,None)
                    st.rerun()

st.markdown("---")

with st.expander("⚙️ Opções avançadas"):
    oa1,oa2,oa3 = st.columns(3)
    with oa1:
        calc_fp     = st.checkbox("Fingerprint comportamental", value=True)
        calc_funder = st.checkbox("Detectar wallets do mesmo dono", value=True)
        show_sim    = st.checkbox("Similaridade entre wallets", value=True)
    with oa2:
        min_buys      = st.number_input("Mínimo de compras por token", 1, 20, 1)
        min_intersect = st.number_input("Mínimo de tokens comprados", 2, n, 2)
        min_score     = st.slider("Score mínimo", 0, 100, 0)
    with oa3:
        use_cache = st.checkbox("Usar cache", value=True)

run = st.button("🚀 Iniciar Scan")

if run:
    token_configs=[]
    erros=[]
    for num in range(1,n+1):
        mint_v = st.session_state.get(f"mint{num}","").strip()
        if not mint_v or len(mint_v)<30: erros.append(f"Token {num}"); continue
        sig_d = st.session_state.get(f"sig_date{num}")
        sig_t = st.session_state.get(f"sig_time{num}","")
        token_configs.append({
            "label":        f"Token {num}",
            "mint":         mint_v,
            "ts_from":      date_to_ts(st.session_state.get(f"from{num}")),
            "ts_to":        date_to_ts(st.session_state.get(f"to{num}"), end=True),
            "signal_ts":    str_to_ts(str(sig_d), sig_t) if sig_d and sig_t else None,
            "signal_window":int(st.session_state.get(f"sig_win{num}", 120)),
        })

    if erros: st.error(f"Preencha os contratos: {', '.join(erros)}"); st.stop()
    if min_intersect>len(token_configs): st.error("Mínimo de tokens > tokens adicionados"); st.stop()

    st.markdown("---")
    st.markdown("## ⏳ Processando...")
    prog  = st.progress(0)
    ptext = st.empty()
    logs  = st.container()

    # Nomes e preços
    ptext.text("Identificando tokens...")
    simbolos={}; nomes={}; precos={}
    for tc in token_configs:
        cd = cache_get(tc["mint"]) if use_cache else None
        if cd:
            simbolos[tc["label"]]=cd.get("symbol","?")
            nomes[tc["label"]]=cd.get("name","")
            precos[tc["label"]]=cd.get("price",0.0)
        else:
            sym,name=get_token_meta(tc["mint"])
            simbolos[tc["label"]]=sym; nomes[tc["label"]]=name
            precos[tc["label"]]=get_token_price(tc["mint"])
    prog.progress(5)

    # Coleta paralela
    ptext.text("🚀 Coletando em paralelo...")
    to_collect=[]; compradores_por_token={}; launch_ts_map={}
    for tc in token_configs:
        cd = cache_get(tc["mint"]) if use_cache else None
        if cd and "compradores" in cd:
            compradores_por_token[tc["label"]]=cd["compradores"]
            launch_ts_map[tc["label"]]=cd.get("launch_ts")
            with logs: st.success(f"💾 {tc['label']} ({simbolos[tc['label']]}) — do cache ({len(cd['compradores'])} compradores)")
        else:
            to_collect.append(tc)

    if to_collect:
        log_queues={}
        results=collect_all_parallel(to_collect, log_queues, min_buys=min_buys)
        for tc in to_collect:
            label=tc["label"]
            comps,lts=results.get(label,({},None))
            compradores_por_token[label]=comps
            launch_ts_map[label]=lts
            if use_cache:
                cache_set(tc["mint"],{"symbol":simbolos[label],"name":nomes[label],
                    "price":precos[label],"compradores":comps,"launch_ts":lts})
            with logs:
                with st.expander(f"📦 Log — {label} ({simbolos[label]}) — {len(comps)} compradores"):
                    for msg in log_queues.get(label,[]): st.text(msg)

    prog.progress(55)

    # Interseção
    ptext.text("Calculando interseção...")
    labels=[tc["label"] for tc in token_configs]
    sets={l:set(compradores_por_token.get(l,{}).keys()) for l in labels}
    wtc={}
    for l,s in sets.items():
        for w in s: wtc[w]=wtc.get(w,0)+1
    candidatos=[w for w,c in wtc.items() if c>=min_intersect]

    ptext.text(f"Filtrando {len(candidatos)} candidatos (isOnCurve + System Program owner)...")

    def prog_cb(done,total,addr):
        prog.progress(55+int((done/max(total,1))*20))
        ptext.text(f"Filtrando: {done}/{total} — {addr[:14]}…")

    traders=batch_filter_humans(candidatos, prog_cb)
    prog.progress(75)

    # Calcula early minutes
    for label in labels:
        lts=launch_ts_map.get(label)
        for w,comp in compradores_por_token.get(label,{}).items():
            if lts and comp.get("first"):
                mins=(comp["first"]-lts)/60
                comp["early_minutes"]=round(mins,1) if mins>=0 else None
            else:
                comp["early_minutes"]=None

    # Fingerprint e score
    wallet_data={}
    for i,w in enumerate(traders):
        prog.progress(75+int((i/max(len(traders),1))*22))
        ptext.text(f"Analisando {i+1}/{len(traders)}: {w[:14]}…")
        fp=get_fingerprint(w,compradores_por_token) if calc_fp else {}
        sc=calc_score(w,compradores_por_token,fp,len(labels))
        wallet_data[w]={"fp":fp,"score":sc,"tokens":wtc.get(w,0)}
        time.sleep(0.05)

    prog.progress(100)
    ptext.text("✅ Análise completa!")

    traders_ok=sorted([w for w in traders if wallet_data[w]["score"]>=min_score],
                      key=lambda w:wallet_data[w]["score"],reverse=True)

    # Detecta mesmo funder
    funder_groups={}
    if calc_funder and traders_ok:
        for w in traders_ok:
            fb=wallet_data[w]["fp"].get("funded_by")
            if fb and fb!=SYSTEM_PROGRAM:
                funder_groups.setdefault(fb,[]).append(w)
        funder_groups={k:v for k,v in funder_groups.items() if len(v)>=2}

    # ── RESULTADO ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Resultado")

    mcols=st.columns(len(labels)+3)
    total_txns=sum(sum(c.get("count",0) for c in compradores_por_token.get(l,{}).values()) for l in labels)
    mcols[0].metric("Txns analisadas",f"{total_txns:,}")
    for i,l in enumerate(labels): mcols[i+1].metric(simbolos[l],len(sets[l]))
    mcols[-2].metric(f"≥{min_intersect} tokens",len(traders))
    mcols[-1].metric("🎯 No ranking",len(traders_ok))

    if funder_groups:
        st.markdown("---")
        st.markdown("### 🔗 Wallets do mesmo dono")
        for funder,wallets in funder_groups.items():
            html=(''.join(f'<code style="display:block;margin:2px">{w}</code>' for w in wallets))
            st.markdown(
                f'<div class="funder-box"><span class="tag tag-yellow">MESMO DONO</span> '
                f'Funder: <code>{funder[:24]}…</code><br>{html}'
                f'<a href="https://solscan.io/account/{funder}" target="_blank" '
                f'style="color:#FFD700;font-size:11px">Ver funder ↗</a></div>',
                unsafe_allow_html=True)

    if not traders_ok:
        st.warning("Nenhum trader encontrado. Tente reduzir o score mínimo ou o mínimo de tokens comprados.")
        st.stop()

    # Tabela ranking
    st.markdown("---")
    st.markdown(f"### 🏆 Ranking — {len(traders_ok)} wallets")
    rows=[]
    for w in traders_ok:
        d=wallet_data[w]; fp=d["fp"]; sl,_=score_label(d["score"])
        row={"Score":d["score"],"Nível":sl,f"Tokens ({len(labels)})":d["tokens"],
             "Wallet":w,"SOL":f"{fp.get('sol_balance',0):.3f}",
             "Token Accs":fp.get("token_accounts","—"),"Trades 30d":fp.get("trades_30d","—"),
             "Idade":f"{fp.get('age_days','nova')} dias" if fp.get("age_days") else "nova",
             "DEX":fp.get("dex_preferred","—"),"Pos SOL":f"{fp.get('avg_position_sol',0):.4f}"}
        for l in labels:
            sym=simbolos[l]; comp=compradores_por_token.get(l,{}).get(w,{})
            em=comp.get("early_minutes") if comp else None
            row[f"{sym} Early"]=(f"⚡{em:.0f}m" if em is not None and em<=60 else f"{em:.0f}m" if em is not None else "—")
            row[f"{sym} Compras"]=comp.get("count",0) if comp else 0
        row["Solscan"]=f"https://solscan.io/account/{w}"
        row["Birdeye"]=f"https://birdeye.so/profile/{w}?chain=solana"
        rows.append(row)

    df=pd.DataFrame(rows)
    st.dataframe(df,column_config={
        "Score":st.column_config.ProgressColumn("Score",min_value=0,max_value=100,format="%d"),
        "Wallet":st.column_config.TextColumn("Wallet",width=210),
        "Solscan":st.column_config.LinkColumn("Solscan ↗"),
        "Birdeye":st.column_config.LinkColumn("Birdeye ↗"),
    },use_container_width=True,hide_index=True)

    csv=df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV",csv,"traders.csv","text/csv")

    # Cards detalhados
    st.markdown("---")
    st.markdown("### 🃏 Perfil detalhado")
    for w in traders_ok:
        d=wallet_data[w]; fp=d["fp"]; sc=d["score"]
        sl,_=score_label(sc); color=score_color(sc)
        short=w[:6]+"…"+w[-6:]
        in_grp=any(w in wl for wl in funder_groups.values())

        with st.expander(f"{sl} | {sc}/100 | {d['tokens']}/{len(labels)} tokens | {short}"):
            st.markdown(f'<div class="score-bar"><div class="score-fill" style="width:{sc}%;background:{color}"></div></div>',unsafe_allow_html=True)
            st.code(w,language=None)
            if in_grp: st.markdown('<span class="tag tag-yellow">🔗 MESMO DONO</span>',unsafe_allow_html=True)

            p1,p2,p3,p4,p5=st.columns(5)
            p1.metric("SOL",f"{fp.get('sol_balance',0):.4f}")
            p2.metric("Token Accs",fp.get("token_accounts","—"))
            p3.metric("Trades 30d",fp.get("trades_30d","—"))
            p4.metric("Pos. média",f"{fp.get('avg_position_sol',0):.3f} SOL")
            p5.metric("Idade",f"{fp.get('age_days','nova')} dias" if fp.get("age_days") else "nova")

            if fp.get("first_tx_date"):
                st.caption(f"Primeira tx: {fp['first_tx_date']} · {fp.get('avg_tx_day',0)} txns/dia")

            dexes=fp.get("dexes_used",set())
            if dexes:
                pref=fp.get("dex_preferred","")
                st.markdown("**DEXes:** "+" ".join(
                    f'<span class="tag {"tag-green" if d==pref else "tag-blue"}">{"⭐ " if d==pref else ""}{d}</span>'
                    for d in dexes),unsafe_allow_html=True)

            if fp.get("funded_by"):
                st.markdown(f'**Financiado por:** <a href="https://solscan.io/account/{fp["funded_by"]}" target="_blank" style="color:#FFD700;font-family:monospace">{fp["funded_by"][:24]}…</a>',unsafe_allow_html=True)

            st.markdown("---")
            for cs in range(0,len(labels),4):
                chunk=labels[cs:cs+4]
                tcols=st.columns(len(chunk))
                for ci,label in enumerate(chunk):
                    sym=simbolos[label]
                    comp=compradores_por_token.get(label,{}).get(w,{})
                    em=comp.get("early_minutes") if comp else None
                    with tcols[ci]:
                        st.markdown(f"**{sym}**")
                        if comp:
                            st.write(f"Compras: **{comp.get('count',0)}**")
                            st.write(f"Tokens: **{comp.get('amount',0):,.0f}**")
                            st.write(f"Última: **{time_ago(comp.get('last',0))}**")
                            sol=comp.get("sol_spent",0)
                            if sol>0: st.write(f"SOL gasto: **{sol:.3f}**")
                            if em is not None:
                                tag="tag-green" if em<=30 else "tag-purple" if em<=120 else "tag-orange"
                                st.markdown(f'<span class="tag {tag}">⚡ {em:.0f}min após launch</span>',unsafe_allow_html=True)
                        else:
                            st.caption("Não comprou este token")

            if show_sim and len(traders_ok)>1:
                st.markdown("---")
                st.caption("**Similaridade com outras wallets:**")
                fp1={"addr":w,**fp}
                sims=[(o,sim_score(fp1,{"addr":o,**wallet_data[o]["fp"]})) for o in traders_ok if o!=w]
                sims=[x for x in sims if x[1]>=40]
                sims.sort(key=lambda x:-x[1])
                if sims:
                    for other,sim in sims[:3]:
                        c2="#14F195" if sim>=70 else "#FF914D"
                        st.markdown(f'<span style="font-family:monospace;font-size:11px">{other[:10]}… — <span style="color:{c2};font-weight:bold">{sim}% similar</span></span>',unsafe_allow_html=True)
                else:
                    st.caption("Nenhuma similaridade >40% encontrada.")

            st.markdown(f"[🔗 Solscan](https://solscan.io/account/{w}) · [🐦 Birdeye](https://birdeye.so/profile/{w}?chain=solana) · [📊 Step](https://step.finance/en/portfolio/{w})")
