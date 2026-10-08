"""코인 1종목의 일봉에서 매매이론들이 공통으로 쓰는 지표를 계산한다.

원칙: 마감된 일봉 + '오늘 진행 중인 봉(현재가 기준)'을 함께 쓴다. 돌파·눌림 판단은 현재가를 기준으로 하고,
거래량처럼 진행 중인 봉으로는 왜곡되는 값은 마감된 봉만 쓴다.
"""
import ta


def _ret(c, d):
    return (c[-1] / c[-1 - d] - 1) if len(c) > d else None


def daily_stats(c):
    """'이 코인을 들고 버티기 얼마나 힘들었나' — 일봉 최대 600일 기준. 화면의 '주가 흐름' 카드에 쓰이는 키와 같게 만든다."""
    n = len(c)
    peak, peak_i, longest, max_dd = c[0], 0, 0, 0.0
    for i, x in enumerate(c):
        if x >= peak:
            peak, peak_i = x, i
        max_dd = min(max_dd, x / peak - 1)
        longest = max(longest, i - peak_i)
    hi = max(c[-365:])
    return {"ret_3m": _ret(c, 90), "ret_6m": _ret(c, 180), "ret_1y": _ret(c, 365), "ret_3y": None,
            "dd_3y": c[-1] / hi - 1, "max_dd": max_dd, "longest_uw": longest / 7, "cur_uw": (n - 1 - peak_i) / 7,
            "wk_since_hi3": (n - 1 - c.index(hi, max(0, n - 365))) / 7}


def pain_score(px):
    dd = min(1.0, max(0.0, (-px["max_dd"] - 0.30) / 0.50))
    wk = min(1.0, max(0.0, (px["longest_uw"] - 26) / 130))
    return round(60 * dd + 40 * wk)


def trend_of(price, s50, s200, s200_prev, ret90):
    """up 상승 / rebound 반등 시도 / flat 횡보 / down 하락 (200일선 기준)"""
    if s200 is None:
        return None
    slope = s200 / s200_prev - 1 if s200_prev else 0.0
    above = price >= s200
    if above and slope >= 0:
        return "up"
    if above:
        return "rebound"
    if (ret90 is not None and ret90 <= -0.15) or slope < -0.03:
        return "down"
    return "flat"


