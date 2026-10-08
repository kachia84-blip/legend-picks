"""존 네프 스타일: 저PER + 배당 + 꾸준한 성장. 총수익률 비율(TRR)이 높은 종목.

주의: 네프 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "neff",
    "name": "존 네프",
    "mono": "네",
    "tagline": "저PER 가치투자의 대가. 싼 가격 + 배당 + 성장",
    "principles": [
        "총수익률 비율 (이익성장률 + 배당수익률) ÷ PER 이 높을 것 (2 이상이 이상적)",
        "PER이 시장보다 크게 낮을 것",
        "배당수익률이 있을 것",
        "이익이 꾸준히 성장하고 적자가 없을 것",
        "재무가 튼튼할 것",
    ],
    "price_rules": [
        "매수가 = 적정가에서 안전마진 25%를 뺀 가격",
        "매도가 = 적정가. PER이 정상 수준으로 오르면 팝니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 배당 삭감, 이익 감소, 적자 전환",
    ],
}
CFG = {"strong": (0.60, 0.15, 75), "buy": (0.50, 0.0, 60), "wait_q": 0.75, "hold": 45}
TAILS = {
    "strong": "싼 PER에 배당과 성장까지 갖춘 총수익률 상위 후보입니다.",
    "buy": "가격 대비 배당과 성장이 매력적입니다.",
    "wait": "재무는 좋지만 PER이 아직 매력적이지 않습니다.",
    "hold": "일부 조건만 충족합니다.",
    "pass": "저PER·배당·성장 어느 쪽도 충분하지 않습니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    n, per, loss, cagr, dy = m["n_years"], m["per"], m["loss_years"], m["ni_cagr"], m["div_yield"]
    checks = []

    if per is None:
        checks.append(check("총수익률 비율(TRR)", "price", 30, 0.0, "순이익이 적자라 산출 불가", ok=False))
    else:
        trr = ((cagr or 0.0) * 100 + (dy or 0.0) * 100) / per
        checks.append(check("총수익률 비율(TRR)", "price", 30, scale(trr, 0.7, 2.0),
                            f"(성장률 {pct(cagr)} + 배당 {pct(dy)}) ÷ PER {per:.1f} = {trr:.2f} (기준 2 이상)", ok=trr >= 1.5))

    checks.append(check("저PER", "price", 20, 0.0 if per is None else 1 - scale(per, 8, 20),
                        "PER 산출 불가" if per is None else f"PER {per:.1f}배 (기준 12배 이하)", ok=per is not None and per <= 12))
    if dy is None:
        checks.append(check("배당수익률", "price", 15, None, "배당 데이터 없음"))
    else:
        checks.append(check("배당수익률", "price", 15, scale(dy, 0.01, 0.04), f"배당수익률 {pct(dy)} (기준 3% 이상)", ok=dy >= 0.03))
    checks.append(check("이익 성장", "quality", 10, 0.0 if cagr is None else scale(cagr, 0.0, 0.15),
                        f"순이익 연평균 {pct(cagr)}", ok=cagr is not None and cagr >= 0.07))
    checks.append(check("흑자 유지", "quality", 15, 1 - loss / n, f"최근 {n}년 중 적자 {loss}년", ok=loss == 0))
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
    return finish(m, checks, CFG, TAILS, 0.25, 0.20)
