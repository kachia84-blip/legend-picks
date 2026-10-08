"""제러미 시겔 스타일(『주식에 장기투자하라』): 배당 성장 우량주를 합리적 PER에 사서 배당을 재투자.

주의: 시겔 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, dividend_checks, finish, pays_dividend, scale

INFO = {
    "id": "siegel",
    "name": "제러미 시겔",
    "mono": "시",
    "tagline": "배당을 재투자하는 장기투자. 배당 성장주를 합리적 가격에",
    "principles": [
        "꾸준히 배당하고 배당을 늘려 온 기업일 것",
        "배당수익률이 시장 평균(약 2%)보다 높을 것",
        "PER이 지나치게 비싸지 않을 것 (20배 이하)",
        "너무 높은 배당(함정)은 경계하고 이익으로 배당이 감당될 것",
    ],
    "price_rules": [
        "적정가 = 잉여현금흐름 기반 내재가치",
        "매수가 = 적정가에서 안전마진 15%를 뺀 가격",
        "매도가 = 적정가. PER이 크게 오르면 팝니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 배당 삭감, 이익 감소",
    ],
}
CFG = {"strong": (0.68, 0.0, 76), "buy": (0.58, -0.20, 62), "wait_q": 0.75, "hold": 48}
TAILS = {
    "strong": "배당 성장과 합리적 가격을 함께 갖춘 장기 배당 투자 후보입니다.",
    "buy": "배당 성장주로 투자할 만하고 가격도 무리가 없습니다.",
    "wait": "배당 성장주지만 PER이 높아 가격 부담이 있습니다.",
    "hold": "일부 조건만 충족합니다.",
    "pass": "배당 성장과 가격 조건을 충분히 만족하지 못합니다.",
}


def evaluate(m):
    if not pays_dividend(m):
        return None
    checks = dividend_checks(m, yield_rng=(0.02, 0.04), cagr_rng=(0.0, 0.10), payout_cap=0.65,
                             w={"yield": 20, "growth": 20, "payout": 10, "cover": 10, "streak": 10})
    per = m["per"]
    checks.append(check("합리적 PER", "price", 20, 0.0 if per is None else 1 - scale(per, 12, 28),
                        "순이익이 적자라 PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 20배 이하)", ok=per is not None and per <= 20))
    return finish(m, checks, CFG, TAILS, 0.15, 0.20)
