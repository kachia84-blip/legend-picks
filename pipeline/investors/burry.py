"""마이클 버리 스타일: 남들이 외면한 딥밸류. 현금흐름과 자산이 가격보다 훨씬 큰 종목.

주의: 버리 본인의 판단이 아니라 그가 공개적으로 밝힌 가치투자 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "burry",
    "name": "마이클 버리",
    "mono": "리",
    "tagline": "『빅쇼트』의 주인공. 숫자로 확인되는 딥밸류",
    "principles": [
        "기업가치 대비 영업이익(EV/EBIT)이 높을 것 = 정말 쌀 것",
        "잉여현금흐름 수익률이 높을 것",
        "PBR이 낮을 것",
        "순현금이거나 부채가 가벼울 것",
        "적자가 아니고 영업이 흑자일 것",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 35%를 뺀 가격",
        "매도가 = 적정가. 시장이 가치를 알아보면 팝니다",
        "손절가 = 진입가의 -20%. 확신이 있으면 더 사지만 재무가 깨지면 접습니다",
        "재무 손절 신호: 적자 전환, 현금흐름 적자, 부채 증가",
    ],
}
CFG = {"strong": (0.60, 0.25, 78), "buy": (0.50, 0.10, 62), "wait_q": 0.75, "hold": 50}
TAILS = {
    "strong": "벌어들이는 현금에 비해 가격이 매우 싸고 재무도 가볍습니다.",
    "buy": "현금흐름 대비 싼 가격에 들어왔습니다.",
    "wait": "재무는 좋지만 현금흐름 대비 아직 싸지 않습니다.",
    "hold": "싼 면이 있으나 확신할 만큼은 아닙니다.",
    "pass": "숫자로 보아 싸지도, 재무가 가볍지도 않습니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    n, loss = m["n_years"], m["loss_years"]
    checks = []

    ey = m["ev_ebit_yield"]
    if fin:
        e = m["earnings_yield"]
        checks.append(check("이익수익률", "price", 25, scale(e, 0.06, 0.15) if e is not None else 0.0,
                            f"순이익 ÷ 시가총액 {pct(e)} (금융업은 EV/EBIT 대신 적용)", ok=e is not None and e >= 0.10))
    else:
        checks.append(check("EV/EBIT 수익률", "price", 25, 0.0 if ey is None else scale(ey, 0.06, 0.18),
                            "EBIT 또는 기업가치 산출 불가" if ey is None else f"EBIT ÷ 기업가치 {pct(ey)} (기준 12% 이상)", ok=ey is not None and ey >= 0.12))

    fy = m["fcf_yield"]
    if fin or fy is None:
        checks.append(check("FCF 수익률", "price", 25, None, "금융업은 잉여현금흐름을 적용하지 않음" if fin else "현금흐름 데이터 없음"))
    else:
        checks.append(check("FCF 수익률", "price", 25, scale(fy, 0.04, 0.12), f"3년 평균 잉여현금흐름 ÷ 시가총액 {pct(fy)} (기준 8% 이상)", ok=fy >= 0.08))

    pb = m["pb"]
    checks.append(check("저PBR", "price", 10, 0.0 if pb is None else 1 - scale(pb, 0.8, 2.5),
                        "PBR 산출 불가" if pb is None else f"PBR {pb:.2f}배 (기준 1.2배 이하)", ok=pb is not None and pb <= 1.2))

    nc = m["net_cash_ratio"]
    if fin or nc is None:
        checks.append(check("순현금·가벼운 부채", "quality", 20, None, "금융업은 적용하지 않음" if fin else "현금·부채 데이터 없음"))
    else:
        checks.append(check("순현금·가벼운 부채", "quality", 20, scale(nc, -0.3, 0.1),
                            f"(현금 − 부채) ÷ 시가총액 {nc * 100:+.0f}% (0 이상이면 순현금)", ok=nc >= -0.05))
    checks.append(check("흑자 유지", "quality", 10, 1 - loss / n, f"최근 {n}년 중 적자 {loss}년", ok=loss == 0))
    om = m["op_margin_avg"]
    if fin or om is None:
        checks.append(check("영업이익률", "quality", 10, None, "금융업은 영업이익률을 적용하지 않음" if fin else "영업이익 데이터 없음"))
    else:
        checks.append(check("영업이익률", "quality", 10, scale(om, 0.03, 0.12), f"평균 영업이익률 {pct(om)}", ok=om >= 0.08))
    return finish(m, checks, CFG, TAILS, 0.35, 0.20)
