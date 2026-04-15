# src/app/domains/policy/infrastructure.py
"""PDF 추출 및 OpenAI 기반 데이터 구조화 구현체."""

import io
import json
from typing import Any

import fitz  # PyMuPDF
import httpx
from openai import AsyncOpenAI

from src.app.core.config import OPENAI_API_KEY
from src.app.domains.policy.interfaces import IPolicyEnricher


class OpenAIPolicyEnricher(IPolicyEnricher):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def _download_pdf_text(self, pdf_url: str) -> str:
        """PDF 주소에서 텍스트를 추출합니다."""
        async with httpx.AsyncClient() as client:
            response = await client.get(pdf_url, timeout=30.0)
            response.raise_for_status()

            with fitz.open(stream=io.BytesIO(response.content), filetype="pdf") as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
            return text

    async def extract_and_structure(
        self, pdf_url: str, original_summary: str
    ) -> dict[str, Any]:
        # 1. 원문 추출
        raw_text = await self._download_pdf_text(pdf_url)

        # 2. AI에게 구조화 요청 (Prompt 설계)
        system_prompt = """
        너는 대한민국 정부의 정책 공고문을 분석하여 시스템 매칭용 JSON 데이터로 변환하는 전문가야.
        제공된 공고문 원문(Text)을 분석하여 아래 JSON 구조에 맞춰 응답해줘.
        
        {
            "target_logic": {
                "sectors": ["업종리스트"],
                "min_revenue": "최소매출조건(숫자만)",
                "max_debt_ratio": "최대부채비율(숫자만)",
                "target_age": "대상연령",
                "region_restricted": "지역제한여부(bool)"
            },
            "bonus_logic": {
                "items": [
                    {"name": "가점항목명", "point": 점수}
                ]
            },
            "ai_summary": "사장님이 이해하기 쉬운 3줄 요약",
            "ai_full_explanation": "공고의 핵심 내용을 친절하게 풀어낸 설명"
        }
        """

        user_prompt = f"원본 요약: {original_summary}\n\n공고문 원문: {raw_text[:6000]}"  # 토큰 제한 고려

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        result["content_raw"] = raw_text
        return result
