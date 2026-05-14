# src/app/agents/biz_mong/nodes/router_node.py
"""비즈몽 에이전트 의도(Intent) 라우터 노드.

[역할]
사용자의 마지막 메시지를 분석하여 4가지 의도 중 하나로 분류하고,
그래프가 다음에 어떤 노드로 이동할지 결정하는 routing 역할을 한다.

[분류 전략 — 2단계 폴백]
1차) GPT (gpt-4o-mini, JSON mode): 빠르고 정확한 LLM 기반 분류
2차) 키워드 매칭(_classify_by_keyword): LLM 호출 실패 시 폴백

[의도 종류]
- greeting   : 인사 및 가벼운 시작 멘트
- general_qa : 정책자금 용어 설명, 사업장 고민 상담, 진단 결과 해석
- rag        : 특정 정책 공고·지원 조건·신청 방법 등 문서 검색 필요
- stats      : 동종업계 평균 비교, 통계 수치 요청
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import time

from openai import AsyncOpenAI

from src.app.agents.biz_mong.telemetry import build_node_log
from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

VALID_INTENTS = frozenset(["greeting", "general_qa", "rag", "stats"])
DEFAULT_INTENT = "general_qa"  # LLM이 알 수 없는 의도를 반환하면 일반 QA로 폴백


async def router_node(
    state: dict,
    client: AsyncOpenAI | None = None,
) -> dict:
    """최신 사용자 메시지를 분류하여 다음 노드로 라우팅한다.

    [로직 순서]
    1. 마지막 사용자 메시지 추출 (없으면 default 의도 반환)
    2. GPT 로 의도 분류 시도
    3. 유효하지 않은 의도면 키워드 기반 폴백 분류
    4. 분류 결과(current_agent)와 node_logs 반환

    Returns:
        current_agent: 다음 노드로 전달할 의도 문자열
        node_logs    : 이 노드 실행 관측 로그
        fallback_mode: 키워드 폴백 사용 여부
    """
    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)
    started_at = datetime.now(timezone.utc)
    started_mono = time.monotonic()

    messages: list = state.get("messages") or []
    last_msg = _get_last_user_message(messages)
    if not last_msg:
        completed_at = datetime.now(timezone.utc)
        return {
            "current_agent": DEFAULT_INTENT,
            "node_logs": [
                build_node_log(
                    node_name="router",
                    sequence=1,
                    status="SUCCESS",
                    latency_ms=int((time.monotonic() - started_mono) * 1000),
                    started_at=started_at,
                    completed_at=completed_at,
                    metadata={"reason": "empty_message", "fallback": True},
                )
            ],
        }

    intent, telemetry = await _classify_intent_llm(_client, last_msg)
    fallback_reason: str | None = None
    if intent not in VALID_INTENTS:
        intent = _classify_by_keyword(last_msg)
        fallback_reason = "keyword_fallback"

    logger.info("[bizmong-router] '%s' -> %s", last_msg[:80], intent)
    completed_at = datetime.now(timezone.utc)
    return {
        "current_agent": intent,
        "node_logs": [
            build_node_log(
                node_name="router",
                sequence=1,
                status="SUCCESS",
                latency_ms=int((time.monotonic() - started_mono) * 1000),
                model_name=telemetry.get("model_name"),
                tokens_in=telemetry.get("tokens_in"),
                tokens_out=telemetry.get("tokens_out"),
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "classified_intent": telemetry.get("classified_intent"),
                    "final_intent": intent,
                    "fallback_reason": fallback_reason,
                },
            )
        ],
        "fallback_mode": "keyword" if fallback_reason else None,
        "fallback_reason": fallback_reason,
    }


async def _classify_intent_llm(
    client: AsyncOpenAI,
    message: str,
) -> tuple[str, dict]:
    """GPT 를 사용하여 사용자 메시지의 의도를 JSON 형식으로 분류한다.

    - response_format=json_object 와 temperature=0.0 을 사용해 결정론적 분류를 유도한다.
    - max_tokens=20 으로 매우 작게 설정하여 비용을 최소화한다.
    - 실패 시 빈 문자열을 반환하며, 호출 측에서 키워드 폴백을 수행한다.
    """
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
        usage = getattr(response, "usage", None)
        intent = str(payload.get("intent", "")).lower()
        return intent, {
            "model_name": "gpt-4o-mini",
            "tokens_in": getattr(usage, "prompt_tokens", None),
            "tokens_out": getattr(usage, "completion_tokens", None),
            "classified_intent": intent,
        }
    except Exception as exc:
        logger.warning("[bizmong-router] intent classification failed: %s", exc)
        return "", {
            "model_name": "gpt-4o-mini",
            "tokens_in": None,
            "tokens_out": None,
            "classified_intent": "",
        }


def _classify_by_keyword(message: str) -> str:
    """LLM 분류 실패 시 키워드 매칭으로 의도를 추정하는 폴백 함수.

    - 인사 키워드 → greeting
    - 통계/비교 키워드 → stats
    - 정책 공고/신청 키워드 → rag
    - 해당 없으면 → general_qa (기본값)
    """
    msg = message.lower()

    greeting_kws = ["안녕", "반가", "고마", "감사", "처음", "hello", "hi"]
    stats_kws = [
        "평균",
        "통계",
        "비교",
        "퍼센타일",
        "동종업계",
        "업계 평균",
        "매출",
        "매출액",
        "매입",
        "순위",
        "상위",
        "하위",
    ]
    rag_kws = [
        "공고",
        "지원조건",
        "신청방법",
        "마감",
        "신청 자격",
        "필요서류",
        "어떤 정책",
        "정책 설명",
        "정책자금",
        "지원금",
        "추천",
        "추천돼",
        "추천돼?",
        "왜 추천",
        "받을 수 있는",
        "신청 가능한",
        "맞는 정책",
        "내 사업에 맞는 정책",
        "해당되는 정책",
    ]

    if any(keyword in msg for keyword in greeting_kws):
        return "greeting"
    if any(keyword in msg for keyword in stats_kws):
        return "stats"
    if any(keyword in msg for keyword in rag_kws):
        return "rag"
    return DEFAULT_INTENT


def _get_last_user_message(messages: list) -> str:
    """메시지 목록에서 가장 최근 사용자 메시지 텍스트를 추출한다."""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
