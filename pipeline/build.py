"""data/raw.json → 지표 계산 → 투자자별 평가 → 진영·종합 순위 → index.html 생성."""
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median

from investors import GROUP_MEMBERS, GROUP_OF, GROUP_ORDER, INVESTORS
from investors.common import TONE_LABEL, levels_from_raw, scale, warnings
from investors.profiles import GROUPS, PROFILES
import coin_theories as ct
from chart_stock import compute as chart_compute
from coin_build import GROUP_ORDER as COIN_GROUPS, build_coin  # noqa: F401
from metrics import compute

BASE = Path(__file__).parent
BUY_TONES = ("strong", "buy")
SECTOR_KR = {
    "Technology": "기술", "Financial Services": "금융", "Healthcare": "헬스케어", "Consumer Cyclical": "경기소비재",
    "Consumer Defensive": "필수소비재", "Industrials": "산업재", "Energy": "에너지", "Basic Materials": "소재",
    "Utilities": "유틸리티", "Communication Services": "커뮤니케이션", "Real Estate": "부동산",
}


# ── 성장 체질: '싸 보이지만 성장이 멈춘 업종(가치 함정)'을 걸러내기 위한 보정 지표 ──
def industry_growth(metrics):
    """산업별(없으면 섹터별) 매출 성장률 중앙값. 표본 3개 미만이면 None."""
    by_ind, by_sec = {}, {}
    for m in metrics:
        if m["ok"] and m["rev_cagr"] is not None:
            by_ind.setdefault(m["industry"], []).append(m["rev_cagr"])
            by_sec.setdefault(m["sector"], []).append(m["rev_cagr"])
    ind = {k: median(v) for k, v in by_ind.items() if k and len(v) >= 3}
    sec = {k: median(v) for k, v in by_sec.items() if k and len(v) >= 3}
    return lambda m: ind.get(m["industry"], sec.get(m["sector"]))


def growth_health(m, ind_g):
    """0~100. 회사 매출 성장(50) + 최근 성장(20) + 같은 산업 평균 성장(30). 자료가 없으면 None."""
    comps = []
    if m["rev_cagr"] is not None:
        comps.append((50, scale(m["rev_cagr"], -0.02, 0.12)))
    if m["rev_yoy"] is not None:
        comps.append((20, scale(m["rev_yoy"], -0.05, 0.12)))
    if ind_g is not None:
        comps.append((30, scale(ind_g, 0.0, 0.10)))
    if not comps:
        return None
    return round(100 * sum(w * v for w, v in comps) / sum(w for w, _ in comps))


def structure(gh):
    if gh is None:
        return "unknown"
    return "growth" if gh >= 60 else "mature" if gh >= 35 else "slow"


