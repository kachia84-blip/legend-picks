"""코인 매매이론 15개 (재무제표가 없는 코인은 차트 이론만으로 평가한다).

각 이론: INFO(소개) + evaluate(m) → 점수·체크리스트·진입 신호 충족 여부·ATR 기반 진입/목표/손절가.
진영: 추세추종 / 돌파·변동성 / 눌림·역추세 (5개씩).
주의: 이론 본인의 판단이 아니라 공개된 규칙을 단순화해 수치로 옮긴 모의 평가다.
"""
import math

from investors.common import check, scale, summary, tally

TONE_COIN = {"strong": "강력 매수 신호", "buy": "매수 신호", "wait": "진입 대기", "hold": "관망", "pass": "신호 없음"}
f0 = lambda x, d=0.0: d if x is None else x
pc = lambda x: "-" if x is None else f"{x * 100:.1f}%"


def tick(v):
    """업비트 호가 단위에 맞춰 가격을 반올림한다."""
    for lim, unit in ((2_000_000, 1000), (1_000_000, 500), (500_000, 100), (100_000, 50), (10_000, 10), (1_000, 5),
                      (100, 1), (10, 0.1), (1, 0.01), (0.1, 0.001)):
        if v >= lim:
            r = round(v / unit) * unit
            return int(r) if unit >= 1 else round(r, 4)
    return round(v, 4)


def coin_levels(m, entry, stop, rmult):
    """ATR 기반 매매 전략. 상태: buy 진입 구간 / near 근접 / wait 대기 / late 이미 올라 추격 주의 / sell 목표 도달."""
    price, atr = m["price"], m["atr"]
    if not (entry and atr):
        return None
    if stop is None or stop >= entry:
        stop = entry - 1.5 * atr
    risk = min(max(entry - stop, 0.8 * atr), 5 * atr)
    stop = entry - risk
    target = entry + rmult * risk
    zone_lo, zone_hi = entry - 0.5 * atr, entry + 1.0 * atr
    if price >= target:
        status = "sell"
    elif price > zone_hi:
        status = "late"
    elif price >= zone_lo:
        status = "buy"
    elif price >= zone_lo - 1.0 * atr:
        status = "near"
    else:
        status = "wait"
    ref = price if status in ("buy", "late") else entry
    rp = m.get("round_fn") or tick     # 코인은 업비트 호가 단위, 주식은 통화에 맞는 반올림을 외부에서 지정한다
    return {"kind": "coin", "price": rp(price), "fair": rp(target), "buy": rp(entry), "sell": rp(target), "stop": rp(stop),
            "entry": rp(entry), "req_mos": 0.0, "stop_pct": risk / entry, "atr": rp(atr), "atr_pct": atr / price,
            "upside": target / ref - 1, "rr": (target - ref) / (ref - stop) if ref > stop else 0.0,
            "to_buy": entry / price - 1, "to_sell": target / price - 1, "status": status}


def finish(m, checks, tails, entry, stop, rmult, active, lead=""):
    score, _ = tally(checks)
    liq = scale(math.log10(max(m["value24"] or 1, 1)), 9.0, 11.0)       # 거래대금 10억~1000억 원: 유동성이 낮으면 감점
    score = round(score * (0.85 + 0.15 * liq))
    tone = ("strong" if active and score >= 80 else "buy" if active and score >= 62 else "wait" if score >= 50
            else "hold" if score >= 30 else "pass")
    return {"score": score, "quality": score, "verdict": TONE_COIN[tone], "tone": tone, "checks": checks,
            "summary": summary(checks, tone, tails, lead), "levels": coin_levels(m, entry, stop, rmult),
            "warnings": m["warnings"], "active": active}


def tails(a, b, c, d, e):
    return {"strong": a, "buy": b, "wait": c, "hold": d, "pass": e}


def Q(name, pts, ratio, detail, ok=None):
    return check(name, "quality", pts, ratio, detail, ok)


