"""원본 재무 데이터(raw)에서 투자자들이 공통으로 쓰는 지표를 계산한다."""
from datetime import datetime, timedelta
from statistics import mean, pstdev

FINANCIAL_SECTORS = {"Financial Services"}


def _ratio(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _cagr(first, last, years):
    if first is None or last is None or first <= 0 or last <= 0 or years <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def dps_stats(rec, mcap0):
    """주당 배당 이력(fetch.py 의 dps)으로 연속 지급·연속 증가·성장률·삭감 횟수·TTM 수익률을 계산한다. 이력이 없으면 빈 dict."""
    d = rec.get("dps")
    if not d or not d.get("by_year"):
        return {"dps_ok": False}
    by = {int(y): v for y, v in d["by_year"].items()}
    cur = datetime.now().year
    last = max(y for y in by if y < cur) if any(y < cur for y in by) else None
    if last is None:
        return {"dps_ok": False}
    paid = 0
    while by.get(last - paid, 0) > 0:
        paid += 1
    up = ok = 0
    y = last
    while by.get(y, 0) > 0 and by.get(y - 1, 0) > 0 and by[y] > by[y - 1] * 1.005:
        up += 1; y -= 1
    y = last
    while by.get(y, 0) > 0 and by.get(y - 1, 0) > 0 and by[y] >= by[y - 1] * 0.97:
        ok += 1; y -= 1
    cagr = lambda n: _cagr(by[last - n], by[last], n) if by.get(last - n, 0) > 0 and by.get(last, 0) > 0 else None
    cuts = sum(1 for y in range(last - 9, last + 1) if by.get(y - 1, 0) > 0 and 0 <= by.get(y, 0) < by[y - 1] * 0.75)
    ttm = d.get("ttm") or 0.0
    # 지급 주기·월·다음 배당락 추정 (배당락일 기준)
    today = datetime.now()
    dts = [(datetime.strptime(x[0], "%Y-%m-%d"), x[1]) for x in (d.get("dates") or [])]
    recent = [x for x in dts if (today - x[0]).days <= 400]
    n12 = len([x for x in dts if (today - x[0]).days <= 365])
    freq = n12 if n12 in (1, 2, 4, 12) else (4 if n12 == 3 else (12 if n12 > 6 else (n12 or None)))
    months = sorted({x[0].month for x in recent}) if recent else []
    nxt = None
    if dts and freq:
        step = 365 / freq
        cand = dts[-1][0] + timedelta(days=step)
        while cand < today - timedelta(days=20) and (cand - dts[-1][0]).days < 800:
            cand += timedelta(days=step)
        nxt = cand.strftime("%Y-%m") if cand >= today - timedelta(days=20) else None
    r3 = (rec.get("px") or {}).get("ret_3y")
    p0 = rec["price"] / (1 + r3) if (r3 is not None and rec.get("price") and r3 > -0.99) else None
    return {"dps_freq": freq, "dps_months": months, "dps_last": (dts[-1][0].strftime("%Y-%m-%d"), dts[-1][1]) if dts else None,
            "dps_next": nxt, "dps_yoc3": (ttm / p0) if (p0 and ttm) else None,
            "dps_ok": True, "dps_paid_years": paid, "dps_streak_up": up, "dps_streak_ok": ok, "dps_cagr5": cagr(5), "dps_cagr10": cagr(10),
            "dps_cuts": cuts, "dps_ttm": ttm, "dps_last_year": last,
            "dps_hist": [[y, by[y]] for y in range(last - 9, last + 1) if y in by]}


def _safety(o):
    """배당 안전 점수(100점): 이익 대비 배당 성향 30 + 현금 여력 25 + 삭감 이력 20 + 지급 연수 15 + 이익 안정 10. A≥80 · B≥65 · C≥50 · D."""
    po, pf, fin = o.get("payout_ni"), o.get("payout_fcf"), o.get("is_financial")
    if o.get("sector") == "Real Estate" and pf is not None:   # 리츠는 회계상 순이익이 감가상각으로 작아 보이므로 현금흐름 기준으로 본다
        po = pf
    pts = 0
    if po is not None:
        pts += 30 if po <= 0.4 else 24 if po <= 0.6 else 14 if po <= 0.8 else 6 if po <= 1.0 else 0
    if fin:
        pts += 20 if (po is not None and po <= 0.6) else 10
    elif pf is not None:
        pts += 25 if pf <= 0.5 else 18 if pf <= 0.75 else 8 if pf <= 1.0 else 0
    c = o.get("dps_cuts") or 0
    pts += 20 if c == 0 else 8 if c == 1 else 0
    y = o.get("dps_paid_years") or 0
    pts += 15 if y >= 20 else 11 if y >= 10 else 7 if y >= 5 else 3
    pts += 10 if o.get("loss_years", 0) == 0 else 3
    return {"score": pts, "grade": "A" if pts >= 80 else "B" if pts >= 65 else "C" if pts >= 50 else "D"}


def intrinsic_value(base, growth, discount=0.10, terminal=0.03, years=10):
    """보수적 2단계 현금흐름 할인. base: 현재 주주이익, growth: 10년간 연성장률."""
    if base is None or base <= 0:
        return None
    total, cf = 0.0, base
    for t in range(1, years + 1):
        cf *= 1 + growth
        total += cf / (1 + discount) ** t
    total += cf * (1 + terminal) / (discount - terminal) / (1 + discount) ** years
    return total


def trend_of(px):
    """주가 추세: up 상승 / rebound 반등 시도 / flat 횡보 / down 하락. (40주 이동평균 기준, 약 200일선)"""
    if not px:
        return None
    above, slope = px["vs_ma40"] >= 0, px["ma40_slope"]
    if above and slope >= 0:
        return "up"
    if above:
        return "rebound"
    if (px["ret_1y"] is not None and px["ret_1y"] <= -0.15) or slope < -0.03:
        return "down"
    return "flat"


def pain_score(px):
    """'이 종목을 들고 버티기 얼마나 힘들었나' 0~100: 최대 낙폭(60) + 고점 회복까지 걸린 최장 기간(40)."""
    if not px:
        return None
    dd = min(1.0, max(0.0, (-px["max_dd"] - 0.20) / 0.40))
    wk = min(1.0, max(0.0, (px["longest_uw"] - 26) / 130))
    return round(60 * dd + 40 * wk)


def compute(rec):
    """종목 1개의 지표 dict. 계산 불가 항목은 None."""
    ys = [y for y in rec.get("years", []) if y.get("net_income") is not None and y.get("equity")]
    out = {
        "ticker": rec["ticker"], "name": rec["name"], "market": rec["market"],
        "sector": rec.get("sector"), "industry": rec.get("industry"),
        "price": rec.get("price"), "market_cap": rec.get("market_cap"),
        "currency": rec.get("currency"), "n_years": len(ys), "ok": False, "issue": None,
    }
    if len(ys) < 3:
        out["issue"] = "재무 데이터 부족(3년 미만)"
        return out
    if not rec.get("market_cap"):
        out["issue"] = "시가총액 없음"
        return out
    if rec.get("fin_currency") and rec.get("currency") and rec["fin_currency"] != rec["currency"]:
        out["issue"] = f"재무통화({rec['fin_currency']})와 거래통화({rec['currency']}) 불일치"
        return out

    fin = rec.get("sector") in FINANCIAL_SECTORS
    ni = [y["net_income"] for y in ys]
    eq = [y["equity"] for y in ys]
    roe = [_ratio(n, e) for n, e in zip(ni, eq)]
    op_m = [_ratio(y.get("op_income"), y.get("revenue")) for y in ys]
    op_m = [m for m in op_m if m is not None]
    gross_m = [_ratio(y.get("gross_profit"), y.get("revenue")) for y in ys]
    gross_m = [m for m in gross_m if m is not None]
    fcf = [y.get("fcf") for y in ys]
    fcf_known = [f for f in fcf if f is not None]
    last = ys[-1]
    debt = last.get("debt")

    span = ys[-1]["year"] - ys[0]["year"]
    ni_cagr = _cagr(ni[0], ni[-1], span)
    rev = [y.get("revenue") for y in ys]
    rev_cagr = _cagr(rev[0], rev[-1], span)

    # 확장 지표 (그레이엄·린치·멍거·피셔·그린블라트용)
    mcap0 = rec["market_cap"]
    per0 = _ratio(mcap0, ni[-1]) if ni[-1] > 0 else None
    pb = _ratio(mcap0, eq[-1]) if eq[-1] and eq[-1] > 0 else None
    cash = last.get("cash") or 0.0
    ev = mcap0 + (debt or 0.0) - cash
    ebit = last.get("op_income")
    invested = eq[-1] + (debt or 0.0) - cash
    cur_ratio = _ratio(last.get("current_assets"), last.get("current_liabilities"))
    divs = [y.get("dividends") for y in ys if y.get("dividends") is not None]
    rnd = last.get("rnd")
    fcf3 = [f for f in fcf[-3:] if f is not None]
    dl = last.get("dividends")
    intr = last.get("interest")
    hi52 = rec.get("week52_high")
    ni_mean = mean(ni)

    # 주주이익(owner earnings) 대용치: 금융업은 순이익, 그 외는 잉여현금흐름. 최근 3년 평균으로 보수적 산출.
    if fin:
        base_series = ni[-3:]
    else:
        base_series = [f for f in fcf[-3:] if f is not None]
    base = mean(base_series) if len(base_series) >= 2 else None
    growth = 0.03 if ni_cagr is None else max(0.0, min(ni_cagr, 0.08))
    iv = intrinsic_value(base, growth)
    mcap = rec["market_cap"]
    mos = None if iv is None else (iv - mcap) / iv

    # 성장주용 가치: 성장률을 반영해 5년 뒤 이익 × 졸업 PER 을 12%로 할인 (보수적으로 성장률 25% 삭감)
    rev_last = last.get("revenue")
    g_src = ni_cagr if ni_cagr is not None else rev_cagr
    iv_g = None
    if g_src is not None:
        g = max(0.0, min(g_src, 0.35)) * 0.75
        exit_per = max(12.0, min(g * 100 * 1.2, 28.0))
        g_base = ni[-1] if ni[-1] > 0 else (mean(fcf3) if len(fcf3) >= 2 and mean(fcf3) > 0 else None)
        if g_base:
            iv_g = g_base * (1 + g) ** 5 * exit_per / 1.12 ** 5

    # 배당 지표: 연간 '배당 지급 총액'(주당 배당이 아님) 기준이라 자사주 매입·주식 수 변화는 반영되지 않는다.
    dpay = [None if y.get("dividends") is None else max(0.0, -y["dividends"]) for y in ys]
    dp_last = dpay[-1]
    dp_pos = [d for d in dpay if d]
    div_cagr = _cagr(dp_pos[0], dp_pos[-1], max(1, len(dp_pos) - 1)) if len(dp_pos) >= 2 and dpay[-1] else None
    div_cuts = sum(1 for a_, b_ in zip(dpay, dpay[1:]) if a_ and b_ is not None and b_ < a_ * 0.9)
    out.update({
        "div_paid": dp_last, "div_years": sum(1 for d in dpay if d), "div_cagr": div_cagr, "div_cuts": div_cuts,
        **dps_stats(rec, mcap0),
        "payout_ni": (dp_last / ni[-1]) if (dp_last and ni[-1] > 0) else None,
        "payout_fcf": (dp_last / fcf[-1]) if (dp_last and fcf[-1] and fcf[-1] > 0) else None,
        "rev_last": rev_last,
        "ni_yoy": ((ni[-1] / ni[-2] - 1) if (len(ni) >= 2 and ni[-2] > 0 and ni[-1] > 0) else None),
        "rev_yoy": ((rev[-1] / rev[-2] - 1) if (len(rev) >= 2 and rev[-1] and rev[-2]) else None),
        "ps": _ratio(mcap, rev_last) if rev_last else None,
        "net_margin": _ratio(ni[-1], rev_last) if rev_last else None,
        "iv_g": iv_g, "mos_g": None if not iv_g else (iv_g - mcap) / iv_g,
        "ok": True, "is_financial": fin, "first_year": ys[0]["year"], "last_year": ys[-1]["year"],
        "roe": roe, "roe_avg": mean(roe),
        "op_margin": op_m, "op_margin_avg": mean(op_m) if op_m else None,
        "op_margin_min": min(op_m) if op_m else None,
        "gross_margin_avg": mean(gross_m) if gross_m else None,
        "net_income": ni, "ni_cagr": ni_cagr, "loss_years": sum(1 for n in ni if n <= 0),
        "debt": debt, "debt_to_ni": (debt / ni[-1]) if (debt is not None and ni[-1] > 0) else None,
        "debt_to_equity": _ratio(debt, eq[-1]),
        "fcf": fcf, "fcf_pos_ratio": (sum(1 for f in fcf_known if f > 0) / len(fcf_known)) if fcf_known else None,
        "fcf_to_ni": (mean([f / n for f, n in zip(fcf, ni) if f is not None and n > 0])
                      if any(f is not None and n > 0 for f, n in zip(fcf, ni)) else None),
        "per": _ratio(mcap, ni[-1]) if ni[-1] > 0 else None,
        "earnings_yield": _ratio(ni[-1], mcap),
        "intrinsic_value": iv, "mos": mos, "iv_growth": growth, "iv_base": base,
        "is_utility": rec.get("sector") == "Utilities",
        "px": rec.get("px"), "trend": trend_of(rec.get("px")), "pain": pain_score(rec.get("px")),
        "align": bool(rec.get("px") and rec["px"].get("align")),
        "knife": bool(rec.get("px")) and trend_of(rec.get("px")) == "down" and rec["px"]["dd_3y"] <= -0.30,
        # 급락 중: 하락 추세 + (3년 고점 대비 -50% 이하 또는 1년 -40% 이하) — 사람이 버티기 매우 어려운 구간
        "severe": bool(rec.get("px")) and trend_of(rec.get("px")) == "down" and (
            rec["px"]["dd_3y"] <= -0.50 or (rec["px"]["ret_1y"] is not None and rec["px"]["ret_1y"] <= -0.40)),
        "rev_cagr": rev_cagr, "pb": pb,
        "peg": (per0 / (ni_cagr * 100)) if (per0 and ni_cagr and ni_cagr > 0.005) else None,
        "current_ratio": cur_ratio,
        "ev_ebit_yield": (ebit / ev) if (ebit is not None and ev > 0) else None,
        "roic": (ebit / invested) if (ebit is not None and invested > 0) else None,
        "rnd_ratio": _ratio(rnd, last.get("revenue")) if rnd else None,
        "div_ratio": (sum(1 for d in divs if d < 0) / len(divs)) if divs else None,
        "op_margin_trend": (op_m[-1] - op_m[0]) if len(op_m) >= 2 else None,
        "fcf_yield": (mean(fcf3) / mcap0) if len(fcf3) >= 2 else None,
        "div_yield": None if dl is None else (-dl / mcap0 if dl < 0 else 0.0),
        "net_cash_ratio": None if last.get("cash") is None else (last["cash"] - (debt or 0.0)) / mcap0,
        "interest_cover": (ebit / abs(intr)) if (ebit is not None and intr) else None,
        "ni_cv": (pstdev(ni) / ni_mean) if ni_mean > 0 else None,
        "drawdown52": (rec["price"] / hi52 - 1) if (rec.get("price") and hi52) else None,
    })
    if out.get("dps_ok"):
        # 주당 배당 이력이 있으면 그것을 우선한다 (재무제표의 배당 총액은 자사주·주식 수 변화에 흔들린다)
        if out["dps_ttm"] and rec.get("price"):
            out["div_yield"] = out["dps_ttm"] / rec["price"]
        elif out["dps_ttm"] == 0:
            out["div_yield"] = 0.0
        if out["dps_cagr5"] is not None:
            out["div_cagr"] = out["dps_cagr5"]
        out["div_cuts"] = out["dps_cuts"]
        out["div_years"] = out["dps_paid_years"]
        out["dps_safety"] = _safety(out)
    return out
