"""제럴딘 와이스 스타일: 배당 수익률로 우량주의 싼 때를 찾는다. 꾸준히 배당해 온 우량주 중 수익률이 높아진 구간.

주의: 와이스 본인의 판단이 아니라 그의 공개된 원칙을 수치화한 모의 평가다. 과거 수익률 밴드 대신 현재 수익률과 배당 안정성을 본다.
"""
from .common import check, ddm_iv, dividend_checks, finish, pays_dividend

INFO = {
    "id": "weiss",
    "name": "제럴딘 와이스",
    "mono": "와",
    "tagline": "배당 수익률로 우량주의 싼 때를 읽는 배당 투자자",
    "principles": [
        "꾸준히 배당하고 삭감하지 않은 우량주만 볼 것",
        "배당수익률이 높아졌다면 주가가 싸다는 신호",
        "배당 성향이 과하지 않아 배당이 안전할 것",
        "이익이 꾸준하고 적자가 없을 것",
    ],
    "price_rules": [
        "적정가 = 배당할인모형(요구수익률 9%, 배당 성장 반영)으로 계산한 값",
        "매수가 = 적정가에서 안전마진 10%를 뺀 가격 (수익률이 높아지는 구간)",
        "매도가 = 적정가. 수익률이 평소 수준으로 내려오면 팝니다",
        "손절가 = 진입가의 -20%",
        "재무 손절 신호: 배당 삭감, 이익 감소",
    ],
}
CFG = {"strong": (0.70, 0.0, 75), "buy": (0.60, -0.15, 62), "wait_q": 0.75, "hold": 48}
TAILS = {
    "strong": "배당이 안정적이고 수익률도 매력적인 우량 배당주입니다.",
    "buy": "배당이 안전하고 수익률이 받아들일 만합니다.",
    "wait": "배당은 안정적이지만 수익률이 낮아 아직 비쌉니다.",
    "hold": "일부 조건만 충족합니다.",
    "pass": "배당 수익률과 안정성이 충분하지 않습니다.",
}


def evaluate(m):
    if not pays_dividend(m):
        return None
    checks = dividend_checks(m, yield_rng=(0.025, 0.05), cagr_rng=(0.0, 0.08), payout_cap=0.65,
                             w={"yield": 30, "growth": 10, "payout": 20, "cover": 10, "streak": 15})
    loss, n = m["loss_years"], m["n_years"]
    checks.append(check("흑자 유지", "quality", 15, 1 - loss / n, f"최근 {n}년 중 적자 {loss}년", ok=loss == 0))
    return finish(m, checks, CFG, TAILS, 0.10, 0.20, iv=ddm_iv(m))
