"""주간 종가(최근 최대 5년)에서 '이 가격을 얼마나 오래, 얼마나 깊게 견뎌야 했나'를 계산한다. 주식·코인이 함께 쓴다."""


def price_stats(c):
    n = len(c)
    if n < 60:
        return None
    cur = c[-1]
    ret = lambda w: (cur / c[-1 - w] - 1) if n > w else None
    tail3 = c[-156:]
    hi3 = max(tail3)
    i_hi3 = n - len(tail3) + tail3.index(hi3)
    peak, peak_i, longest, max_dd = c[0], 0, 0, 0.0
    for i, x in enumerate(c):
        if x >= peak:
            peak, peak_i = x, i
        max_dd = min(max_dd, x / peak - 1)
        longest = max(longest, i - peak_i)
    ma40 = sum(c[-40:]) / 40
    ma40_prev = sum(c[-52:-12]) / 40
    # 이평선 정배열: 주가 ≥ 4주선 > 12주선 > 24주선 > 40주선 (대략 20·60·120·200일선이 위에서부터 차례로)
    ma4, ma12, ma24 = sum(c[-4:]) / 4, sum(c[-12:]) / 12, sum(c[-24:]) / 24
    align = bool(cur >= ma4 > ma12 > ma24 > ma40)
    return {
        "align": align, "ma4": ma4, "ma12": ma12, "ma24": ma24, "ma40": ma40,
        "ret_3m": ret(13), "ret_6m": ret(26), "ret_1y": ret(52), "ret_3y": ret(156),
        "dd_3y": cur / hi3 - 1, "wk_since_hi3": n - 1 - i_hi3,
        "max_dd": max_dd, "longest_uw": longest, "cur_uw": n - 1 - peak_i,
        "vs_ma40": cur / ma40 - 1, "ma40_slope": ma40 / ma40_prev - 1,
    }
