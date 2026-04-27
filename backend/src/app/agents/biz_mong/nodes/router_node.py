# src/app/agents/biz_mong/nodes/router_node.py
"""Node: Router — LLM 기반 사용자 의도(Intent) 분류.

분류 결과에 따라 6개 경로 중 하나로 라우팅한다:
  - greeting:    인사·잡담 → LLM 없이 웰컴 응답
  - general_qa:  일반 설명 질문 ("이 단어 뭐야?") → GPT 직접 답변 (tools 없이)
  - diagnosis:   정책 자금 진단 (하드필터 → LLM 채점)
  - simulator:   가상 시나리오 시뮬레이션
  - rag:         특정 정책/제도에 대한 질의응답
  - stats:       동종업계 통계 비교

[설계 의도]:
  - greeting/general_qa 는 LangGraph 도구 파이프라인을 거치지 않는다.
  - 도구가 필요한 4가지(진단/시뮬/RAG/통계)만 무거운 경로로 보낸다.
  - GPT-4o-mini 로 intent 를 1~2 토큰 수준의 JSON 으로 분류한다.
  - 모호한 경우 diagnosis 를 기본값으로 사용한다.
  - intent 분류 실패 시 폴백으로 키워드 매칭을 사용한다.
"""

from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

VALID_INTENTS = frozenset(["greeting", "general_qa", "diagnosis", "simulator", "rag", "stats"])
DEFAULT_INTENT = "diagnosis"


# ═══════════════════════════════════════════════════════════════════════════════
# 노드 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def router_node(
    state: dict,
    client: AsyncOpenAI | None = None,
) -> dict:
    """사용자 메시지를 분석하여 current_agent 를 설정한다.

    반환값은 일반 dict (routing 은 conditional_edges 가 담당).

    State 입력:
        messages: 대화 히스토리
    State 출력:
        current_agent: "greeting" | "general_qa" | "diagnosis" | "simulator" | "rag" | "stats"
    """
    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)

    messages: list = state.get("messages") or []
    last_msg = _get_last_user_message(messages)

    if not last_msg:
        logger.warning("[router] 사용자 메시지 없음 → 기본값 diagnosis")
        return {"current_agent": DEFAULT_INTENT}

    # ── LLM 분류 ──────────────────────────────────────────────────────────
    intent = await _classify_intent_llm(_client, last_msg)

    # ── 폴백: 키워드 매칭 ────────────────────────────────────────────────
    if intent not in VALID_INTENTS:
        intent = _classify_by_keyword(last_msg)

    logger.info("[router] 의도 분류: '%s' → %s", last_msg[:60], intent)
    return {"current_agent": intent}


# ═══════════════════════════════════════════════════════════════════════════════
# 내부 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def _classify_intent_llm(client: AsyncOpenAI, message: str) -> str:
    """GPT-4o-mini 로 의도를 분류한다. 실패 시 빈 문자열 반환."""
    system_prompt = """사용자 메시지를 다음 6가지 의도 중 하나로 분류하세요.
반드시 아래 JSON 형식으로만 응답하세요.

[의도 분류 기준]
- greeting: 인사, 잡담, 감사, 안부 등 업무와 무관한 대화
  예: "안녕", "반가워요", "고마워", "잘 있었어요?", "오늘 날씨 어때"
- general_qa: 정책·금융·창업 관련 용어 설명, 단순 개념 질문 (검색·DB 조회 불필요)
  예: "부채비율이 뭐야?", "이자보상배율이 무슨 뜻이야?", "보증서 담보가 뭔가요?"
- diagnosis: 어떤 정책 자금을 받을 수 있는지 진단·추천 요청
  예: "어떤 지원금 받을 수 있나요?", "내 사업장에 맞는 정책 알려줘", "진단해 줘"
- simulator: 조건 변경 시 어떻게 달라지는지 시뮬레이션 요청
  예: "직원 늘리면 어떻게 돼요?", "특허 취득하면 점수가 오르나요?", "대환대출 이자 절감"
- rag: 특정 정책·제도에 대한 질의응답 (공고 내용 검색 필요)
  예: "청년 창업 패키지가 뭔가요?", "소상공인 대출 조건은?", "이 정책 신청 방법"
- stats: 동종업계 비교·시장 통계 요청
  예: "같은 업종 평균 매출은?", "우리 회사 수준이 어느 정도야?", "비슷한 업체들과 비교"

{"intent": "분류결과"}"""

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
        data = json.loads(response.choices[0].message.content)
        return data.get("intent", "").lower()
    except Exception as exc:
        logger.warning("[router] LLM 분류 실패: %s", exc)
        return ""


def _classify_by_keyword(message: str) -> str:
    """키워드 기반 폴백 의도 분류기."""
    msg = message.lower()

    greeting_kws = ["안녕", "반가워", "고마워", "감사", "잘 있었", "처음 뵙", "하이", "헬로", "hi", "hello"]
    general_qa_kws = ["뭐야", "뭔가요", "무슨 뜻", "무슨뜻", "의미가", "뭐예요", "설명해줘", "알려줘", "이게 뭐"]
    simulator_kws = ["시뮬레이션", "변경", "늘리면", "취득하면", "대환", "이자", "만약", "가정"]
    rag_kws = ["신청 방법", "신청방법", "자격 조건", "자격조건", "공고", "어디서", "어떻게 신청"]
    stats_kws = ["평균", "통계", "비교", "업계", "얼마나", "수준", "같은 업종"]

    if any(kw in msg for kw in greeting_kws):
        return "greeting"
    if any(kw in msg for kw in general_qa_kws):
        return "general_qa"
    if any(kw in msg for kw in simulator_kws):
        return "simulator"
    if any(kw in msg for kw in stats_kws):
        return "stats"
    if any(kw in msg for kw in rag_kws):
        return "rag"
    return DEFAULT_INTENT


def _get_last_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
        if hasattr(msg, "content") and getattr(msg, "type", "") == "human":
            return msg.content
    return ""
