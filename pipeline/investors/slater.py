"""짐 슬레이터 스타일(줄루 원칙): PEG가 낮은 성장주. 성장은 빠른데 가격은 아직 못 따라온 종목.

주의: 슬레이터 본인의 판단이 아니라 『줄루 원칙』의 기준을 수치화한 모의 평가다.
"""
from .common import check, finish, pct, scale

INFO = {
    "id": "slater",
    "name": "짐 슬레이터",
    "mono": "슬",
    "tagline": "줄루 원칙. PEG가 낮은 성장주를 일찍 발견",
    "principles": [
        "PEG(PER ÷ 이익성장률)가 1 이하, 낮을수록 좋음",
        "이익과 매출이 빠르게 늘 것",
        "영업이익률이 높을 것",
        "이익보다 현금이 더 많이 들어올 것",
        "부채가 낮을 것",
        "매출 대비 가격(PSR)이 낮을 것",
    ],
    "price_rules": [
        "적정가 = 이익 성장률을 반영한 5년 뒤 가치를 연 12%로 할인한 값(성장률은 25% 보수적으로 삭감)",
        "매수가 = 적정가에서 안전마진 20%를 뺀 가격",
        "매도가 = 적정가. PEG가 1.5를 넘기 전에 정리합니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 성장 둔화로 PEG가 급등, 현금흐름 적자, 부채 증가",
    ],
}
CFG = {"strong": (0.65, -0.10, 78), "buy": (0.55, -0.25, 66), "wait_q": 0.75, "hold": 50}
TAILS = {
    "strong": "성장에 비해 가격이 매우 싼 줄루 원칙의 모범 사례입니다.",
    "buy": "성장 대비 가격이 매력적입니다.",
    "wait": "재무와 성장은 좋지만 PEG가 높아졌습니다. 기다리는 쪽입니다.",
    "hold": "성장 대비 가격의 매력이 일부만 있습니다.",
    "pass": "PEG와 성장, 현금창출 면에서 기준에 못 미칩니다.",
}


def evaluate(m):
    fin = m["is_financial"]
    per, peg, cagr, rc, om, ps = m["per"], m["peg"], m["ni_cagr"], m["rev_cagr"], m["op_margin_avg"], m["ps"]
    checks = []

    if peg is None:
        why = "순이익 적자" if per is None else "이익이 늘지 않아"
        checks.append(check("PEG", "price", 30, 0.0, f"{why} PEG 산출 불가", ok=False))
    else:
        checks.append(check("PEG", "price", 30, 1 - scale(peg, 0.5, 1.5), f"PEG {peg:.2f} (기준 1 이하, 0.75 이하가 이상적)", ok=peg <= 1.0))
    checks.append(check("이익 성장", "quality", 15, 0.0 if cagr is None else scale(cagr, 0.08, 0.25),
                        "이익 성장률 산출 불가" if cagr is None else f"순이익 연평균 {pct(cagr)} (기준 15% 이상)", ok=cagr is not None and cagr >= 0.15))
    checks.append(check("매출 성장", "quality", 10, None if rc is None else scale(rc, 0.05, 0.20),
                        "매출 데이터 없음" if rc is None else f"매출 연평균 {pct(rc)} (기준 10% 이상)", ok=rc is not None and rc >= 0.10))
    if fin or om is None:
        checks.append(check("영업이익률", "quality", 10, None, "금융업은 적용하지 않음" if fin else "영업이익 데이터 없음"))
    else:
        checks.append(check("영업이익률", "quality", 10, scale(om, 0.08, 0.20), f"평균 영업이익률 {pct(om)} (기준 10% 이상)", ok=om >= 0.10))
    conv = m["fcf_to_ni"]
    if fin or conv is None:
        checks.append(check("현금 > 이익", "quality", 10, None, "금융업은 적용하지 않음" if fin else "현금흐름 데이터 없음"))
    else:
        checks.append(check("현금 > 이익", "quality", 10, scale(conv, 0.7, 1.2), f"순이익 대비 현금전환 {pct(conv)} (기준 100% 이상)", ok=conv >= 1.0))
    de = m["debt_to_equity"]
    if fin or de is None:
        checks.append(check("낮은 부채", "quality", 15, None, "금융업은 적용하지 않음" if fin else "부채 데이터 없음"))
    else:
        checks.append(check("낮은 부채", "quality", 15, 1 - scale(de, 0.3, 1.0), f"부채/자본 {de:.2f}배 (기준 0.5배 이하)", ok=de <= 0.5))
    checks.append(check("저PSR", "price", 10, None if ps is None else 1 - scale(ps, 1, 5),
                        "매출 데이터 없음" if ps is None else f"PSR {ps:.1f}배 (기준 2배 이하)", ok=ps is not None and ps <= 2))
    return finish(m, checks, CFG, TAILS, 0.20, 0.20, iv=m.get("iv_g") or 0)
