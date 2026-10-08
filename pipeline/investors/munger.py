"""찰리 멍거 스타일: 아주 훌륭한 기업을 적당한 가격에. 질이 곧 안전마진이다.

주의: 멍거 본인의 판단이 아니라 그가 공개적으로 밝힌 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "munger",
    "name": "찰리 멍거",
    "mono": "멍",
    "tagline": "버핏의 파트너. 훌륭한 기업을 적당한 가격에",
    "principles": [
        "투하자본수익률(ROIC)이 높은 사업",
        "높은 매출총이익률로 드러나는 해자(가격 결정력)",
        "오랫동안 일관되게 높은 ROE",
        "빚에 의존하지 않고 현금을 꾸준히 창출",
        "이익이 계속 성장할 것",
        "비싸지만 않으면 된다 (싼 가격보다 기업의 질이 우선)",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 10%만 뺀 가격 (훌륭한 기업은 크게 깎지 않음)",
        "매도가 = 적정가. 단, 멍거는 좋은 기업을 쉽게 팔지 말라고 합니다",
        "손절가 = 진입가의 -25%. 가격보다 '해자가 무너졌는지'를 더 봅니다",
        "재무 손절 신호: ROIC·ROE 급락, 마진 붕괴, 적자 전환, 부채 증가",
    ],
}
CFG = {"strong": (0.75, 0.0, 80), "buy": (0.70, -0.15, 70), "wait_q": 0.75, "hold": 50}
TAILS = {
    "strong": "자본 수익성과 해자가 뛰어나고 가격도 무리하지 않습니다. 멍거식 '훌륭한 기업'입니다.",
    "buy": "기업의 질이 높고 가격이 받아들일 만합니다.",
    "wait": "훌륭한 기업이지만 지금은 가격이 너무 높습니다.",
    "hold": "좋은 면이 있지만 해자·자본수익성 기준에는 못 미칩니다.",
    "pass": "멍거가 말하는 '훌륭한 기업'의 기준에 맞지 않습니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    n = m["n_years"]
    checks = []

    roic = m["roic"]
    if fin or roic is None:
        checks.append(check("ROIC", "quality", 25, None, "금융업은 ROIC를 적용하지 않음" if fin else "투하자본 산출 불가"))
    else:
        checks.append(check("ROIC", "quality", 25, scale(min(roic, 0.5), 0.08, 0.25), f"투하자본수익률 {pct(roic)} (기준 15% 이상)", ok=roic >= 0.15))

    gm = m["gross_margin_avg"]
    if fin or gm is None:
        checks.append(check("해자(매출총이익률)", "quality", 15, None, "금융업은 매출총이익률을 적용하지 않음" if fin else "매출총이익 데이터 없음"))
    else:
        checks.append(check("해자(매출총이익률)", "quality", 15, scale(gm, 0.25, 0.60), f"평균 매출총이익률 {pct(gm)} (기준 40% 이상)", ok=gm >= 0.40))

    good = sum(1 for r in m["roe"] if r is not None and r >= 0.12)
    checks.append(check("ROE 일관성", "quality", 15, good / n, f"{n}년 중 {good}년이 ROE 12% 이상", ok=good == n))

    if fin:
        checks.append(check("낮은 부채", "quality", 10, None, "금융업은 부채 지표를 적용하지 않음"))
    elif m["debt"] is None:
        checks.append(check("낮은 부채", "quality", 10, None, "부채 데이터 없음"))
    elif m["debt"] <= 0:
        checks.append(check("낮은 부채", "quality", 10, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
    else:
        d = m["debt_to_ni"]
        checks.append(check("낮은 부채", "quality", 10, 0.0 if d is None else 1 - scale(d, 2, 8),
                            "순이익이 적자라 부채 상환 능력 불충분" if d is None else f"총부채가 순이익의 {d:.1f}배 (기준 3배 이하)",
                            ok=d is not None and d <= 3))

    if fin or m["fcf_pos_ratio"] is None:
        checks.append(check("현금 창출력", "quality", 15, None, "금융업은 잉여현금흐름을 적용하지 않음" if fin else "현금흐름 데이터 없음"))
    else:
        pos, conv = m["fcf_pos_ratio"], m["fcf_to_ni"]
        r = 0.55 * pos + 0.45 * (0.0 if conv is None else scale(conv, 0.3, 0.9))
        checks.append(check("현금 창출력", "quality", 15, r, f"잉여현금흐름 흑자 {pos * 100:.0f}% · 현금전환 {pct(conv)}", ok=r >= 0.7))

    cagr = m["ni_cagr"]
    checks.append(check("이익 성장", "quality", 10, 0.0 if cagr is None else scale(cagr, 0.0, 0.10),
                        f"순이익 연평균 {pct(cagr)}", ok=cagr is not None and cagr >= 0.05))

    per = m["per"]
    checks.append(check("가격 합리성", "price", 10, 0.0 if per is None else 1 - scale(per, 16, 50),
                        "PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 25배 이하)", ok=per is not None and per <= 25))
    return finish(m, checks, CFG, TAILS, 0.10, 0.25)
