"""비즈픽 도메인 Pydantic 스키마."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class BizPickListItem(BaseModel):
    """비즈픽 목록 조회 시 반환되는 개별 아이템 정보."""
    content_id: uuid.UUID
    title: str
    thumbnail_url: Optional[str] = None
    category: str
    view_count: int
    like_count: int
    is_liked: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BizPickListResponseData(BaseModel):
    """목록 조회 응답의 전체 데이터 구조 (페이징 정보 포함)."""
    items: List[BizPickListItem]
    total_count: int
    total_pages: int


class RelatedPolicy(BaseModel):
    """콘텐츠 상세 페이지 하단에 노출되는 연관 정책 정보."""
    id: uuid.UUID
    title: str

    model_config = ConfigDict(from_attributes=True)


class BizPickDetailResponseData(BaseModel):
    """콘텐츠 상세 조회 시 반환되는 상세 정보."""
    content_id: uuid.UUID
    title: str
    body_html: str
    author: str = "비즈업 에디터"
    view_count: int  # 상세 페이지 표시용
    like_count: int  # 상세 페이지 표시용
    is_liked: bool = False
    related_policies: List[RelatedPolicy] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TodayPickItem(BaseModel):
    """오늘의 추천 콘텐츠 (명세서 v1.0 규격 반영)."""
    content_id: uuid.UUID
    title: str

    model_config = ConfigDict(from_attributes=True)


class BizPickLikeResponseData(BaseModel):
    """좋아요(찜하기) 토글 후 반환되는 결과 데이터."""
    is_liked: bool
    total_likes: int


class CategoryItem(BaseModel):
    """카테고리 목록 조회를 위한 정보."""
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)