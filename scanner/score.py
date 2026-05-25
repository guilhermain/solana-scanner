"""
Score consolidado de confiança do trader (0-100).
Pondera múltiplos fatores sem penalizar wallets novas.
"""

def calcular_score(wallet: str, compradores_por_token: dict,
                   fp: dict, total_tokens: int, min_intersect: int) -> int:
    score = 0

    # 1. Quantos tokens comprou vs total (25 pts)
    tokens_comprados = sum(1 for l in compradores_por_token
                           if wallet in compradores_por_token[l])
    score += min(25, int((tokens_comprados / total_tokens) * 25))

    # 2. Frequência de trades 30d (20 pts)
    t30 = fp.get("trades_30d", 0)
    if   t30 >= 100: score += 20
    elif t30 >= 50:  score += 15
    elif t30 >= 20:  score += 10
    elif t30 >= 5:   score += 5

    # 3. Saldo SOL (10 pts) — sem penalizar contas novas com pouco SOL
    sol = fp.get("sol_balance", 0)
    if   sol >= 10:  score += 10
    elif sol >= 1:   score += 7
    elif sol >= 0.1: score += 4
    elif sol > 0:    score += 2

    # 4. Token accounts (10 pts) — diversidade de tokens operados
    tkc = fp.get("token_accounts", 0)
    if   tkc >= 20: score += 10
    elif tkc >= 10: score += 7
    elif tkc >= 3:  score += 4
    elif tkc >= 1:  score += 2

    # 5. Early buyer em algum token (20 pts)
    for label, comp in compradores_por_token.items():
        info = comp.get(wallet, {})
        early = info.get("early_minutes")
        if early is not None:
            if   early <= 5:   score += 20; break
            elif early <= 15:  score += 15; break
            elif early <= 60:  score += 10; break
            elif early <= 240: score += 5;  break

    # 6. Tem DEX preferido definido (5 pts) — usa sempre o mesmo DEX = padrão humano
    if fp.get("dex_preferred"):
        score += 5

    # 7. Posição SOL média > 0 (10 pts) — gastou SOL real
    pos = fp.get("avg_position_sol", 0)
    if   pos >= 1:    score += 10
    elif pos >= 0.1:  score += 6
    elif pos > 0:     score += 3

    return min(100, score)


def score_label(s: int) -> tuple:
    if s >= 75: return "🟢 ELITE",     "green"
    if s >= 50: return "🟣 SÓLIDO",    "purple"
    if s >= 25: return "🟠 INICIANTE", "orange"
    return              "🔴 FRACO",     "red"

def score_color(s: int) -> str:
    if s >= 75: return "#14F195"
    if s >= 50: return "#9945FF"
    if s >= 25: return "#FF914D"
    return              "#FF4D4D"
