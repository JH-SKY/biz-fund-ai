"""KSIC 기반 정책자금 제외 업종 (접두·정확 일치).

금융·보험(64~66), 부동산(68), 전문직(711/712/715), 유흥 주점(56211), 사행(91), 의료(861).
"""

from __future__ import annotations

# 세세분류 정확 일치 (5자리 등)
_EXCLUDED_KSIC_EXACT: frozenset[str] = frozenset(
    {
        "56211",  # 유흥 주점(예: 음식점업 중 해당 세세분류)
    }
)

# 접두: 긴 것부터 매칭할 것 (startswith)
_EXCLUDED_KSIC_PREFIXES: tuple[str, ...] = (
    "711",  # 전문직(세부)
    "712",
    "715",
    "861",  # 의료
    "64",  # 금융·보험권(64~66)
    "65",
    "66",
    "68",  # 부동산
    "91",  # 사행·오락(91xxx)
)


def is_ksic_policy_excluded(ksic_code: str | None) -> bool:
    """True면 추천 엔진에서 1차 결격(빨강) 후보로 취급."""
    if not ksic_code or not ksic_code.strip():
        return False
    code = ksic_code.strip()
    if code in _EXCLUDED_KSIC_EXACT:
        return True
    for p in _EXCLUDED_KSIC_PREFIXES:
        if code.startswith(p):
            return True
    return False
