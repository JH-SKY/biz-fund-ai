"""채팅 도메인의 외부 의존성(AI/LLM) 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod
import uuid
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.app.domains.chat.exception import ai_service_unavailable


class LLMResponse(BaseModel):
    """LLM 응답 표준 모델."""

    content: str = Field(..., description="AI가 생성한 답변 본문")
    referenced_policy_ids: list[str] = Field(
        default_factory=list,
        description="참고 정책 ID 목록",
    )
    trace_id: str | None = Field(None, description="외부 호출 추적 ID")
    total_cost: float | None = Field(None, description="추정 비용(USD)")


class ILLMEngine(ABC):
    """채팅 서비스가 사용하는 LLM 엔진 인터페이스."""

    @abstractmethod
    async def generate_reply(
        self,
        session_id: str,
        user_message: str,
        business_context: dict[str, Any],
    ) -> LLMResponse:
        """사용자 질문에 대한 답변을 생성한다."""

    @abstractmethod
    async def summarize_title(self, messages: list[str]) -> str:
        """최근 대화 내용을 짧은 제목으로 요약한다."""


class MockLLMEngine(ILLMEngine):
    """초기 개발용 Mock 엔진."""

    async def generate_reply(
        self,
        session_id: str,
        user_message: str,
        business_context: dict[str, Any],
    ) -> LLMResponse:
        return LLMResponse(
            content=(
                "사장님 현재 사업장 정보를 보니 청년추가채용장려금 대상일 가능성이 있습니다. "
                "자세한 정보를 원하시면 추가 질문을 남겨 주세요."
            ),
            referenced_policy_ids=[],
            trace_id=f"mock-trace-{session_id}",
            total_cost=0.00123456,
        )

    async def summarize_title(self, messages: list[str]) -> str:
        return "IT 창업 지원사업 문의"


class OpenAILLMEngine(ILLMEngine):
    """OpenAI Responses API 기반 실제 채팅 엔진."""

    def __init__(
        self,
        *,
        api_key: str,
        chat_model: str = "gpt-4o-mini",
        title_model: str = "gpt-4o-mini",
    ) -> None:
        self._api_key = api_key
        self._chat_model = chat_model
        self._title_model = title_model
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def generate_reply(
        self,
        session_id: str,
        user_message: str,
        business_context: dict[str, Any],
    ) -> LLMResponse:
        client = self._require_client()
        try:
            response = await client.responses.create(
                model=self._chat_model,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "당신은 Biz-Fund-AI의 정책자금 상담 도우미입니다. "
                                    "한국 소상공인과 중소기업 사용자를 대상으로, 확실하지 않은 내용은 단정하지 말고 "
                                    "추가 확인이 필요한 항목을 분명히 구분해서 설명하세요. "
                                    "답변은 실무적으로 도움이 되도록 간결하게 작성하고, 필요하면 다음 행동을 2~3단계로 제안하세요."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    f"세션 ID: {session_id}\n"
                                    f"사업장 정보: {self._render_business_context(business_context)}\n"
                                    f"질문: {user_message}"
                                ),
                            }
                        ],
                    },
                ],
            )
        except Exception:
            raise ai_service_unavailable()

        return LLMResponse(
            content=self._extract_text(response) or "답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            referenced_policy_ids=[],
            trace_id=getattr(response, "id", f"openai-chat-{uuid.uuid4()}"),
            total_cost=None,
        )

    async def summarize_title(self, messages: list[str]) -> str:
        client = self._require_client()
        joined_messages = "\n".join(f"- {message}" for message in messages[-5:])
        try:
            response = await client.responses.create(
                model=self._title_model,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "대화 내용을 20자 안팎의 짧은 한국어 제목으로 요약하세요. "
                                    "따옴표 없이 제목만 반환하세요."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": joined_messages}],
                    },
                ],
            )
        except Exception:
            raise ai_service_unavailable()

        title = (self._extract_text(response) or "").strip()
        return title or "새 상담"

    def _require_client(self) -> AsyncOpenAI:
        if self._client is None or not self._api_key:
            raise ai_service_unavailable()
        return self._client

    @staticmethod
    def _render_business_context(business_context: dict[str, Any]) -> str:
        if not business_context:
            return "사업장 정보 없음"
        parts = []
        for key, value in business_context.items():
            if value in (None, "", []):
                continue
            parts.append(f"{key}={value}")
        return ", ".join(parts) if parts else "사업장 정보 없음"

    @staticmethod
    def _extract_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        chunks: list[str] = []
        for item in getattr(response, "output", None) or []:
            for content in getattr(item, "content", None) or []:
                value = getattr(content, "text", None)
                if isinstance(value, str) and value.strip():
                    chunks.append(value.strip())
        return "\n".join(chunks).strip()
