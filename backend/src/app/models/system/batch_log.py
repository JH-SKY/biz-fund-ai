# src/app/models/system/batch_log.py
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.app.models.base import Base


class BatchLog(Base):
    """배치·크롤링 작업 이력. 설계서: batch_logs."""

    __tablename__ = "batch_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="배치 실행 로그 고유 식별자",
    )
    job_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="작업 명칭 (예: POLICY_CRAWLING)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="실행 상태 (SUCCESS·FAILED·RUNNING 등)"
    )
    total_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="처리 대상 전체 건수"
    )
    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="성공 반영 건수"
    )
    fail_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="실패 건수"
    )
    error_details: Mapped[Optional[Any]] = mapped_column(
        JSONB, nullable=True, comment="오류 상세 (JSON)"
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="작업 시작 일시",
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True, comment="작업 종료 일시"
    )
