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


def pays_dividend(m):
    """배당 투자자는 최근 연도에 배당을 지급한 종목만 평가한다."""
    return (bool(m.get("div_paid")) or bool(m.get("dps_ok"))) and (m.get("div_yield") or 0) > 0


def ddm_iv(m, r=0.09, g_cap=0.05):
    """배당할인모형 대용치: 배당 총액 x (1+g) / (요구수익률 - g). g 는 최근 배당 성장률(0~5%로 제한)."""
    d = m.get("div_paid")
    if not d:
        return None
    g = clamp(m.get("div_cagr") or 0.0, 0.0, g_cap)
    return d * (1 + g) / (r - g)


def dividend_checks(m, yield_rng=(0.015, 0.04), cagr_rng=(0.0, 0.10), payout_cap=0.65, w=None):
    """배당 투자자들이 공통으로 보는 항목(수익률·성장·안전·지속). w 로 항목별 배점을 바꾼다(0이면 항목 제외)."""
    w = {"yield": 20, "growth": 20, "payout": 15, "cover": 10, "streak": 10, **(w or {})}
    dy, g, po, pf = m["div_yield"], m["div_cagr"], m["payout_ni"], m["payout_fcf"]
    cuts, yrs, n = m["div_cuts"], m["div_years"], m["n_years"]
    lo, hi = yield_rng
    out = []
    if w["yield"]:
        # 수익률은 높을수록 좋되, 너무 높으면(배당 함정 가능성) 점수를 깎는다
        y_ratio = scale(dy, lo, hi) if dy <= hi * 1.75 else max(0.4, 1 - scale(dy, hi * 1.75, hi * 3))
        out.append(check("배당수익률", "price", w["yield"], y_ratio,
                         f"배당수익률 {pct(dy)} (기준 {lo * 100:.1f}~{hi * 100:.1f}%, 너무 높으면 함정 주의)", ok=dy >= lo))
    if w["growth"]:
        out.append(check("배당 성장", "quality", w["growth"], None if g is None else scale(g, *cagr_rng),
                         "배당 이력이 짧아 성장률 산출 불가" if g is None else (f"주당 배당 연평균 {pct(g)} 성장 (5년)" if m.get("dps_ok") else f"배당 총액 연평균 {pct(g)} 성장 (최근 {yrs}년 지급)"),
                         ok=g is not None and g >= cagr_rng[1] * 0.5))
    if w["payout"]:
        out.append(check("배당 성향(이익)", "quality", w["payout"],
                         None if po is None else 1 - scale(po, payout_cap * 0.6, payout_cap * 1.4),
                         "순이익이 적자라 산출 불가" if po is None else f"순이익의 {po * 100:.0f}%를 배당 (기준 {payout_cap * 100:.0f}% 이하)",
                         ok=po is not None and po <= payout_cap))
    if w["cover"]:
        if m["is_financial"]:
            out.append(check("현금 배당 여력", "quality", w["cover"], None, "금융업은 잉여현금흐름 기준을 적용하지 않음"))
        else:
            out.append(check("현금 배당 여력", "quality", w["cover"], None if pf is None else 1 - scale(pf, 0.5, 1.0),
                             "잉여현금흐름이 적자라 배당을 현금으로 못 감당" if pf is None else f"잉여현금흐름의 {pf * 100:.0f}%를 배당",
                             ok=pf is not None and pf <= 0.75))
    if w["streak"]:
        if m.get("dps_ok"):
            su, ok_ = m["dps_streak_up"], m["dps_streak_ok"]
            ratio = (0.5 * scale(yrs, 3, 20) + 0.5 * scale(max(su, ok_ * 0.5), 0, 10)) * (1.0 if cuts == 0 else 0.5)
            out.append(check("배당 지속·증가", "quality", w["streak"], ratio,
                             f"{yrs}년 연속 지급 · {su}년 연속 증가 · 최근 10년 삭감 {cuts}회", ok=cuts == 0 and yrs >= 10))
        else:
            out.append(check("배당 지속", "quality", w["streak"], 0.0 if yrs < n else (1.0 if cuts == 0 else 0.4),
                             f"최근 {n}년 중 {yrs}년 지급 · 25% 넘는 삭감 {cuts}회", ok=yrs >= n and cuts == 0))
    return out
