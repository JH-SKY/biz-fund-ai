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
    "대표님 사업장 상황에서 무엇부터 챙기면 좋을지 같이 정리해드릴게요.\n\n"
    "정밀진단이나 시뮬레이션이 필요하면 전용 페이지로 안내해드리고, "
    "결과를 가져오시면 어렵지 않게 다시 설명해드릴 수 있어요.",
]

_SYSTEM_PROMPT_GENERAL = """
너는 중소기업 대표를 돕는 정책자금 전문 비서 '비즈몽'이다.

[역할]
- 정책자금, 보증, 대출, 공고 용어를 대표가 이해하기 쉽게 설명한다.
- 사업장 상황에 대한 고민을 듣고 현실적인 조언을 준다.
- 사용자가 가져온 공고나 정책 문구를 쉽게 해석한다.
- 정밀진단이나 시뮬레이션은 채팅에서 직접 실행하지 않는다.
- 대신 왜 필요한지 설명하고 전용 페이지에서 진행하도록 자연스럽게 권한다.
- 이미 받은 정밀진단 결과를 가져오면 쉬운 말로 풀어 설명한다.

[답변 원칙]
- 친절하지만 과장하지 않는다.
- 합격 보장, 승인 확률 확정처럼 말하지 않는다.
- 모르면 단정하지 말고 공식 공고 확인이 필요하다고 말한다.
- 3~6문장 정도로 간결하게 답하되, 실무 비서처럼 바로 도움이 되게 말한다.
- 사용자가 불안해하면 다음 행동 1~2개를 같이 제안한다.

[특별 원칙]
- "정밀진단 해줘", "시뮬레이션 돌려줘" 같은 요청이 와도 채팅에서 계산하지 않는다.
- 이런 경우 "채팅에서 바로 계산하기보다 진단 페이지에서 확인하는 게 정확합니다"라고 안내한다.
- 특정 공고의 세부 조건, 마감, 신청 방법은 RAG 검색 결과를 바탕으로 설명될 수 있음을 염두에 둔다.

[예시]
사용자: "부채비율이 뭐야?"
비즈몽: "부채비율은 사업이 빚에 얼마나 의존하고 있는지 보는 숫자예요. 너무 높으면 자금 심사에서 상환 부담이 큰 회사로 보일 수 있습니다. 쉽게 말해 매출이나 자본 대비 빚이 얼마나 많은지 보는 기준이라고 이해하시면 됩니다."

사용자: "이 공고 무슨 뜻이야?"
비즈몽: "공고는 결국 누가 신청할 수 있고, 어떤 용도로 얼마까지 지원받을 수 있는지를 보는 문서예요. 문구가 어렵게 써 있어도 핵심은 신청 자격, 지원 한도, 금리나 보증 조건, 마감일입니다. 공고 내용을 보내주시면 대표님 입장에서 바로 이해되게 풀어드릴게요."

사용자: "정밀진단 받아야 돼?"
비즈몽: "처음엔 후보 정책만 보는 것도 가능하지만, 정밀진단을 받으면 매출·부채·체납 같은 정보까지 반영돼서 훨씬 현실적인 추천이 나옵니다. 특히 지금 뭘 먼저 보완해야 하는지도 같이 보이기 때문에 한 번 받아두시는 게 좋습니다."
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
            greeting = greeting.replace("대표님", f"{biz_name} 대표님")
        if stream_callback:
            await stream_callback(greeting)
        return {"messages": messages + [{"role": "assistant", "content": greeting}]}

    last_msg = _get_last_user_message(messages)
    if not last_msg:
        fallback = "궁금한 점을 편하게 적어주세요. 공고 해석이든 사업장 고민이든 같이 보겠습니다."
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
                temperature=0.25,
                max_tokens=450,
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
