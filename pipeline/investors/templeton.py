"""존 템플턴 스타일: 최대 비관의 순간에 가장 싸게. 모두가 팔 때 흑자 기업을 산다.

주의: 템플턴 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "templeton",
    "name": "존 템플턴",
    "mono": "템",
    "tagline": "비관이 극에 달했을 때 사는 글로벌 역발상 가치투자자",
    "principles": [
        "PER이 아주 낮을 것 (시장 평균의 절반 수준)",
        "PBR이 낮을 것",
        "52주 고점에서 크게 떨어져 비관이 가격에 반영돼 있을 것",
        "그래도 흑자를 유지하고 재무가 버틸 것",
        "내재가치보다 40% 이상 싸게 살 것",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 40%를 뺀 가격 (비관 속에서 가장 싸게)",
        "매도가 = 적정가. 비관이 낙관으로 바뀌면 팝니다",
        "손절가 = 진입가의 -25%. 더 싼 종목이 나오면 갈아타라고 했습니다",
        "재무 손절 신호: 적자 전환, ROE 10% 미만, 부채 과다 → 싼 데는 이유가 있었다는 뜻",
    ],
}
CFG = {"strong": (0.60, 0.25, 75), "buy": (0.50, 0.10, 60), "wait_q": 0.85, "hold": 45}
TAILS = {
    "strong": "비관이 가격에 깊이 반영됐는데 재무는 버티는 템플턴식 후보입니다.",
    "buy": "싸고 비관적인 구간에 들어섰습니다.",
    "wait": "재무는 건강하지만 아직 충분히 비관적인(싼) 가격이 아닙니다.",
    "hold": "싼 면이 있으나 확신할 만큼은 아닙니다.",
    "pass": "싸지도, 비관이 반영돼 있지도 않습니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    n, per, pb, dd, loss = m["n_years"], m["per"], m["pb"], m["drawdown52"], m["loss_years"]
    checks = []

    checks.append(check("저PER", "price", 25, 0.0 if per is None else 1 - scale(per, 6, 18),
                        "순이익이 적자라 PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 10배 이하)", ok=per is not None and per <= 10))
    checks.append(check("저PBR", "price", 15, 0.0 if pb is None else 1 - scale(pb, 0.7, 2.5),
                        "PBR 산출 불가" if pb is None else f"PBR {pb:.2f}배 (기준 1배 이하)", ok=pb is not None and pb <= 1.0))
    if dd is None:
        checks.append(check("비관 정도", "price", 20, None, "52주 고점 데이터 없음"))
    else:
        checks.append(check("비관 정도", "price", 20, scale(-dd, 0.10, 0.45), f"52주 고점 대비 {dd * 100:.0f}% (기준 -25% 이하)", ok=dd <= -0.25))
    checks.append(check("흑자 유지", "quality", 15, 1 - loss / n, f"최근 {n}년 중 적자 {loss}년", ok=loss == 0))
    if fin:
        checks.append(check("재무 버팀력", "quality", 15, None, "금융업은 부채 지표를 적용하지 않음"))
    elif m["debt"] is None:
        checks.append(check("재무 버팀력", "quality", 15, None, "부채 데이터 없음"))
    elif m["debt"] <= 0:
        checks.append(check("재무 버팀력", "quality", 15, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
    else:
        d = m["debt_to_ni"]
        checks.append(check("재무 버팀력", "quality", 15, 0.0 if d is None else 1 - scale(d, 2, 8),
                            "순이익이 적자라 부채 상환 능력 불충분" if d is None else f"총부채가 순이익의 {d:.1f}배", ok=d is not None and d <= 4))
    mos = m["mos"]
    checks.append(check("안전마진", "price", 10, 0.0 if mos is None else scale(mos, 0.0, 0.5),
                        "내재가치 산출 불가" if mos is None else f"추정 내재가치 대비 {mos * 100:+.0f}% (기준 +40%)", ok=mos is not None and mos >= 0.40))
    return finish(m, checks, CFG, TAILS, 0.40, 0.25)
