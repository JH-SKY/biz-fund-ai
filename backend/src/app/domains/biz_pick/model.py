"""비즈픽 도메인 SQLAlchemy 모델 — biz_picks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import TIMESTAMP, Boolean, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.app.database.postgres.base import Base


class BizPick(Base):
    """biz_picks 테이블 — 사용자에게 도움을 주는 '꿀팁' 콘텐츠 보관소."""

    __tablename__ = "biz_picks"

    # 1. 식별자 및 기본 정보
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="콘텐츠 고유 ID",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="콘텐츠 제목 (리스트 노출용)"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="카테고리 (세무·정책자금·노무 등)",
    )

    # 2. 본문 및 미디어
    # [비유] content_html은 '편지 내용'이고, thumbnail_url은 '편지 봉투의 사진'입니다.
    content_html: Mapped[str] = mapped_column(
        Text, nullable=False, comment="HTML 본문 (Rich Text 에디터 원본)"
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="썸네일 이미지 주소"
    )

    # 3. 노출 및 통계 상태
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        comment="공개 여부 (False면 임시 저장/비공개)",
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="누적 조회수",
    )
    like_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="좋아요 수 (인기순 정렬에 활용)",
    )

    # 4. 관리 정보
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="발행 시점",
    )
