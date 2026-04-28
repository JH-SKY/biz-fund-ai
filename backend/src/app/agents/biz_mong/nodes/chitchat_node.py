"""Lightweight counselor node for BizMong."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Awaitable, Callable

from openai import AsyncOpenAI

from src.app.agents.biz_mong.telemetry import build_node_log
from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

PROMPT_VERSION_GENERAL = "bizmong-general-v1"

_GREETING_RESPONSES = [
    "안녕하세요. 비즈몽입니다.\n\n"
    "정책자금 용어를 쉽게 풀어드리고, 공고 내용을 대표님 입장에서 해석해드리고, "
    "사업장 상황에서 무엇부터 챙기면 좋을지 함께 정리해드릴게요.\n\n"
    "정밀진단이나 시뮬레이션이 필요하면 전용 페이지로 안내해드리고, "
    "결과를 가져오시면 이해하기 쉽게 다시 설명해드릴 수 있어요."
]

_SYSTEM_PROMPT_GENERAL = """
당신은 중소기업 대표를 돕는 정책자금 전문 비서 '비즈몽'이다.

[역할]
- 정책자금, 보증, 대출 공고 용어를 대표가 이해하기 쉽게 설명한다.
- 사업장 상황에 대한 고민을 듣고 현실적인 조언을 준다.
- 사용자가 가져온 공고나 정책 문구를 쉽게 해석한다.
- 정밀진단이나 시뮬레이션은 채팅에서 직접 실행하지 않는다.
- 대신 왜 필요한지 설명하고 전용 페이지로 자연스럽게 안내한다.
- 이미 받은 정밀진단 결과는 쉬운 말로 다시 설명한다.

[답변 원칙]
- 친절하지만 과장하지 않는다.
- 승인 가능성, 합격 확률처럼 확정적으로 말하지 않는다.
- 모르는 내용은 추정하지 말고 공식 공고 확인이 필요하다고 말한다.
- 3~6문장 정도로 간결하게 답한다.
- 필요하면 마지막에 다음 행동 1~2개를 제안한다.
"""

StreamCallback = Callable[[str], Awaitable[None]]


async def chitchat_node(
    state: dict,
    client: AsyncOpenAI | None = None,
    stream_callback: StreamCallback | None = None,
) -> dict:
    started_at = datetime.now(timezone.utc)
    started_mono = time.monotonic()

    current_agent: str = state.get("current_agent", "greeting")
    messages: list = state.get("messages") or []
    biz_info: dict = state.get("biz_info") or {}
    biz_name: str = biz_info.get("biz_name", "")

    if current_agent == "greeting":
        greeting = _GREETING_RESPONSES[0]
        if biz_name:
            greeting = greeting.replace("대표님", f"{biz_name} 대표님")
        if stream_callback:
            await stream_callback(greeting)
        return {
            "messages": messages + [{"role": "assistant", "content": greeting}],
            "node_logs": [
                build_node_log(
                    node_name="general_qa",
                    sequence=2,
                    status="SUCCESS",
                    latency_ms=int((time.monotonic() - started_mono) * 1000),
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    metadata={"mode": "greeting", "prompt_version": PROMPT_VERSION_GENERAL},
                )
            ],
            "prompt_version": PROMPT_VERSION_GENERAL,
        }

    last_msg = _get_last_user_message(messages)
    if not last_msg:
        fallback = "궁금한 점을 편하게 적어주세요. 공고 해석이든 사업장 고민이든 같이 정리해드릴게요."
        if stream_callback:
            await stream_callback(fallback)
        return {
            "messages": messages + [{"role": "assistant", "content": fallback}],
            "node_logs": [
                build_node_log(
                    node_name="general_qa",
                    sequence=2,
                    status="SUCCESS",
                    latency_ms=int((time.monotonic() - started_mono) * 1000),
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    metadata={"mode": "empty", "prompt_version": PROMPT_VERSION_GENERAL},
                )
            ],
            "prompt_version": PROMPT_VERSION_GENERAL,
        }

    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)
    history = [
        message
        for message in messages
        if isinstance(message, dict) and message.get("role") in ("user", "assistant")
    ][-12:]
    gpt_messages = [{"role": "system", "content": _SYSTEM_PROMPT_GENERAL}] + history

    usage = None
    status = "SUCCESS"
    try:
        if stream_callback:
            answer = await _stream_general_qa(_client, gpt_messages, stream_callback)
        else:
            response = await _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=gpt_messages,
                temperature=0.25,
                max_tokens=450,
            )
            answer = (response.choices[0].message.content or "").strip()
            usage = getattr(response, "usage", None)
        logger.info("[bizmong-chitchat] answer generated (%d chars)", len(answer))
    except Exception as exc:
        logger.warning("[bizmong-chitchat] generation failed: %s", exc)
        answer = "일시적인 오류가 있었어요. 같은 질문을 한 번만 다시 보내주시면 바로 이어서 도와드릴게요."
        if stream_callback:
            await stream_callback(answer)
        status = "ERROR"

    return {
        "messages": messages + [{"role": "assistant", "content": answer}],
        "node_logs": [
            build_node_log(
                node_name="general_qa",
                sequence=2,
                status=status,
                latency_ms=int((time.monotonic() - started_mono) * 1000),
                model_name="gpt-4o-mini",
                tokens_in=getattr(usage, "prompt_tokens", None),
                tokens_out=getattr(usage, "completion_tokens", None),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                metadata={"mode": current_agent, "prompt_version": PROMPT_VERSION_GENERAL},
            )
        ],
        "prompt_version": PROMPT_VERSION_GENERAL,
    }


async def _stream_general_qa(
    client: AsyncOpenAI,
    gpt_messages: list,
    callback: StreamCallback,
) -> str:
    collected: list[str] = []
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=gpt_messages,
        temperature=0.25,
        max_tokens=450,
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
