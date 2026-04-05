"""채팅 도메인 외부 의존성(AI/LLM) 인터페이스."""

from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """
    LLM 엔진의 응답 규격입니다.
    비유: 배달원(LLM)이 가져온 '배달 완료 보고서'와 같습니다.
    """
    content: str = Field(..., description="AI가 생성한 답변 본문")
    referenced_policy_ids: List[str] = Field(default_factory=list, description="RAG로 검색된 참고 정책 ID 목록")
    trace_id: Optional[str] = Field(None, description="LangSmith 등 모니터링을 위한 추적 ID")
    total_cost: Optional[float] = Field(None, description="해당 요청에 소요된 추정 비용 (USD)")


class ILLMEngine(ABC):
    """
    비즈몽 LLM / RAG 엔진의 인터페이스입니다.
    설계 의도: 구체적인 AI 모델(GPT-4, Claude 등)에 의존하지 않고 교체 가능하도록 추상화합니다.
    """

    @abstractmethod
    async def generate_reply(
        self,
        session_id: str,
        user_message: str,
        business_context: Dict[str, Any], # dict -> Dict[str, Any]로 구체화
    ) -> LLMResponse:
        """
        1. RAG(검색 증강 생성)를 활용하여 사용자 질문에 대한 답변을 생성합니다.
        - session_id: 대화 맥락 유지를 위한 키
        - business_context: 사장님의 업종, 매출 등 맞춤형 답변을 위한 정보
        """
        pass

    @abstractmethod
    async def summarize_title(self, messages: List[str]) -> str:
        """
        2. 전체 대화 내용을 바탕으로 상담 목록에 표시할 짧은 제목을 요약합니다.
        """
        pass


class MockLLMEngine(ILLMEngine):
    """
    초기 개발 및 유닛 테스트용 Mock 구현체입니다.
    실제 AI 호출 없이 정해진 응답을 반환하여 개발 속도를 높입니다.
    """

    async def generate_reply(
        self,
        session_id: str,
        user_message: str,
        business_context: Dict[str, Any],
    ) -> LLMResponse:
        """가상의 AI 답변을 즉시 반환합니다."""
        return LLMResponse(
            content="사장님, 현재 사업장 정보를 보니 '청년추가채용장려금' 대상이 될 가능성이 높습니다! 더 자세한 정보를 원하시면 추가로 말씀해주세요.",
            referenced_policy_ids=[],  
            trace_id=f"mock-trace-{session_id}",
            total_cost=0.00123456,
        )

    async def summarize_title(self, messages: List[str]) -> str:
        """가상의 요약 제목을 반환합니다."""
        return "IT 창업 인건비 지원 사업 문의"