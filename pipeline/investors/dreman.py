"""데이비드 드레먼 스타일(『역발상 투자』): 시장이 외면한 우량 배당주. 저PER·저PBR + 배당 + 튼튼한 재무.

주의: 드레먼 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, dividend_checks, finish, pays_dividend, pct, scale

INFO = {
    "id": "dreman",
    "name": "데이비드 드레먼",
    "mono": "드",
    "tagline": "외면받는 우량 배당주를 사는 역발상 투자",
    "principles": [
        "PER·PBR이 낮을 것 (시장이 외면한 가격)",
        "배당수익률이 시장 평균보다 높을 것",
        "배당 성향이 낮아 배당이 안전하고 삭감 이력이 없을 것",
        "재무가 튼튼하고 수익성이 꾸준할 것 (싼 데는 이유가 없어야 함)",
    ],
    "price_rules": [
        "적정가 = 잉여현금흐름 기반 내재가치",
        "매수가 = 적정가에서 안전마진 25%를 뺀 가격",
        "매도가 = 적정가. 시장이 다시 관심을 가지면 팝니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 배당 삭감, 이익 감소, 부채 급증",
    ],
}
CFG = {"strong": (0.60, 0.15, 74), "buy": (0.50, 0.0, 60), "wait_q": 0.80, "hold": 45}
TAILS = {
    "strong": "싸게 거래되는 우량 배당주로, 역발상 투자 후보입니다.",
    "buy": "가격이 싸고 배당도 안전한 편입니다.",
    "wait": "배당과 재무는 좋지만 가격이 아직 싸지 않습니다.",
    "hold": "일부 조건만 충족합니다.",
    "pass": "저평가·배당·안전성을 충분히 갖추지 못했습니다.",
}


def evaluate(m):
    if not pays_dividend(m):
        return None
    per, pb = m["per"], m["pb"]
    checks = [
        check("저PER", "price", 20, 0.0 if per is None else 1 - scale(per, 8, 18),
              "순이익이 적자라 PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 12배 이하)", ok=per is not None and per <= 12),
        check("저PBR", "price", 10, None if pb is None else 1 - scale(pb, 1.0, 3.0),
              "PBR 산출 불가" if pb is None else f"PBR {pb:.2f}배 (기준 2배 이하)", ok=pb is not None and pb <= 2),
    ]
    checks += dividend_checks(m, yield_rng=(0.025, 0.05), cagr_rng=(0.0, 0.08), payout_cap=0.55,
                              w={"yield": 25, "growth": 5, "payout": 15, "cover": 10, "streak": 10})
    roe = m["roe_avg"]
    checks.append(check("수익성(ROE)", "quality", 10, 0.0 if roe is None else scale(roe, 0.05, 0.15),
                        f"최근 평균 ROE {pct(roe)} (기준 12% 이상)", ok=roe is not None and roe >= 0.12))
    cr = m["current_ratio"]
    if m["is_financial"]:
        checks.append(check("단기 유동성", "quality", 5, None, "금융업은 유동비율을 적용하지 않음"))
    else:
        checks.append(check("단기 유동성", "quality", 5, None if cr is None else scale(cr, 1.0, 2.0),
                            "유동비율 산출 불가" if cr is None else f"유동비율 {cr:.2f}배 (기준 1.5배 이상)", ok=cr is not None and cr >= 1.5))
    return finish(m, checks, CFG, TAILS, 0.25, 0.20)
