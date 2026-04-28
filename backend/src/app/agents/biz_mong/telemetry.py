"""Helpers for BizMong observability."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


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
