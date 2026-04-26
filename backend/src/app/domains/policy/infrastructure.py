# src/app/domains/policy/infrastructure.py
"""정책 공고 수집 인프라 계층.

설계 원칙:
  Infrastructure 계층은 파일 파싱(PDF)·외부 API 호출 등
  순수 "기술적 I/O"만 담당하며, 비즈니스 판단은 Service 계층에 위임합니다.

파서 전략:
  PDF 텍스트 파싱만 지원합니다.
  스캔본(이미지 PDF), HWP, HWPX 등 다른 형식은 파싱하지 않습니다.
  파싱 실패 시 Vision 폴백 없이 즉시 ValueError를 발생시킵니다.
"""

from __future__ import annotations

import html as html_std
import io
import logging
import re
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

_MAGIC_PDF = b"%PDF"


# ─────────────────────────────────────────────────────────────────────────────
# [유틸리티] HTML 태그 제거 및 텍스트 정제
# ─────────────────────────────────────────────────────────────────────────────

def clean_html_text(raw: str) -> str:
    """기업마당 API의 bsnsSumryCn(공고 요약) 필드에서 HTML 태그를 제거하고 순수 텍스트를 반환합니다.

    HTML 태그가 섞여 들어가면 GPT가 태그 분석에 토큰을 낭비하고 구조화 성능이 떨어집니다.
    파싱이 완전 실패했을 때 Fallback 원문으로 쓰이기 때문에 반드시 정제해야 합니다.
    """
    if not raw:
        return ""

    text = html_std.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# [파서] PDF 텍스트 파서
# ─────────────────────────────────────────────────────────────────────────────

class PDFDocumentParser:
    """PyMuPDF(fitz)를 활용한 PDF 텍스트 파서.

    텍스트 추출에 실패하거나 추출량이 너무 적으면 ValueError를 발생시킵니다.
    스캔본(이미지 PDF) 폴백은 지원하지 않습니다.
    """

    async def parse(self, content: bytes) -> dict[str, Any]:
        try:
            with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
                text = "".join(page.get_text() for page in doc)
        except Exception as exc:
            raise ValueError(f"PDF 파싱 실패: {exc}") from exc

        if len(text.strip()) < 100:
            raise ValueError(
                f"PDF에서 유의미한 텍스트를 추출하지 못했습니다. ({len(text.strip())}자 — 스캔본이거나 이미지 전용 PDF일 가능성)"
            )

        logger.debug("  [PDF] 텍스트 추출 완료 (%d자)", len(text))
        return {"type": "text", "data": text}


# ─────────────────────────────────────────────────────────────────────────────
# [팩토리] 파서 생성
# ─────────────────────────────────────────────────────────────────────────────

class DocumentParserFactory:
    """파일의 Magic Number를 확인하고 PDF 파서를 반환합니다.

    PDF 이외의 파일 형식(HWP, HWPX, 이미지 등)은 지원하지 않으며,
    즉시 ValueError를 발생시킵니다.
    """

    @staticmethod
    def from_content(content: bytes, *, filename_hint: str = "") -> PDFDocumentParser:
        if content[:4] != _MAGIC_PDF:
            raise ValueError(
                f"PDF 형식이 아닌 파일입니다. PDF만 파싱 가능합니다. "
                f"(hint={filename_hint or '없음'}, header={content[:4].hex()})"
            )
        logger.debug("  [PDF] Magic Number 확인 → PDFDocumentParser")
        return PDFDocumentParser()
