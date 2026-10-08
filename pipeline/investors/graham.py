"""벤저민 그레이엄 스타일: 방어적 가치투자. 싸고 튼튼한 기업을 충분한 안전마진으로.

주의: 그레이엄 본인의 판단이 아니라 『현명한 투자자』의 기준을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "graham",
    "name": "벤저민 그레이엄",
    "mono": "그",
    "tagline": "가치투자의 아버지. 싸고 튼튼한 기업을 큰 안전마진으로",
    "principles": [
        "PER이 낮을 것 (15배 이하)",
        "PBR이 낮을 것 (1.5배 이하)",
        "PER × PBR 이 22.5 이하일 것 (그레이엄 수)",
        "유동자산이 유동부채의 2배 이상, 부채는 자본 이내",
        "적자 없이 이익이 꾸준하고 배당을 계속 줄 것",
        "내재가치보다 최소 1/3 이상 싸게 살 것",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 33%(그레이엄의 1/3 원칙)를 뺀 가격",
        "매도가 = 적정가(내재가치). 가격이 가치에 닿으면 팔고 다른 싼 종목으로",
        "손절가 = 진입가의 -15%. 그레이엄은 가격보다 재무 훼손을 손절 사유로 봅니다",
        "재무 손절 신호: 적자 전환, ROE 10% 미만, 부채 과다, 잉여현금흐름 적자",
    ],
}
CFG = {"strong": (0.70, 0.30, 75), "buy": (0.60, 0.10, 60), "wait_q": 0.65, "hold": 45}
TAILS = {
    "strong": "싸고 튼튼합니다. 그레이엄이 가장 좋아하는 유형입니다.",
    "buy": "가격과 재무가 방어적 투자자의 기준을 대체로 충족합니다.",
    "wait": "재무는 튼튼하지만 아직 충분히 싸지 않습니다. 기다리는 쪽입니다.",
    "hold": "기준을 일부만 충족합니다. 더 싸지거나 재무가 나아지면 다시 봅니다.",
    "pass": "싸지도 튼튼하지도 않아 방어적 투자자의 기준에 맞지 않습니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    per, pb, n = m["per"], m["pb"], m["n_years"]
    checks = []

    checks.append(check("저PER", "price", 15, 0.0 if per is None else 1 - scale(per, 10, 25),
                        "순이익이 적자라 PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 15배 이하)",
                        ok=per is not None and per <= 15))
    checks.append(check("저PBR", "price", 15, 0.0 if pb is None else 1 - scale(pb, 1.0, 3.0),
                        "자본이 없거나 잠식되어 PBR 산출 불가" if pb is None else f"PBR {pb:.2f}배 (기준 1.5배 이하)",
                        ok=pb is not None and pb <= 1.5))
    if per is not None and pb is not None:
        g = per * pb
        checks.append(check("그레이엄 수", "price", 10, 1 - scale(g, 22.5, 60), f"PER × PBR = {g:.1f} (기준 22.5 이하)", ok=g <= 22.5))
    else:
        checks.append(check("그레이엄 수", "price", 10, 0.0, "PER 또는 PBR을 산출할 수 없음", ok=False))

    cr = m["current_ratio"]
    if fin or cr is None:
        checks.append(check("유동비율", "quality", 10, None, "금융업은 유동비율을 적용하지 않음" if fin else "유동자산·부채 데이터 없음"))
    else:
        checks.append(check("유동비율", "quality", 10, scale(cr, 1.0, 2.0), f"유동비율 {cr:.2f}배 (기준 2배 이상)", ok=cr >= 2))

    de = m["debt_to_equity"]
    if fin or de is None:
        checks.append(check("부채 ≤ 자본", "quality", 15, None, "금융업은 부채비율을 적용하지 않음" if fin else "부채 데이터 없음"))
    else:
        checks.append(check("부채 ≤ 자본", "quality", 15, 1 - scale(de, 0.5, 2.0), f"부채/자본 {de:.2f}배 (기준 1배 이하)", ok=de <= 1.0))

    cagr, loss = m["ni_cagr"], m["loss_years"]
    ratio = (0.0 if loss else 0.67) + (0.33 * scale(cagr, 0.0, 0.03) if cagr is not None else 0.0)
    checks.append(check("이익 안정성", "quality", 15, ratio, f"적자 {loss}년 · 순이익 연평균 성장률 {pct(cagr)}", ok=(loss == 0 and (cagr or 0) > 0)))

    dv = m["div_ratio"]
    if dv is None:
        checks.append(check("배당 지급", "quality", 10, None, "배당 데이터 없음"))
    else:
        checks.append(check("배당 지급", "quality", 10, dv, f"{n}년 중 {round(dv * n)}년 배당 지급", ok=dv == 1))

    mos = m["mos"]
    checks.append(check("안전마진", "price", 10, 0.0 if mos is None else scale(mos, -0.1, 0.4),
                        "내재가치 산출 불가" if mos is None else f"추정 내재가치 대비 {mos * 100:+.0f}% (기준 +33%)",
                        ok=mos is not None and mos >= 0.33))
    return finish(m, checks, CFG, TAILS, 0.33, 0.15)
