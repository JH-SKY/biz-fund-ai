# src/app.domains/notification/model.py
"""알림 도메인 SQLAlchemy 모델 — notifications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.domains.auth.model import User
    from src.app.domains.business.model import Business

from sqlalchemy import Boolean, ForeignKey, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.database.postgres.base import Base


class Notification(Base):
    """
    notifications 테이블 — 사용자 알림 발송 이력.
    
    1. 식별자: UUID를 사용하여 분산 환경에서도 충돌 없는 ID를 생성합니다.
    2. 관계: 특정 유저(User)와 사업장(Business)에 종속된 구조를 가집니다.
    3. 상태 관리: 읽음(is_read) 여부와 생성 시점을 관리하여 클라이언트의 뱃지 UI 등에 활용됩니다.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="알림 고유 식별자 (자동 생성되는 우편물 번호입니다)",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="수신 사용자 ID (누구에게 보낼지 정하는 수신인 주소입니다)",
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=True,
        comment="연관 사업장 ID (특정 가게와 관련된 알림일 경우에만 기록합니다)",
    )
    type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        comment="알림 유형 (예: POLICY_MATCH, CHAT_ANSWER 등 유형별 아이콘 구분에 사용)"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=text("'새로운 알림'"),
        comment="알림 제목 (사용자에게 노출될 큰 글씨의 요약 내용입니다)"
    ) # 명세서 요구사항에 따라 title 컬럼 추가
    message: Mapped[str] = mapped_column(
        Text, 
        nullable=False, 
        comment="알림 본문 (상세한 안내 문구가 담기는 그릇입니다)"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="읽음 여부 (사용자가 확인했는지 체크하는 확인 도장입니다)",
    )
    link_url: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        comment="이동 URL (클릭 시 앱/웹 내 특정 페이지로 안내하는 지름길입니다)"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), # 실무급: 타임존을 포함하여 정확한 발송 시점을 기록합니다
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="알림 생성 일시",
    )

    # Relationship 설정: SQL 조인(Join) 없이도 객체 지향적으로 데이터를 가져오는 연결 통로입니다. [cite: 2026-03-05]
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    business: Mapped[Optional["Business"]] = relationship(
        "Business", back_populates="notifications"
    )