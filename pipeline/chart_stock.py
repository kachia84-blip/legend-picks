"""주식용 차트 지표: 코인과 같은 지표 계산기(coin_metrics)를 재사용해 일봉 OHLCV 로 계산한다."""
import coin_metrics as cm


def _round_fn(currency):
    if currency == "KRW":
        return lambda v: int(round(v / 10.0) * 10) if v >= 1000 else round(v, 1)
    return lambda v: round(v, 2)


def compute(rec, bench_ret90):
    """rec: fetch.py 가 저장한 종목 레코드. 일봉이 모자라거나 없으면 None.

    bench_ret90: 같은 시장(미국/한국) 종목들의 최근 90일 수익률 중앙값 → '시장 대비 상대강도'의 기준.
    """
    cs = rec.get("candles")
    if not cs or len(cs) < 270 or not rec.get("price"):
        return None
    try:
        m = cm.compute({"market": rec["ticker"], "name": rec["name"], "price": rec["price"], "candles": cs,
                        "change24": None, "value24": 1e11})   # 거래대금 감점은 코인 전용이라 중립값으로 둔다
    except Exception:
        return None
    m["bench"] = "시장"
    m["rs90"] = (m["ret90"] or 0) - (bench_ret90 or 0)
    m["btc_up"] = True
    m["round_fn"] = _round_fn(rec.get("currency"))
    return m