def consensus_for(m, results, members, all_mode, gh, cm=None):
    """여러 투자자의 평가를 하나로 합친다. all_mode 면 성장주·저평가·복합 세 진영의 추천 비율을 균등 반영한다."""
    votes = [{"id": i.INFO["id"], "name": i.INFO["name"], "mono": i.INFO["mono"], "group": GROUP_OF[i.INFO["id"]],
              "score": results[i.INFO["id"]]["score"], "quality": results[i.INFO["id"]]["quality"],
              "tone": results[i.INFO["id"]]["tone"], "verdict": results[i.INFO["id"]]["verdict"]}
             for i in members if i.INFO["id"] in results]
    if not votes:
        return None
    total = len(votes)
    backers = [v for v in votes if v["tone"] in BUY_TONES]
    waits = sum(1 for v in votes if v["tone"] == "wait")
    count = len(backers)
    avg = mean(v["score"] for v in votes)

    grp = {}
    for g in GROUP_ORDER:
        gv = [v for v in votes if v["group"] == g]
        if gv:
            grp[g] = [sum(1 for v in gv if v["tone"] in BUY_TONES), len(gv)]
    support = mean(b / t for b, t in grp.values()) if all_mode else count / total

    if support >= 0.55:
        tone = "strong"
    elif count >= 2 and support >= 0.27:
        tone = "buy"
    elif waits >= 2 and waits / total >= 0.40:
        tone = "wait"
    elif count >= 1 or avg >= 50:
        tone = "hold"
    else:
        tone = "pass"

    # 보정 1) 성장 체질: 성장이 멈춘 기업은 한 단계 낮춘다
    capped = None
    if gh is not None and gh < 35 and tone == "strong":
        tone, capped = "buy", "성장 둔화 우려로 한 단계 낮춤"
    elif gh is not None and gh < 20 and tone == "buy":
        tone, capped = "hold", "성장 둔화 우려로 한 단계 낮춤"
    # 보정 2) 떨어지는 칼날: 싸 보여도 하락 추세 + 3년 고점 대비 -30% 이상이면 사람이 버티기 어렵다 → 한 단계 낮춘다
    if m["severe"] and tone in ("strong", "buy"):
        # 보정 3) 급락 중: 재무가 좋아 보여도 추세 전환 전까지는 관망으로 둔다
        tone, capped = "hold", f"급락 중(3년 고점 대비 {m['px']['dd_3y'] * 100:.0f}%)이라 추세 전환 확인 전까지 관망"
    elif m["knife"]:
        if tone == "strong":
            tone, capped = "buy", "하락 추세(떨어지는 칼날)라 한 단계 낮춤"
        elif tone == "buy":
            tone, capped = "hold", "하락 추세(떨어지는 칼날)라 한 단계 낮춤"

    verdict = {
        "strong": f"{count}/{total}명 추천 · 강력", "buy": f"{count}/{total}명 추천",
        "wait": "좋은 기업 · 가격 부담",
        "hold": (f"{count}/{total}명 추천 · 의견 갈림" if count else "보통 · 의견 갈림"), "pass": "추천 없음",
    }[tone]

    # 가격 전략: 재무 기반 현인들의 가격은 평균을 낸다(차트 현인의 ATR 가격은 성격이 달라 섞지 않는다).
    # 차트 진영만의 종합이면 차트 현인들의 가격을 평균해 ATR 기준으로 다시 판정한다.
    levels = None
    is_chart_only = all(GROUP_OF[v["id"]] == "chart" for v in votes)
    if is_chart_only:
        lv = [results[v["id"]]["levels"] for v in (backers or votes) if results[v["id"]]["levels"]]
        if lv and cm is not None:
            e, s_, t_ = mean(l["buy"] for l in lv), mean(l["stop"] for l in lv), mean(l["sell"] for l in lv)
            levels = ct.coin_levels(cm, e, s_, (t_ - e) / (e - s_) if e > s_ else 2.0)
    else:
        fund = [v for v in (backers or votes) if GROUP_OF[v["id"]] != "chart"] or [v for v in votes if GROUP_OF[v["id"]] != "chart"]
        lv = [results[v["id"]]["levels"] for v in fund if results[v["id"]]["levels"]]
        if lv:
            raws = [l["raw"] for l in lv]
            levels = levels_from_raw(
                m["price"], mean(r["fair"] for r in raws), mean(r["buy"] for r in raws), mean(r["sell"] for r in raws),
                mean(r["stop"] for r in raws), m["currency"], mean(l["req_mos"] for l in lv), mean(l["stop_pct"] for l in lv))

    short = lambda v: v["name"].split()[-1]
    hi, lo = max(votes, key=lambda v: v["score"]), min(votes, key=lambda v: v["score"])
    lead = (f"{total}명 중 {count}명({'·'.join(short(v) for v in backers)})이 매수 후보로 꼽았습니다."
            if count else f"{total}명 중 매수 후보로 꼽은 투자자가 없습니다.")
    if all_mode:
        names = {"growth": "성장주", "value": "저평가", "mixed": "복합", "chart": "차트"}
        lead += " 진영별 추천 " + " · ".join(f"{names[g]} {b}/{t}" for g, (b, t) in grp.items()) + "."
    lead += f" 가장 높게 본 사람은 {short(hi)}({hi['score']}점), 가장 낮게 본 사람은 {short(lo)}({lo['score']}점)입니다."
    tail = {"strong": "여러 관점이 한목소리로 좋게 보는 종목입니다.",
            "buy": "일부 투자자가 매수 후보로 봅니다. 투자자별 의견 차이를 확인하세요.",
            "wait": "기업은 좋게 보지만 가격이 부담스럽다는 의견이 많습니다.",
            "hold": "투자자들의 의견이 갈립니다.", "pass": "대부분의 투자자 기준에 맞지 않습니다."}[tone]
    if capped:
        tail += f" ({capped})"
    return {
        "score": round(avg), "quality": round(mean(v["quality"] for v in votes)), "verdict": verdict, "tone": tone,
        "checks": [], "summary": f"{lead} {tail}", "levels": levels, "warnings": warnings(m),
        "votes": votes, "backers": [v["mono"] for v in backers], "count": count, "total": total, "grp": grp,
        # 순위: 추천 지지율 + 평균 점수 + 성장 체질 + 주가 추세(상승 +8 … 하락 -6, 떨어지는 칼날 추가 -8)
        "rank": support * 100 + avg * 0.25 + (gh if gh is not None else 50) * 0.15
                + {"up": 8, "rebound": 4, "flat": 0, "down": -6}.get(m["trend"], 0)
                - (8 if m["knife"] else 0) - (25 if m["severe"] else 0),
    }


