"""투자자 모듈들이 함께 쓰는 도구: 점수 계산, 판정, 가격 전략, 재무 경고."""


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def scale(x, lo, hi):
    """lo 이하 0, hi 이상 1, 사이는 선형."""
    return clamp((x - lo) / (hi - lo))


def pct(x):
    return "-" if x is None else f"{x * 100:.1f}%"


def check(name, group, max_pts, ratio, detail, ok=None):
    """ratio: 0~1 달성률. None 이면 해당 없음(점수 계산에서 제외)."""
    if ratio is None:
        return {"name": name, "group": group, "points": 0, "max": 0, "ok": None, "detail": detail}
    return {"name": name, "group": group, "points": round(max_pts * ratio, 1), "max": max_pts,
            "ok": (ratio >= 0.7) if ok is None else ok, "detail": detail}


def tally(checks):
    """(총점 0~100, 기업 질 0~1)  — 해당없음 항목은 분모에서 빠진다."""
    avail = sum(c["max"] for c in checks)
    pts = sum(c["points"] for c in checks)
    q_av = sum(c["max"] for c in checks if c["group"] == "quality")
    q_pts = sum(c["points"] for c in checks if c["group"] == "quality")
    return (round(100 * pts / avail) if avail else 0), ((q_pts / q_av) if q_av else 0.0)


TONE_LABEL = {"strong": "강력 매수 후보", "buy": "매수 후보", "wait": "훌륭한 기업 · 가격 부담",
              "hold": "보통 · 관찰", "pass": "부적합"}


def verdict(score, quality, mos, cfg):
    """cfg = {strong:(질,안전마진,총점), buy:(질,안전마진,총점), wait_q:질, hold:총점}"""
    m = -1.0 if mos is None else mos
    sq, sm, ss = cfg["strong"]
    bq, bm, bs = cfg["buy"]
    if quality >= sq and m >= sm and score >= ss:
        tone = "strong"
    elif quality >= bq and m >= bm and score >= bs:
        tone = "buy"
    elif quality >= cfg["wait_q"]:
        tone = "wait"
    elif score >= cfg["hold"]:
        tone = "hold"
    else:
        tone = "pass"
    return TONE_LABEL[tone], tone


def summary(checks, tone, tails, lead=""):
    scored = [c for c in checks if c["max"]]
    strengths = sorted((c for c in scored if c["points"] / c["max"] >= 0.7), key=lambda c: -c["points"] / c["max"])[:2]
    weak = sorted((c for c in scored if c["points"] / c["max"] < 0.5), key=lambda c: c["points"] / c["max"])[:2]
    short = lambda c: c["detail"].split(" (")[0]
    parts = [lead] if lead else []
    if strengths:
        parts.append("강점: " + ", ".join(f"{c['name']}({short(c)})" for c in strengths) + ".")
    if weak:
        parts.append("걸리는 점: " + ", ".join(f"{c['name']}({short(c)})" for c in weak) + ".")
    parts.append(tails[tone])
    return " ".join(parts)


def round_price(v, cur):
    if cur != "KRW":
        return round(v, 2)
    for limit, unit in ((500_000, 1000), (100_000, 500), (50_000, 100), (10_000, 50), (5_000, 10)):
        if v >= limit:
            return int(round(v / unit) * unit)
    return int(round(v / 5) * 5) or 1


def make_levels(m, req_mos, stop_pct=0.20, iv=None):
    """재무 기준 가격 전략 (차트 아님).

    적정가 = 추정 내재가치를 주당으로 환산
    매수가 = 적정가 × (1 − 요구 안전마진)
    매도가 = 적정가 (내재가치에 닿으면 이익 실현)
    손절가 = 진입가(매수가·현재가 중 낮은 쪽) × (1 − 손절폭)
    """
    iv = m["intrinsic_value"] if iv is None else iv
    price, mcap, cur = m["price"], m["market_cap"], m["currency"]
    if not iv or not price or not mcap:
        return None
    fair = iv / mcap * price
    buy = fair * (1 - req_mos)
    entry = min(buy, price)
    stop = entry * (1 - stop_pct)
    return levels_from_raw(price, fair, buy, fair, stop, cur, req_mos, stop_pct)


def levels_from_raw(price, fair, buy, sell, stop, cur, req_mos, stop_pct):
    entry = min(buy, price)
    if price <= buy:
        status = "buy"
    elif price <= buy * 1.10:
        status = "near"
    elif price < sell:
        status = "wait"
    else:
        status = "sell"
    rp = lambda v: round_price(v, cur)
    return {
        "price": rp(price), "fair": rp(fair), "buy": rp(buy), "sell": rp(sell), "stop": rp(stop), "entry": rp(entry),
        "req_mos": req_mos, "stop_pct": stop_pct,
        "upside": sell / entry - 1, "rr": (sell - entry) / (entry - stop) if entry > stop else 0.0,
        "to_buy": buy / price - 1, "to_sell": sell / price - 1, "status": status,
        "raw": {"buy": buy, "sell": sell, "stop": stop, "fair": fair},
    }


def warnings(m):
    """재무가 이미 나빠졌는지: 가격과 무관하게 '팔아야 할 이유'가 되는 신호들."""
    w = []
    roe = m["roe"][-1]
    if m["net_income"][-1] <= 0:
        w.append("최근 연도 순이익이 적자입니다")
    elif roe is not None and roe < 0.10:
        w.append(f"최근 ROE {roe * 100:.1f}%로 10% 아래입니다")
    if not m["is_financial"]:
        if m["debt_to_ni"] is not None and m["debt_to_ni"] > 5:
            w.append(f"총부채가 순이익의 {m['debt_to_ni']:.1f}배로 과다합니다")
        if m["fcf"] and m["fcf"][-1] is not None and m["fcf"][-1] < 0:
            w.append("최근 연도 잉여현금흐름이 적자입니다")
    if m["loss_years"] >= 2:
        w.append(f"최근 {m['n_years']}년 중 {m['loss_years']}년 적자입니다")
    return w


def growth_iv(m):
    """성장주용 내재가치(metrics.iv_g). 없으면 None."""
    return m.get("iv_g")


def finish(m, checks, cfg, tails, req_mos, stop_pct, lead="", iv=None):
    """모든 투자자가 공통으로 마지막에 호출: 판정·요약·가격 전략을 묶어 반환.

    iv 를 주면(성장주 가치 등) 안전마진과 가격 전략을 그 값으로 계산하고,
    주지 않으면 기본(잉여현금흐름 기반) 내재가치를 쓴다.
    """
    score, quality = tally(checks)
    mos = m["mos"] if iv is None else (None if not iv else (iv - m["market_cap"]) / iv)
    v, tone = verdict(score, quality, mos, cfg)
    return {
        "score": score, "quality": round(quality * 100), "verdict": v, "tone": tone,
        "checks": checks, "summary": summary(checks, tone, tails, lead),
        "levels": make_levels(m, req_mos(quality) if callable(req_mos) else req_mos, stop_pct, iv),
        "warnings": warnings(m),
    }
