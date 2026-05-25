"""
Fingerprint comportamental de traders.
Analisa: horário de trade, tamanho de posição, DEX preferido,
velocidade de entrada, e funded_by (origem do SOL inicial).
"""
import requests
import time
from collections import Counter

DEX_NAMES = {
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter v6",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter v4",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "Jupiter v3",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM",
    "27haf8L6oxUeXrHrgEgsexjSY5hbVUWEmvv9Nyxg8vQv": "Raydium CLMM",
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": "Orca",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc" : "Orca Whirlpool",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "Meteora DLMM",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "Raydium CPMM",
    "DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M": "Jupiter DCA",
    "opnb2LAfJYbRMAHHvqjCwQxanZn7n7YzmjMERkCDHMT" : "OpenBook",
}

def get_funded_by(addr: str, rpc_url: str) -> str | None:
    """
    Retorna o endereço que financiou (enviou SOL inicial) para esta wallet.
    Pega a transação mais antiga e verifica quem enviou SOL.
    """
    try:
        r = requests.post(rpc_url,
            json={"jsonrpc":"2.0","id":1,"method":"getSignaturesForAddress",
                  "params":[addr,{"limit":1000,"commitment":"finalized"}]},
            timeout=15)
        sigs = r.json().get("result",[])
        if not sigs: return None

        # Pega a transação mais antiga
        oldest = sigs[-1]
        r2 = requests.post(rpc_url,
            json={"jsonrpc":"2.0","id":2,"method":"getTransaction",
                  "params":[oldest["signature"],
                            {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}]},
            timeout=15)
        tx = r2.json().get("result")
        if not tx: return None

        # Procura quem enviou SOL para este endereço
        for nt in tx.get("meta",{}).get("innerInstructions",[]):
            pass  # não necessário aqui

        # nativeTransfers é mais direto
        for nt in tx.get("meta",{}).get("postTokenBalances",[]):
            pass

        # Tenta via accountKeys + preBalances/postBalances
        accs = [a.get("pubkey","") for a in
                tx.get("transaction",{}).get("message",{}).get("accountKeys",[])]
        pre  = tx.get("meta",{}).get("preBalances",[])
        post = tx.get("meta",{}).get("postBalances",[])

        funder = None
        for i, acc in enumerate(accs):
            if acc == addr and i < len(pre) and i < len(post):
                if post[i] > pre[i]:  # recebeu SOL
                    # Quem perdeu SOL nessa tx é o funder
                    for j, acc2 in enumerate(accs):
                        if acc2 != addr and j < len(pre) and j < len(post):
                            if pre[j] > post[j]:
                                funder = acc2
                                break
        return funder
    except:
        return None


