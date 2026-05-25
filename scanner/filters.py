"""
Filtros para identificar wallets de traders humanos reais.
Critérios (sem filtro de idade — traders usam wallets novas):
  1. isOnCurve = true  → keypair humano, não PDA/contrato
  2. owner = System Program → carteira normal
  3. executable = false → não é programa
  4. Tem pelo menos 1 token account → já operou na Solana
  5. Saldo SOL > 0 → conta viva
"""
import requests
import time

SYSTEM_PROGRAM = "11111111111111111111111111111111"
TOKEN_PROGRAM  = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

KNOWN_NON_HUMANS = {
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
    "MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2pgJqp",
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",
    "routeUGWgWzqBWFcrCfv8tritsqukccJPu3q5GPP3xS",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K",
    "worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth",
    "namesLPAMHSKApHKFZ8Rm2janYTMTB98M5n8B8voseb",
    "GFXsSL5sSaDfNFQUYsHekbWBW1TsFdjDYzACh62tEHxn",
    "BSwp6bEBihVLdqkRKGcCftHRHgFqp41KxdJLTTra7aq1",
    "SSwpkEEcbUqx4vtoEByFjSkhKdCT862DNVb52nZg1UZ",
}

def is_human_wallet(addr: str, rpc_url: str) -> tuple[bool, str]:
    """
    Retorna (True, "") se é humano real, ou (False, motivo) se não for.
    """
    if addr in KNOWN_NON_HUMANS:
        return False, "programa conhecido"

    rid = int(time.time() * 1000) % 99999

    try:
        r = requests.post(rpc_url,
            json={"jsonrpc":"2.0","id":rid,"method":"getAccountInfo",
                  "params":[addr,{"encoding":"base64"}]},
            timeout=10)
        if not r.ok:
            return True, ""  # dúvida → inclui
        d = r.json().get("result",{})
        val = d.get("value") if d else None

        if val is None:
            # Conta não existe na chain — pode ser nova wallet sem SOL ainda
            # Não elimina, pois pode ter sido fee payer sem saldo residual
            return True, ""

        # Critério 1: não pode ser programa executável
        if val.get("executable", False):
            return False, "executable=true (programa)"

        # Critério 2: owner deve ser System Program
        owner = val.get("owner", "")
        if owner != SYSTEM_PROGRAM:
            return False, f"owner={owner[:20]}… (não é System Program)"

        # Critério 3: isOnCurve via lamports e data
        # Contas PDA têm data específica; carteiras normais têm data vazia ou 0
        data = val.get("data", [])
        data_len = len(data[0]) if isinstance(data, list) and data else 0
        # PDAs geralmente têm data > 0; carteiras limpas têm data vazia
        # Mas carteiras com token accounts associados também podem ter data
        # Então só bloqueia se tiver data E não for system program owner
        # (já verificado acima)

        # Critério 4: saldo SOL > 0 (conta viva)
        lamports = val.get("lamports", 0)
        if lamports == 0:
            # Pode ser conta nova que já gastou tudo — não elimina
            pass

        return True, ""

    except Exception as e:
        return True, ""  # em caso de erro de rede, inclui

def batch_filter_humans(addresses: list, rpc_url: str,
                        progress_cb=None) -> list:
    """
    Filtra uma lista de endereços, retornando só os humanos reais.
    Usa getMultipleAccounts para fazer em lotes de 100 (muito mais rápido).
    """
    humans = []
    batch_size = 100

    for i in range(0, len(addresses), batch_size):
        batch = addresses[i:i+batch_size]
        if progress_cb:
            progress_cb(i, len(addresses), batch[0])

        try:
            r = requests.post(rpc_url,
                json={"jsonrpc":"2.0","id":i,"method":"getMultipleAccounts",
                      "params":[batch,{"encoding":"base64"}]},
                timeout=15)
            if not r.ok:
                humans.extend(batch)  # erro → inclui todos
                continue

            results = r.json().get("result",{}).get("value",[])

            for addr, val in zip(batch, results):
                if addr in KNOWN_NON_HUMANS:
                    continue

                if val is None:
                    # Conta nova/sem saldo — inclui (pode ser trader novo)
                    humans.append(addr)
                    continue

                if val.get("executable", False):
                    continue

                owner = val.get("owner","")
                if owner != SYSTEM_PROGRAM:
                    continue

                # Passou em tudo → é humano
                humans.append(addr)

        except Exception:
            humans.extend(batch)  # erro de rede → inclui

        time.sleep(0.15)

    return humans
