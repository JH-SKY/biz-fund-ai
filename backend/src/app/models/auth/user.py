# src/app/models/auth/user.py
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.models.business.business import Business
    from src.app.models.chat.chat import ChatRoom
    from src.app.models.chat.chat_log import ChatLog
    from src.app.models.system.lead_request import LeadRequest
    from src.app.models.system.notification import Notification

from sqlalchemy import Boolean, String, TIMESTAMP, Text, text, Enum as sqlalchemy_Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


# 1. 소셜 제공자 타입 정의 (개념 연결):
# - KAKAO, NAVER 등 허용된 값만 들어오도록 제한하여 데이터 무결성 확보
class SocialProvider(str, Enum):
    KAKAO = "KAKAO"
    NAVER = "NAVER"


class User(Base):
    __tablename__ = "users"

    # 2. PK 및 필수 식별 정보 (흐름 파악):
    # - id: 보안과 확정성을 위해 순차적 숫자 대신 UUID 사용
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="사용자 고유 식별자",
    )

    # - email: 소셜 연동 핵심 정보 (로그인 계정)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    # 3. 사용자 프로필 정보 (설계 의도):
    # - name: 실명 (서류 자동 작성용)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # - phone: 알림톡 수신용 (선택 사항)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # - nickname: 서비스 활동명 (선택 사항)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 4. 상태 및 소셜 연동 관리 (기능 연결):
    # - status: active/deleted 상태 플래그
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # - social_id: 소셜 앱 내부 고정 ID
    social_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # - social_provider: 가입 경로 구분 (ENUM 사용)
    social_provider: Mapped[SocialProvider] = mapped_column(
        sqlalchemy_Enum(SocialProvider), nullable=False
    )
    # - profile_image_url: 소셜 프로필 이미지
    profile_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 5. 시스템 및 마케팅 관리 (사고 과정):
    # - is_active: 서비스 이용 가능 여부
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # - marketing_agreed_at: 정책 알림 푸시 법적 근거 데이터
    marketing_agreed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    # - created_at: 가입 시점 기록 (유입 분석용)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    businesses: Mapped[list["Business"]] = relationship(
        "Business", back_populates="user"
    )
    chat_rooms: Mapped[list["ChatRoom"]] = relationship(
        "ChatRoom", back_populates="user"
    )
    chat_logs: Mapped[list["ChatLog"]] = relationship(
        "ChatLog", back_populates="user"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    lead_requests: Mapped[list["LeadRequest"]] = relationship(
        "LeadRequest", back_populates="user"
    )