def compute(rec):
    cs = rec["candles"]
    done, live = cs[:-1], cs[-1]
    price = float(rec["price"])
    o = [x[1] for x in done]; h = [x[2] for x in done]; l = [x[3] for x in done]; c = [x[4] for x in done]
    val = [x[5] for x in done]
    # 오늘 진행 중인 봉: 종가 자리에 현재가를 넣는다
    H, L, C = h + [max(live[2], price)], l + [min(live[3], price)], c + [price]
    out = {"market": rec["market"], "ticker": rec["market"], "name": rec["name"], "price": price, "currency": "KRW",
           "change24": rec.get("change24"), "value24": rec.get("value24"), "n_days": len(cs), "ok": True, "issue": None}

    a = ta.atr(H, L, C)
    out["atr"] = a
    out["atr_pct"] = a / price if a else None

    # 이동평균
    for n in (20, 50, 60, 120, 150, 200, 210):
        out[f"s{n}"] = ta.sma(C, n)
    out["s20_prev"] = ta.sma(C, 20, 5)
    out["s60_prev"] = ta.sma(C, 60, 10)
    out["s150_prev"] = ta.sma(C, 150, 20)
    out["s200_prev"] = ta.sma(C, 200, 20)
    out["s210_prev"] = ta.sma(C, 210, 20)

    out["rsi14"], out["rsi2"] = ta.rsi(C, 14), ta.rsi(C, 2)
    out["adx"], out["pdi"], out["mdi"] = ta.adx(H, L, C)
    m = ta.macd(C)
    out["macd"], out["macd_sig"], out["hist"], out["hist_prev"], out["macd_since"] = m if m else (None,) * 5
    b = ta.bollinger(C)
    out["bb_mid"], out["bb_up"], out["bb_lo"], out["pctb"], out["bw"], out["bw_pct"] = b if b else (None,) * 6

    # 돈치안 채널: '직전 마감 봉들'의 최고·최저 (현재가가 이를 넘으면 돌파)
    out["hi20"], out["hi55"], out["hi120"] = max(h[-20:]), max(h[-55:]), max(h[-120:])
    out["lo10"], out["lo20"] = min(l[-10:]), min(l[-20:])

    # 다우: 스윙 고점·저점
    ph, pl = ta.pivots(H[:-1], L[:-1], 4)
    out["ph"], out["pl"] = [p for _, p in ph[-3:]], [p for _, p in pl[-3:]]

    # 일목균형표
    ich = ta.ichimoku(H, L, C)
    if ich:
        ten, kij, sa, sb, chik = ich
        out.update({"ten": ten, "kij": kij, "span_a": sa, "span_b": sb, "cloud_top": max(sa, sb), "cloud_bot": min(sa, sb),
                    "chikou_ok": price > chik})

    # 거래량(마감 봉 기준)과 변동성 돌파 기준값
    v20 = sum(val[-21:-1]) / 20
    out["vol_ratio"] = val[-1] / v20 if v20 else None
    out["vol_ratio3"] = (sum(val[-3:]) / 3) / v20 if v20 else None
    out["today_open"] = float(live[1])
    out["prev_range"] = h[-1] - l[-1]
    out["prev_high"], out["prev_low"], out["prev_close"], out["prev_open"] = h[-1], l[-1], c[-1], o[-1]
    out["low5"] = min(L[-5:])

    # 최근 돌파 경과일: 최근 10일 안에 '직전 n일 고점'을 넘은 구간이 시작된 날로부터 며칠 지났는지 (없으면 None)
    def break_age(n):
        age = None
        for back in range(0, 10):
            i = len(C) - 1 - back
            if i - n >= 0 and C[i] > max(H[i - n:i]):
                age = back          # 더 과거까지 이어지면 가장 오래된 돌파일로 갱신
            else:
                break
        return age
    out["break55_age"], out["break120_age"] = break_age(55), break_age(120)

    # 박스(20일): 폭과 현재 위치
    out["box_w"] = (out["hi20"] - out["lo20"]) / out["lo20"] if out["lo20"] else None
    out["box_pos"] = (price - out["lo20"]) / (out["hi20"] - out["lo20"]) if out["hi20"] != out["lo20"] else 0.5

    # 수익률·고저점
    for d in (7, 30, 90, 365):
        out[f"ret{d}"] = _ret(C, d)
    out["high365"], out["low365"] = max(H[-365:]), min(L[-365:])
    out["dd365"] = price / out["high365"] - 1
    out["from_low365"] = price / out["low365"] - 1

    # 주간 추세(엘더): 주봉 13주 EMA 의 방향
    wk = C[::-1][::7][::-1]
    if len(wk) >= 30:
        e = ta.ema_series(wk, 13)
        out["wk_ema_up"] = e[-1] > e[-2] and wk[-1] > e[-1]
    else:
        out["wk_ema_up"] = None

    # 주가 흐름·추세·정배열 (화면의 공통 태그와 같은 이름)
    px = daily_stats(C)
    out["px"], out["pain"] = px, pain_score(px)
    out["trend"] = trend_of(price, out["s50"], out["s200"], out["s200_prev"], out["ret90"])
    out["knife"] = out["trend"] == "down" and out["dd365"] <= -0.30
    out["severe"] = out["trend"] == "down" and (out["dd365"] <= -0.55 or (out["ret90"] is not None and out["ret90"] <= -0.40))
    s = out
    out["align"] = bool(s["s200"] and price >= s["s20"] > s["s60"] > s["s120"] > s["s200"])

    # 추세 훼손 신호 (재무 손절 신호의 코인판)
    w = []
    if s["s200"] and price < s["s200"]:
        w.append("가격이 200일선 아래입니다 (장기 추세 약세)")
    if s["s20"] and s["s60"] and s["s20"] < s["s60"]:
        w.append("20일선이 60일선 아래로 내려갔습니다 (데드크로스)")
    if s["rsi14"] and s["rsi14"] >= 80:
        w.append(f"RSI {s['rsi14']:.0f}로 과열입니다")
    if out["atr_pct"] and out["atr_pct"] >= 0.08:
        w.append(f"하루 변동폭(ATR)이 가격의 {out['atr_pct'] * 100:.0f}%로 매우 큽니다")
    if out["dd365"] <= -0.40:
        w.append(f"1년 고점 대비 {out['dd365'] * 100:.0f}%입니다")
    out["warnings"] = w

    # 차트(마감 봉 + 현재가, 5일 간격으로 줄여서)
    pts = C[::-1][::5][::-1]
    out["spark"] = [round(x) if price >= 1000 else round(x, 2 if price >= 10 else 4) for x in pts]
    return out
