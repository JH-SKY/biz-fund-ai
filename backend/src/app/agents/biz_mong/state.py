# src/app/agents/biz_mong/state.py
"""비즈몽 LangGraph 에이전트의 공유 상태(State) 정의.

LangGraph 는 각 노드가 상태 딕셔너리를 입력받아 변경된 부분만 반환하는 구조.
BizMongState 는 그 구조의 타입 힌트 역할을 하며, 실제 값은 일반 dict 로 전달된다.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph.message import add_messages


class BizMongState(dict):
    """비즈몽 상담 흐름의 LangGraph 상태 컨테이너.

    각 필드 설명:
        messages       : 대화 히스토리 (add_messages 리듀서로 누적됨)
        user_id        : 요청한 사용자 UUID 문자열
        business_id    : 사용자의 사업장 UUID 문자열
        room_id        : 채팅 세션(방) UUID 문자열 — LangGraph thread_id 로 사용
        biz_info       : 사업장 기본 정보 (biz_name, ksic_code, region_sido 등)
        financial_data : 재무 스냅샷 데이터 (annual_revenue, employee_count 등)
        current_agent  : router_node 가 결정한 의도 (greeting | general_qa | rag | stats)
        stats_insight  : stats_node 결과 — 동종업계 비교 인사이트
        is_error       : 처리 중 오류 발생 여부
        error_message  : 오류 상세 메시지
    """

    messages = add_messages  # 메시지 리스트는 덮어쓰지 않고 누적(append) 방식으로 업데이트
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
    """새로운 채팅 세션의 초기 상태 딕셔너리를 생성한다.

    기존 thread_id(room_id)에 대한 상태가 없을 때(첫 메시지)만 호출된다.
    이후 메시지부터는 messages 키만 추가하면 된다.
    """
    return {
        "messages": [{"role": "user", "content": first_message}],
        "user_id": user_id,
        "business_id": business_id,
        "room_id": room_id,
        "biz_info": {},          # 이후 get_biz_info 툴이 채워넣음
        "financial_data": {},    # 이후 재무 조회 툴이 채워넣음
        "current_agent": "",     # router_node 가 결정
        "stats_insight": {},     # stats_node 가 채워넣음
        "is_error": False,
        "error_message": "",
    }
