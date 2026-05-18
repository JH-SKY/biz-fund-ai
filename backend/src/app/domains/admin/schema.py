# src/app/domains/admin/schema.py
"""Admin API Pydantic schemas."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminLoginRequest(BaseModel):
    """Admin login payload."""

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
    category: str = Field(..., max_length=50, description="정책 카테고리")
    content: str = Field(..., description="정책 상세 본문")
    agency_name: str = Field(..., max_length=100)
    support_amount: str | None = Field(None, max_length=100)
    apply_url: str | None = None
    closed_at: date | None = None


class PolicyCreateResponseData(BaseModel):
    policy_id: str
    created_at: str


class PolicyPatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=50)
    agency_name: str | None = Field(None, max_length=100)
    support_amount: str | None = Field(None, max_length=100)
    apply_url: str | None = None
    closed_at: date | None = None
    content: str | None = None


class ContentPublishRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., max_length=255)
    body_html: str = Field(..., description="HTML 본문")
    category: str = Field(..., max_length=50)
    thumbnail_url: str | None = None
    is_published: bool = True


class ContentPublishResponseData(BaseModel):
    content_id: str


class ContentPatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(None, max_length=255)
    body_html: str | None = None
    category: str | None = Field(None, max_length=50)
    thumbnail_url: str | None = None
    is_published: bool | None = None


class AiCardNewsGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    policy_url: str | None = None
    policy_id: str | None = None
    raw_text: str | None = None


class AiRelatedPoliciesRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content_body: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


class ChatMonitorItem(BaseModel):
    session_id: str
    user_id: str
    user_name: str | None = None
    user_msg: str
    ai_res: str
    agent_type: str | None = None
    timestamp: str


class ChatMonitorResponseData(BaseModel):
    items: list[ChatMonitorItem]
    total_count: int = 0
    total_pages: int = 0


class DashboardStatsData(BaseModel):
    new_users_today: int
    active_chats_today: int
    popular_policies: list[dict[str, Any]]


class AuditLogItem(BaseModel):
    audit_id: str
    admin_id: str
    admin_name: str | None = None
    action: str
    target: str | None
    ip_address: str | None = None
    diff: dict | None = None
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
    status: str = Field(..., description="계정 상태 코드")
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
