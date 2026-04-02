# src/app/models/policy/biz_pick.py
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.app.models.base import Base


class BizPick(Base):
    """비즈픽 콘텐츠(이슈·꿀팁). 설계서: biz_picks — 정책 ID는 본문·JSON에서 참조."""

    __tablename__ = "biz_picks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="콘텐츠 고유 식별자",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="콘텐츠 제목"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="카테고리 (세무·정책자금 등)"
    )
    content_html: Mapped[str] = mapped_column(
        Text, nullable=False, comment="HTML 본문 (관리자 API에서 그대로 저장·조회)"
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="썸네일 이미지 URL"
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="발행(공개) 여부",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="작성·발행 일시",
    )
