"""업비트 공개 시세(키 불필요)에서 원화마켓 거래대금 상위 코인의 일봉을 받아 data/coin_raw.json 에 저장한다.

사용: python coin_fetch.py
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).parent
RAW = BASE / "data" / "coin_raw.json"
API = "https://api.upbit.com/v1"
HEAD = {"User-Agent": "legend-picks/1.0", "Accept": "application/json"}
TOP_N = 60            # 거래대금 상위 몇 개를 평가할지
DAYS = 600            # 일봉 몇 개(약 20개월)
MIN_DAYS = 260        # 200일선 등을 계산하려면 최소 이만큼의 이력이 필요
STABLE = {"KRW-USDT", "KRW-USDC", "KRW-USD1", "KRW-DAI"}   # 가격이 고정이라 매매이론 대상이 아님


def get(path, **params):
    for attempt in range(6):
        r = requests.get(f"{API}/{path}", params=params, headers=HEAD, timeout=20)
        if r.status_code == 429:           # 요청 제한: 잠깐 쉬고 다시
            time.sleep(0.6 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("업비트 요청 제한이 계속됩니다")


def candles(market):
    """일봉 DAYS 개 (오래된 것 → 최신). 마지막 1개는 아직 진행 중인 오늘 봉이다."""
    out, to = [], None
    while len(out) < DAYS:
        part = get("candles/days", market=market, count=200, **({"to": to} if to else {}))
        if not part:
            break
        out.extend(part)
        to = part[-1]["candle_date_time_utc"] + "Z"      # 가장 오래된 봉 이전부터 이어서
        time.sleep(0.13)
        if len(part) < 200:
            break
    out = out[:DAYS][::-1]
    return [[c["candle_date_time_kst"][:10], c["opening_price"], c["high_price"], c["low_price"], c["trade_price"],
             c["candle_acc_trade_price"]] for c in out]


def main():
    RAW.parent.mkdir(exist_ok=True)
    markets = [m for m in get("market/all", isDetails="false") if m["market"].startswith("KRW-") and m["market"] not in STABLE]
    names = {m["market"]: m["korean_name"] for m in markets}
    ids = list(names)
    ticks = []
    for i in range(0, len(ids), 80):
        ticks += get("ticker", markets=",".join(ids[i:i + 80]))
        time.sleep(0.13)
    ticks.sort(key=lambda t: -t["acc_trade_price_24h"])
    pick = ticks[:TOP_N + 10]    # 이력이 짧은 신규 상장은 빠지므로 여유를 둔다

    out, skipped = {}, []
    for t in pick:
        if len(out) >= TOP_N:
            break
        mk = t["market"]
        try:
            cs = candles(mk)
        except Exception as e:
            skipped.append(f"{mk}({type(e).__name__})")
            continue
        if len(cs) < MIN_DAYS:
            skipped.append(f"{mk}(이력 {len(cs)}일)")
            continue
        out[mk] = {"market": mk, "name": names[mk], "price": t["trade_price"], "change24": t["signed_change_rate"],
                   "value24": t["acc_trade_price_24h"], "candles": cs}
        print(f"{mk} {names[mk]}: {len(cs)}일")

    print(f"정상 {len(out)}/{TOP_N}, 제외 {skipped}")
    if len(out) < 0.8 * TOP_N:
        print("코인 데이터가 너무 부족합니다. 저장하지 않고 중단합니다.")
        sys.exit(1)
    RAW.write_text(json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "coins": out},
                              ensure_ascii=False), encoding="utf-8")
    print(f"저장 {len(out)}개")


if __name__ == "__main__":
    main()
