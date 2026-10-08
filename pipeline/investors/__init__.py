"""투자자 모듈 레지스트리.

새 투자자 추가 방법: investors/ 아래에 buffett.py 처럼 INFO(dict) 와 evaluate(m) -> dict|None 을
정의한 파일을 만들고, 아래 GROUP_MEMBERS 에 소속(성장주/저평가/복합)을 적고, profiles.py 에 소개를 추가하면 끝.
(evaluate 가 None 을 돌려주면 그 종목은 해당 투자자의 평가 대상이 아님.)
종합 순위와 진영별 종합은 build.py 가 자동으로 합산한다. 진영은 5명씩 균형을 맞춘다.
"""
from . import (ackman, buffett, burry, fisher, graham, greenblatt, lynch, marks, munger, neff,
               oneil, price, slater, templeton, wood)

from .chart import CHART_INVESTORS  # noqa: E402  (차트 현인: 재무가 아니라 일봉 차트로 판단)

GROUP_MEMBERS = {
    "growth": [fisher, oneil, wood, price, slater],
    "value": [graham, templeton, burry, neff, marks],
    "mixed": [buffett, munger, lynch, greenblatt, ackman],
    "chart": CHART_INVESTORS,
}
GROUP_ORDER = ["growth", "value", "mixed", "chart"]
INVESTORS = [m for g in GROUP_ORDER for m in GROUP_MEMBERS[g]]
GROUP_OF = {m.INFO["id"]: g for g in GROUP_ORDER for m in GROUP_MEMBERS[g]}
