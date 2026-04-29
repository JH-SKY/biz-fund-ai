# src/app/agents/biz_mong/telemetry.py
"""비즈몽 에이전트 관측성(Observability) 헬퍼.

[담당 역할]
- 각 노드의 실행 결과를 구조화된 로그 딕셔너리로 변환 (build_node_log)
- LLM 호출 비용(USD)을 토큰 수 기반으로 추정 (estimate_cost_usd)
- 생성된 노드 로그는 AgentNodeLog 테이블에 저장되어 모니터링·비용 분석에 활용된다.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


# 모델별 1,000토큰당 비용 (입력, 출력) — USD 기준
# 가격이 변경되면 이 딕셔너리만 업데이트하면 된다.
MODEL_PRICING_USD_PER_1K: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.005, 0.015),
}


def estimate_cost_usd(
    *,
    model_name: str | None,
    tokens_in: int | None,
    tokens_out: int | None,
) -> Decimal | None:
    """토큰 수와 모델명을 기반으로 LLM 호출 비용(USD)을 추정한다.

    - 모델명이 없거나 가격 정보가 없으면 None 반환.
    - 소수점 8자리까지 반올림하여 Decimal 반환 (float 부동소수점 오차 방지).
    """
    if model_name is None:
        return None
    pricing = MODEL_PRICING_USD_PER_1K.get(model_name)
    if pricing is None:
        return None

    prompt_rate, completion_rate = pricing
    prompt_tokens = max(tokens_in or 0, 0)
    completion_tokens = max(tokens_out or 0, 0)
    cost = (prompt_tokens / 1000 * prompt_rate) + (
        completion_tokens / 1000 * completion_rate
    )
    return Decimal(str(cost)).quantize(
        Decimal("0.00000001"),
        rounding=ROUND_HALF_UP,
    )


def build_node_log(
    *,
    node_name: str,
    sequence: int,
    status: str = "SUCCESS",
    latency_ms: int | None = None,
    model_name: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    started_at: Any = None,
    completed_at: Any = None,
    error_code: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
    cost_usd: Decimal | None = None,
) -> dict[str, Any]:
    """에이전트 노드 실행 결과를 구조화된 로그 딕셔너리로 생성한다.

    Args:
        node_name    : 노드 이름 (예: "router", "rag_retrieval", "rag_generation")
        sequence     : 이번 실행 흐름에서의 순서 번호 (router=1, 이후 노드=2, 3...)
        status       : 실행 결과 (SUCCESS | ERROR)
        latency_ms   : 노드 실행 소요 시간 (밀리초)
        model_name   : 사용된 LLM 모델명 (비용 계산에 사용)
        tokens_in    : 입력 토큰 수
        tokens_out   : 출력 토큰 수
        started_at   : 노드 시작 시각 (datetime)
        completed_at : 노드 완료 시각 (datetime)
        error_code   : 오류 코드 (오류 발생 시)
        error_message: 오류 메시지 (오류 발생 시)
        metadata     : 노드별 추가 정보 (예: result_count, region_filter 등)
        cost_usd     : 외부에서 직접 비용을 넣을 경우 사용 (없으면 자동 추정)

    Returns:
        AgentNodeLog 테이블 구조와 대응되는 딕셔너리
    """
    # cost_usd 가 명시되지 않았으면 토큰 수 기반 자동 추정
    computed_cost = cost_usd if cost_usd is not None else estimate_cost_usd(
        model_name=model_name,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    return {
        "node_name": node_name,
        "sequence": sequence,
        "status": status,
        "latency_ms": latency_ms,
        "model_name": model_name,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": computed_cost,
        "started_at": started_at,
        "completed_at": completed_at,
        "error_code": error_code,
        "error_message": error_message,
        "metadata": metadata or {},
    }
