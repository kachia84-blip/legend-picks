"""기술적 지표 (표준 라이브러리만 사용). 모든 함수는 '마감된 일봉' 리스트(오래된 것 → 최신)를 받는다."""


def sma(x, n, back=0):
    """back 일 전 시점의 n일 단순이동평균."""
    end = len(x) - back
    return sum(x[end - n:end]) / n if end >= n and n > 0 else None


def ema_series(x, n):
    k = 2 / (n + 1)
    out = [x[0]]
    for v in x[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(c, n=14):
    """웰스 와일더 RSI."""
    if len(c) <= n:
        return None
    gains = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    losses = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):
        ag, al = (ag * (n - 1) + g) / n, (al * (n - 1) + l) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def _tr(h, l, c):
    return [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]


def atr(h, l, c, n=14):
    tr = _tr(h, l, c)
    if len(tr) < n:
        return None
    a = sum(tr[:n]) / n
    for t in tr[n:]:
        a = (a * (n - 1) + t) / n
    return a


def adx(h, l, c, n=14):
    """(ADX, +DI, -DI)"""
    if len(c) < 2 * n + 2:
        return None, None, None
    tr = _tr(h, l, c)
    pdm = [max(h[i] - h[i - 1], 0) if (h[i] - h[i - 1]) > (l[i - 1] - l[i]) else 0 for i in range(1, len(c))]
    mdm = [max(l[i - 1] - l[i], 0) if (l[i - 1] - l[i]) > (h[i] - h[i - 1]) else 0 for i in range(1, len(c))]
    atr_s, p_s, m_s = sum(tr[:n]), sum(pdm[:n]), sum(mdm[:n])
    dxs = []
    for i in range(n, len(tr)):
        atr_s = atr_s - atr_s / n + tr[i]
        p_s = p_s - p_s / n + pdm[i]
        m_s = m_s - m_s / n + mdm[i]
        pdi, mdi = 100 * p_s / atr_s, 100 * m_s / atr_s
        dxs.append((100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0, pdi, mdi))
    if len(dxs) < n:
        return None, None, None
    a = sum(d[0] for d in dxs[:n]) / n
    for d in dxs[n:]:
        a = (a * (n - 1) + d[0]) / n
    return a, dxs[-1][1], dxs[-1][2]


def macd(c, fast=12, slow=26, sig=9):
    """(macd, signal, hist, 직전 hist, 최근 골든크로스 후 경과일 or None)"""
    if len(c) < slow + sig + 5:
        return None
    ef, es = ema_series(c, fast), ema_series(c, slow)
    line = [a - b for a, b in zip(ef, es)]
    sg = ema_series(line, sig)
    hist = [a - b for a, b in zip(line, sg)]
    since = None
    for i in range(len(hist) - 1, 0, -1):
        if hist[i] > 0 >= hist[i - 1]:
            since = len(hist) - 1 - i
            break
        if hist[i] <= 0:
            break
    return line[-1], sg[-1], hist[-1], hist[-2], since


def bollinger(c, n=20, k=2.0):
    """(중심, 상단, 하단, %b, 밴드폭, 밴드폭 최근 120일 내 백분위 0~1)"""
    if len(c) < n + 120:
        return None

    def at(end):
        w = c[end - n:end]
        m = sum(w) / n
        sd = (sum((x - m) ** 2 for x in w) / n) ** 0.5
        return m, m + k * sd, m - k * sd, (2 * k * sd / m if m else 0)

    m, up, lo, bw = at(len(c))
    hist = [at(e)[3] for e in range(len(c) - 120, len(c) + 1)]
    pct = sum(1 for b in hist if b <= bw) / len(hist)
    pb = (c[-1] - lo) / (up - lo) if up != lo else 0.5
    return m, up, lo, pb, bw, pct


def pivots(h, l, k=5):
    """좌우 k일보다 높은(낮은) 스윙 고점·저점. [(인덱스, 가격)]"""
    highs, lows = [], []
    for i in range(k, len(h) - k):
        if h[i] == max(h[i - k:i + k + 1]):
            highs.append((i, h[i]))
        if l[i] == min(l[i - k:i + k + 1]):
            lows.append((i, l[i]))
    return highs, lows


def ichimoku(h, l, c):
    """현재 시점의 (전환선, 기준선, 선행스팬A, 선행스팬B, 후행스팬 비교용 26일 전 종가). 구름은 26일 전에 계산한 값."""
    def mid(end, n):
        hh, ll = max(h[end - n:end]), min(l[end - n:end])
        return (hh + ll) / 2
    if len(c) < 52 + 26:
        return None
    ten, kij = mid(len(c), 9), mid(len(c), 26)
    e = len(c) - 26
    span_a = (mid(e, 9) + mid(e, 26)) / 2
    span_b = mid(e, 52)
    return ten, kij, span_a, span_b, c[-27]
