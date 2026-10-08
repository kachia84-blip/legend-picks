"""차트 현인 5명(주식용): 재무가 아니라 일봉 차트로만 판단한다.

코인 매매이론(coin_theories.py)과 같은 규칙을 주식 일봉에 적용한다. 평가에는 chart_stock.py 가 계산한 차트 지표를 쓴다.
(그래서 evaluate 에는 재무 지표가 아니라 차트 지표 dict 를 넘긴다.)
"""
from types import SimpleNamespace

import coin_theories as ct
from investors.common import TONE_LABEL

# 주식 차트 현인은 주식 화면의 평가 용어("강력 매수 후보" 등)를 그대로 쓴다
def _wrap(fn):
    def evaluate(m):
        r = fn(m)
        r["verdict"] = TONE_LABEL[r["tone"]]
        return r
    return evaluate


def _info(theory_id, new_id, name, mono, tagline, extra_rules=None):
    t = next(x for x in ct.THEORIES if x["id"] == theory_id)
    return SimpleNamespace(
        KIND="chart",
        INFO={"id": new_id, "name": name, "mono": mono, "tagline": tagline, "principles": t["principles"],
              "price_rules": (extra_rules or []) + t["price_rules"]},
        evaluate=_wrap(t["evaluate"]), PROFILE=t["profile"])


NOTE = "진입가·목표가·손절가는 재무가 아니라 차트(ATR)로 계산합니다"

WEINSTEIN = _info("weinstein", "weinstein_s", "스탠 와인스타인", "와", "스테이지 분석: 30주선 위로 올라선 '스테이지 2' 주식만 산다", [NOTE])
MINERVINI = _info("minervini", "minervini_s", "마크 미너비니", "미", "트렌드 템플릿 8조건을 갖춘 주도주만 산다", [NOTE])
LIVERMORE = _info("livermore", "livermore_s", "제시 리버모어", "리", "피벗 포인트: 거래량을 동반한 신고가 돌파", [NOTE])
DARVAS = _info("darvas", "darvas_s", "니콜라스 다바스", "바", "박스 이론: 좁은 박스의 상단을 뚫을 때 산다", [NOTE])
GRANVILLE = _info("granville", "granville_s", "조셉 그랜빌", "랜", "그랜빌의 법칙: 상승하는 이평선에서 지지받을 때 산다", [NOTE])

CHART_INVESTORS = [WEINSTEIN, MINERVINI, LIVERMORE, DARVAS, GRANVILLE]
