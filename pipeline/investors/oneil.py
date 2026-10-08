"""윌리엄 오닐 스타일(CAN SLIM): 이익이 폭발적으로 늘고 신고가를 향하는 주도주.

주의: 오닐 본인의 판단이 아니라 『최고의 주식 최적의 타이밍』의 원칙 중 재무로 확인 가능한 부분을 수치화한 모의 평가다.
(기관 매수·시장 방향 등 일부 항목은 데이터가 없어 제외했다.)
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "oneil",
    "name": "윌리엄 오닐",
    "mono": "오",
    "tagline": "CAN SLIM. 이익이 폭발하는 주도주를 신고가 부근에서",
    "principles": [
        "C: 가장 최근 이익이 전년보다 25% 이상 늘 것",
        "A: 연평균 이익 성장률이 25% 이상일 것",
        "매출도 함께 빠르게 늘 것",
        "ROE가 17% 이상일 것",
        "N·L: 52주 신고가 근처에서 거래되는 주도주일 것",
        "이익률이 개선되고 영업이익률이 높을 것",
    ],
    "price_rules": [
        "적정가 = 이익 성장률을 반영한 5년 뒤 가치를 연 12%로 할인한 값(성장률은 25% 보수적으로 삭감)",
        "매수가 = 적정가에서 안전마진 10%를 뺀 가격 (주도주는 비싸도 산다고 봄)",
        "매도가 = 적정가. 이익 성장이 꺾이면 그 전에 팔아야 합니다",
        "손절가 = 진입가의 -8%. 오닐의 유명한 7~8% 손절 원칙입니다",
        "재무 손절 신호: 이익 성장 둔화, 적자 전환, 마진 하락",
    ],
}
CFG = {"strong": (0.70, -0.30, 80), "buy": (0.58, -0.50, 68), "wait_q": 0.80, "hold": 50}
TAILS = {
    "strong": "이익과 매출이 폭발적으로 늘고 주가도 강한 오닐식 주도주 후보입니다.",
    "buy": "성장 조건 대부분을 갖췄습니다.",
    "wait": "성장은 훌륭하지만 가격이 이미 많이 올라 있습니다.",
    "hold": "CAN SLIM 조건 일부만 충족합니다.",
    "pass": "이익 성장과 주가 강도가 주도주 기준에 못 미칩니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    yoy, cagr, ry, rc, roe, dd = m["ni_yoy"], m["ni_cagr"], m["rev_yoy"], m["rev_cagr"], m["roe"][-1], m["drawdown52"]
    checks = []

    checks.append(check("C 최근 이익 성장", "quality", 20, 0.0 if yoy is None else scale(yoy, 0.10, 0.30),
                        "최근 이익이 적자이거나 전년이 적자라 산출 불가" if yoy is None else f"최근 순이익이 전년 대비 {pct(yoy)} (기준 25% 이상)", ok=yoy is not None and yoy >= 0.25))
    checks.append(check("A 연간 이익 성장", "quality", 20, 0.0 if cagr is None else scale(cagr, 0.10, 0.30),
                        "연평균 이익 성장률 산출 불가" if cagr is None else f"순이익 연평균 {pct(cagr)} (기준 25% 이상)", ok=cagr is not None and cagr >= 0.25))
    parts = [scale(x, 0.05, 0.25) for x in (ry, rc) if x is not None]
    checks.append(check("매출 성장", "quality", 15, (sum(parts) / len(parts)) if parts else None,
                        "매출 데이터 없음" if not parts else f"최근 매출 {pct(ry)} · 연평균 {pct(rc)} (기준 20% 이상)", ok=bool(parts) and sum(parts) / len(parts) >= 0.7))
    checks.append(check("ROE", "quality", 15, 0.0 if roe is None else scale(roe, 0.10, 0.20),
                        f"최근 ROE {pct(roe)} (기준 17% 이상)", ok=roe is not None and roe >= 0.17))
    if dd is None:
        checks.append(check("N·L 신고가 근접", "price", 15, None, "52주 고점 데이터 없음"))
    else:
        checks.append(check("N·L 신고가 근접", "price", 15, 1 - scale(-dd, 0.05, 0.30), f"52주 고점 대비 {dd * 100:.0f}% (기준 -15% 이내)", ok=dd >= -0.15))
    tr = m["op_margin_trend"]
    if fin or tr is None:
        checks.append(check("이익률 개선", "quality", 10, None, "금융업은 적용하지 않음" if fin else "이익률 추세 데이터 없음"))
    else:
        checks.append(check("이익률 개선", "quality", 10, scale(tr, -0.02, 0.04), f"영업이익률 변화 {tr * 100:+.1f}%p", ok=tr >= 0))
    om = m["op_margin_avg"]
    if fin or om is None:
        checks.append(check("영업이익률", "quality", 5, None, "금융업은 적용하지 않음" if fin else "영업이익 데이터 없음"))
    else:
        checks.append(check("영업이익률", "quality", 5, scale(om, 0.08, 0.20), f"평균 영업이익률 {pct(om)}", ok=om >= 0.15))
    return finish(m, checks, CFG, TAILS, 0.10, 0.08, iv=m.get("iv_g") or 0)
