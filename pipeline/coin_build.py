"""코인: 지표 계산 → 매매이론 15개 평가 → 진영별·종합 순위 → build.py 가 합칠 데이터 묶음을 만든다."""
import json
from datetime import datetime
from pathlib import Path
from statistics import mean

import coin_metrics as cm
from coin_theories import GROUPS, THEORIES, TONE_COIN, coin_levels

GROUP_ORDER = ["ctrend", "cbreak", "crev"]
TONE_CODES = ["strong", "buy", "wait", "hold", "pass"]
BUY = ("strong", "buy")
GROUP_OF = {t["id"]: t["group"] for t in THEORIES}
SHORT = {"turtle": "터틀", "weinstein": "와인스타인", "minervini": "미너비니", "dow": "다우", "ichimoku": "일목", "williams": "윌리엄스",
         "livermore": "리버모어", "darvas": "다바스", "oneil_c": "오닐", "bollinger": "볼린저", "connors": "코너스", "granville": "그랜빌",
         "wilder": "와일더", "appel": "아펠", "elder": "엘더"}
IDS = [t["id"] for t in THEORIES]


def consensus(m, results, members, all_mode):
    votes = [{"id": t["id"], "name": t["name"], "mono": t["mono"], "group": t["group"], "score": results[t["id"]]["score"],
              "quality": results[t["id"]]["quality"], "tone": results[t["id"]]["tone"], "verdict": results[t["id"]]["verdict"]}
             for t in members]
    total = len(votes)
    backers = [v for v in votes if v["tone"] in BUY]
    waits = sum(1 for v in votes if v["tone"] == "wait")
    count, avg = len(backers), mean(v["score"] for v in votes)
    grp = {}
    for g in GROUP_ORDER:
        gv = [v for v in votes if v["group"] == g]
        if gv:
            grp[g] = [sum(1 for v in gv if v["tone"] in BUY), len(gv)]
    support = mean(b / t for b, t in grp.values()) if all_mode else count / total

    # 코인은 돌파 신호가 드물어(진영 하나가 비는 날이 많음) 주식보다 기준을 조금 낮춘다
    min_count = 3 if all_mode else 2
    tone = ("strong" if support >= 0.45 else "buy" if count >= min_count and support >= 0.22 else
            "wait" if waits >= 2 and waits / total >= 0.40 else "hold" if count >= 1 or avg >= 50 else "pass")
    capped = None
    if m["severe"] and tone in BUY:
        tone, capped = "hold", f"급락 중(1년 고점 대비 {m['dd365'] * 100:.0f}%)이라 추세 전환 확인 전까지 관망"
    elif m["knife"]:
        if tone == "strong":
            tone, capped = "buy", "하락 추세(떨어지는 칼날)라 한 단계 낮춤"
        elif tone == "buy":
            tone, capped = "hold", "하락 추세(떨어지는 칼날)라 한 단계 낮춤"
    verdict = {"strong": f"{count}/{total}개 이론 신호 · 강력", "buy": f"{count}/{total}개 이론 신호", "wait": "진입 대기 우세",
               "hold": (f"{count}/{total}개 이론 신호 · 의견 갈림" if count else "관망"), "pass": "신호 없음"}[tone]

    src = backers or votes
    lv = [results[v["id"]]["levels"] for v in src if results[v["id"]]["levels"]]
    levels = None
    if lv:
        e, s, t = mean(l["buy"] for l in lv), mean(l["stop"] for l in lv), mean(l["sell"] for l in lv)
        levels = coin_levels(m, e, s, (t - e) / (e - s) if e > s else 2.0)

    short = lambda v: v["name"].split()[-1]
    hi, lo = max(votes, key=lambda v: v["score"]), min(votes, key=lambda v: v["score"])
    lead = (f"{total}개 이론 중 {count}개({'·'.join(short(v) for v in backers)})가 매수 신호를 냈습니다." if count
            else f"{total}개 이론 중 매수 신호를 낸 이론이 없습니다.")
    if all_mode:
        names = {"ctrend": "추세추종", "cbreak": "돌파·변동성", "crev": "눌림·역추세"}
        lead += " 진영별 " + " · ".join(f"{names[g]} {b}/{t}" for g, (b, t) in grp.items()) + "."
    lead += f" 가장 높게 본 이론은 {short(hi)}({hi['score']}점), 가장 낮게 본 이론은 {short(lo)}({lo['score']}점)입니다."
    tail = {"strong": "여러 관점의 차트 신호가 한목소리로 겹칩니다.", "buy": "일부 이론이 매수 신호를 냅니다. 이론별 차이를 확인하세요.",
            "wait": "신호가 만들어지는 중입니다. 진입 조건 충족 여부를 지켜보세요.", "hold": "이론들의 의견이 갈립니다.",
            "pass": "대부분의 이론에서 신호가 없습니다."}[tone]
    if capped:
        tail += f" ({capped})"
    return {
        "score": round(avg), "quality": round(mean(v["quality"] for v in votes)), "verdict": verdict, "tone": tone, "checks": [],
        "summary": f"{lead} {tail}", "levels": levels, "warnings": m["warnings"], "votes": votes, "backers": [v["mono"] for v in backers],
        "count": count, "total": total, "grp": grp,
        "rank": support * 100 + avg * 0.25 + {"up": 8, "rebound": 4, "flat": 0, "down": -6}.get(m["trend"], 0)
                - (8 if m["knife"] else 0) - (25 if m["severe"] else 0),
    }


