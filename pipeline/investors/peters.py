"""조슈아 피터스 스타일(『The Ultimate Dividend Playbook』): 배당수익률 + 배당 성장률 = 총수익, 그리고 배당 안전.

주의: 피터스 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, ddm_iv, dividend_checks, finish, pays_dividend, pct, scale

INFO = {
    "id": "peters",
    "name": "조슈아 피터스",
    "mono": "피",
    "tagline": "배당수익률 + 배당 성장률로 총수익을 계산하는 배당 투자자",
    "principles": [
        "총수익 추정 = 배당수익률 + 배당 성장률이 높을 것 (10% 안팎이 이상적)",
        "배당이 이익과 현금흐름으로 안전하게 감당될 것",
        "배당을 삭감한 적이 없을 것",
        "재무가 튼튼하고 적자가 없을 것",
    ],
    "price_rules": [
        "적정가 = 배당할인모형(요구수익률 9%, 배당 성장 반영)으로 계산한 값",
        "매수가 = 적정가에서 안전마진 10%를 뺀 가격",
        "매도가 = 적정가. 총수익 추정이 낮아지면 팝니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 배당 삭감, 배당 성향 급등",
    ],
}
CFG = {"strong": (0.70, 0.0, 76), "buy": (0.60, -0.15, 62), "wait_q": 0.75, "hold": 48}
TAILS = {
    "strong": "배당과 배당 성장을 합친 총수익 추정이 높고 배당도 안전합니다.",
    "buy": "총수익 추정이 괜찮은 안전한 배당주입니다.",
    "wait": "배당은 안전하지만 총수익 추정이 낮습니다.",
    "hold": "일부 조건만 충족합니다.",
    "pass": "총수익 추정과 안전성이 충분하지 않습니다.",
}


def evaluate(m):
    if not pays_dividend(m):
        return None
    dy, g = m["div_yield"], m["div_cagr"]
    tr = dy * 100 + (min(g, 0.15) * 100 if g is not None else 0.0)
    checks = [check("총수익 추정(수익률+성장)", "price", 35, scale(tr, 4, 12),
                    f"배당수익률 {pct(dy)} + 배당 성장 {pct(g)} = {tr:.1f}% (기준 10% 이상)", ok=tr >= 8)]
    checks += dividend_checks(m, yield_rng=(0.02, 0.05), cagr_rng=(0.0, 0.10), payout_cap=0.65,
                              w={"yield": 0, "growth": 10, "payout": 20, "cover": 15, "streak": 10})
    loss, n = m["loss_years"], m["n_years"]
    checks.append(check("흑자 유지", "quality", 10, 1 - loss / n, f"최근 {n}년 중 적자 {loss}년", ok=loss == 0))
    return finish(m, checks, CFG, TAILS, 0.10, 0.20, iv=ddm_iv(m))
