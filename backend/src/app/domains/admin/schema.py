# src/app/domains/admin/schema.py
"""관리자 API Pydantic 스키마 (admin.md)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminLoginRequest(BaseModel):
    """토큰 발급용 (명세 외 운영 편의)."""

    login_id: str = Field(..., min_length=1, description="관리자 로그인 ID")
    password: str = Field(..., min_length=1, description="평문 비밀번호")


class AdminLoginResponseData(BaseModel):
    admin_token: str
    admin_id: str
    name: str
    role: str
    expires_at: str


class PolicyCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., max_length=255)
    category: str = Field(..., max_length=50, description="지원 분류·유형 코드 (예: EXPORT)")
    content: str = Field(..., description="상세 모집 요강 (원문)")
    target_region: str = Field(..., max_length=50, description="예: NATIONWIDE")
    apply_start_date: date | None = None
    apply_end_date: date | None = None


class PolicyCreateResponseData(BaseModel):
    policy_id: str
    created_at: str


class PolicyPatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(None, max_length=255)
    apply_end_date: date | None = None
    content: str | None = None


class ContentPublishRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., max_length=255)
    body_html: str = Field(..., description="HTML 본문")
    thumbnail_url: str | None = None
    is_published: bool = True


class ContentPublishResponseData(BaseModel):
    content_id: str


class ContentPatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(None, max_length=255)
    body_html: str | None = None
    thumbnail_url: str | None = None
    is_published: bool | None = None


class ChatMonitorItem(BaseModel):
    session_id: str
    user_msg: str
    ai_res: str
    timestamp: str


class ChatMonitorResponseData(BaseModel):
    items: list[ChatMonitorItem]


class DashboardStatsData(BaseModel):
    new_users_today: int
    active_chats_today: int
    popular_policies: list[dict[str, Any]]


class AuditLogItem(BaseModel):
    admin_id: str
    action: str
    target: str | None
    created_at: str


class BatchStatusItem(BaseModel):
    job_id: str
    job_name: str
    last_run: str | None
    status: str
    total_count: int | None = None
    processed_count: int | None = None
    success_count: int | None = None
    fail_count: int | None = None
    duration_ms: int | None = None
    next_run: str | None = None


class BatchDetailData(BaseModel):
    job_id: str
    raw_log: str


class AdminUserItem(BaseModel):
    user_id: str
    name: str
    email: str
    status: str = Field(..., description="계정 상태 코드 (예: active, DELETED)")
    is_active: bool
    created_at: str


class AdminUserListData(BaseModel):
    items: list[AdminUserItem]
    total_count: int
    total_pages: int


class CorrectionNoteRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    feedback_id: str
    question_pattern: str = Field(..., min_length=1)
    expected_answer: str = Field(..., min_length=1)
    applies_to_agent: str = Field(default="ALL")
    is_active: bool = True