def build_coin(base: Path):
    src = json.loads((base / "data" / "coin_raw.json").read_text(encoding="utf-8"))
    raw = src["coins"]
    fetched = datetime.fromisoformat(src["fetched_at"])
    M = {k: cm.compute(v) for k, v in raw.items()}
    btc = M.get("KRW-BTC")
    btc_up = bool(btc and btc["trend"] == "up" and btc["price"] > btc["s50"])
    for m in M.values():
        m["rs90"] = (m["ret90"] or 0) - ((btc["ret90"] or 0) if btc else 0)
        m["btc_up"] = btc_up

    keys = ["price", "change24", "value24", "atr_pct", "rsi14", "rsi2", "adx", "pdi", "mdi", "bw_pct", "pctb", "vol_ratio", "vol_ratio3",
            "rs90", "dd365", "ret7", "ret30", "ret90", "box_w", "break55_age", "macd_since", "trend", "knife", "severe", "pain", "align", "ret365"]
    stocks_base, charts, pxs = {}, {}, {}
    per_theory = {t["id"]: [] for t in THEORIES}
    groups_stocks = {g: [] for g in GROUP_ORDER}
    all_stocks = []
    for mk, m in M.items():
        b = {k: (round(m[k], 4) if isinstance(m.get(k), float) else m.get(k)) for k in keys}
        b.update({"name": m["name"], "market": "coin", "sector": "코인", "industry": "", "currency": "KRW",
                  "above200": bool(m["price"] >= m["s200"]), "gap200": round(m["price"] / m["s200"] - 1, 4),
                  "hi55": bool(m["price"] > m["hi55"]), "gh": None, "struct": "unknown", "warnings": m["warnings"],
                  "years": f"최근 {m['n_days']}일 일봉"})
        stocks_base[mk] = b
        charts[mk] = m["spark"]
        pxs[mk] = {k: (None if v is None else round(v, 3)) for k, v in m["px"].items()}
        results = {t["id"]: t["evaluate"](m) for t in THEORIES}
        card = {"ticker": mk}
        for t in THEORIES:
            per_theory[t["id"]].append({**card, **results[t["id"]]})
        for g in GROUP_ORDER:
            groups_stocks[g].append({**card, **consensus(m, results, [t for t in THEORIES if t["group"] == g], False)})
        all_stocks.append({**card, **consensus(m, results, THEORIES, True)})

    for lst in [all_stocks, *groups_stocks.values()]:
        lst.sort(key=lambda s: -s["rank"])

    details = {}

    def pack(pid, stocks, is_cons):
        items, det = [], {}
        for s in stocks:
            L = s["levels"]
            it = {"t": s["ticker"], "score": s["score"], "quality": s["quality"], "tone": s["tone"],
                  "levels": None if not L else {k: (round(v, 4) if isinstance(v, float) else v) for k, v in L.items()}}
            if is_cons:
                it.update({"verdict": s["verdict"], "count": s["count"], "total": s["total"], "grp": s["grp"], "rank": round(s["rank"], 2),
                           "votes": [[IDS.index(v["id"]), v["score"], v["quality"], TONE_CODES.index(v["tone"])] for v in s["votes"]]})
            else:
                it["verdict"] = s["verdict"]
            items.append(it)
            det[s["ticker"]] = {"s": s["summary"], "c": [[c["name"], "q", c["points"], c["max"], None if c["ok"] is None else int(c["ok"]), c["detail"]] for c in s["checks"]]}
        details[pid] = det
        return items

    n = len(THEORIES)
    all_info = {
        "id": "call", "short": "코인 종합", "name": "코인 종합", "mono": "종", "consensus": True, "group": "all", "domain": "coin",
        "tagline": f"차트 매매이론 {n}개가 고르게 신호를 낸 코인", "vote_ids": IDS,
        "intro": "추세추종·돌파·눌림 세 진영의 신호 비율을 똑같이 반영해 순위를 정합니다. 한 진영에서만 신호가 나는 코인은 순위가 내려갑니다.",
        "principles": [f"{n}개 매매이론이 각자의 기준으로 모든 코인을 따로 평가합니다", "추세추종·돌파·눌림 각 5개 이론의 '매수 신호' 비율을 같은 비중으로 합산합니다",
                       "하락 추세(떨어지는 칼날)·급락 중인 코인은 등급과 순위를 낮춥니다", "거래대금이 작은 코인은 점수를 깎습니다(유동성 위험)",
                       "코인은 재무제표가 없어 차트 매매이론만으로 판단합니다"],
        "price_rules": ["진입가·손절가·목표가는 이론마다 다르며, 모두 ATR(평균 변동폭) 기반입니다", "종합의 가격은 신호를 낸 이론들 가격의 평균입니다",
                        "손절가는 진입가 아래 1~3ATR, 목표가는 위험의 1.5~3배입니다"],
        "stocks": pack("call", all_stocks, True)}
    group_infos = []
    for g in GROUP_ORDER:
        gi = GROUPS[g]
        mem = [t for t in THEORIES if t["group"] == g]
        group_infos.append({"id": g, "short": gi["name"], "name": gi["name"] + " 종합", "mono": gi["mono"], "consensus": True, "group": g, "domain": "coin",
                            "tagline": gi["tagline"], "intro": gi["intro"], "members": [t["id"] for t in mem], "vote_ids": IDS,
                            "principles": [f"{t['name']}: {t['tagline']}" for t in mem],
                            "price_rules": ["진입가·손절가·목표가는 신호를 낸 이론들 가격의 평균", "개별 이론의 가격은 각 이론 탭에서 확인"],
                            "stocks": pack(g, groups_stocks[g], True)})
    singles = []
    for t in THEORIES:
        best = max(per_theory[t["id"]], key=lambda s: sum(c["max"] for c in s["checks"]))
        singles.append({"id": t["id"], "short": SHORT.get(t["id"], t["name"].split()[-1]), "name": t["name"], "mono": t["mono"], "group": t["group"], "domain": "coin",
                        "tagline": t["tagline"], "principles": t["principles"], "price_rules": t["price_rules"], "profile": t["profile"],
                        "photo": None, "photo_credit": None, "rubric": [[c["name"], c["max"]] for c in best["checks"]],
                        "stocks": pack(t["id"], per_theory[t["id"]], False)})
    groups_meta = {g: {"name": GROUPS[g]["name"], "mono": GROUPS[g]["mono"]} for g in GROUP_ORDER}
    return {"investors": [all_info, *group_infos, *singles], "base": stocks_base, "charts": charts, "px": pxs, "details": details,
            "groups": groups_meta, "fetched": fetched, "count": len(M), "btc_up": btc_up}