def main():
    raw = json.loads((BASE / "data" / "raw.json").read_text(encoding="utf-8"))
    uni = json.loads((BASE / "universe.json").read_text(encoding="utf-8"))
    order = {t: i for market in ("us", "kr") for i, (t, _) in enumerate(uni[market])}
    photos = {}
    if (BASE / "photos.json").exists():
        photos = json.loads((BASE / "photos.json").read_text(encoding="utf-8-sig"))

    metrics = [compute(rec) for rec in raw.values() if rec["ticker"] in order]
    metrics.sort(key=lambda m: order[m["ticker"]])
    excluded = [{"ticker": m["ticker"], "name": m["name"], "market": m["market"], "issue": m["issue"]}
                for m in metrics if not m["ok"]]
    ind_of = industry_growth(metrics)

    # 차트 현인용 지표: 일봉으로 계산하고, 상대강도 기준은 같은 시장(미국/한국) 종목들의 90일 수익률 중앙값
    chart_m = {}
    for m in metrics:
        if m["ok"]:
            c = chart_compute(raw[m["ticker"]], 0.0)
            if c:
                chart_m[m["ticker"]] = c
    for mk in ("us", "kr"):
        rets = [c["ret90"] for t, c in chart_m.items() if raw[t]["market"] == mk and c["ret90"] is not None]
        med = median(rets) if rets else 0.0
        for t, c in chart_m.items():
            if raw[t]["market"] == mk:
                c["rs90"] = (c["ret90"] or 0) - med

    def base(m, gh):
        cv = chart_m.get(m["ticker"]) or {}
        return {"ticker": m["ticker"], "name": m["name"], "market": m["market"],
                "rsi2": cv.get("rsi2"), "rsi14": cv.get("rsi14"), "adx": cv.get("adx"), "bw_pct": cv.get("bw_pct"),
                "above200": bool(cv) and cv["price"] >= cv["s200"],
                "vol_ratio3": cv.get("vol_ratio3"), "hi55": bool(cv) and cv["price"] > cv["hi55"], "macd_since": cv.get("macd_since"),
                "sector": SECTOR_KR.get(m["sector"], m["sector"]), "industry": m["industry"],
                "price": m["price"], "currency": m["currency"], "market_cap": m["market_cap"], "per": m["per"],
                "mos": m["mos"], "roe": m["roe_avg"], "op_margin": m["op_margin_avg"], "debt_to_ni": m["debt_to_ni"],
                "rev_cagr": m["rev_cagr"], "rev_yoy": m["rev_yoy"], "gh": gh, "struct": structure(gh),
                "ni_yoy": m["ni_yoy"], "trend": m["trend"], "knife": m["knife"], "severe": m["severe"], "pain": m["pain"], "align": m["align"],
                # 한눈에 보는 태그 판정용 지표
                "peg": m["peg"], "pb": m["pb"], "ps": m["ps"], "fcf_yield": m["fcf_yield"], "div_yield": m["div_yield"],
                "net_cash": m["net_cash_ratio"], "fin": m["is_financial"], "loss": m["net_income"][-1] <= 0,
                "fcf_neg": bool(m["fcf"] and m["fcf"][-1] is not None and m["fcf"][-1] < 0),
                "debt0": m["debt"] is not None and m["debt"] <= 0,
                "years": f"{m['first_year']}~{m['last_year']}"}

    per_investor = {inv.INFO["id"]: [] for inv in INVESTORS}
    groups_stocks = {g: [] for g in GROUP_ORDER}
    all_stocks = []
    base_map = {}  # 종목 기본 정보는 한 번만 저장하고, 투자자별 목록에는 점수 등 달라지는 값만 넣는다
    for m in metrics:
        if not m["ok"]:
            continue
        gh = growth_health(m, ind_of(m))
        b = base(m, gh)
        base_map[m["ticker"]] = {**{k: (round(v, 4) if isinstance(v, float) else v) for k, v in b.items() if k != "ticker"},
                                 "warnings": warnings(m)}
        results = {}
        cm = chart_m.get(m["ticker"])
        for inv in INVESTORS:
            # 차트 현인은 재무 지표가 아니라 차트 지표를 받는다 (일봉이 부족한 종목은 평가하지 않는다)
            arg = cm if getattr(inv, "KIND", "") == "chart" else m
            ev = inv.evaluate(arg) if arg is not None else None
            if ev is not None:
                results[inv.INFO["id"]] = ev
                per_investor[inv.INFO["id"]].append({**b, **ev})
        for g in GROUP_ORDER:
            c = consensus_for(m, results, GROUP_MEMBERS[g], False, gh, cm)
            if c:
                groups_stocks[g].append({**b, **c})
        all_stocks.append({**b, **consensus_for(m, results, INVESTORS, True, gh, cm)})

    for stocks in [all_stocks, *groups_stocks.values(), *per_investor.values()]:
        for s in stocks:
            if s["levels"]:
                s["levels"].pop("raw", None)
    for stocks in [all_stocks, *groups_stocks.values()]:
        stocks.sort(key=lambda s: -s["rank"])

    n_inv = len(INVESTORS)
    INV_IDS = [inv.INFO["id"] for inv in INVESTORS]
    TONE_CODES = ["strong", "buy", "wait", "hold", "pass"]
    details = {}  # 투자자별 상세(체크리스트·요약): 종목을 눌렀을 때만 따로 불러온다

    def slim_levels(L):
        return None if not L else {k: (round(v, 4) if isinstance(v, float) else v) for k, v in L.items()}

    def pack(pid, stocks, consensus):
        items, det = [], {}
        for s in stocks:
            it = {"t": s["ticker"], "score": s["score"], "quality": s["quality"], "tone": s["tone"],
                  "levels": slim_levels(s["levels"])}
            if consensus:
                it.update({"verdict": s["verdict"], "count": s["count"], "total": s["total"], "grp": s["grp"],
                           "rank": round(s["rank"], 2),
                           "votes": [[INV_IDS.index(v["id"]), v["score"], v["quality"], TONE_CODES.index(v["tone"])]
                                     for v in s["votes"]]})
            items.append(it)
            det[s["ticker"]] = {"s": s["summary"], "c": [
                [c["name"], "q" if c["group"] == "quality" else "p", c["points"], c["max"],
                 None if c["ok"] is None else int(c["ok"]), c["detail"]] for c in s["checks"]]}
        details[pid] = det
        return items

    all_info = {
        "id": "all", "short": "종합", "name": "종합", "mono": "종", "consensus": True, "group": "all",
        "tagline": f"전설의 투자자 {n_inv}명(현인 15 + 차트 현인 5)이 고르게 추천한 종목",
        "intro": "성장주·저평가·복합·차트 네 진영의 추천 비율을 똑같이 반영해 순위를 정합니다. 한 진영에서만 인기 있는 종목은 순위가 내려갑니다.",
        "principles": [
            f"{n_inv}명의 투자자가 각자의 기준으로 모든 종목을 따로 평가합니다",
            "성장주·저평가·복합·차트 각 5명의 '매수 후보' 추천 비율을 똑같은 비중으로 합산합니다",
            "차트 현인(와인스타인·미너비니·리버모어·다바스·그랜빌)은 재무가 아니라 일봉 차트로만 판단합니다",
            "싸 보이지만 성장이 멈춘 기업(가치 함정)은 '성장 체질' 점수로 순위와 등급을 낮춥니다",
            "추천 수가 같으면 평균 점수, 성장 체질 순으로 앞섭니다",
            "일부 투자자(마법공식·집중투자·파괴적 혁신)는 금융업을 평가하지 않아, 그 종목은 나머지끼리 비교합니다",
        ],
        "price_rules": [
            "적정가 = 추정 내재가치 (잉여현금흐름 기반, 성장주는 성장 반영 가치)",
            "매수가·손절가 = 매수 후보로 꼽은 투자자들이 제시한 가격의 평균 (없으면 평가한 전원 평균)",
            "매도가 = 적정가. 투자자별 가격은 각 투자자 탭에서 확인",
        ],
        "stocks": pack("all", all_stocks, True),
    }
    group_infos = []
    for g in GROUP_ORDER:
        gi = GROUPS[g]
        members = [m.INFO for m in GROUP_MEMBERS[g]]
        group_infos.append({
            "id": g, "short": gi["name"], "name": gi["name"] + " 종합", "mono": gi["mono"], "consensus": True, "group": g,
            "tagline": gi["tagline"], "intro": gi["intro"], "members": [i["id"] for i in members],
            "principles": [f"{i['name']}: {i['tagline']}" for i in members],
            "price_rules": ["적정가 = 이 진영 투자자들이 쓰는 내재가치", "매수가·손절가 = 매수 후보로 꼽은 투자자들 가격의 평균",
                            "매도가 = 적정가. 투자자별 가격은 각 투자자 탭에서 확인"],
            "stocks": pack(g, groups_stocks[g], True),
        })
    singles = []
    for inv in INVESTORS:
        pid = inv.INFO["id"]
        ph = photos.get(pid)
        best = max(per_investor[pid], key=lambda s: sum(c["max"] for c in s["checks"]))
        singles.append({
            **inv.INFO, "short": inv.INFO["name"].split()[-1], "group": GROUP_OF[pid], "profile": PROFILES[pid],
            "photo": ph["file"] if ph else None, "photo_credit": ph if ph else None,
            "rubric": [[c["name"], c["max"]] for c in best["checks"]],
            "stocks": pack(pid, per_investor[pid], False),
        })
    investors = [all_info, *group_infos, *singles]
    for v in investors:
        v["domain"] = "stock"
    # 코인: 재무제표가 없으므로 차트 매매이론 15개로 따로 평가해 같은 화면 구조에 합친다
    coin = build_coin(BASE) if (BASE / "data" / "coin_raw.json").exists() else None
    if coin:
        investors += coin["investors"]
        base_map.update(coin["base"])
        details.update(coin["details"])

    charts = {t: raw[t]["spark"] for t in raw if t in order and raw[t].get("spark")}
    # 화면에는 이평선 값 자체가 필요 없으므로 제외한다(정배열 여부는 base 의 align 으로 전달)
    pxs = {m["ticker"]: {k: (None if v is None else round(v, 3)) for k, v in m["px"].items()
                         if k not in ("align", "ma4", "ma12", "ma24", "ma40")}
           for m in metrics if m["ok"] and m["px"]}
    # 데이터 기준 시각: 빌드한 때가 아니라 시세·재무를 실제로 내려받은 때(한국시간)
    kst = timezone(timedelta(hours=9))
    fetched = max(datetime.fromisoformat(r["fetched_at"]) for r in raw.values() if r.get("fetched_at"))
    fy = Counter(m["last_year"] for m in metrics if m["ok"]).most_common(1)[0][0]
    groups_meta = {g: {"name": GROUPS[g]["name"], "mono": GROUPS[g]["mono"]} for g in GROUP_ORDER}
    coin_meta = {}
    if coin:
        charts.update(coin["charts"])
        pxs.update(coin["px"])
        groups_meta.update(coin["groups"])
        coin_meta = {"coin_fetched": coin["fetched"].astimezone(kst).strftime("%Y-%m-%d %H:%M"),
                     "coin_fetched_ms": int(coin["fetched"].timestamp() * 1000), "coin_count": coin["count"], "btc_up": coin["btc_up"]}
    payload = {**coin_meta, "generated": datetime.now().strftime("%Y-%m-%d %H:%M"), "investors": investors, "excluded": excluded,
               "fetched": fetched.astimezone(kst).strftime("%Y-%m-%d %H:%M"), "fetched_ms": int(fetched.timestamp() * 1000), "fy": fy,
               "charts": charts, "px": pxs, "stocks": base_map, "invIds": INV_IDS,
               "groups": groups_meta}
    html = (BASE / "template.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*__APP__*/", (BASE / "app.js").read_text(encoding="utf-8"))
    # 클라우드(GitHub Actions)에서는 DEPLOY_DIR(저장소 루트)로 바로 내보낸다
    cloud = bool(os.environ.get("DEPLOY_DIR"))
    if not cloud:
        (BASE / "index.html").write_text(html, encoding="utf-8")
    deploy = Path(os.environ["DEPLOY_DIR"]) if cloud else BASE / "github_deploy"
    deploy.mkdir(exist_ok=True)
    (deploy / "index.html").write_text(html, encoding="utf-8")
    shutil.copytree(BASE / "pwa", deploy, dirs_exist_ok=True)
    (deploy / "data").mkdir(exist_ok=True)
    for pid, det in details.items():
        (deploy / "data" / f"{pid}.json").write_text(json.dumps(det, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if not cloud:
        # 갱신용 소스를 저장소의 pipeline/ 에 함께 둔다 → GitHub 서버가 PC 없이도 같은 방식으로 갱신할 수 있다
        pl = deploy / "pipeline"
        if pl.exists():
            shutil.rmtree(pl)
        pl.mkdir()
        for name in ("fetch.py", "metrics.py", "build.py", "template.html", "app.js", "universe.json", "photos.json", "requirements.txt",
                     "pxstats.py", "ta.py", "coin_fetch.py", "coin_metrics.py", "coin_theories.py", "coin_build.py", "chart_stock.py"):
            if (BASE / name).exists():
                shutil.copy2(BASE / name, pl / name)
        for d in ("investors", "pwa"):
            shutil.copytree(BASE / d, pl / d, ignore=shutil.ignore_patterns("__pycache__"))

    print("제외", len(excluded), "| 투자자", n_inv, "| 종합 평가", len(all_stocks), "종목")
    for inv in investors:
        by = {}
        for s in inv["stocks"]:
            by[s["tone"]] = by.get(s["tone"], 0) + 1
        print(f'  {inv["name"]:10s} {len(inv["stocks"]):4d}종목 ', {k: by.get(k, 0) for k in TONE_LABEL})


if __name__ == "__main__":
    main()