def get_wallet_fingerprint(addr: str, rpc_url: str,
                           compradores_por_token: dict) -> dict:
    """
    Gera fingerprint comportamental da wallet.
    """
    fp = {
        "addr":           addr,
        "sol_balance":    0.0,
        "token_accounts": 0,
        "trades_30d":     0,
        "age_days":       None,
        "first_tx_date":  None,
        "avg_tx_day":     0.0,
        "dex_preferred":  None,
        "dexes_used":     set(),
        "avg_position_sol": 0.0,
        "trade_hours":    [],       # horas UTC das compras
        "funded_by":      None,
        "early_minutes":  {},       # label -> minutos após lançamento
    }

    # Saldo SOL
    try:
        r = requests.post(rpc_url,
            json={"jsonrpc":"2.0","id":1,"method":"getBalance",
                  "params":[addr,{"commitment":"finalized"}]}, timeout=8)
        fp["sol_balance"] = r.json().get("result",{}).get("value",0)/1e9
    except: pass

    # Token accounts
    try:
        r = requests.post(rpc_url,
            json={"jsonrpc":"2.0","id":2,"method":"getTokenAccountsByOwner",
                  "params":[addr,
                    {"programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding":"base64","dataSlice":{"offset":0,"length":0}}]},
            timeout=8)
        fp["token_accounts"] = len(r.json().get("result",{}).get("value",[]))
    except: pass

    # Histórico de assinaturas
    try:
        r = requests.post(rpc_url,
            json={"jsonrpc":"2.0","id":3,"method":"getSignaturesForAddress",
                  "params":[addr,{"limit":1000,"commitment":"finalized"}]},
            timeout=15)
        sigs = r.json().get("result",[])
        if sigs:
            ts30 = int(time.time()) - (30*86400)
            fp["trades_30d"] = len([s for s in sigs if s.get("blockTime",0)>=ts30])
            all_ts = [s.get("blockTime",0) for s in sigs if s.get("blockTime")]
            if all_ts:
                oldest_ts = min(all_ts)
                age = (int(time.time())-oldest_ts)/86400
                fp["age_days"]      = round(age, 1)
                fp["first_tx_date"] = __import__('datetime').datetime.fromtimestamp(oldest_ts).strftime("%d/%m/%Y")
                if age > 0: fp["avg_tx_day"] = round(len(sigs)/age, 2)

        # DEXes usados (amostra 20 txns)
        dex_counter = Counter()
        for s in sigs[:20]:
            try:
                r2 = requests.post(rpc_url,
                    json={"jsonrpc":"2.0","id":4,"method":"getTransaction",
                          "params":[s["signature"],
                            {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}]},
                    timeout=10)
                tx = r2.json().get("result")
                if tx:
                    for acc in tx.get("transaction",{}).get("message",{}).get("accountKeys",[]):
                        pk = acc.get("pubkey","")
                        if pk in DEX_NAMES:
                            dex_counter[DEX_NAMES[pk]] += 1
                            fp["dexes_used"].add(DEX_NAMES[pk])
            except: pass
            time.sleep(0.08)

        if dex_counter:
            fp["dex_preferred"] = dex_counter.most_common(1)[0][0]
    except: pass

    # Horários de compra e posição média em SOL
    all_buy_times = []
    all_sol_spent = []
    for label, comp_map in compradores_por_token.items():
        comp = comp_map.get(addr, {})
        if comp:
            all_buy_times.extend(comp.get("buy_times", []))
            sol = comp.get("sol_spent", 0)
            if sol > 0: all_sol_spent.append(sol)

    fp["trade_hours"] = [
        __import__('datetime').datetime.fromtimestamp(ts).hour
        for ts in all_buy_times
    ]
    if all_sol_spent:
        fp["avg_position_sol"] = round(sum(all_sol_spent)/len(all_sol_spent), 4)

    # Funded by
    fp["funded_by"] = get_funded_by(addr, rpc_url)

    return fp


def group_by_funder(wallet_fps: list) -> dict:
    """
    Agrupa wallets que têm o mesmo funded_by.
    Wallets com mesmo funder = provavelmente mesmo dono.
    """
    groups = {}
    for fp in wallet_fps:
        funder = fp.get("funded_by")
        if funder and funder != "11111111111111111111111111111111":
            if funder not in groups:
                groups[funder] = []
            groups[funder].append(fp["addr"])
    # Só retorna grupos com 2+ wallets
    return {k: v for k, v in groups.items() if len(v) >= 2}


def similarity_score(fp1: dict, fp2: dict) -> int:
    """
    Compara dois fingerprints e retorna score de similaridade 0-100.
    Quanto maior, mais provável que sejam o mesmo trader.
    """
    score = 0

    # DEX preferido igual
    if fp1.get("dex_preferred") and fp1["dex_preferred"] == fp2.get("dex_preferred"):
        score += 25

    # Tamanho de posição parecido (±30%)
    p1 = fp1.get("avg_position_sol", 0)
    p2 = fp2.get("avg_position_sol", 0)
    if p1 > 0 and p2 > 0:
        ratio = min(p1,p2)/max(p1,p2)
        if ratio >= 0.7: score += 25
        elif ratio >= 0.4: score += 10

    # Horários de trade parecidos
    h1 = fp1.get("trade_hours", [])
    h2 = fp2.get("trade_hours", [])
    if h1 and h2:
        avg1 = sum(h1)/len(h1)
        avg2 = sum(h2)/len(h2)
        if abs(avg1-avg2) <= 2: score += 20
        elif abs(avg1-avg2) <= 4: score += 10

    # Mesmo funder
    if (fp1.get("funded_by") and
        fp1["funded_by"] == fp2.get("funded_by") and
        fp1["funded_by"] != "11111111111111111111111111111111"):
        score += 30

    return min(100, score)
