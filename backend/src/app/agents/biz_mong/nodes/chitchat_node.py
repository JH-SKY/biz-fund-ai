# src/app/agents/biz_mong/nodes/chitchat_node.py
"""Node: Chitchat — 인사/잡담 및 일반 질문 직접 처리 노드.

두 가지 경우를 처리한다:
  1. greeting (인사/잡담): LLM 호출 없이 규칙 기반 웰컴 메시지 반환.
  2. general_qa (일반 개념 질문): GPT-4o-mini 1회 직접 응답.
     - DB 조회 없음, 벡터 검색 없음, 도구 없음.
     - 단순 용어 설명, 개념 풀이 등에 활용.

[설계 의도]:
  - 인사/잡담/단순 질문은 heavy pipeline (hard_filter → llm_evaluator) 을
    완전히 우회한다 → 비용 0 또는 GPT 1회로 즉각 응답.
  - biz_info 가 있으면 사장님 호칭에 상호명을 쓴다.
  - stream_callback 을 넘기면 general_qa 에서 토큰 단위 스트리밍을 지원한다.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Callable, Awaitable

from openai import AsyncOpenAI

from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_GREETING_RESPONSES = [
    "안녕하세요 사장님! 😊 저는 비즈몽 AI 상담사입니다.\n\n"
    "궁금한 게 있으시면 편하게 물어보세요!\n\n"
    "**할 수 있는 것들**\n"
    "• 내 사업장에 맞는 정책자금 진단\n"
    "• 조건 바꿨을 때 점수 시뮬레이션\n"
    "• 특정 공고·제도 설명\n"
    "• 동종업계 비교 통계",
]

_SYSTEM_PROMPT_GENERAL = (
    "당신은 대한민국 중소기업·소상공인 정책자금 전문 상담사 비즈몽입니다.\n"
    "사용자의 질문에 대해 친절하고 간결하게 답변하세요.\n"
    "- 재무·회계·정책 용어 설명은 쉬운 말로 풀어서 설명하세요.\n"
    "- 모르거나 불확실한 내용은 단정하지 말고 '정확한 내용은 담당 기관에 문의하세요'라고 안내하세요.\n"
    "- 답변은 3~5문장 이내로 짧게 유지하세요.\n"
    "- 정책자금 진단이 필요하면 '진단 요청'을 해달라고 안내하세요."
)

# stream_callback 타입: 토큰 청크를 받아 처리하는 코루틴
StreamCallback = Callable[[str], Awaitable[None]]


async def chitchat_node(
    state: dict,
    client: AsyncOpenAI | None = None,
    stream_callback: StreamCallback | None = None,
) -> dict:
    """인사/잡담 또는 일반 개념 질문에 응답한다.

    State 입력:
        current_agent: "greeting" | "general_qa"
        messages: 대화 히스토리
        biz_info: 사업장 기본정보 (선택)
    State 출력:
        messages: assistant 응답 추가
    """
    current_agent: str = state.get("current_agent", "greeting")
    messages: list = state.get("messages") or []
    biz_info: dict = state.get("biz_info") or {}
    biz_name: str = biz_info.get("biz_name", "")

    # ── greeting: LLM 없이 바로 응답 ──────────────────────────────────────
    if current_agent == "greeting":
        greeting = _GREETING_RESPONSES[0]
        if biz_name:
            greeting = greeting.replace("사장님!", f"{biz_name} 사장님!")
        if stream_callback:
            await stream_callback(greeting)
        logger.info("[chitchat] greeting → 규칙 기반 응답")
        return {
            "messages": messages + [{"role": "assistant", "content": greeting}],
        }

    # ── general_qa: GPT 직접 답변 ─────────────────────────────────────────
    last_msg = _get_last_user_message(messages)
    if not last_msg:
        fallback = "질문을 입력해 주세요."
        if stream_callback:
            await stream_callback(fallback)
        return {
            "messages": messages + [{"role": "assistant", "content": fallback}],
        }

    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)
    history = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    history = history[-12:]
    gpt_messages = [{"role": "system", "content": _SYSTEM_PROMPT_GENERAL}] + history

    try:
        if stream_callback:
            # 스트리밍 모드: 토큰 단위로 callback 호출
            answer = await _stream_general_qa(_client, gpt_messages, stream_callback)
        else:
            # 일반 모드: 전체 응답 반환
            response = await _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=gpt_messages,
                temperature=0.3,
                max_tokens=400,
            )
            answer = response.choices[0].message.content.strip()
        logger.info("[chitchat] general_qa → 응답 완료 (%d chars)", len(answer))
    except Exception as exc:
        logger.warning("[chitchat] GPT 호출 실패: %s", exc)
        answer = "죄송합니다, 잠시 오류가 발생했습니다. 다시 시도해 주세요."
        if stream_callback:
            await stream_callback(answer)

    return {
        "messages": messages + [{"role": "assistant", "content": answer}],
    }


async def _stream_general_qa(
    client: AsyncOpenAI,
    gpt_messages: list,
    callback: StreamCallback,
) -> str:
    """GPT 스트리밍으로 토큰마다 callback 을 호출하고 전체 텍스트를 반환한다."""
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

logger = logging.getLogger(__name__)

_GREETING_RESPONSES = [
    "안녕하세요 사장님! 😊 저는 비즈몽 AI 상담사입니다.\n\n"
    "궁금한 게 있으시면 편하게 물어보세요!\n\n"
    "**할 수 있는 것들**\n"
    "• 내 사업장에 맞는 정책자금 진단\n"
    "• 조건 바꿨을 때 점수 시뮬레이션\n"
    "• 특정 공고·제도 설명\n"
    "• 동종업계 비교 통계",
]

_SYSTEM_PROMPT_GENERAL = (
    "당신은 대한민국 중소기업·소상공인 정책자금 전문 상담사 비즈몽입니다.\n"
    "사용자의 질문에 대해 친절하고 간결하게 답변하세요.\n"
    "- 재무·회계·정책 용어 설명은 쉬운 말로 풀어서 설명하세요.\n"
    "- 모르거나 불확실한 내용은 단정하지 말고 '정확한 내용은 담당 기관에 문의하세요'라고 안내하세요.\n"
    "- 답변은 3~5문장 이내로 짧게 유지하세요.\n"
    "- 정책자금 진단이 필요하면 '진단 요청'을 해달라고 안내하세요."
)


async def chitchat_node(
    state: dict,
    client: AsyncOpenAI | None = None,
) -> dict:
    """인사/잡담 또는 일반 개념 질문에 응답한다.

    State 입력:
        current_agent: "greeting" | "general_qa"
        messages: 대화 히스토리
        biz_info: 사업장 기본정보 (선택)
    State 출력:
        messages: assistant 응답 추가
    """
    current_agent: str = state.get("current_agent", "greeting")
    messages: list = state.get("messages") or []
    biz_info: dict = state.get("biz_info") or {}
    biz_name: str = biz_info.get("biz_name", "")

    # ── greeting: LLM 없이 바로 응답 ──────────────────────────────────────
    if current_agent == "greeting":
        greeting = _GREETING_RESPONSES[0]
        if biz_name:
            greeting = greeting.replace("사장님!", f"{biz_name} 사장님!")
        logger.info("[chitchat] greeting → 규칙 기반 응답")
        return {
            "messages": messages + [{"role": "assistant", "content": greeting}],
        }

    # ── general_qa: GPT 1회 직접 답변 ────────────────────────────────────
    last_msg = _get_last_user_message(messages)
    if not last_msg:
        return {
            "messages": messages + [
                {"role": "assistant", "content": "질문을 입력해 주세요."}
            ],
        }

    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)

    # 대화 히스토리 최근 6턴만 포함 (맥락 유지, 비용 절약)
    history = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    history = history[-12:]  # user+assistant 쌍으로 최대 6턴

    gpt_messages = [{"role": "system", "content": _SYSTEM_PROMPT_GENERAL}] + history

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=gpt_messages,
            temperature=0.3,
            max_tokens=400,
        )
        answer = response.choices[0].message.content.strip()
        logger.info("[chitchat] general_qa → GPT 직접 응답 (%d chars)", len(answer))
    except Exception as exc:
        logger.warning("[chitchat] GPT 호출 실패: %s", exc)
        answer = "죄송합니다, 잠시 오류가 발생했습니다. 다시 시도해 주세요."

    return {
        "messages": messages + [{"role": "assistant", "content": answer}],
    }


def _get_last_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
