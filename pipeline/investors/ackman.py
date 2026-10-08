"""빌 애크먼 스타일: 단순하고 예측 가능한, 현금을 쏟아내는 고품질 기업에 집중 투자.

주의: 애크먼 본인의 판단이 아니라 그가 공개적으로 밝힌 원칙을 수치화한 모의 평가다.
금융업은 이 기준(잉여현금흐름·ROIC)이 맞지 않아 평가하지 않는다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "ackman",
    "name": "빌 애크먼",
    "mono": "애",
    "tagline": "집중 투자의 승부사. 단순하고 예측 가능한 현금 창출 기업",
    "principles": [
        "사업이 단순하고 이익이 예측 가능할 것(변동 적음)",
        "잉여현금흐름 수익률이 매력적일 것",
        "투하자본수익률(ROIC)이 높을 것",
        "부채가 낮을 것",
        "높은 영업이익률로 드러나는 해자",
        "이익이 꾸준히 성장할 것",
        "금융업은 평가하지 않음",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 15%를 뺀 가격 (훌륭한 기업은 크게 깎지 않음)",
        "매도가 = 적정가. 단, 훌륭한 기업이라면 더 오래 들고 갈 수 있습니다",
        "손절가 = 진입가의 -25%. 소수 종목에 집중하므로 사업이 훼손될 때만 접습니다",
        "재무 손절 신호: 이익 변동성 확대, 마진 하락, 현금흐름 적자, 부채 증가",
    ],
}
CFG = {"strong": (0.75, 0.0, 80), "buy": (0.68, -0.10, 70), "wait_q": 0.75, "hold": 50}
TAILS = {
    "strong": "단순하고 예측 가능한 현금 창출 기계가 합리적인 가격에 있습니다.",
    "buy": "고품질 기업을 받아들일 만한 가격에 살 수 있습니다.",
    "wait": "훌륭한 사업이지만 현금흐름 대비 가격이 높습니다.",
    "hold": "일부 조건만 충족합니다.",
    "pass": "예측 가능성이나 현금 창출력이 부족합니다.",
}


def evaluate(m):
    if m["is_financial"]:
        return None
    n, cv, loss = m["n_years"], m["ni_cv"], m["loss_years"]
    checks = []

    fy = m["fcf_yield"]
    if fy is None:
        checks.append(check("FCF 수익률", "price", 20, None, "현금흐름 데이터 없음"))
    else:
        checks.append(check("FCF 수익률", "price", 20, scale(fy, 0.02, 0.06), f"3년 평균 잉여현금흐름 ÷ 시가총액 {pct(fy)} (기준 4% 이상)", ok=fy >= 0.04))

    roic = m["roic"]
    if roic is None:
        checks.append(check("ROIC", "quality", 20, None, "투하자본 산출 불가"))
    else:
        checks.append(check("ROIC", "quality", 20, scale(min(roic, 0.5), 0.10, 0.25), f"투하자본수익률 {pct(roic)} (기준 15% 이상)", ok=roic >= 0.15))

    if cv is None:
        checks.append(check("예측 가능성", "quality", 20, 0.0, "이익이 적자이거나 평균이 0 이하라 변동성 산출 불가", ok=False))
    else:
        r = 1 - scale(cv, 0.1, 0.6)
        if loss:
            r = min(r, 0.3)
        checks.append(check("예측 가능성", "quality", 20, r, f"순이익 변동계수 {cv:.2f} · 적자 {loss}년", ok=(loss == 0 and cv <= 0.3)))

    if m["debt"] is None:
        checks.append(check("낮은 부채", "quality", 15, None, "부채 데이터 없음"))
    elif m["debt"] <= 0:
        checks.append(check("낮은 부채", "quality", 15, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
    else:
        d = m["debt_to_ni"]
        checks.append(check("낮은 부채", "quality", 15, 0.0 if d is None else 1 - scale(d, 2, 8),
                            "순이익이 적자라 부채 상환 능력 불충분" if d is None else f"총부채가 순이익의 {d:.1f}배 (기준 3배 이하)", ok=d is not None and d <= 3))

    om = m["op_margin_avg"]
    if om is None:
        checks.append(check("해자(영업이익률)", "quality", 15, None, "영업이익 데이터 없음"))
    else:
        checks.append(check("해자(영업이익률)", "quality", 15, scale(om, 0.10, 0.25), f"평균 영업이익률 {pct(om)} (기준 15% 이상)", ok=om >= 0.15))

    cagr = m["ni_cagr"]
    checks.append(check("이익 성장", "quality", 10, 0.0 if cagr is None else scale(cagr, 0.0, 0.10),
                        f"순이익 연평균 {pct(cagr)}", ok=cagr is not None and cagr >= 0.05))
    return finish(m, checks, CFG, TAILS, 0.15, 0.25)
