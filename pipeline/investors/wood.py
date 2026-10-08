"""캐시 우드 스타일: 파괴적 혁신. 지금 이익이 없어도 폭발적으로 성장하는 기술 기업.

주의: 우드 본인의 판단이 아니라 ARK의 공개된 투자 철학을 수치화한 모의 평가다.
이익이 없는 기업이 많아 매출 기반 가치(5년 뒤 매출 × 졸업 PSR)로 가격 전략을 계산한다. 금융업은 평가하지 않는다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "wood",
    "name": "캐시 우드",
    "mono": "우",
    "tagline": "파괴적 혁신 투자. 5년 뒤의 매출을 보고 투자",
    "principles": [
        "매출이 빠르게 성장할 것 (연 20% 이상)",
        "최근 성장이 가속될 것",
        "높은 매출총이익률 = 규모가 커질수록 수익이 폭발할 구조",
        "R&D에 적극적으로 투자할 것",
        "영업이익률이 개선되는 방향일 것 (적자여도 좋아지고 있으면 OK)",
        "자금 여력이 충분할 것",
        "금융업은 평가하지 않음",
    ],
    "price_rules": [
        "적정가 = 5년 뒤 매출(성장률 20% 삭감) × 졸업 PSR(총이익률에 따라 4~16배)을 연 15%로 할인한 값",
        "매수가 = 적정가에서 안전마진 20%를 뺀 가격",
        "매도가 = 적정가. 성장이 둔화되면 가격과 무관하게 정리합니다",
        "손절가 = 진입가의 -30%. 변동성이 큰 혁신주라 넉넉하게 잡습니다",
        "재무 손절 신호: 매출 성장 급락, 현금 소진, 마진 악화",
    ],
}
CFG = {"strong": (0.70, -0.30, 78), "buy": (0.58, -0.50, 66), "wait_q": 0.80, "hold": 50}
TAILS = {
    "strong": "매출이 가파르게 늘고 규모의 경제가 기대되는 혁신 성장주입니다.",
    "buy": "혁신 성장의 조건 상당수를 갖췄습니다.",
    "wait": "성장은 훌륭하지만 5년 뒤 매출을 감안해도 가격이 높습니다.",
    "hold": "혁신 성장주라고 확신하기엔 일부 조건이 부족합니다.",
    "pass": "빠른 성장과 규모의 경제 신호가 약합니다.",
}


def _ps_value(m):
    rev, rc = m["rev_last"], m["rev_cagr"]
    if not rev or rc is None:
        return None
    g = max(0.0, min(rc, 0.45)) * 0.8
    gm = m["gross_margin_avg"]
    exit_ps = 4.0 + 12.0 * scale(gm if gm is not None else 0.4, 0.30, 0.80)  # 마진이 높을수록 높은 졸업 PSR (4~16배)
    return rev * (1 + g) ** 5 * exit_ps / 1.15 ** 5


def evaluate(m):
    if m["is_financial"]:
        return None
    rc, ry, gm, rd, tr, nc, ps = m["rev_cagr"], m["rev_yoy"], m["gross_margin_avg"], m["rnd_ratio"], m["op_margin_trend"], m["net_cash_ratio"], m["ps"]
    checks = []

    checks.append(check("매출 성장", "quality", 30, None if rc is None else scale(rc, 0.10, 0.40),
                        "매출 데이터 없음" if rc is None else f"매출 연평균 {pct(rc)} (기준 20% 이상)", ok=rc is not None and rc >= 0.20))
    checks.append(check("성장 가속", "quality", 10, None if ry is None else scale(ry, 0.10, 0.40),
                        "매출 데이터 없음" if ry is None else f"최근 매출 성장 {pct(ry)} (기준 20% 이상)", ok=ry is not None and ry >= 0.20))
    checks.append(check("총이익률(규모의 경제)", "quality", 15, None if gm is None else scale(gm, 0.30, 0.70),
                        "매출총이익 데이터 없음" if gm is None else f"평균 매출총이익률 {pct(gm)} (기준 50% 이상)", ok=gm is not None and gm >= 0.50))
    checks.append(check("R&D 투자", "quality", 15, None if rd is None else scale(rd, 0.03, 0.15),
                        "R&D 지출 데이터 없음(해당 없음)" if rd is None else f"매출 대비 R&D {pct(rd)} (기준 10% 이상)", ok=rd is not None and rd >= 0.10))
    checks.append(check("마진 개선", "quality", 15, None if tr is None else scale(tr, -0.03, 0.10),
                        "이익률 추세 데이터 없음" if tr is None else f"영업이익률 변화 {tr * 100:+.1f}%p", ok=tr is not None and tr >= 0.02))
    checks.append(check("자금 여력", "quality", 10, None if nc is None else scale(nc, -0.20, 0.05),
                        "현금·부채 데이터 없음" if nc is None else f"(현금 − 부채) ÷ 시가총액 {nc * 100:+.0f}%", ok=nc is not None and nc >= -0.05))
    checks.append(check("가격 부담(PSR)", "price", 5, None if ps is None else 1 - scale(ps, 5, 25),
                        "매출 데이터 없음" if ps is None else f"PSR {ps:.1f}배 (낮을수록 좋음)", ok=ps is not None and ps <= 10))
    return finish(m, checks, CFG, TAILS, 0.20, 0.30, iv=_ps_value(m) or 0)
