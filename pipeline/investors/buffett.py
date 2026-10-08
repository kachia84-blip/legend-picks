"""워렌 버핏 스타일: 이해할 수 있는 훌륭한 사업을, 합리적인 가격에.

주의: 버핏 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "buffett",
    "name": "워렌 버핏",
    "mono": "버",
    "tagline": "훌륭한 기업을 적정한 가격에 사서 오래 보유",
    "principles": [
        "높고 꾸준한 자기자본이익률(ROE)",
        "빚이 적고 이익으로 쉽게 갚을 수 있을 것",
        "적자 없이 꾸준히 늘어나는 이익",
        "이익이 실제 현금(잉여현금흐름)으로 들어올 것",
        "경쟁자가 넘보기 어려운 높은 영업이익률(해자)",
        "내재가치보다 충분히 싸게 살 것(안전마진)",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진(기업 질 80점↑ 20%, 65점↑ 30%, 그 외 40%)을 뺀 가격",
        "매도가 = 적정가(내재가치). 이 가격을 넘으면 안전마진이 사라진 구간",
        "손절가 = 진입가의 -20%. 단, 재무가 멀쩡한데 가격만 빠졌다면 오히려 추가 매수 기회",
        "재무 손절 신호: 적자 전환, ROE 10% 미만, 부채 과다, 잉여현금흐름 적자 → 가격과 무관하게 매도 검토",
    ],
}

CFG = {"strong": (0.70, 0.15, 80), "buy": (0.65, 0.0, 0), "wait_q": 0.70, "hold": 50}
TAILS = {
    "strong": "사업의 질과 가격이 모두 만족스러운 구간입니다.",
    "buy": "좋은 사업을 합리적인 가격에 살 수 있는 구간입니다.",
    "wait": "기업은 훌륭하지만 지금 가격이 비쌉니다. 더 싸질 때까지 기다리는 쪽입니다.",
    "hold": "원칙에 일부만 부합합니다. 지켜보는 정도입니다.",
    "pass": "버핏식 기준(꾸준한 수익성·낮은 부채·현금창출)에 맞지 않습니다.",
}


def evaluate(m):
    checks = []
    fin = m["is_financial"]
    n = m["n_years"]

    # 1) ROE 수준 (레버리지·자사주 소각으로 부풀려진 값을 막기 위해 30%에서 상한)
    roe = m["roe_avg"]
    checks.append(check("ROE 수준", "quality", 15, scale(min(roe, 0.30), 0.05, 0.20),
                        f"최근 {n}년 평균 ROE {pct(roe)} (기준 15% 이상)", ok=roe >= 0.15))

    # 2) ROE 일관성
    good = sum(1 for r in m["roe"] if r is not None and r >= 0.12)
    checks.append(check("ROE 일관성", "quality", 10, good / n, f"{n}년 중 {good}년이 ROE 12% 이상", ok=good == n))

    # 3) 이익 안정성·성장
    cagr, loss = m["ni_cagr"], m["loss_years"]
    stab = 0.0 if loss else 0.6
    growth = 0.0 if cagr is None else 0.4 * scale(cagr, 0.0, 0.05)
    checks.append(check("이익 안정성·성장", "quality", 10, stab + growth,
                        f"적자 {loss}년 · 순이익 연평균 성장률 {pct(cagr)}", ok=(loss == 0 and (cagr or 0) > 0)))

    # 4) 부채 부담: 순이익으로 갚는 데 몇 년? (금융업은 부채가 사업이라 제외)
    if fin:
        checks.append(check("부채 부담", "quality", 15, None, "금융업은 부채 지표를 적용하지 않음"))
    else:
        d = m["debt_to_ni"]
        if m["debt"] is None:
            checks.append(check("부채 부담", "quality", 15, None, "부채 데이터 없음"))
        elif m["debt"] <= 0:
            checks.append(check("부채 부담", "quality", 15, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
        elif d is None:
            checks.append(check("부채 부담", "quality", 15, 0.0, "순이익이 적자라 부채 상환 능력 불충분", ok=False))
        else:
            checks.append(check("부채 부담", "quality", 15, 1 - scale(d, 2, 8),
                                f"총부채가 순이익의 {d:.1f}배 (기준 3배 이하)", ok=d <= 3))

    # 5) 현금 창출력
    if fin or m["fcf_pos_ratio"] is None:
        checks.append(check("현금 창출력", "quality", 15, None,
                            "금융업은 잉여현금흐름 지표를 적용하지 않음" if fin else "현금흐름 데이터 없음"))
    else:
        pos, conv = m["fcf_pos_ratio"], m["fcf_to_ni"]
        ratio = 0.55 * pos + 0.45 * (0.0 if conv is None else scale(conv, 0.3, 0.9))
        checks.append(check("현금 창출력", "quality", 15, ratio,
                            f"잉여현금흐름 흑자 비율 {pos * 100:.0f}% · 순이익 대비 현금전환 {pct(conv)}", ok=ratio >= 0.7))

    # 6) 해자(영업이익률)
    om, omin = m["op_margin_avg"], m["op_margin_min"]
    if fin or om is None:
        checks.append(check("해자(영업이익률)", "quality", 15, None,
                            "금융업은 영업이익률을 적용하지 않음" if fin else "영업이익 데이터 없음"))
    else:
        steady = 1.0 if (om > 0 and omin >= 0.7 * om) else 0.0
        checks.append(check("해자(영업이익률)", "quality", 15, 0.67 * scale(om, 0.05, 0.20) + 0.33 * steady,
                            f"평균 영업이익률 {pct(om)}, 최저 {pct(omin)} (높고 흔들리지 않을수록 좋음)"))

    # 7) 안전마진
    mos = m["mos"]
    if mos is None:
        checks.append(check("안전마진", "price", 20, 0.0, "내재가치 산출 불가(현금흐름이 적자이거나 부족)", ok=False))
    else:
        per = f" (PER {m['per']:.1f}배)" if m["per"] else ""
        checks.append(check("안전마진", "price", 20, scale(mos, -0.30, 0.30),
                            f"추정 내재가치 대비 {mos * 100:+.0f}%{per}", ok=mos >= 0.15))

    req = lambda q: 0.20 if q >= 0.80 else 0.30 if q >= 0.65 else 0.40
    return finish(m, checks, CFG, TAILS, req, 0.20)
