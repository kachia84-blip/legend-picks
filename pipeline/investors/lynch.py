"""피터 린치 스타일: 합리적인 가격의 성장주(GARP). 성장률 대비 싼 주식을 찾는다.

주의: 린치 본인의 판단이 아니라 『월가의 영웅』의 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "lynch",
    "name": "피터 린치",
    "mono": "린",
    "tagline": "성장률보다 싼 주식(PEG). 일상에서 찾은 성장주",
    "principles": [
        "PEG(PER ÷ 이익성장률)가 1 이하, 낮을수록 좋음",
        "이익이 연 10~25% 꾸준히 자랄 것 (너무 높은 성장은 지속 불가)",
        "매출도 함께 늘어날 것",
        "부채가 적을 것",
        "이익이 실제 현금으로 들어오고 ROE가 높을 것",
        "성장에 비해 PER이 과하지 않을 것",
    ],
    "price_rules": [
        "적정가 = 이익 성장률을 반영한 5년 뒤 가치를 연 12%로 할인한 값(성장률은 25% 보수적으로 삭감)",
        "매수가 = 적정가에서 안전마진 20%를 뺀 가격",
        "매도가 = 적정가. 성장 스토리가 가격에 모두 반영된 구간",
        "손절가 = 진입가의 -25%. 성장주는 변동이 커서 넉넉하게 잡습니다",
        "재무 손절 신호: 성장 둔화(이익 감소), 적자 전환, 부채 급증, 현금흐름 적자 → 스토리가 깨진 것",
    ],
}
CFG = {"strong": (0.65, 0.0, 78), "buy": (0.55, -0.15, 65), "wait_q": 0.70, "hold": 50}
TAILS = {
    "strong": "성장에 비해 가격이 싸고 재무도 건강합니다. 린치가 찾는 '10배 후보'에 가깝습니다.",
    "buy": "성장 대비 가격이 합리적인 편입니다.",
    "wait": "좋은 성장주지만 성장률에 비해 가격이 높습니다. 기다리는 쪽입니다.",
    "hold": "성장성이나 가격 중 일부가 아쉽습니다. 지켜보는 정도입니다.",
    "pass": "성장이 약하거나 가격 대비 매력이 부족합니다.",
}


def _kind(cagr, loss):
    if loss >= 1:
        return "경기순환·회생주"
    if cagr is None:
        return "분류 불가"
    if cagr >= 0.20:
        return "고성장주"
    if cagr >= 0.10:
        return "성장 우량주"
    if cagr > 0:
        return "저성장·안정주"
    return "정체·쇠퇴주"


def evaluate(m):
    fin = m["is_financial"]
    per, peg, cagr, loss = m["per"], m["peg"], m["ni_cagr"], m["loss_years"]
    checks = []

    if peg is None:
        why = "순이익 적자" if per is None else "이익이 늘지 않아"
        checks.append(check("PEG", "price", 25, 0.0, f"{why} PEG 산출 불가", ok=False))
    else:
        checks.append(check("PEG", "price", 25, 1 - scale(peg, 0.5, 2.0), f"PEG {peg:.2f} (PER {per:.1f}배 ÷ 성장률 {cagr * 100:.0f}%, 기준 1 이하)", ok=peg <= 1.0))

    if cagr is None:
        checks.append(check("이익 성장률", "quality", 20, 0.0, "이익이 적자 전환 등으로 성장률 산출 불가", ok=False))
    else:
        r = scale(cagr, 0.05, 0.20) * (0.6 if cagr > 0.5 else 1.0)
        note = " (지나치게 높아 지속성 의심)" if cagr > 0.5 else " (기준 10% 이상)"
        checks.append(check("이익 성장률", "quality", 20, r, f"순이익 연평균 {pct(cagr)}{note}", ok=0.10 <= cagr <= 0.5))

    rc = m["rev_cagr"]
    if rc is None:
        checks.append(check("매출 성장", "quality", 10, None, "매출 데이터 없음"))
    else:
        checks.append(check("매출 성장", "quality", 10, scale(rc, 0.0, 0.12), f"매출 연평균 {pct(rc)}", ok=rc >= 0.06))

    de = m["debt_to_equity"]
    if fin or de is None:
        checks.append(check("낮은 부채", "quality", 15, None, "금융업은 부채비율을 적용하지 않음" if fin else "부채 데이터 없음"))
    else:
        checks.append(check("낮은 부채", "quality", 15, 1 - scale(de, 0.3, 1.5), f"부채/자본 {de:.2f}배 (기준 0.5배 이하)", ok=de <= 0.5))

    fp = m["fcf_pos_ratio"]
    if fin or fp is None:
        checks.append(check("현금 창출", "quality", 10, None, "금융업은 잉여현금흐름을 적용하지 않음" if fin else "현금흐름 데이터 없음"))
    else:
        checks.append(check("현금 창출", "quality", 10, fp, f"잉여현금흐름 흑자 비율 {fp * 100:.0f}%", ok=fp >= 0.75))

    roe = m["roe_avg"]
    checks.append(check("ROE", "quality", 10, scale(roe, 0.08, 0.20), f"평균 ROE {pct(roe)} (기준 15% 이상)", ok=roe >= 0.15))

    checks.append(check("PER 합리성", "price", 10, 0.0 if per is None else 1 - scale(per, 15, 40),
                        "PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 25배 이하)", ok=per is not None and per <= 25))
    return finish(m, checks, CFG, TAILS, 0.20, 0.25, lead=f"린치 분류: {_kind(cagr, loss)}.", iv=m.get("iv_g") or 0)