# ── 추세추종 ───────────────────────────────────────────────────────────────
def ev_turtle(m):
    p, hi20, hi55 = m["price"], m["hi20"], m["hi55"]
    c = [
        Q("55일 고점 돌파", 30, scale(p / hi55, 0.90, 1.0), f"현재가가 55일 고점 대비 {pc(p / hi55 - 1)} (돌파 기준 0% 이상)", p > hi55),
        Q("20일 고점 돌파", 20, scale(p / hi20, 0.92, 1.0), f"현재가가 20일 고점 대비 {pc(p / hi20 - 1)}", p > hi20),
        Q("장기 추세 필터(200일선)", 15, 1.0 if p >= m["s200"] else scale(p / m["s200"], 0.9, 1.0), f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
        Q("추세 강도(ADX)", 15, scale(f0(m["adx"]), 15, 30), f"ADX {f0(m['adx']):.0f} (기준 25 이상)", f0(m["adx"]) >= 25),
        Q("변동성(N) 적정", 10, 1 - scale(m["atr_pct"], 0.04, 0.10), f"하루 변동폭(ATR) {pc(m['atr_pct'])}", m["atr_pct"] <= 0.06),
        Q("거래 활발", 10, scale(f0(m["vol_ratio3"]), 0.8, 1.4), f"최근 3일 거래대금이 20일 평균의 {f0(m['vol_ratio3']):.1f}배"),
    ]
    active = p > hi20 and p >= m["s200"]
    entry = hi20
    stop = max(m["lo10"], entry - 2 * m["atr"])
    return finish(m, c, tails("20·55일 고점을 넘는 강한 돌파입니다. 터틀 규칙의 진입 조건을 모두 갖췄어요.", "터틀 진입 조건(20일 고점 돌파+장기 상승)을 충족합니다.",
                              "고점 돌파가 임박했어요. 돌파 가격을 지켜보세요.", "돌파 신호가 아직 약합니다.", "터틀 기준으로는 진입할 자리가 아닙니다."), entry, stop, 2.0, active)


def ev_weinstein(m):
    p, s210, s210p = m["price"], m["s210"], m["s210_prev"]
    slope = s210 / s210p - 1
    c = [
        Q("30주선 위(스테이지 2)", 25, 1.0 if p > s210 else scale(p / s210, 0.9, 1.0), f"30주선(210일) 대비 {pc(p / s210 - 1)}", p > s210),
        Q("30주선 우상향", 25, scale(slope, 0, 0.03), f"30주선의 최근 20일 변화 {pc(slope)}", slope > 0),
        Q("과열 아님", 15, 1 - scale(p / s210, 1.25, 1.6), f"30주선보다 {pc(p / s210 - 1)} 위 (30% 이내가 안전)", p <= s210 * 1.3),
        Q("중기선이 장기선 위", 15, 1.0 if m["s50"] > m["s200"] else scale(m["s50"] / m["s200"], 0.95, 1.0), f"50일선/200일선 {m['s50'] / m['s200']:.2f}", m["s50"] > m["s200"]),
        Q(f"{m.get('bench', 'BTC')} 대비 상대강도", 10, scale(m["rs90"], -0.1, 0.2), f"최근 90일 {m.get('bench', 'BTC')} 대비 {pc(m['rs90'])}", m["rs90"] > 0),
        Q("거래량 확인", 10, scale(f0(m["vol_ratio3"]), 0.8, 1.5), f"최근 3일 거래대금 {f0(m['vol_ratio3']):.1f}배"),
    ]
    active = p > s210 and slope > 0 and p <= s210 * 1.35
    entry = p if active else s210 * 1.03
    stop = s210 * 0.97
    return finish(m, c, tails("상승 단계(스테이지 2)가 뚜렷합니다. 와인스타인이 가장 좋아하는 모양이에요.", "상승 단계에 올라탄 상태입니다.", "30주선 부근에서 방향을 정하는 중이에요.",
                              "상승 단계로 보기엔 이릅니다.", "하락·천장 단계에 가깝습니다."), entry, stop, 2.5, active)


def ev_minervini(m):
    p = m["price"]
    conds = [
        ("가격 > 150·200일선", p > m["s150"] and p > m["s200"], p / max(m["s150"], m["s200"]) - 1),
        ("150일선 > 200일선", m["s150"] > m["s200"], m["s150"] / m["s200"] - 1),
        ("200일선 상승 중", m["s200"] > m["s200_prev"], m["s200"] / m["s200_prev"] - 1),
        ("50일선 > 150·200일선", m["s50"] > m["s150"] and m["s50"] > m["s200"], m["s50"] / max(m["s150"], m["s200"]) - 1),
        ("가격 > 50일선", p > m["s50"], p / m["s50"] - 1),
        ("저점 대비 +30% 이상", m["from_low365"] >= 0.30, m["from_low365"]),
        ("고점 대비 -25% 이내", m["dd365"] >= -0.25, m["dd365"]),
        (f"{m.get('bench', 'BTC')} 대비 상대강도 양호", m["rs90"] > 0, m["rs90"]),
    ]
    c = [Q(n, 12.5, 1.0 if ok else 0.0, f"{n}: {'충족' if ok else '미충족'} ({pc(v)})", ok) for n, ok, v in conds]
    cnt = sum(1 for _, ok, _ in conds if ok)
    active = cnt >= 7
    entry = max(p, m["hi20"]) if active else m["hi20"]
    stop = max(m["s50"] * 0.99, entry - 2.5 * m["atr"])
    return finish(m, c, tails(f"트렌드 템플릿 8개 조건 중 {cnt}개를 충족한 주도 코인입니다.", f"8개 조건 중 {cnt}개를 충족해 거의 완성된 상승 구조예요.",
                              f"{cnt}개 조건 충족. 몇 개만 더 갖추면 후보가 됩니다.", f"{cnt}개 조건 충족으로 아직 부족합니다.", f"{cnt}개 조건만 충족해 주도 코인이 아닙니다."), entry, stop, 3.0, active,
                  lead=f"조건 {cnt}/8 충족.")


def ev_dow(m):
    p, ph, pl = m["price"], m["ph"], m["pl"]
    hh = len(ph) >= 2 and ph[-1] > ph[-2]
    hl = len(pl) >= 2 and pl[-1] > pl[-2]
    c = [
        Q("고점이 높아짐(HH)", 25, 1.0 if hh else 0.0, "최근 스윙 고점이 이전 고점보다 높음" if hh else "최근 스윙 고점이 이전보다 낮거나 같음", hh) if len(ph) >= 2 else check("고점이 높아짐(HH)", "quality", 25, None, "스윙 고점 데이터 부족"),
        Q("저점이 높아짐(HL)", 25, 1.0 if hl else 0.0, "최근 스윙 저점이 이전 저점보다 높음" if hl else "최근 스윙 저점이 이전보다 낮거나 같음", hl) if len(pl) >= 2 else check("저점이 높아짐(HL)", "quality", 25, None, "스윙 저점 데이터 부족"),
        Q("직전 고점 부근", 15, scale(p / ph[-1], 0.93, 1.0) if ph else None, f"직전 스윙 고점 대비 {pc(p / ph[-1] - 1) if ph else '-'}", bool(ph) and p >= ph[-1] * 0.98),
        Q("직전 저점 위(추세 유효)", 10, (1.0 if p > pl[-1] else 0.0) if pl else None, "직전 스윙 저점을 지키는 중" if pl and p > pl[-1] else "직전 스윙 저점을 이탈", bool(pl) and p > pl[-1]),
        Q("200일선 위", 15, 1.0 if p >= m["s200"] else scale(p / m["s200"], 0.9, 1.0), f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
        Q("거래량 확인", 10, scale(f0(m["vol_ratio3"]), 0.8, 1.4), f"최근 3일 거래대금 {f0(m['vol_ratio3']):.1f}배"),
    ]
    active = bool(hh and hl and pl and p > pl[-1])
    entry = ph[-1] if ph and p < ph[-1] else p
    stop = pl[-1] if pl else None
    return finish(m, c, tails("고점과 저점이 모두 높아지는 교과서적 상승 추세입니다.", "다우 이론의 상승 추세 조건을 충족합니다.", "추세가 만들어지는 중이에요. 다음 고점·저점을 확인하세요.",
                              "추세가 뚜렷하지 않습니다.", "고점·저점이 낮아지는 하락 추세에 가깝습니다."), entry, stop, 2.0, active)


def ev_ichimoku(m):
    p, top, bot = m["price"], m["cloud_top"], m["cloud_bot"]
    pos = 1.0 if p > top else (0.4 if p >= bot else 0.0)
    c = [
        Q("가격이 구름대 위", 25, pos, "구름대 위" if p > top else "구름대 안" if p >= bot else "구름대 아래", p > top),
        Q("전환선 > 기준선", 20, scale(m["ten"] / m["kij"], 0.98, 1.02), f"전환선/기준선 {m['ten'] / m['kij']:.3f}", m["ten"] > m["kij"]),
        Q("가격 > 기준선", 15, 1.0 if p > m["kij"] else scale(p / m["kij"], 0.95, 1.0), f"기준선 대비 {pc(p / m['kij'] - 1)}", p > m["kij"]),
        Q("후행스팬 양호", 10, 1.0 if m["chikou_ok"] else 0.0, "26일 전 가격보다 높음" if m["chikou_ok"] else "26일 전 가격보다 낮음", m["chikou_ok"]),
        Q("양운(구름 상승 방향)", 15, 1.0 if m["span_a"] > m["span_b"] else 0.0, "선행스팬A > B" if m["span_a"] > m["span_b"] else "선행스팬A < B", m["span_a"] > m["span_b"]),
        Q("구름대에서 과도하게 멀지 않음", 15, 1 - scale(p / top, 1.15, 1.4), f"구름 상단보다 {pc(p / top - 1)} 위", p <= top * 1.25),
    ]
    active = p > top and m["ten"] > m["kij"]
    entry = p if active else top
    stop = max(top * 0.99, entry - 3 * m["atr"])
    return finish(m, c, tails("삼역호전(구름 위·전환선>기준선·후행스팬 양호)에 가까운 강한 상승 신호입니다.", "구름대 위에서 상승 방향이 유지됩니다.", "구름대 부근에서 방향을 정하는 중이에요.",
                              "일목 기준으로 뚜렷한 신호가 없습니다.", "구름대 아래라 하락 우위입니다."), entry, stop, 2.0, active)


# ── 돌파·변동성 ─────────────────────────────────────────────────────────────
def ev_williams(m):
    p, op, rng = m["price"], m["today_open"], m["prev_range"]
    trig = op + 0.5 * rng
    frac = (p - op) / (0.5 * rng) if rng else 0.0
    body = abs(m["prev_close"] - m["prev_open"]) / rng if rng else 0.0
    c = [
        Q("변동성 돌파(시가+전일폭×0.5)", 40, max(0.0, min(1.0, frac)), f"돌파 기준 {tick(trig):,}원까지 {pc(max(0, 1 - frac))} 남음" if frac < 1 else "오늘 돌파 기준을 넘었어요", frac >= 1),
        Q("전일 변동폭 충분", 15, scale(rng / p, 0.01, 0.04), f"전일 변동폭 {pc(rng / p)}", rng / p >= 0.02),
        Q("20일선 위", 15, 1.0 if p > m["s20"] else scale(p / m["s20"], 0.95, 1.0), f"20일선 대비 {pc(p / m['s20'] - 1)}", p > m["s20"]),
        Q("200일선 위", 10, 1.0 if p >= m["s200"] else 0.0, f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
        Q("거래량 활발", 10, scale(f0(m["vol_ratio"]), 0.8, 1.5), f"전일 거래대금 {f0(m['vol_ratio']):.1f}배"),
        Q("전일 방향성 뚜렷", 10, scale(body, 0.3, 0.7), f"전일 몸통/전체 {body:.0%}", body >= 0.5),
    ]
    active = frac >= 1 and p > m["s20"]
    entry = trig
    stop = entry - 1.0 * m["atr"]
    return finish(m, c, tails("오늘 변동성 돌파가 확인됐어요. 래리 윌리엄스식 단기 매수 신호입니다.", "변동성 돌파 조건을 충족했습니다.", "돌파 기준에 가까워졌어요. 가격이 기준을 넘는지 지켜보세요.",
                              "오늘은 돌파 신호가 약합니다.", "돌파 흐름이 없습니다."), entry, stop, 1.5, active)


def ev_livermore(m):
    p = m["price"]
    age = m["break120_age"]
    fresh = 0.0 if age is None else 1.0 if age <= 3 else 0.5
    c = [
        Q("120일 신고가 돌파", 30, 1.0 if p > m["hi120"] else scale(p / m["hi120"], 0.9, 1.0), f"120일 고점 대비 {pc(p / m['hi120'] - 1)}", p > m["hi120"]),
        Q("돌파가 신선함(최근 돌파)", 15, fresh, "돌파한 지 얼마 안 됨" if fresh == 1.0 else ("돌파 후 시간이 조금 지남" if fresh else "최근 돌파 없음"), fresh == 1.0),
        Q("거래량 급증", 25, scale(max(f0(m["vol_ratio"]), f0(m["vol_ratio3"])), 1.0, 2.0), f"거래대금이 평균의 {max(f0(m['vol_ratio']), f0(m['vol_ratio3'])):.1f}배", max(f0(m["vol_ratio"]), f0(m["vol_ratio3"])) >= 1.5),
        Q("돌파 전 횡보(에너지 응축)", 15, 1 - scale(m["box_w"], 0.15, 0.40), f"20일 박스 폭 {pc(m['box_w'])}", m["box_w"] <= 0.25),
        Q("추세 방향 일치", 15, (1.0 if p > m["s50"] else 0.4) * (1.0 if p > m["s200"] else 0.5), "50·200일선 위" if p > m["s50"] and p > m["s200"] else "일부 이평선 아래", p > m["s50"] and p > m["s200"]),
    ]
    active = p > m["hi55"] and max(f0(m["vol_ratio"]), f0(m["vol_ratio3"])) >= 1.2
    entry = m["hi55"]
    stop = max(entry * 0.90, entry - 2.5 * m["atr"])
    return finish(m, c, tails("거래량을 동반한 신고가 돌파입니다. 리버모어가 말한 '최소 저항선' 돌파예요.", "고점 돌파와 거래량 확인이 됐습니다.", "피벗(고점)에 근접했어요. 거래량 동반 돌파를 기다리세요.",
                              "피벗 돌파 신호가 없습니다.", "고점에서 멀어 피벗 매매 대상이 아닙니다."), entry, stop, 3.0, active)


def ev_darvas(m):
    p = m["price"]
    c = [
        Q("박스 상단 돌파", 30, 1.0 if p > m["hi20"] else scale(p / m["hi20"], 0.93, 1.0), f"20일 박스 상단 대비 {pc(p / m['hi20'] - 1)}", p > m["hi20"]),
        Q("박스가 좁고 단단함", 20, 1 - scale(m["box_w"], 0.12, 0.35), f"박스 폭 {pc(m['box_w'])}", m["box_w"] <= 0.20),
        Q("박스 상단에 근접", 15, scale(m["box_pos"], 0.6, 1.0), f"박스 내 위치 {m['box_pos']:.0%}", m["box_pos"] >= 0.8),
        Q("거래량 확대", 20, scale(f0(m["vol_ratio3"]), 0.8, 1.6), f"최근 3일 거래대금 {f0(m['vol_ratio3']):.1f}배", f0(m["vol_ratio3"]) >= 1.2),
        Q("상승 추세 속의 박스", 15, (1.0 if p > m["s60"] else 0.3) * (1.0 if m["s60"] > m["s60_prev"] else 0.5), "60일선 위·상승" if p > m["s60"] and m["s60"] > m["s60_prev"] else "60일선 약세", p > m["s60"] and m["s60"] > m["s60_prev"]),
    ]
    active = p > m["hi20"] and m["box_w"] <= 0.35
    entry = m["hi20"]
    stop = max(m["lo20"], entry - 3 * m["atr"])
    return finish(m, c, tails("좁은 박스를 거래량과 함께 뚫었습니다. 다바스 박스 이론의 매수 신호예요.", "박스 상단 돌파 조건을 충족합니다.", "박스 상단에 붙어 있어요. 돌파 여부를 지켜보세요.",
                              "박스 돌파 신호가 약합니다.", "박스 이론 대상이 아닙니다."), entry, stop, 2.0, active)


def ev_oneil(m):
    p = m["price"]
    c = [
        Q("1년 신고가 근접·돌파", 30, scale(p / m["high365"], 0.85, 1.0), f"1년 고점 대비 {pc(p / m['high365'] - 1)}", p >= m["high365"] * 0.97),
        Q("거래량 급증", 25, scale(f0(m["vol_ratio3"]), 1.0, 2.0), f"최근 3일 거래대금 {f0(m['vol_ratio3']):.1f}배 (기준 1.4배 이상)", f0(m["vol_ratio3"]) >= 1.4),
        Q("상대강도(RS) 우수", 20, scale(m["rs90"], 0.0, 0.25), f"최근 90일 {m.get('bench', 'BTC')} 대비 {pc(m['rs90'])}", m["rs90"] > 0.05),
        Q("조정 후 형성한 베이스", 15, 1 - scale(m["box_w"], 0.15, 0.35), f"20일 박스 폭 {pc(m['box_w'])}", m["box_w"] <= 0.25),
        Q("시장(BTC) 방향", 10, 1.0 if m["btc_up"] else 0.3, "BTC 상승 추세" if m["btc_up"] else "BTC가 약세 또는 횡보", m["btc_up"]),
    ]
    active = p >= m["high365"] * 0.97 and f0(m["vol_ratio3"]) >= 1.3
    entry = m["high365"]
    stop = entry * 0.92
    return finish(m, c, tails("신고가권에서 거래량이 터졌어요. 오닐이 찾는 주도주 돌파 모양입니다.", "신고가 부근 돌파 조건을 충족합니다.", "신고가에 가까워졌어요. 거래량 동반 돌파를 기다리세요.",
                              "주도주 돌파 모양이 아닙니다.", "신고가에서 멀어 오닐 기준에 맞지 않습니다."), entry, stop, 3.0, active)


def ev_bollinger(m):
    p = m["price"]
    c = [
        Q("스퀴즈(밴드폭 수축)", 30, 1 - scale(m["bw_pct"], 0.2, 0.6), f"밴드폭이 최근 120일 중 하위 {m['bw_pct']:.0%} 수준", m["bw_pct"] <= 0.3),
        Q("상단 밴드 돌파·접근", 30, scale(m["pctb"], 0.8, 1.0), f"%b {m['pctb']:.2f} (1 이상이면 상단 돌파)", m["pctb"] >= 0.95),
        Q("중심선 위 + 우상향", 15, (1.0 if p > m["bb_mid"] else 0.0) * (1.0 if m["s20"] > m["s20_prev"] else 0.5), "중심선 위·상승" if p > m["bb_mid"] and m["s20"] > m["s20_prev"] else "중심선 아래이거나 하락", p > m["bb_mid"] and m["s20"] > m["s20_prev"]),
        Q("거래량 확대", 15, scale(f0(m["vol_ratio3"]), 1.0, 1.8), f"최근 3일 거래대금 {f0(m['vol_ratio3']):.1f}배", f0(m["vol_ratio3"]) >= 1.3),
        Q("200일선 위", 10, 1.0 if p >= m["s200"] else 0.0, f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
    ]
    active = m["pctb"] >= 0.95 and m["bw_pct"] <= 0.5
    entry = m["bb_up"]
    stop = m["bb_mid"]
    return finish(m, c, tails("좁게 수축했던 밴드가 위로 터졌어요. 볼린저 스퀴즈 돌파 신호입니다.", "스퀴즈 이후 상단 돌파 조건을 충족합니다.", "밴드가 좁아졌어요. 곧 방향이 정해질 수 있습니다.",
                              "스퀴즈 돌파 신호가 아닙니다.", "밴드 하단 쪽이라 돌파 매매 대상이 아닙니다."), entry, stop, 2.0, active)


# ── 눌림·역추세 ─────────────────────────────────────────────────────────────
def ev_connors(m):
    p, r2 = m["price"], f0(m["rsi2"], 50)
    c = [
        Q("RSI(2) 과매도", 40, 1 - scale(r2, 5, 30), f"RSI(2) {r2:.0f} (10 미만이면 강한 과매도)", r2 < 10),
        Q("장기 상승 추세 속(200일선 위)", 30, 1.0 if p >= m["s200"] else 0.0, f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
        Q("단기 눌림(20일선 아래)", 10, 1.0 if p < m["s20"] else 0.3, "20일선 아래로 눌림" if p < m["s20"] else "20일선 위", p < m["s20"]),
        Q("중기선이 장기선 위", 10, 1.0 if m["s50"] > m["s200"] else 0.3, f"50일선/200일선 {m['s50'] / m['s200']:.2f}", m["s50"] > m["s200"]),
        Q("변동성 정상", 10, 1 - scale(m["atr_pct"], 0.05, 0.10), f"ATR {pc(m['atr_pct'])}", m["atr_pct"] <= 0.07),
    ]
    active = r2 < 10 and p >= m["s200"]
    entry = p
    stop = p - 2.5 * m["atr"]
    return finish(m, c, tails("상승 추세 속에서 단기 투매가 나왔어요. 코너스 RSI(2) 눌림목 매수 자리입니다.", "상승 추세 속 단기 과매도 조건을 충족합니다.", "단기 과매도에 가까워졌어요.",
                              "눌림목 신호가 약합니다.", "상승 추세가 아니라 눌림목 매매 대상이 아닙니다."), entry, stop, 1.5, active)


def ev_granville(m):
    p, s60, s60p = m["price"], m["s60"], m["s60_prev"]
    slope = s60 / s60p - 1
    dist = p / s60 - 1
    touch = m["low5"] <= s60 * 1.02 and p > s60
    c = [
        Q("60일선 우상향", 25, scale(slope, 0.0, 0.03), f"60일선 최근 10일 변화 {pc(slope)}", slope > 0),
        Q("60일선 부근 눌림", 30, 1 - scale(abs(dist - 0.015), 0.02, 0.10), f"60일선 대비 {pc(dist)} (−3%~+6%가 눌림 구간)", -0.03 <= dist <= 0.06),
        Q("지지 확인(이평선 터치 후 지킴)", 15, 1.0 if touch else 0.0, "최근 5일 안에 60일선을 건드린 뒤 위에서 마감" if touch else "최근 지지 확인 없음", touch),
        Q("과열 아님", 15, 1 - scale(p / s60, 1.15, 1.35), f"60일선보다 {pc(dist)} 위", p <= s60 * 1.15),
        Q("200일선 위", 15, 1.0 if p >= m["s200"] else 0.0, f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
    ]
    active = slope > 0 and touch and p >= m["s200"]
    entry = p
    stop = s60 * 0.97
    return finish(m, c, tails("상승하는 60일선에서 지지를 확인했어요. 그랜빌 법칙의 눌림목 매수입니다.", "이평선 지지 반등 조건을 충족합니다.", "이평선에 다가왔어요. 지지 여부를 지켜보세요.",
                              "이평선 눌림 신호가 아닙니다.", "이평선이 꺾였거나 이탈해 매수 신호가 아닙니다."), entry, stop, 2.0, active)


def ev_wilder(m):
    p, adx, r = m["price"], f0(m["adx"]), f0(m["rsi14"], 50)
    pdi, mdi = f0(m["pdi"]), f0(m["mdi"], 1)
    c = [
        Q("추세 강도(ADX)", 25, scale(adx, 18, 30), f"ADX {adx:.0f} (25 이상이면 추세 있음)", adx >= 25),
        Q("상승 방향(+DI > −DI)", 15, scale(pdi / max(mdi, 0.1), 0.9, 1.2), f"+DI {pdi:.0f} / −DI {mdi:.0f}", pdi > mdi),
        Q("RSI(14) 눌림 구간", 30, 1 - scale(abs(r - 42), 5, 20), f"RSI(14) {r:.0f} (35~50이 눌림 구간)", 32 <= r <= 50),
        Q("200일선 위", 15, 1.0 if p >= m["s200"] else 0.0, f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
        Q("변동성 안정", 15, scale(0.09 - m["atr_pct"], 0, 0.05), f"ATR {pc(m['atr_pct'])}", m["atr_pct"] <= 0.06),
    ]
    active = adx >= 25 and pdi > mdi and 32 <= r <= 50
    entry = p
    stop = p - 2 * m["atr"]
    return finish(m, c, tails("강한 상승 추세 속 RSI가 눌렸어요. 와일더식 추세 속 눌림목 자리입니다.", "추세가 살아 있고 RSI가 눌린 조건을 충족합니다.", "추세는 있으나 눌림이 덜 왔어요.",
                              "RSI·ADX 조건이 맞지 않습니다.", "추세가 약하거나 하락 방향이라 맞지 않습니다."), entry, stop, 2.0, active)


def ev_appel(m):
    p, since, hist, hp = m["price"], m["macd_since"], f0(m["hist"]), f0(m["hist_prev"])
    cross = 0.0 if since is None else (1.0 if since <= 3 else 0.6 if since <= 7 else 0.2)
    c = [
        Q("MACD 골든크로스(최근)", 35, cross, f"골든크로스 {since}일 전" if since is not None else "최근 골든크로스 없음", since is not None and since <= 5),
        Q("히스토그램 증가", 20, 1.0 if hist > hp else 0.3, "막대가 커지는 중" if hist > hp else "막대가 줄어드는 중", hist > hp),
        Q("0선 아래에서의 반전", 15, (1.0 if f0(m["macd"]) < 0 else 0.7) if since is not None and since <= 7 else 0.3, "0선 아래에서 올라섬(강한 반전)" if f0(m["macd"]) < 0 else "0선 위", f0(m["macd"]) < 0 and since is not None and since <= 7),
        Q("200일선 위", 15, 1.0 if p >= m["s200"] else 0.0, f"200일선 대비 {pc(p / m['s200'] - 1)}", p >= m["s200"]),
        Q("거래량 확인", 15, scale(f0(m["vol_ratio3"]), 0.8, 1.4), f"최근 3일 거래대금 {f0(m['vol_ratio3']):.1f}배"),
    ]
    active = since is not None and since <= 5 and hist > 0
    entry = p
    stop = p - 2 * m["atr"]
    return finish(m, c, tails("MACD가 막 상향 반전했어요. 아펠식 매수 신호입니다.", "MACD 골든크로스 조건을 충족합니다.", "MACD가 반전에 가까워졌어요.",
                              "MACD 반전 신호가 없습니다.", "MACD가 하락 방향입니다."), entry, stop, 2.0, active)


def ev_elder(m):
    p, r, wk = m["price"], f0(m["rsi14"], 50), m["wk_ema_up"]
    c = [
        Q("주봉(큰 물결) 상승", 35, (1.0 if wk else 0.0) if wk is not None else None, "주봉 13주 EMA가 오르고 가격이 그 위" if wk else "주봉 추세가 상승이 아님", bool(wk)),
        Q("일봉(작은 물결) 눌림", 30, 1 - scale(r, 35, 55), f"RSI(14) {r:.0f} (45 이하가 눌림)", r <= 45),
        Q("전일 고점 돌파 시도", 20, scale(p / m["prev_high"], 0.97, 1.0), f"전일 고점 대비 {pc(p / m['prev_high'] - 1)}", p > m["prev_high"]),
        Q("변동성(위험) 관리", 15, 1 - scale(m["atr_pct"], 0.05, 0.10), f"ATR {pc(m['atr_pct'])}", m["atr_pct"] <= 0.06),
    ]
    active = bool(wk) and r <= 45 and p > m["prev_high"]
    entry = m["prev_high"]
    stop = min(m["prev_low"], entry - 1.0 * m["atr"])
    return finish(m, c, tails("큰 물결은 오르는데 작은 물결이 눌렸다가 반등하기 시작했어요. 엘더 삼중창의 매수 신호입니다.", "삼중창 매수 조건을 충족합니다.", "주봉은 상승이고 눌림이 진행 중이에요. 전일 고점 돌파를 기다리세요.",
                              "삼중창 조건이 맞지 않습니다.", "주봉 추세가 하락이라 매수 신호가 아닙니다."), entry, stop, 2.0, active)


# ── 등록부 ─────────────────────────────────────────────────────────────────
GROUPS = {
    "ctrend": {"name": "추세추종", "mono": "추", "tagline": "이미 만들어진 추세에 올라타는 5개 이론",
               "intro": "추세추종 5개 이론은 이평선·고점·구름대로 '추세가 살아 있는지'를 먼저 확인합니다. 방향이 위일 때만 사고, 추세가 꺾이면 팝니다."},
    "cbreak": {"name": "돌파·변동성", "mono": "돌", "tagline": "가격이 저항을 뚫는 순간을 노리는 5개 이론",
               "intro": "돌파·변동성 5개 이론은 박스·고점·밴드를 거래량과 함께 뚫는 순간을 노립니다. 돌파가 가짜일 수 있어 손절을 짧게 가져갑니다."},
    "crev": {"name": "눌림·역추세", "mono": "눌", "tagline": "오른 코인이 잠깐 쉴 때를 사는 5개 이론",
             "intro": "눌림·역추세 5개 이론은 상승 추세 속에서 일시적으로 과매도·눌림이 온 자리를 삽니다. 추세 자체가 꺾였다면 매수하지 않습니다."},
}


def T(id_, name, mono, group, tagline, principles, rules, fn, profile):
    return {"id": id_, "name": name, "mono": mono, "group": group, "tagline": tagline, "principles": principles, "price_rules": rules,
            "evaluate": fn, "profile": profile}


THEORIES = [
    T("turtle", "터틀 트레이딩", "터", "ctrend", "리처드 데니스의 터틀: 20·55일 고점 돌파에 올라타고 ATR로 위험 관리",
      ["가격이 20일·55일 고점을 넘으면 매수", "200일선 위의 장기 상승 추세에서만", "ADX로 추세 강도 확인", "ATR(N)로 변동성과 손절폭 결정"],
      ["진입가 = 20일 고점(돌파 가격)", "손절가 = 10일 저점 또는 진입가 − 2N 중 높은 쪽", "목표가 = 진입가 + 위험의 2배", "분할은 1N씩 올라갈 때마다 추가(피라미딩)"], ev_turtle,
      {"role": "추세추종의 고전 · 터틀 규칙", "meta": "1983년 미국", "bio": "상품 트레이더 리처드 데니스가 윌리엄 에크하르트와 함께 일반인을 모집해 가르친 '터틀' 실험에서 나온 규칙입니다. 규칙만 지키면 누구나 트레이더가 될 수 있다는 것을 보여줬습니다.",
       "philosophy": "가격이 최근 고점을 넘으면 추세가 시작됐다고 보고 따라 들어갑니다. 손실은 짧게(ATR 기준 손절), 수익은 길게 가져가며, 승률보다 손익비를 중시합니다.", "keywords": ["돈치안 돌파", "ATR 손절", "피라미딩"], "works": "터틀 트레이딩 규칙"}),
    T("weinstein", "스탠 와인스타인", "와", "ctrend", "스테이지 분석: 30주선 위로 올라선 '스테이지 2'만 산다",
      ["가격이 30주선(약 210일) 위", "30주선이 우상향", "30주선에서 너무 멀리 올라간 과열은 피함", "시장 대비 상대강도 우위"],
      ["진입가 = 현재가(스테이지 2 중) 또는 30주선 +3%", "손절가 = 30주선 −3% (이탈하면 스테이지 3·4)", "목표가 = 위험의 2.5배"], ev_weinstein,
      {"role": "스테이지 분석의 창시자", "meta": "미국", "bio": "『시장 분석 비법(Secrets for Profiting in Bull and Bear Markets)』에서 주가의 사이클을 바닥(1)·상승(2)·천장(3)·하락(4) 네 단계로 나눠 설명한 차트 분석가입니다.",
       "philosophy": "30주 이동평균선을 위로 돌파해 올라가는 스테이지 2에서만 매수하고, 천장·하락 단계는 피합니다. 거래량이 돌파를 확인해 줘야 합니다.", "keywords": ["30주선", "스테이지 2", "거래량 확인"], "works": "『시장 분석 비법』"}),
    T("minervini", "마크 미너비니", "미", "ctrend", "트렌드 템플릿 8조건을 갖춘 주도 코인만 산다",
      ["가격 > 150·200일선, 150일선 > 200일선", "200일선이 최소 한 달 상승", "50일선이 150·200일선 위, 가격이 50일선 위", "저점 대비 +30% 이상, 고점 대비 -25% 이내", "상대강도(BTC 대비) 우위"],
      ["진입가 = 최근 고점(피벗) 돌파", "손절가 = 50일선 아래 또는 진입가 − 2.5ATR", "목표가 = 위험의 3배"], ev_minervini,
      {"role": "슈퍼 퍼포먼스 · 트렌드 템플릿", "meta": "미국", "bio": "미국 트레이더로, 1997년 US 투자 챔피언십에서 높은 수익률로 우승한 것으로 알려졌습니다. 『Trade Like a Stock Market Wizard』에서 트렌드 템플릿을 소개했습니다.",
       "philosophy": "이미 강한 상승 추세에 있는 종목만 고르고, 변동성이 줄어드는 눌림(VCP) 뒤 돌파에서 사며, 틀리면 짧게 손절합니다.", "keywords": ["트렌드 템플릿", "VCP", "상대강도"], "works": "『Trade Like a Stock Market Wizard』"}),
    T("dow", "찰스 다우", "다", "ctrend", "다우 이론: 고점과 저점이 함께 높아지면 상승 추세",
      ["최근 스윙 고점이 이전 고점보다 높음", "최근 스윙 저점이 이전 저점보다 높음", "직전 스윙 저점을 지키는 한 추세 유효", "거래량이 추세를 확인"],
      ["진입가 = 직전 스윙 고점 돌파(이미 넘었으면 현재가)", "손절가 = 직전 스윙 저점", "목표가 = 위험의 2배"], ev_dow,
      {"role": "다우 이론의 창시자", "meta": "1851–1902 · 미국", "bio": "월스트리트저널을 창간하고 다우존스 지수를 만든 언론인으로, 시장 추세를 읽는 '다우 이론'의 뿌리를 놓았습니다.",
       "philosophy": "시장은 큰 흐름(주추세)이 있고, 고점과 저점이 계속 높아지면 상승 추세, 낮아지면 하락 추세라고 봅니다. 추세는 확실한 반전 신호가 나오기 전까지 계속된다고 가정합니다.", "keywords": ["주추세", "고점·저점", "추세 지속"], "works": "월스트리트저널 사설"}),
    T("ichimoku", "일목균형표", "일", "ctrend", "구름대 위에서 전환선이 기준선을 넘으면 상승 우위",
      ["가격이 구름대 위", "전환선(9일) > 기준선(26일)", "후행스팬이 26일 전 가격보다 위", "양운(선행스팬A > B)"],
      ["진입가 = 현재가(삼역호전 중) 또는 구름 상단", "손절가 = 구름 상단 −1% 또는 진입가 − 3ATR 중 높은 쪽", "목표가 = 위험의 2배"], ev_ichimoku,
      {"role": "일본의 균형표 · 호소다 고이치", "meta": "일본(1930년대 발표)", "bio": "'이치모쿠 산진'이라는 필명의 일본인 호소다 고이치가 오랜 연구 끝에 발표한 균형표입니다. 한눈에 추세·지지·저항을 보도록 설계됐습니다.",
       "philosophy": "가격이 구름대 위에 있고 전환선이 기준선 위, 후행스팬이 가격 위일 때(삼역호전) 가장 강한 상승으로 봅니다. 구름대는 지지와 저항 역할을 합니다.", "keywords": ["구름대", "삼역호전", "균형"], "works": "일목균형표"}),
    T("williams", "래리 윌리엄스", "윌", "cbreak", "변동성 돌파: 오늘 시가 + 전일 변동폭 × 0.5를 넘으면 매수",
      ["오늘 가격이 시가 + 전일 변동폭 × 0.5 위", "전일 변동폭이 충분히 큼", "20일선·200일선 위", "거래량과 전일 방향성 확인"],
      ["진입가 = 시가 + 전일 변동폭 × 0.5", "손절가 = 진입가 − 1ATR", "목표가 = 위험의 1.5배 (단기, 다음 날 시가 청산이 원칙)"], ev_williams,
      {"role": "변동성 돌파 · 월드컵 챔피언", "meta": "1942년생 · 미국", "bio": "1987년 로빈스 월드컵 트레이딩 챔피언십에서 우승한 트레이더로, 변동성 돌파 전략으로 널리 알려졌습니다. 우리나라 코인 자동매매에서도 가장 많이 쓰이는 전략입니다.",
       "philosophy": "하루의 변동폭 안에서 어느 한쪽으로 크게 움직이기 시작하면 그 방향이 하루를 지배한다고 봅니다. 시가에 전일 변동폭의 일정 비율을 더한 가격을 넘으면 사고, 짧게 먹고 나옵니다.", "keywords": ["변동성 돌파", "K값 0.5", "단기 매매"], "works": "『래리 윌리엄스의 단기매매 비법』"}),
    T("livermore", "제시 리버모어", "리", "cbreak", "피벗 포인트: 거래량을 동반한 신고가 돌파",
      ["120일 신고가를 넘음", "돌파가 막 일어난 신선한 상태", "거래량이 평균을 크게 웃돔", "돌파 전 횡보로 에너지가 응축"],
      ["진입가 = 55일 고점(피벗) 돌파", "손절가 = 진입가 −10% 또는 −2.5ATR 중 높은 쪽", "목표가 = 위험의 3배"], ev_livermore,
      {"role": "월가의 전설적 투기자", "meta": "1877–1940 · 미국", "bio": "『어느 주식 투자자의 회상』의 실제 모델로 알려진 투기자입니다. 『주식 매매하는 법』에서 피벗 포인트와 최소 저항선 개념을 설명했습니다.",
       "philosophy": "가격이 오랜 횡보 끝에 고점(피벗)을 거래량과 함께 넘으면 '최소 저항선' 방향으로 움직인다고 봅니다. 확인된 뒤에 사고, 틀리면 바로 자릅니다.", "keywords": ["피벗 포인트", "최소 저항선", "거래량 돌파"], "works": "『주식 매매하는 법』"}),
    T("darvas", "니콜라스 다바스", "바", "cbreak", "박스 이론: 좁은 박스의 상단을 뚫을 때 산다",
      ["20일 박스 상단을 돌파", "박스 폭이 좁고 단단함", "박스 상단에 근접", "거래량이 늘어남"],
      ["진입가 = 박스 상단 돌파", "손절가 = 박스 하단 또는 진입가 − 3ATR 중 높은 쪽", "목표가 = 위험의 2배"], ev_darvas,
      {"role": "박스 이론의 창시자", "meta": "1900–1963 · 헝가리 출신", "bio": "무용가로 활동하며 해외 공연 중 전보로 주식을 거래해 큰 수익을 낸 것으로 유명합니다. 『나는 주식으로 200만 달러를 벌었다』를 썼습니다.",
       "philosophy": "주가는 일정한 박스(상단·하단) 안에서 움직이다가 박스 상단을 돌파하면 새 박스로 올라간다고 봅니다. 박스 상단 돌파에서 사고, 박스 하단을 이탈하면 팝니다.", "keywords": ["박스 상단", "새 박스", "손절선"], "works": "『나는 주식으로 200만 달러를 벌었다』"}),
    T("oneil_c", "윌리엄 오닐", "오", "cbreak", "신고가 부근에서 거래량이 터지는 주도주를 산다",
      ["1년 신고가에 근접하거나 돌파", "거래량이 평균의 1.4배 이상", "BTC 대비 상대강도 우위", "조정 후 형성한 베이스", "BTC가 상승 추세"],
      ["진입가 = 1년 고점(신고가선)", "손절가 = 진입가 −8% (오닐의 7~8% 손절)", "목표가 = 위험의 3배"], ev_oneil,
      {"role": "CAN SLIM의 창시자", "meta": "1933–2023 · 미국", "bio": "투자 전문지 '인베스터스 비즈니스 데일리'를 창간했고, 『최고의 주식 최적의 타이밍』에서 CAN SLIM 투자법을 소개했습니다. 여기서는 차트로 확인되는 신고가·거래량·상대강도만 적용했습니다.",
       "philosophy": "이미 강한 주도주가 신고가를 넘으며 거래량이 터질 때가 가장 좋은 매수 시점이라고 봅니다. 틀리면 7~8%에서 바로 손절하는 것이 원칙입니다.", "keywords": ["신고가 돌파", "거래량 급증", "7~8% 손절"], "works": "『최고의 주식 최적의 타이밍』"}),
    T("bollinger", "존 볼린저", "볼", "cbreak", "밴드가 좁아졌다가 위로 터질 때(스퀴즈 돌파)",
      ["볼린저 밴드폭이 최근 120일 중 하위권(스퀴즈)", "가격이 상단 밴드에 접근·돌파", "중심선(20일선) 위에서 우상향", "거래량 확대"],
      ["진입가 = 상단 밴드", "손절가 = 중심선(20일선)", "목표가 = 위험의 2배"], ev_bollinger,
      {"role": "볼린저 밴드의 개발자", "meta": "미국", "bio": "금융 분석가이자 방송 해설가로, 이동평균에 표준편차를 더한 '볼린저 밴드'를 만든 사람입니다.",
       "philosophy": "변동성은 줄었다 늘었다를 반복하므로, 밴드가 극단적으로 좁아진(스퀴즈) 뒤에는 큰 움직임이 온다고 봅니다. 상단을 거래량과 함께 뚫으면 상승 쪽으로 봅니다.", "keywords": ["스퀴즈", "밴드폭", "변동성 수축"], "works": "볼린저 밴드"}),
    T("connors", "래리 코너스", "코", "crev", "RSI(2) 눌림목: 상승 추세 속 단기 과매도를 산다",
      ["RSI(2)가 10 미만의 극단적 과매도", "가격이 200일선 위(장기 상승 추세)", "20일선 아래로 단기 눌림", "중기선이 장기선 위"],
      ["진입가 = 현재가", "손절가 = 진입가 − 2.5ATR (넓게)", "목표가 = 위험의 1.5배 (단기 반등 후 청산)"], ev_connors,
      {"role": "단기 평균회귀 매매의 대가", "meta": "미국", "bio": "『단기 매매 전략(Short Term Trading Strategies That Work)』 등에서 RSI 2일선을 이용한 단기 눌림목 매매를 통계적으로 검증해 알린 트레이더입니다.",
       "philosophy": "상승 추세인 종목이 단기간에 지나치게 떨어지면 되돌림이 온다고 봅니다. 장기 추세가 위일 때 극단적 과매도를 사고, 반등하면 곧바로 청산합니다.", "keywords": ["RSI(2)", "평균회귀", "200일선 필터"], "works": "『단기 매매 전략』"}),
    T("granville", "조셉 그랜빌", "랜", "crev", "그랜빌의 법칙: 상승하는 이평선에서 지지받을 때 산다",
      ["60일선이 우상향", "가격이 60일선 부근(-3%~+6%)까지 눌림", "최근 이평선을 건드린 뒤 위에서 마감(지지 확인)", "과열(이격 과대) 아님", "200일선 위"],
      ["진입가 = 현재가", "손절가 = 60일선 −3% (이평 이탈)", "목표가 = 위험의 2배"], ev_granville,
      {"role": "그랜빌의 8법칙", "meta": "1923–2013 · 미국", "bio": "주가와 이동평균선의 관계를 8가지 매매 규칙으로 정리한 『그랜빌의 시장 투자 전략』의 저자입니다. 거래량 지표인 OBV도 개발했습니다.",
       "philosophy": "이동평균선이 오르는 중에 가격이 이평선 근처로 내려왔다가 지지받고 다시 오르면 매수 신호라고 봅니다. 이평선에서 너무 멀리 벌어지면(이격 과대) 조정을 경계합니다.", "keywords": ["이동평균선", "눌림 지지", "이격도"], "works": "『그랜빌의 시장 투자 전략』"}),
    T("wilder", "웰스 와일더", "와일", "crev", "추세가 강할 때(ADX) RSI가 눌리면 산다",
      ["ADX 25 이상의 뚜렷한 추세", "+DI가 −DI보다 큼(상승 방향)", "RSI(14)가 35~50의 눌림 구간", "200일선 위", "변동성(ATR) 안정"],
      ["진입가 = 현재가", "손절가 = 진입가 − 2ATR", "목표가 = 위험의 2배"], ev_wilder,
      {"role": "RSI·ATR·ADX의 개발자", "meta": "1935년생 · 미국", "bio": "1978년 『New Concepts in Technical Trading Systems』에서 RSI, ATR, ADX, 파라볼릭 SAR 등 오늘날 표준이 된 지표를 발표했습니다.",
       "philosophy": "ADX로 추세의 유무와 강도를 먼저 확인하고, 추세가 살아 있을 때 RSI가 눌린 자리를 매수 기회로 봅니다. 추세가 약하면 매매하지 않습니다.", "keywords": ["RSI", "ADX", "ATR"], "works": "『New Concepts in Technical Trading Systems』"}),
    T("appel", "제럴드 아펠", "아", "crev", "MACD가 막 상향 반전할 때(골든크로스) 산다",
      ["MACD가 시그널선을 상향 돌파한 지 얼마 안 됨", "히스토그램이 커지는 중", "0선 아래에서 반전하면 더 강한 신호", "200일선 위", "거래량 확인"],
      ["진입가 = 현재가", "손절가 = 진입가 − 2ATR", "목표가 = 위험의 2배"], ev_appel,
      {"role": "MACD의 개발자", "meta": "미국", "bio": "1970년대에 두 이동평균의 차이를 이용한 모멘텀 지표 MACD를 만든 투자 자문가이자 작가입니다.",
       "philosophy": "단기 이평과 장기 이평의 간격이 좁아졌다 벌어지는 모습으로 모멘텀의 전환을 읽습니다. MACD가 시그널선을 아래에서 위로 뚫는 순간을 매수 신호로 봅니다.", "keywords": ["MACD", "골든크로스", "모멘텀 전환"], "works": "MACD"}),
    T("elder", "알렉산더 엘더", "엘", "crev", "삼중창: 큰 물결이 상승일 때 작은 물결의 눌림을 산다",
      ["주봉(큰 물결) 추세가 상승", "일봉(작은 물결) 오실레이터가 눌림", "전일 고점을 넘는 순간 진입", "변동성(위험) 관리"],
      ["진입가 = 전일 고점 돌파", "손절가 = 전일 저점 또는 진입가 − 1ATR 중 낮은 쪽", "목표가 = 위험의 2배"], ev_elder,
      {"role": "삼중창 매매 시스템", "meta": "미국", "bio": "정신과 의사 출신 트레이더로, 『심리투자 법칙(Trading for a Living)』에서 세 개의 시간 단위로 시장을 보는 삼중창 시스템을 소개했습니다.",
       "philosophy": "큰 시간대(주봉)의 추세 방향으로만 거래하고, 작은 시간대(일봉)에서 눌림이 왔을 때 사며, 전일 고점을 넘는 순간 진입합니다. 감정 관리와 위험 관리를 강조합니다.", "keywords": ["삼중창", "큰 물결·작은 물결", "심리 관리"], "works": "『심리투자 법칙』"}),
]
