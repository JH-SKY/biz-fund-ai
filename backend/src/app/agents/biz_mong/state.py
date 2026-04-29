"""Shared state for the lightweight BizMong graph."""

from __future__ import annotations

from typing import Any

from langgraph.graph.message import add_messages


class BizMongState(dict):
    """LangGraph state container for the BizMong counselor flow."""

    messages = add_messages
    user_id: str
    business_id: str
    room_id: str
    biz_info: dict
    financial_data: dict
    current_agent: str
    stats_insight: dict
    is_error: bool
    error_message: str


def make_initial_state(
    *,
    user_id: str,
    business_id: str,
    room_id: str,
    first_message: str,
) -> dict[str, Any]:
    return {
        "messages": [{"role": "user", "content": first_message}],
        "user_id": user_id,
        "business_id": business_id,
        "room_id": room_id,
        "biz_info": {},
        "financial_data": {},
        "current_agent": "",
        "stats_insight": {},
        "is_error": False,
        "error_message": "",
    }
