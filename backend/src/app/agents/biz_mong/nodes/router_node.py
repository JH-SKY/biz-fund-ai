"""Intent router for BizMong."""

from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

VALID_INTENTS = frozenset(["greeting", "general_qa", "rag", "stats"])
DEFAULT_INTENT = "general_qa"


async def router_node(
    state: dict,
    client: AsyncOpenAI | None = None,
) -> dict:
    """Route the latest user message to the lightweight counselor flow."""
    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)

    messages: list = state.get("messages") or []
    last_msg = _get_last_user_message(messages)
    if not last_msg:
        return {"current_agent": DEFAULT_INTENT}

    intent = await _classify_intent_llm(_client, last_msg)
    if intent not in VALID_INTENTS:
        intent = _classify_by_keyword(last_msg)

    logger.info("[bizmong-router] '%s' -> %s", last_msg[:80], intent)
    return {"current_agent": intent}


async def _classify_intent_llm(client: AsyncOpenAI, message: str) -> str:
    system_prompt = """
사용자 메시지를 아래 4가지 중 하나로만 분류하세요.
반드시 JSON 하나만 반환하세요.

- greeting: 인사, 가벼운 대화, 시작 멘트
- general_qa: 정책자금 용어 설명, 사업장 고민 상담, 정밀진단/시뮬레이션 기능 안내, 결과 해석 요청
- rag: 특정 공고, 지원조건, 신청방법, 마감, 필요서류처럼 정책 문서 검색이 필요한 질문
- stats: 동종업계 평균, 비교 통계, 퍼센타일 같은 수치 비교 요청

중요:
- 채팅 안에서 정밀진단이나 시뮬레이션을 직접 실행하지 않는다.
- 그런 요청도 general_qa로 분류한다.

{"intent":"..."}
"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=20,
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        return str(payload.get("intent", "")).lower()
    except Exception as exc:
        logger.warning("[bizmong-router] intent classification failed: %s", exc)
        return ""


def _classify_by_keyword(message: str) -> str:
    msg = message.lower()

    greeting_kws = ["안녕", "반가", "고마", "감사", "처음", "hello", "hi"]
    stats_kws = ["평균", "통계", "비교", "퍼센타일", "동종업계", "업계 평균"]
    rag_kws = [
        "공고",
        "지원조건",
        "신청방법",
        "마감",
        "신청 자격",
        "필요서류",
        "어떤 정책",
        "정책 설명",
    ]

    if any(keyword in msg for keyword in greeting_kws):
        return "greeting"
    if any(keyword in msg for keyword in stats_kws):
        return "stats"
    if any(keyword in msg for keyword in rag_kws):
        return "rag"
    return DEFAULT_INTENT


def _get_last_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
