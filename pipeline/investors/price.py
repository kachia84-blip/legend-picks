"""토머스 로 프라이스 스타일: 성장주 투자의 선구자. 이익이 오래, 꾸준히, 인플레이션보다 빨리 자라는 우량 기업.

주의: 프라이스 본인의 판단이 아니라 그의 공개된 성장주 투자 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "price",
    "name": "토머스 로 프라이스",
    "mono": "프",
    "tagline": "성장주 투자의 아버지. 오래 꾸준히 자라는 우량 성장 기업",
    "principles": [
        "이익이 적자 없이 오랫동안 꾸준히 성장할 것",
        "매출도 함께 성장할 것",
        "자기자본이익률(ROE)과 순이익률이 높을 것",
        "부채가 낮고 현금 창출력이 있을 것",
        "성장에 비해 가격이 지나치게 비싸지 않을 것",
    ],
    "price_rules": [
        "적정가 = 이익 성장률을 반영한 5년 뒤 가치를 연 12%로 할인한 값(성장률은 25% 보수적으로 삭감)",
        "매수가 = 적정가에서 안전마진 15%를 뺀 가격",
        "매도가 = 적정가. 성장이 둔화되는 시점이 매도 신호입니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 이익 성장 정체, 마진 하락, 부채 증가",
    ],
}
CFG = {"strong": (0.72, -0.10, 80), "buy": (0.62, -0.25, 68), "wait_q": 0.78, "hold": 50}
TAILS = {
    "strong": "꾸준한 성장, 높은 수익성, 건강한 재무를 모두 갖춘 우량 성장주입니다.",
    "buy": "우량 성장주로 볼 만하고 가격도 감당할 수준입니다.",
    "wait": "우량 성장주이지만 가격이 부담스럽습니다.",
    "hold": "성장의 질에서 일부 아쉬움이 있습니다.",
    "pass": "꾸준한 우량 성장의 증거가 부족합니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    cagr, loss, rc, roe, nm = m["ni_cagr"], m["loss_years"], m["rev_cagr"], m["roe_avg"], m["net_margin"]
    checks = []

    r = 0.0 if cagr is None else scale(cagr, 0.05, 0.20)
    if loss:
        r = min(r, 0.3)
    checks.append(check("이익 성장 지속", "quality", 25, r, f"적자 {loss}년 · 순이익 연평균 {pct(cagr)} (기준 10% 이상)", ok=(loss == 0 and cagr is not None and cagr >= 0.10)))
    checks.append(check("매출 성장", "quality", 15, None if rc is None else scale(rc, 0.03, 0.12),
                        "매출 데이터 없음" if rc is None else f"매출 연평균 {pct(rc)} (기준 7% 이상)", ok=rc is not None and rc >= 0.07))
    checks.append(check("ROE", "quality", 15, scale(min(roe, 0.40), 0.12, 0.25), f"평균 ROE {pct(roe)} (기준 15% 이상)", ok=roe >= 0.15))
    checks.append(check("순이익률", "quality", 10, None if nm is None else scale(nm, 0.05, 0.20),
                        "매출 데이터 없음" if nm is None else f"순이익률 {pct(nm)} (기준 10% 이상)", ok=nm is not None and nm >= 0.10))
    if fin:
        checks.append(check("낮은 부채", "quality", 15, None, "금융업은 부채 지표를 적용하지 않음"))
    elif m["debt"] is None:
        checks.append(check("낮은 부채", "quality", 15, None, "부채 데이터 없음"))
    elif m["debt"] <= 0:
        checks.append(check("낮은 부채", "quality", 15, 1.0, "이자 부담 부채가 사실상 없음", ok=True))
    else:
        d = m["debt_to_ni"]
        checks.append(check("낮은 부채", "quality", 15, 0.0 if d is None else 1 - scale(d, 2, 8),
                            "순이익이 적자라 부채 상환 능력 불충분" if d is None else f"총부채가 순이익의 {d:.1f}배", ok=d is not None and d <= 3))
    if fin or m["fcf_pos_ratio"] is None:
        checks.append(check("현금 창출", "quality", 10, None, "금융업은 잉여현금흐름을 적용하지 않음" if fin else "현금흐름 데이터 없음"))
    else:
        fp = m["fcf_pos_ratio"]
        checks.append(check("현금 창출", "quality", 10, fp, f"잉여현금흐름 흑자 비율 {fp * 100:.0f}%", ok=fp >= 0.75))
    mg = m.get("mos_g")
    checks.append(check("합리적 가격", "price", 10, 0.0 if mg is None else scale(mg, -0.30, 0.30),
                        "성장 가치 산출 불가" if mg is None else f"성장 반영 적정가 대비 {mg * 100:+.0f}%", ok=mg is not None and mg >= 0.0))
    return finish(m, checks, CFG, TAILS, 0.15, 0.20, iv=m.get("iv_g") or 0)
