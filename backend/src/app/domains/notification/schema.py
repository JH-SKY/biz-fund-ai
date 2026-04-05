"""알림(Notification) 도메인 Pydantic 스키마."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    """
    알림 목록 조회를 위한 개별 아이템 스키마.
    
    1. 식별자: noti_id는 클라이언트에서 리스트 렌더링 시 key 값으로 사용됩니다.
    2. 콘텐츠: title과 content(기존 message)를 분리하여 UI에서 가독성을 높입니다.
    3. 이동 경로: deep_link가 있을 경우 클릭 시 해당 메뉴로 즉시 이동합니다.
    """
    noti_id: str = Field(..., description="알림 고유 식별자 (UUID String)")
    type: str = Field(..., description="알림 유형 (예: POLICY_MATCH, CHAT_ANSWER)")
    title: str = Field(..., description="알림 제목") 
    content: str = Field(..., description="알림 상세 본문")
    is_read: bool = Field(..., description="읽음 상태 여부")
    deep_link: Optional[str] = Field(None, description="클릭 시 이동할 앱/웹 내부 경로")
    created_at: datetime = Field(..., description="알림 생성 일시")


class NotificationListResponseData(BaseModel):
    """알림 목록 응답 데이터 구조 (페이징 포함)."""
    items: List[NotificationItem]
    total_count: int = Field(..., description="조건에 맞는 전체 알림 개수")


class UnreadCountResponseData(BaseModel):
    """미확인 알림 개수 응답."""
    unread_count: int = Field(..., description="아직 읽지 않은 알림의 총 합계")


class ReadNotificationResponseData(BaseModel):
    """개별 알림 읽음 처리 결과."""
    noti_id: str
    is_read: bool


class NotificationSettingsResponseData(BaseModel):
    """
    사용자 알림 설정 상태 조회 응답.
    
    각 필드는 사용자가 특정 카테고리의 알림을 받을지 말지 결정하는 '수신함 스위치' 상태입니다. [cite: 2026-03-05]
    """
    push_enabled: bool = Field(True, description="전체 푸시 알림 허용 여부")
    marketing_enabled: bool = Field(False, description="마케팅 정보 수신 동의 여부")
    policy_update_enabled: bool = Field(True, description="맞춤 정책 업데이트 알림 여부")
    chat_answer_enabled: bool = Field(True, description="AI 상담(비즈몽) 답변 완료 알림 여부")


class UpdateNotificationSettingsRequest(BaseModel):
    """
    알림 설정 수정을 위한 요청 스키마.
    
    Optional로 설정하여 변경을 원하는 항목만 선택적으로 보낼 수 있는 '부분 수정' 방식입니다. [cite: 2026-03-05]
    """
    push_enabled: Optional[bool] = None
    marketing_enabled: Optional[bool] = None
    policy_update_enabled: Optional[bool] = None
    chat_answer_enabled: Optional[bool] = None