"""로웰 밀러 스타일(『최고의 단일 투자』): 높은 품질 + 꾸준히 늘어나는 배당 + 적당한 수익률. 배당성장주 투자의 대표 이론.

주의: 밀러 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, dividend_checks, finish, pays_dividend, pct, scale

INFO = {
    "id": "miller",
    "name": "로웰 밀러",
    "mono": "밀",
    "tagline": "품질 좋은 기업의 '늘어나는 배당'에 장기 투자",
    "principles": [
        "배당을 계속 늘려 온 우량 기업일 것",
        "수익률이 높지 않아도 성장이 수익률을 키울 것 (현재 수익률 + 성장)",
        "배당이 이익과 현금흐름으로 충분히 감당될 것",
        "수익성(ROE)이 높고 재무가 튼튼할 것",
        "너무 비싸게 사지 않을 것",
    ],
    "price_rules": [
        "적정가 = 잉여현금흐름 기반 내재가치",
        "매수가 = 적정가에서 안전마진 15%를 뺀 가격",
        "매도가 = 적정가. 배당 성장이 꺾이면 팝니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 배당 삭감, 배당 성향 급등",
    ],
}
CFG = {"strong": (0.72, 0.0, 78), "buy": (0.62, -0.20, 64), "wait_q": 0.78, "hold": 50}
TAILS = {
    "strong": "품질, 배당 성장, 배당 안전성을 모두 갖춘 배당성장주입니다.",
    "buy": "배당이 늘어나는 우량주로 볼 만합니다.",
    "wait": "기업은 훌륭하지만 현재 가격이 비싼 편입니다.",
    "hold": "일부 조건만 충족합니다.",
    "pass": "배당 성장과 품질이 충분하지 않습니다.",
}


def evaluate(m):
    if not pays_dividend(m):
        return None
    checks = dividend_checks(m, yield_rng=(0.01, 0.035), cagr_rng=(0.02, 0.12), payout_cap=0.60,
                             w={"yield": 10, "growth": 30, "payout": 15, "cover": 10, "streak": 10})
    roe = m["roe_avg"]
    checks.append(check("수익성(ROE)", "quality", 15, 0.0 if roe is None else scale(roe, 0.08, 0.20),
                        f"최근 평균 ROE {pct(roe)} (기준 15% 이상)", ok=roe is not None and roe >= 0.15))
    d = m["debt_to_ni"]
    if m["is_financial"] or m["debt"] is None:
        checks.append(check("재무 안정", "quality", 10, None, "부채 지표를 적용하지 않음"))
    elif m["debt"] <= 0:
        checks.append(check("재무 안정", "quality", 10, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
    else:
        checks.append(check("재무 안정", "quality", 10, 0.0 if d is None else 1 - scale(d, 2, 6),
                            "순이익이 적자라 상환 능력 불충분" if d is None else f"총부채가 순이익의 {d:.1f}배", ok=d is not None and d <= 4))
    return finish(m, checks, CFG, TAILS, 0.15, 0.20)
