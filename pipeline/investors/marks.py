"""하워드 막스 스타일: 수익보다 리스크를 먼저 본다. 안전한 기업을 크게 싼 가격에.

주의: 막스 본인의 판단이 아니라 『투자에 대한 생각』 등 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "marks",
    "name": "하워드 막스",
    "mono": "막",
    "tagline": "리스크 관리의 달인. 잃지 않는 투자가 먼저",
    "principles": [
        "이익이 흔들리지 않고 적자가 없을 것",
        "이자를 감당하고도 남는 재무 구조",
        "현금흐름이 꾸준히 흑자일 것",
        "마진이 크게 출렁이지 않을 것",
        "내재가치보다 확실히 싸게, 합리적인 PER으로 살 것",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 30%를 뺀 가격",
        "매도가 = 적정가. 가격이 가치에 닿으면 위험 대비 보상이 줄어듭니다",
        "손절가 = 진입가의 -15%. 리스크 관리를 위해 가장 타이트하게 잡습니다",
        "재무 손절 신호: 이자보상 악화, 현금흐름 적자, 이익 급변동",
    ],
}
CFG = {"strong": (0.70, 0.25, 78), "buy": (0.60, 0.10, 62), "wait_q": 0.72, "hold": 50}
TAILS = {
    "strong": "이익이 안정적이고 재무가 튼튼한데 가격까지 크게 쌉니다. 잃을 확률이 낮은 구조입니다.",
    "buy": "안전성이 높고 가격에 여유가 있습니다.",
    "wait": "안전한 기업이지만 가격 여유(안전마진)가 부족합니다.",
    "hold": "안전성과 가격 중 한쪽이 아쉽습니다.",
    "pass": "이익 변동이 크거나 재무 위험이 있어 리스크가 큽니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    n, cv, loss = m["n_years"], m["ni_cv"], m["loss_years"]
    checks = []

    if cv is None:
        checks.append(check("이익 안정성", "quality", 20, 0.0, "이익이 적자이거나 평균이 0 이하라 변동성 산출 불가", ok=False))
    else:
        r = 1 - scale(cv, 0.1, 0.6)
        if loss:
            r = min(r, 0.3)
        checks.append(check("이익 안정성", "quality", 20, r, f"순이익 변동계수 {cv:.2f} · 적자 {loss}년 (낮을수록 안정)", ok=(loss == 0 and cv <= 0.3)))

    if fin:
        checks.append(check("이자·부채 부담", "quality", 20, None, "금융업은 부채 지표를 적용하지 않음"))
    else:
        parts, det = [], []
        cover = m["interest_cover"]
        if cover is not None:
            parts.append(scale(min(cover, 50), 2, 8)); det.append(f"이자보상배율 {cover:.1f}배(기준 5배 이상)")
        if m["debt"] is not None and m["debt"] <= 0:
            parts.append(1.0); det.append("이자 부담 부채 없음")
        elif m["debt_to_ni"] is not None:
            parts.append(1 - scale(m["debt_to_ni"], 2, 8)); det.append(f"총부채가 순이익의 {m['debt_to_ni']:.1f}배")
        elif m["debt"] is not None:
            parts.append(0.0); det.append("순이익 적자라 상환 능력 불충분")
        if parts:
            r = sum(parts) / len(parts)
            checks.append(check("이자·부채 부담", "quality", 20, r, " · ".join(det), ok=r >= 0.7))
        else:
            checks.append(check("이자·부채 부담", "quality", 20, None, "부채·이자 데이터 없음"))

    if fin or m["fcf_pos_ratio"] is None:
        checks.append(check("현금흐름 안전", "quality", 15, None, "금융업은 잉여현금흐름을 적용하지 않음" if fin else "현금흐름 데이터 없음"))
    else:
        pos, conv = m["fcf_pos_ratio"], m["fcf_to_ni"]
        r = 0.6 * pos + 0.4 * (0.0 if conv is None else scale(conv, 0.3, 0.9))
        checks.append(check("현금흐름 안전", "quality", 15, r, f"잉여현금흐름 흑자 {pos * 100:.0f}% · 현금전환 {pct(conv)}", ok=r >= 0.7))

    om, omin = m["op_margin_avg"], m["op_margin_min"]
    if fin or om is None or om <= 0:
        checks.append(check("마진 안정", "quality", 10, None, "금융업은 영업이익률을 적용하지 않음" if fin else "영업이익 데이터 없음"))
    else:
        checks.append(check("마진 안정", "quality", 10, scale(omin / om, 0.5, 0.9), f"최저 마진이 평균의 {omin / om * 100:.0f}% (평균 {pct(om)})", ok=omin / om >= 0.75))

    mos = m["mos"]
    checks.append(check("안전마진", "price", 25, 0.0 if mos is None else scale(mos, 0.0, 0.4),
                        "내재가치 산출 불가" if mos is None else f"추정 내재가치 대비 {mos * 100:+.0f}% (기준 +30%)", ok=mos is not None and mos >= 0.30))
    per = m["per"]
    checks.append(check("가격 합리성", "price", 10, 0.0 if per is None else 1 - scale(per, 12, 30),
                        "PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 15배 이하)", ok=per is not None and per <= 15))
    return finish(m, checks, CFG, TAILS, 0.30, 0.15)
