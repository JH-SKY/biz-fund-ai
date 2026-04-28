"""Lightweight counselor node for BizMong."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from openai import AsyncOpenAI

from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_GREETING_RESPONSES = [
    "안녕하세요. 비즈몽입니다.\n\n"
    "정책자금 용어를 쉽게 풀어드리고, 공고 내용을 해석해드리고, "
    "대표님 사업장 상황에 맞는 다음 행동을 같이 정리해드릴게요.\n\n"
    "정밀진단이나 시뮬레이션이 필요하면 전용 페이지로 안내해드리고, "
    "결과를 가져오시면 쉽게 설명해드릴 수 있어요.",
]

_SYSTEM_PROMPT_GENERAL = """
너는 중소기업 대표를 돕는 정책자금 전문 비서 '비즈몽'이다.

역할:
- 정책자금, 보증, 대출, 공고 용어를 쉽게 설명한다.
- 사용자의 사업장 고민을 듣고 현실적인 조언을 준다.
- 특정 공고가 언급되면 이해하기 쉽게 해석해준다.
- 정밀진단이나 시뮬레이션을 채팅에서 직접 실행하지 않는다.
- 대신 필요할 때 정밀진단 페이지나 시뮬레이션 페이지를 친절히 권한다.
- 사용자가 이미 받은 진단 결과를 가져오면 이해하기 쉽게 풀어준다.

답변 원칙:
- 과장하지 말고, 모르면 단정하지 않는다.
- 한국어로 답하고, 3~6문장 정도로 간결하지만 친절하게 답한다.
- 딱딱한 심사관이 아니라 대표의 실무 비서처럼 말한다.
- 정밀진단/시뮬레이션 요청이 오면 "채팅에서 바로 계산하기보다 진단 페이지에서 확인하는 게 정확하다"고 안내한다.
"""

StreamCallback = Callable[[str], Awaitable[None]]


async def chitchat_node(
    state: dict,
    client: AsyncOpenAI | None = None,
    stream_callback: StreamCallback | None = None,
) -> dict:
    current_agent: str = state.get("current_agent", "greeting")
    messages: list = state.get("messages") or []
    biz_info: dict = state.get("biz_info") or {}
    biz_name: str = biz_info.get("biz_name", "")

    if current_agent == "greeting":
        greeting = _GREETING_RESPONSES[0]
        if biz_name:
            greeting = greeting.replace("대표", f"{biz_name} 대표")
        if stream_callback:
            await stream_callback(greeting)
        return {"messages": messages + [{"role": "assistant", "content": greeting}]}

    last_msg = _get_last_user_message(messages)
    if not last_msg:
        fallback = "궁금한 점을 편하게 적어주세요."
        if stream_callback:
            await stream_callback(fallback)
        return {"messages": messages + [{"role": "assistant", "content": fallback}]}

    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)
    history = [
        message
        for message in messages
        if isinstance(message, dict) and message.get("role") in ("user", "assistant")
    ][-12:]
    gpt_messages = [{"role": "system", "content": _SYSTEM_PROMPT_GENERAL}] + history

    try:
        if stream_callback:
            answer = await _stream_general_qa(_client, gpt_messages, stream_callback)
        else:
            response = await _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=gpt_messages,
                temperature=0.3,
                max_tokens=400,
            )
            answer = (response.choices[0].message.content or "").strip()
        logger.info("[bizmong-chitchat] answer generated (%d chars)", len(answer))
    except Exception as exc:
        logger.warning("[bizmong-chitchat] generation failed: %s", exc)
        answer = "잠시 오류가 있었어요. 같은 질문을 한 번만 더 보내주시면 바로 이어서 도와드릴게요."
        if stream_callback:
            await stream_callback(answer)

    return {"messages": messages + [{"role": "assistant", "content": answer}]}


async def _stream_general_qa(
    client: AsyncOpenAI,
    gpt_messages: list,
    callback: StreamCallback,
) -> str:
    collected: list[str] = []
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=gpt_messages,
        temperature=0.3,
        max_tokens=400,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            collected.append(delta)
            await callback(delta)
    return "".join(collected)


def _get_last_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
