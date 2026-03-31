# src/app/models/business/document.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.models.business.business import Business

from sqlalchemy import Date, ForeignKey, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.base import Base


class Document(Base):
    """디지털 서류함. 설계서: documents."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="서류 고유 식별자",
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        comment="소속 사업장 ID (businesses.id)",
    )
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="서류 종류 (사업자등록증 등)"
    )
    file_url: Mapped[str] = mapped_column(
        Text, nullable=False, comment="저장소(S3 등) 파일 경로"
    )
    issued_at: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="서류 발급 일자"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="업로드 일시",
    )

    business: Mapped["Business"] = relationship("Business", back_populates="documents")
