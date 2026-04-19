# src/app/agents/biz_mong/state.py
"""BizMong 멀티 에이전트 공유 상태(State) 정의.

설계 원칙:
  - next_node 문자열 필드 제거 → LangGraph Command(goto=...) 패턴으로 라우팅을 처리한다.
  - thread_id = ChatRoom.id 로 MemorySaver가 대화방 단위의 맥락을 유지한다.
  - pending_intent: 시뮬레이터 가드 로직에서 진단이 선행 실행된 뒤 복귀할 의도를 저장한다.

State 필드 갱신 규칙 (LangGraph):
  - 노드가 반환하는 dict 는 기존 state 위에 merge(shallow-overwrite) 된다.
  - messages 필드만 add_messages reducer 로 append 된다.
"""

from __future__ import annotations

from typing import Annotated, Any, List, Optional

from langgraph.graph.message import add_messages


class BizMongState(dict):
    """LangGraph StateGraph 에서 노드 간 데이터를 주고받는 전역 상태.

    TypedDict 가 아닌 dict 서브클래스를 사용하는 이유:
      LangGraph 1.x 에서 TypedDict 선언은 static type-hint 용도이며, 런타임에서
      실제 state 는 일반 dict 처럼 동작한다. 필드 명세는 아래 __annotations__ 로 관리한다.

    사용법:
        state["biz_info"] = {...}  # dict 접근
        state.get("diagnosis_report") or {}  # 안전 접근
    """

    # ── 기본: 채팅 기록 및 식별자 ─────────────────────────────────────────
    messages: Annotated[list, add_messages]
    user_id: str
    business_id: str
    room_id: str           # ChatRoom.id → LangGraph thread_id 로 활용

    # ── 데이터: DB 모델 기반 정보 ────────────────────────────────────────
    biz_info: dict         # Business 모델: 상호명, 지역, 설립일, 특허/벤처 여부 등
    financial_data: dict   # BusinessFinancialSnapshot: 매출, 인원, 부채, 체납 여부 등

    # ── 프로세스: 에이전트 작업 공간 ────────────────────────────────────
    current_agent: str                # ["diagnosis", "simulator", "rag", "stats"]
    candidate_policies: List[dict]    # Hard Filter 통과 정책 목록
    diagnosis_report: dict            # {score, reason, advice, ranked_policies}
    simulation_report: dict           # {virtual_state, diff, benefit_amount, insights}
    stats_insight: dict               # {market_trend, peer_comparison, percentile}

    # ── 제어 ──────────────────────────────────────────────────────────────
    is_error: bool
    error_message: str
    pending_intent: Optional[str]     # "simulator" → 진단 완료 후 시뮬레이터 복귀 의도


# ── 초기 상태 팩토리 ─────────────────────────────────────────────────────────


def make_initial_state(
    *,
    user_id: str,
    business_id: str,
    room_id: str,
    first_message: str,
) -> dict[str, Any]:
    """새 대화 시작 시 초기 상태를 생성한다.

    Args:
        user_id: 로그인 사용자 UUID 문자열
        business_id: 조회할 사업장 UUID 문자열
        room_id: ChatRoom.id — LangGraph thread_id 로 활용
        first_message: 사용자의 첫 번째 메시지 텍스트
    """
    return {
        "messages": [{"role": "user", "content": first_message}],
        "user_id": user_id,
        "business_id": business_id,
        "room_id": room_id,
        "biz_info": {},
        "financial_data": {},
        "current_agent": "",
        "candidate_policies": [],
        "diagnosis_report": {},
        "simulation_report": {},
        "stats_insight": {},
        "is_error": False,
        "error_message": "",
        "pending_intent": None,
    }
