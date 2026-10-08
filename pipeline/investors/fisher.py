"""필립 피셔 스타일: 오래 성장할 수 있는 뛰어난 성장 기업에 투자한다.

주의: 피셔 본인의 판단이 아니라 『위대한 기업에 투자하라』의 원칙을 재무 수치로 옮긴 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "fisher",
    "name": "필립 피셔",
    "mono": "피",
    "tagline": "성장주 투자의 선구자. 위대한 기업을 오래 보유",
    "principles": [
        "매출이 오랫동안 꾸준히 성장할 것",
        "이익도 매출과 함께 늘어날 것",
        "평균을 훨씬 웃도는 영업이익률",
        "이익률이 개선되는 추세일 것",
        "연구개발(R&D)에 꾸준히 투자할 것",
        "성장을 감당할 만큼 재무가 튼튼하고 자본수익성이 높을 것",
    ],
    "price_rules": [
        "적정가 = 이익 성장률을 반영한 5년 뒤 가치를 연 12%로 할인한 값(성장률은 25% 보수적으로 삭감)",
        "매수가 = 적정가에서 안전마진 10%를 뺀 가격 (훌륭한 성장은 비싸게 사도 보상받는다고 봄)",
        "매도가 = 적정가. 피셔는 성장이 이어지는 한 오래 보유하라고 합니다",
        "손절가 = 진입가의 -25%. 성장 스토리가 훼손될 때만 팝니다",
        "재무 손절 신호: 매출·이익 성장 정체, 이익률 하락, 적자 전환",
    ],
}
CFG = {"strong": (0.75, -0.25, 80), "buy": (0.65, -0.35, 68), "wait_q": 0.75, "hold": 50}
TAILS = {
    "strong": "매출·이익이 함께 크게 자라는 위대한 성장 기업의 모습입니다.",
    "buy": "성장성과 수익성이 좋고 가격도 감당할 만합니다.",
    "wait": "성장은 훌륭하지만 가격이 지나치게 높아 보입니다.",
    "hold": "성장의 일부 조건만 충족합니다.",
    "pass": "오래 성장할 기업이라는 증거가 재무에서 부족합니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    checks = []

    rc = m["rev_cagr"]
    checks.append(check("매출 성장", "quality", 20, None if rc is None else scale(rc, 0.03, 0.15),
                        "매출 데이터 없음" if rc is None else f"매출 연평균 {pct(rc)} (기준 10% 이상)", ok=rc is not None and rc >= 0.10))

    cagr = m["ni_cagr"]
    checks.append(check("이익 성장", "quality", 20, 0.0 if cagr is None else scale(cagr, 0.05, 0.20),
                        "이익이 적자 전환 등으로 성장률 산출 불가" if cagr is None else f"순이익 연평균 {pct(cagr)} (기준 10% 이상)",
                        ok=cagr is not None and cagr >= 0.10))

    om = m["op_margin_avg"]
    if fin or om is None:
        checks.append(check("영업이익률", "quality", 15, None, "금융업은 영업이익률을 적용하지 않음" if fin else "영업이익 데이터 없음"))
    else:
        checks.append(check("영업이익률", "quality", 15, scale(om, 0.08, 0.25), f"평균 영업이익률 {pct(om)} (기준 15% 이상)", ok=om >= 0.15))

    tr = m["op_margin_trend"]
    if fin or tr is None:
        checks.append(check("이익률 개선", "quality", 10, None, "금융업은 적용하지 않음" if fin else "이익률 추세 데이터 없음"))
    else:
        checks.append(check("이익률 개선", "quality", 10, scale(tr, -0.03, 0.03), f"영업이익률 변화 {tr * 100:+.1f}%p ({m['first_year']}→{m['last_year']})", ok=tr >= 0))

    rd = m["rnd_ratio"]
    if rd is None:
        checks.append(check("R&D 투자", "quality", 10, None, "R&D 지출 데이터 없음(제조·유통 등은 해당 없음)"))
    else:
        checks.append(check("R&D 투자", "quality", 10, scale(rd, 0.0, 0.08), f"매출 대비 R&D {pct(rd)} (기준 5% 이상)", ok=rd >= 0.05))

    if fin:
        checks.append(check("재무 안정", "quality", 10, None, "금융업은 부채 지표를 적용하지 않음"))
    elif m["debt"] is None:
        checks.append(check("재무 안정", "quality", 10, None, "부채 데이터 없음"))
    elif m["debt"] <= 0:
        checks.append(check("재무 안정", "quality", 10, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
    else:
        d = m["debt_to_ni"]
        checks.append(check("재무 안정", "quality", 10, 0.0 if d is None else 1 - scale(d, 2, 8),
                            "순이익이 적자라 부채 상환 능력 불충분" if d is None else f"총부채가 순이익의 {d:.1f}배", ok=d is not None and d <= 4))

    roe = m["roe_avg"]
    checks.append(check("ROE", "quality", 15, scale(min(roe, 0.35), 0.10, 0.25), f"평균 ROE {pct(roe)} (기준 15% 이상)", ok=roe >= 0.15))
    return finish(m, checks, CFG, TAILS, 0.10, 0.25, iv=m.get("iv_g") or 0)
