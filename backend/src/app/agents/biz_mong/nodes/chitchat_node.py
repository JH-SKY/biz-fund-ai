# src/app/agents/biz_mong/nodes/chitchat_node.py
"""비즈몽 일반 상담(chitchat / general_qa) 노드.

[역할]
- greeting: 미리 작성된 환영 메시지를 반환 (LLM 호출 없음 → 비용 0원)
- general_qa: 정책자금 용어 설명, 사업장 고민 상담, 진단 결과 해석 등
  GPT (gpt-4o-mini) 가 최근 12개 메시지 히스토리를 보고 답변 생성

[스트리밍 지원]
stream_callback 이 전달되면 청크 단위로 스트림 전송.
API 응답에서 스트리밍이 활성화되면 usage 정보를 얻을 수 없으므로
토큰 사용량은 None 으로 기록된다.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Awaitable, Callable

from openai import AsyncOpenAI

from src.app.agents.biz_mong.telemetry import build_node_log
from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

PROMPT_VERSION_GENERAL = "bizmong-general-v1"  # 프롬프트 버전 추적용 (변경 시 올려야 함)

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
    """일반 상담 노드 — 인사 응답 또는 GPT 기반 QA 답변을 생성한다.

    [로직 순서]
    1. current_agent == "greeting" 이면 미리 정의된 환영 메시지 즉시 반환
    2. 마지막 사용자 메시지 없으면 안내 메시지 반환
    3. 최근 12개 메시지 히스토리 + 시스템 프롬프트로 GPT 답변 생성
       - stream_callback 있으면 스트리밍, 없으면 일반 호출
    4. 오류 발생 시 안내 메시지 반환 (서비스 중단 없이 graceful 처리)

    Args:
        state           : 현재 그래프 상태
        client          : OpenAI AsyncClient (없으면 자동 생성)
        stream_callback : 청크를 받을 비동기 콜백 (스트리밍 API용)
    """
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
    # 최근 12개 메시지만 컨텍스트로 사용 (토큰 절약, 오래된 대화 제외)
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
    """GPT 응답을 스트리밍으로 받아 콜백에 전달하고, 전체 텍스트를 반환한다.

    스트리밍 모드에서는 usage 정보를 얻을 수 없어 토큰 비용 추적이 불가하다.
    """
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
            await callback(delta)  # 청크 단위로 클라이언트에 즉시 전송
    return "".join(collected)


def _get_last_user_message(messages: list) -> str:
    """메시지 목록에서 가장 최근 사용자 메시지 텍스트를 추출한다."""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
