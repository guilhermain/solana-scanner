"""
Coleta paralela de compradores por token.
Usa ThreadPoolExecutor para buscar múltiplos tokens ao mesmo tempo.
Fee payer = comprador real (elimina routers/intermediários).
"""
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

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
}

def _fetch_page(hapi_key: str, mint: str, before: str = None) -> list:
    url = f"https://api.helius.xyz/v0/addresses/{mint}/transactions?api-key={hapi_key}&limit=100"
    if before:
        url += f"&before={before}"
    r = requests.get(url, timeout=25)
    if not r.ok:
        raise Exception(f"HTTP {r.status_code}")
    return r.json() or []

def collect_buyers(
    mint: str,
    hapi_key: str,
    ts_from: int = None,
    ts_to: int = None,
    signal_ts: int = None,
    signal_window_minutes: int = 120,
    min_buys: int = 1,
    log_cb=None,
) -> dict:
    """
    Varre TODAS as transações do token e retorna compradores reais.

    Parâmetros:
    - ts_from/ts_to: janela de data ampla (filtro de data do calendário)
    - signal_ts: timestamp do sinal do Telegram
    - signal_window_minutes: compradores só nessa janela após o sinal
    - min_buys: mínimo de compras para considerar

    Retorna dict: addr -> {count, amount, first, last, sol_spent, buy_times}
    """
    compradores = {}
    before = None
    total_tx = 0
    pagina = 0
    launch_ts = None

    # Se tem signal_ts, o filtro temporal é mais restrito
    effective_from = ts_from
    effective_to   = ts_to
    if signal_ts:
        sig_start = signal_ts - (30 * 60)   # 30min antes do sinal
        sig_end   = signal_ts + (signal_window_minutes * 60)
        effective_from = max(ts_from, sig_start) if ts_from else sig_start
        effective_to   = min(ts_to,   sig_end)   if ts_to   else sig_end

    while True:
        pagina += 1
        try:
            batch = _fetch_page(hapi_key, mint, before)
        except Exception as e:
            if log_cb: log_cb(f"  ⚠ Erro pág {pagina}: {e} — retentando...")
            time.sleep(2)
            try:
                batch = _fetch_page(hapi_key, mint, before)
            except Exception as e2:
                if log_cb: log_cb(f"  ✗ Falha definitiva pág {pagina}: {e2}")
                break

        if not batch:
            break

        total_tx += len(batch)
        parou = False

        for tx in batch:
            ts        = tx.get("timestamp", 0)
            fee_payer = tx.get("feePayer", "")

            # Parar se passou da data mínima (txns são do mais recente ao mais antigo)
            if effective_from and ts < effective_from:
                parou = True
                break

            # Pular se fora da janela máxima
            if effective_to and ts > effective_to:
                continue

            # Guardar launch_ts (txn mais antiga processada)
            if launch_ts is None or ts < launch_ts:
                launch_ts = ts

            # Processar token transfers
            for tt in tx.get("tokenTransfers", []):
                if tt.get("mint", "") != mint:
                    continue
                dest   = tt.get("toUserAccount", "")
                amount = float(tt.get("tokenAmount", 0))

                if not dest or dest in SKIP_PROGRAMS or dest == mint:
                    continue

                # FEE PAYER = comprador real
                if dest != fee_payer:
                    continue

                if dest not in compradores:
                    compradores[dest] = {
                        "count": 0, "amount": 0.0,
                        "first": ts, "last": ts,
                        "sol_spent": 0.0,
                        "buy_times": [],
                    }

                compradores[dest]["count"]  += 1
                compradores[dest]["amount"] += amount
                compradores[dest]["buy_times"].append(ts)
                if ts < compradores[dest]["first"]: compradores[dest]["first"] = ts
                if ts > compradores[dest]["last"]:  compradores[dest]["last"]  = ts

            # Estimar SOL gasto (nativeTransfers de saída do fee_payer)
            if fee_payer and fee_payer in compradores:
                for nt in tx.get("nativeTransfers", []):
                    if nt.get("fromUserAccount") == fee_payer:
                        compradores[fee_payer]["sol_spent"] += nt.get("amount", 0) / 1e9

        if log_cb:
            periodo = ""
            if effective_from or effective_to:
                f = datetime.fromtimestamp(effective_from).strftime("%d/%m %H:%M") if effective_from else "início"
                t = datetime.fromtimestamp(effective_to).strftime("%d/%m %H:%M")   if effective_to   else "agora"
                periodo = f" | {f}→{t}"
            log_cb(f"  Pág {pagina:03d} | {total_tx} txns | {len(compradores)} compradores{periodo}")

        if parou or len(batch) < 100:
            break

        before = batch[-1]["signature"]
        time.sleep(0.25)

    # Aplica filtro mínimo de compras
    result = {k: v for k, v in compradores.items() if v["count"] >= min_buys}
    return result, launch_ts


def collect_all_parallel(tokens: list, hapi_key: str, log_queues: dict,
                         **kwargs) -> dict:
    """
    Coleta compradores de múltiplos tokens em paralelo.

    tokens: lista de dicts {label, mint, ts_from, ts_to, signal_ts, signal_window}
    Retorna: {label: (compradores_dict, launch_ts)}
    """
    results = {}

    def worker(token_info):
        label  = token_info["label"]
        mint   = token_info["mint"]
        log_q  = log_queues.get(label, [])

        def log_cb(msg):
            log_q.append(msg)

        comps, launch_ts = collect_buyers(
            mint        = mint,
            hapi_key    = hapi_key,
            ts_from     = token_info.get("ts_from"),
            ts_to       = token_info.get("ts_to"),
            signal_ts   = token_info.get("signal_ts"),
            signal_window_minutes = token_info.get("signal_window", 120),
            min_buys    = kwargs.get("min_buys", 1),
            log_cb      = log_cb,
        )
        return label, comps, launch_ts

    max_workers = min(len(tokens), 5)  # máx 5 threads simultâneas
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, t): t["label"] for t in tokens}
        for future in as_completed(futures):
            try:
                label, comps, launch_ts = future.result()
                results[label] = (comps, launch_ts)
            except Exception as e:
                label = futures[future]
                results[label] = ({}, None)
                log_queues.get(label, []).append(f"✗ Erro fatal: {e}")

    return results
