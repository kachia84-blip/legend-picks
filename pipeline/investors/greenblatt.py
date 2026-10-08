"""조엘 그린블라트 스타일: 마법공식. 자본수익률이 높고(좋은 기업) 이익수익률도 높은(싼 가격) 종목.

주의: 그린블라트 본인의 판단이 아니라 『주식시장을 이기는 작은 책』의 공식을 단순화한 모의 평가다.
(원 공식은 종목 간 순위를 매기지만, 여기서는 절대 기준으로 점수화했다. 금융업·유틸리티는 공식에서 제외한다.)
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "greenblatt",
    "name": "조엘 그린블라트",
    "mono": "블",
    "tagline": "마법공식. 좋은 기업을 싼 값에 (높은 ROIC + 높은 이익수익률)",
    "principles": [
        "이익수익률(EBIT ÷ 기업가치)이 높을 것 = 싼 가격",
        "투하자본수익률(ROIC)이 높을 것 = 좋은 기업",
        "이익이 적자로 무너지지 않을 것",
        "재무가 안전할 것",
        "금융업·유틸리티는 공식을 적용하지 않음",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 20%를 뺀 가격",
        "매도가 = 적정가. 마법공식은 보통 1년 보유 후 교체합니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 이익수익률·ROIC가 급락해 더 이상 공식 상위권이 아닐 때",
    ],
}
CFG = {"strong": (0.70, 0.0, 80), "buy": (0.60, -0.10, 65), "wait_q": 0.70, "hold": 50}
TAILS = {
    "strong": "자본수익률이 높은데 가격까지 싸서 마법공식 상위권 후보입니다.",
    "buy": "좋은 기업을 적당히 싼 가격에 살 수 있는 편입니다.",
    "wait": "기업은 좋지만 이익수익률이 낮아 가격이 부담됩니다.",
    "hold": "공식의 두 조건 중 하나가 아쉽습니다.",
    "pass": "자본수익률과 이익수익률이 모두 낮아 공식 상위권이 아닙니다.",
}


def evaluate(m):
    if m["is_financial"] or m["is_utility"]:
        return None  # 마법공식 대상 아님
    n = m["n_years"]
    checks = []

    ey = m["ev_ebit_yield"]
    checks.append(check("이익수익률", "price", 35, 0.0 if ey is None else scale(ey, 0.04, 0.14),
                        "EBIT 또는 기업가치 산출 불가" if ey is None else f"EBIT ÷ 기업가치 {pct(ey)} (기준 10% 이상)",
                        ok=ey is not None and ey >= 0.10))

    roic = m["roic"]
    if roic is None:
        checks.append(check("투하자본수익률", "quality", 35, None, "투하자본이 0 이하라 ROIC 산출 불가"))
    else:
        checks.append(check("투하자본수익률", "quality", 35, scale(min(roic, 0.6), 0.08, 0.30), f"ROIC {pct(roic)} (기준 20% 이상)", ok=roic >= 0.20))

    loss = m["loss_years"]
    checks.append(check("이익 안정성", "quality", 15, 1 - loss / n, f"최근 {n}년 중 적자 {loss}년", ok=loss == 0))

    if m["debt"] is None:
        checks.append(check("재무 안전", "quality", 15, None, "부채 데이터 없음"))
    elif m["debt"] <= 0:
        checks.append(check("재무 안전", "quality", 15, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
    else:
        d = m["debt_to_ni"]
        checks.append(check("재무 안전", "quality", 15, 0.0 if d is None else 1 - scale(d, 2, 8),
                            "순이익이 적자라 부채 상환 능력 불충분" if d is None else f"총부채가 순이익의 {d:.1f}배", ok=d is not None and d <= 4))
    return finish(m, checks, CFG, TAILS, 0.20, 0.20)
