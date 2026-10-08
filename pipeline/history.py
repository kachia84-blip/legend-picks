"""추천 기록: 순위 변동(어제 대비)과 '지난 추천 성적표'를 만든다.

저장 위치는 배포 저장소의 data/history.json (매시간 갱신할 때마다 이어서 쌓는다).
- hourly: 최근 60시간의 시장별 종합 순위(상위 50). 순위 변동 계산용
- days:   날짜별 마지막 기록 = 시장별 종합 상위 10 + 전 종목 가격. 성적표 계산용 (400일 보관)
PC 와 GitHub 서버가 번갈아 갱신하므로, PC 에서는 원격 기록을 받아 합친 뒤 쓴다.
"""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

KST = timezone(timedelta(hours=9))
MARKETS = ("us", "kr", "coin")
POS_N = 50
WINDOWS = [(1, "어제"), (7, "1주 전"), (30, "1개월 전")]


def _read(text):
    try:
        d = json.loads(text)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def load(deploy: Path, merge_remote=False):
    h = _read((deploy / "data" / "history.json").read_text(encoding="utf-8")) if (deploy / "data" / "history.json").exists() else {}
    if merge_remote:
        try:
            subprocess.run(["git", "fetch", "-q", "origin", "main"], cwd=deploy, capture_output=True, timeout=60)
            r = subprocess.run(["git", "show", "origin/main:data/history.json"], cwd=deploy, capture_output=True, timeout=30,
                               text=True, encoding="utf-8")
            if r.returncode == 0:
                h = merge(h, _read(r.stdout))
        except Exception:
            pass
    h.setdefault("hourly", [])
    h.setdefault("days", {})
    return h


def merge(a, b):
    out = {"hourly": [], "days": {}}
    seen = {}
    for x in (a.get("hourly") or []) + (b.get("hourly") or []):
        seen[x["ts"]] = x
    out["hourly"] = [seen[k] for k in sorted(seen)]
    for src in (a.get("days") or {}, b.get("days") or {}):
        for day, v in src.items():
            if day not in out["days"] or v.get("ts", "") > out["days"][day].get("ts", ""):
                out["days"][day] = v
    return out


def record(h, now, lists, prices):
    """lists: {market: [종합 순위 순 티커]}, prices: {티커: 현재가}. 오늘 기록을 덮어쓴다."""
    ts = now.astimezone(KST).strftime("%Y-%m-%dT%H:%M")
    day = ts[:10]
    pos = {m: lists.get(m, [])[:POS_N] for m in MARKETS}
    h["hourly"] = [x for x in h["hourly"] if x["ts"] != ts]
    h["hourly"].append({"ts": ts, "pos": pos})
    cutoff = (now.astimezone(KST) - timedelta(hours=60)).strftime("%Y-%m-%dT%H:%M")
    h["hourly"] = [x for x in h["hourly"] if x["ts"] >= cutoff]
    h["days"][day] = {"ts": ts, "pos": {m: lists.get(m, [])[:10] for m in MARKETS},
                      "px": {t: p for t, p in prices.items() if p}}
    for old in sorted(h["days"])[:-400]:
        del h["days"][old]
    return h


def _parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M").replace(tzinfo=KST)


def rank_change(h, now, lists):
    """어제(약 24시간 전) 순위와 비교한 변동. {티커: 정수(오름 +, 내림 -) 또는 'N'(신규 진입)}, 비교 기준 라벨, 상위 5위에서 빠진 종목."""
    now = now.astimezone(KST)
    snaps = [x for x in h["hourly"] if _parse(x["ts"]) < now - timedelta(hours=2)]
    if not snaps:
        return None
    ref = None
    old = [x for x in snaps if _parse(x["ts"]) <= now - timedelta(hours=20)]
    if old:
        ref, label = old[-1], "어제"
    else:
        first = snaps[0]
        age = (now - _parse(first["ts"])).total_seconds() / 3600
        if age < 6:
            return None
        ref, label = first, f"{int(age)}시간 전"
    chg, out = {}, {}
    for m in MARKETS:
        prev = ref["pos"].get(m) or []
        cur = (lists.get(m) or [])[:POS_N]
        pi = {t: i for i, t in enumerate(prev)}
        for i, t in enumerate(cur):
            if t in pi:
                chg[t] = pi[t] - i
            elif i < 20:
                chg[t] = "N"
        dropped = [t for t in prev[:5] if t not in cur[:5]]
        out[m] = dropped
    return {"label": label, "chg": chg, "out": out}


def performance(h, now, lists, prices, market_of):
    """시장별로, N일 전 종합 TOP 5 를 샀다면 지금까지 수익률. 시장 중간값(그날 전 종목의 중간 수익률)과 비교한다."""
    today = now.astimezone(KST).date()
    res = {}
    for m in MARKETS:
        wins = []
        for n, label in WINDOWS:
            want = (today - timedelta(days=n)).strftime("%Y-%m-%d")
            days = [d for d in h["days"] if d <= want]
            if not days:
                continue
            day = max(days)
            gap = (today - timedelta(days=n) - datetime.strptime(day, "%Y-%m-%d").date()).days
            if gap > {1: 1, 7: 2, 30: 4}[n]:   # 기록이 그 시점과 너무 멀면 건너뜀(라벨이 거짓이 되지 않게)
                continue
            snap = h["days"][day]
            top = (snap["pos"].get(m) or [])[:5]
            rets = []
            for t in top:
                p0, p1 = snap["px"].get(t), prices.get(t)
                if p0 and p1:
                    rets.append((t, p1 / p0 - 1))
            allr = [prices[t] / p0 - 1 for t, p0 in snap["px"].items() if market_of.get(t) == m and prices.get(t) and p0]
            if len(rets) < 3 or len(allr) < 10:
                continue
            avg = sum(r for _, r in rets) / len(rets)
            wins.append({"label": label, "day": day, "avg": round(avg, 4), "bench": round(median(allr), 4),
                         "up": sum(1 for _, r in rets if r > 0), "n": len(rets),
                         "picks": [[t, round(r, 4)] for t, r in rets]})
        res[m] = wins
    first = min(h["days"]) if h["days"] else None
    return {"since": first, "days": len(h["days"]), "perf": res}


def save(h, deploy: Path):
    (deploy / "data").mkdir(exist_ok=True)
    (deploy / "data" / "history.json").write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
