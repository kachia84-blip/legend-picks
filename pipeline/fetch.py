"""yfinance로 종목별 연간 재무제표를 받아 data/raw.json 에 저장한다.

사용: python fetch.py          (이미 받은 종목은 건너뛰고 새 종목·실패 종목만)
      python fetch.py --force  (전부 다시 받기)
"""
import json
import math
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

from pxstats import price_stats

warnings.filterwarnings("ignore")

BASE = Path(__file__).parent
RAW = BASE / "data" / "raw.json"

ROWS = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "gross_profit": ["Gross Profit"],
    "op_income": ["Operating Income", "Total Operating Income As Reported"],
    "net_income": ["Net Income Common Stockholders", "Net Income"],
    "equity": ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"],
    "debt": ["Total Debt"],
    "fcf": ["Free Cash Flow"],
    "ocf": ["Operating Cash Flow"],
    "capex": ["Capital Expenditure"],
    "current_assets": ["Current Assets"],
    "current_liabilities": ["Current Liabilities"],
    "cash": ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"],
    "rnd": ["Research And Development"],
    "dividends": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "interest": ["Interest Expense", "Interest Expense Non Operating"],
}
SOURCE = {"revenue": "inc", "gross_profit": "inc", "op_income": "inc", "net_income": "inc",
          "equity": "bs", "debt": "bs", "fcf": "cf", "ocf": "cf", "capex": "cf",
          "current_assets": "bs", "current_liabilities": "bs", "cash": "bs", "rnd": "inc", "dividends": "cf", "interest": "inc"}
SCHEMA = 6  # 수집 항목이 늘면 올려서 기존 데이터를 다시 받게 한다


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def pick(df, names, col):
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index and col in df.columns:
            v = num(df.at[n, col])
            if v is not None:
                return v
    return None


def fetch_one(ticker, name, market):
    k = yf.Ticker(ticker)
    info = {}
    try:
        info = k.info or {}
    except Exception:
        pass
    stmts = {"inc": k.income_stmt, "bs": k.balance_sheet, "cf": k.cashflow}
    cols = set()
    for df in stmts.values():
        if df is not None and not df.empty:
            cols |= set(df.columns)
    years = []
    for col in sorted(cols):
        row = {"year": col.year}
        for key, names in ROWS.items():
            row[key] = pick(stmts[SOURCE[key]], names, col)
        years.append(row)
    years = [y for y in years if y["net_income"] is not None or y["equity"] is not None]
    px, spark, candles = None, None, None
    try:
        # 일봉 5년: 주간 통계·차트 + 차트 현인들이 쓰는 최근 일봉(OHLCV)을 한 번에 얻는다
        hist = k.history(period="5y", interval="1d", auto_adjust=False).dropna(subset=["Open", "High", "Low", "Close"])
        closes = [float(x) for x in hist["Close"].tolist()]
        weekly = closes[::-1][::5][::-1]            # 거래일 5일 간격 = 약 1주
        px = price_stats(weekly)
        if px:
            pts = closes[::-1][::10][::-1]
            spark = [round(x) if closes[-1] >= 1000 else round(x, 2) for x in pts]
        r = lambda x: round(float(x), 4 if x < 100 else 2)
        vol = hist["Volume"].fillna(0).tolist()
        candles = [[d.strftime("%Y-%m-%d"), r(o), r(h), r(l), r(c), round(float(c) * float(v))]
                   for d, o, h, l, c, v in zip(hist.index, hist["Open"], hist["High"], hist["Low"], hist["Close"], vol)][-520:]
    except Exception:
        pass
    return {
        "px": px, "spark": spark, "candles": candles,
        "ticker": ticker,
        "name": name,
        "market": market,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "fin_currency": info.get("financialCurrency"),
        "price": num(info.get("currentPrice") or info.get("regularMarketPrice")),
        "market_cap": num(info.get("marketCap")),
        "shares": num(info.get("sharesOutstanding")),
        "week52_high": num(info.get("fiftyTwoWeekHigh")),
        "week52_low": num(info.get("fiftyTwoWeekLow")),
        "years": years,
        "schema": SCHEMA,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main():
    force = "--force" in sys.argv
    uni = json.loads((BASE / "universe.json").read_text(encoding="utf-8"))
    RAW.parent.mkdir(exist_ok=True)
    raw = {}
    if RAW.exists() and not force:
        raw = json.loads(RAW.read_text(encoding="utf-8"))

    todo = []
    for market in ("us", "kr"):
        for ticker, name in uni[market]:
            old = raw.get(ticker)
            if old and old.get("years") and old.get("market_cap") and old.get("schema") == SCHEMA:
                old["name"] = name
                continue
            todo.append((ticker, name, market))
    print(f"받을 종목 {len(todo)}개 (기존 {len(raw)}개)")

    failed = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fetch_one, *args): args for args in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            ticker, name, market = futs[fut]
            try:
                raw[ticker] = fut.result()
                n = len(raw[ticker]["years"])
                print(f"[{i}/{len(todo)}] {ticker} {name}: {n}년치")
            except Exception as e:
                failed.append(ticker)
                print(f"[{i}/{len(todo)}] {ticker} {name}: 실패 ({type(e).__name__}: {e})")

    # 안전장치: 재무·시총이 제대로 온 종목이 80% 미만이면(데이터 제공처 차단·장애 등) 저장·배포하지 않고 중단한다
    total = sum(len(uni[m]) for m in ("us", "kr"))
    good = sum(1 for r in raw.values() if len(r.get("years", [])) >= 3 and r.get("market_cap"))
    print(f"완료 {time.time() - t0:.0f}초, 정상 {good}/{total}개, 실패 {len(failed)}개 {failed}")
    if good < 0.8 * total:
        print(f"데이터가 너무 부족합니다({good}/{total}). 저장하지 않고 중단합니다.")
        sys.exit(1)
    RAW.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장 {len(raw)}개")


if __name__ == "__main__":
    main()
