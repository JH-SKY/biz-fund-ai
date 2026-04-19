# src/app/domains/policy/infrastructure.py
"""정책 공고 수집 인프라 계층.

설계 원칙 (.cursorrules §1):
  Infrastructure 계층은 파일 파싱(PDF, HWP, 이미지)·외부 API 호출 등
  순수 "기술적 I/O"만 담당하며, 비즈니스 판단은 Service 계층에 위임합니다.

바이너리 우선 파서 전략 (.cursorrules §2.1):
  기업마당 API의 printFlpthNm 은 URL만으로는 내부 파일 형식을 알 수 없습니다.
  따라서 파일을 먼저 다운로드한 뒤, 첫 몇 바이트(Magic Number)를 읽어 형식을 확정합니다.

최적화 전략 (2026.04 적용):
  - HWP 텍스트 추출 실패 시 무의미하게 GPT Vision으로 보내던 폴백(Fallback) 제거 (비용 낭비 차단).
  - 혼란을 야기하는 미사용 코드(from_url) 삭제.
"""

from __future__ import annotations

import base64
import html as html_std
import io
import logging
import re
import zipfile
from abc import ABC, abstractmethod
from typing import Any
from xml.etree import ElementTree as ET

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# [Magic Number 상수] 파일 형식 판별의 '지문' 역할
#
# 모든 이진 파일은 첫 몇 바이트에 파일 형식을 나타내는 고유 서명을 가집니다.
# URL 주소가 어떻게 생겼든 이 바이트는 속일 수 없습니다.
# ─────────────────────────────────────────────────────────────────────────────
_MAGIC_PDF = b"%PDF"  # PDF 1.x~2.x 모두 동일
_MAGIC_OLE2 = b"\xd0\xcf\x11\xe0"  # HWP 2.x~5.x (OLE2 Compound Document)
_MAGIC_ZIP = b"PK\x03\x04"  # ZIP 기반: HWPX, DOCX, 일반 ZIP
_MAGIC_JPEG = b"\xff\xd8\xff"  # JPEG
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"  # PNG (8바이트 시그니처)
_MAGIC_GIF = (b"GIF87", b"GIF89")  # GIF87a, GIF89a
_MAGIC_BMP = b"BM"  # BMP


# ─────────────────────────────────────────────────────────────────────────────
# [유틸리티] HTML 태그 제거 및 텍스트 정제
# ─────────────────────────────────────────────────────────────────────────────

def clean_html_text(raw: str) -> str:
    """기업마당 API의 bsnsSumryCn(공고 요약) 필드에서 HTML 태그를 제거하고 순수 텍스트를 반환합니다.

    [왜 이 작업이 필요한가?]
    HTML 태그가 섞여 들어가면 GPT가 태그 분석에 토큰을 낭비하고 구조화 성능이 떨어집니다.
    파싱이 완전 실패했을 때 Fallback 원문으로 쓰이기 때문에 반드시 정제해야 합니다.
    """
    if not raw:
        return ""

    # 1. HTML 엔티티 → 유니코드 변환 (&nbsp; → 공백, &amp; → & 등)
    text = html_std.unescape(raw)

    # 2. HTML 태그 제거 (<p>, <br/>, <span> 등)
    text = re.sub(r"<[^>]+>", " ", text)

    # 3. non-breaking space(\xa0) → 일반 공백 변환
    text = text.replace("\xa0", " ")

    # 4. 탭·연속 공백 → 단일 공백 압축
    text = re.sub(r"[ \t]+", " ", text)

    # 5. 3줄 이상 연속 줄바꿈 → 2줄로 압축 (단락 구분은 유지)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# [계층 1] 문서 파서 인터페이스 (IDocumentParser)
# ─────────────────────────────────────────────────────────────────────────────

class IDocumentParser(ABC):
    """파일 바이너리를 받아 AI가 소화할 수 있는 형태로 변환하는 파서 인터페이스.

    Returns:
        {"type": "text",   "data": str}       — 텍스트 추출 성공
        {"type": "images", "data": list[str]} — Base64 인코딩 이미지 리스트 (Vision용)
    """

    @abstractmethod
    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#[계층 2] 구체 파서 구현체
# ─────────────────────────────────────────────────────────────────────────────

class PDFDocumentParser(IDocumentParser):
    """PyMuPDF(fitz)를 활용한 PDF 파서."""

    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        try:
            with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
                text = "".join(page.get_text() for page in doc)

                # 1. 일반 텍스트가 포함된 정상 PDF
                if len(text.strip()) > 100:
                    if verbose:
                        logger.info("  [PDF] 텍스트 추출 완료 (%d자)", len(text))
                    return {"type": "text", "data": text}

                # 2. 텍스트가 없는 스캔본(이미지 PDF) → 첫 3페이지를 이미지로 떠서 Vision AI 위임
                if verbose:
                    logger.info("  [PDF] 스캔본 감지 → Vision AI fallback (첫 3페이지)")
                images_b64: list[str] = []
                for page in doc[:3]:
                    pix = page.get_pixmap(dpi=150)
                    images_b64.append(base64.b64encode(pix.tobytes("png")).decode())
                return {"type": "images", "data": images_b64}

        except Exception as exc:
            logger.warning("  [PDF] 파싱 실패(%s) → 이미지 파서로 재시도", exc)
            return await ImageDocumentParser().parse(content, verbose=verbose)


class HWPDocumentParser(IDocumentParser):
    """HWP(OLE2) 및 HWPX(ZIP-XML) 파일에서 텍스트를 추출하는 파서."""

    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        # 첫 4바이트로 HWP(OLE) vs HWPX(ZIP) 분기
        if content[:4] == _MAGIC_ZIP:
            text = self._parse_hwpx_zip(content)
            parser_type = "HWPX"
        else:
            text = self._parse_hwp_ole(content)
            parser_type = "HWP OLE2"

        # [핵심 품질 검증] 100자 이상 추출된 경우만 정상으로 인정
        if text and len(text.strip()) > 100:
            if verbose:
                logger.info("  [%s] 텍스트 추출 완료 (%d자)", parser_type, len(text))
            return {"type": "text", "data": text}

        #[비용 낭비 차단] 이전에는 실패 시 HWP 바이너리를 Vision AI로 보냈으나,
        # GPT Vision은 이미지 파일만 해독 가능하므로 HWP 바이너리를 주면 에러/할루시네이션이 발생합니다.
        # 따라서 쓸데없는 API 비용을 내지 않고 명시적인 파싱 에러(ValueError)를 던집니다.
        logger.warning("  [%s] 텍스트 추출 실패 또는 너무 짧음 — Vision 폴백을 차단하고 에러 발생", parser_type)
        raise ValueError(f"{parser_type} 파일에서 유의미한 텍스트를 추출하지 못했습니다. (데이터 유실 의심)")

    def _parse_hwpx_zip(self, content: bytes) -> str:
        """HWPX(ZIP-XML) 형식에서 순수 텍스트(t 태그) 추출."""
        texts: list[str] =[]
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                section_files = sorted(
                    n for n in zf.namelist() if "BodyText" in n and n.endswith(".xml")
                )
                for name in section_files:
                    with zf.open(name) as f:
                        root = ET.parse(f).getroot()
                        for elem in root.iter():
                            local_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                            if local_tag == "t" and elem.text:
                                texts.append(elem.text)
        except Exception as exc:
            logger.debug("  [HWPX] ZIP-XML 파싱 실패: %s", exc)
        return "\n".join(texts)

    def _parse_hwp_ole(self, content: bytes) -> str:
        """HWP OLE2 형식의 PrvText 스트림(미리보기 텍스트) 추출."""
        try:
            import olefile
        except ImportError:
            logger.warning("  [HWP] olefile 패키지 미설치 — HWP OLE 파싱 불가")
            return ""

        try:
            with olefile.OleFileIO(io.BytesIO(content)) as ole:
                if ole.exists("PrvText"):
                    raw = ole.openstream("PrvText").read()
                    return raw.decode("utf-16-le", errors="ignore").strip()
        except Exception as exc:
            logger.debug("  [HWP OLE] 파싱 실패: %s", exc)
        return ""


class ImageDocumentParser(IDocumentParser):
    """이미지 파일(JPG·PNG·GIF 등)을 Base64로 인코딩하는 파서 (Vision AI용)."""

    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        if verbose:
            logger.info("  [IMAGE] 이미지 → Base64 인코딩 후 Vision AI 전달")
        b64 = base64.b64encode(content).decode()
        return {"type": "images", "data": [b64]}


# ─────────────────────────────────────────────────────────────────────────────
# [계층 3] 파서 팩토리 (DocumentParserFactory)
# ─────────────────────────────────────────────────────────────────────────────

class DocumentParserFactory:
    """다운로드된 파일의 Magic Number를 읽어 알맞은 파서 인스턴스를 반환합니다."""

    @staticmethod
    def from_content(content: bytes, *, filename_hint: str = "") -> IDocumentParser:
        """[권장] 다운로드된 파일의 Magic Number 지문으로 파서를 결정합니다."""
        header = content[:8]

        # 1. PDF
        if header[:4] == _MAGIC_PDF:
            logger.debug("  [MAGIC] PDF 감지 → PDFDocumentParser")
            return PDFDocumentParser()

        # 2. HWP OLE2
        if header[:4] == _MAGIC_OLE2:
            logger.debug("  [MAGIC] HWP OLE2 감지 → HWPDocumentParser")
            return HWPDocumentParser()

        # 3. ZIP 기반 (HWPX or 일반 ZIP)
        if header[:4] == _MAGIC_ZIP:
            hint_lower = filename_hint.lower()
            if hint_lower.endswith(".hwpx"):
                logger.debug("[MAGIC] ZIP + hint=.hwpx → HWPDocumentParser(HWPX)")
                return HWPDocumentParser()
            
            # 그 외 ZIP 파일: 사업신청서·양식일 가능성이 높음. (무리한 해제 방지)
            logger.debug("  [MAGIC] ZIP 감지 (hint=%s) → ImageDocumentParser(Vision AI)", filename_hint or "없음")
            return ImageDocumentParser()

        # 4. 이미지 형식들 (JPG, PNG, GIF, BMP)
        if header[:3] == _MAGIC_JPEG:
            return ImageDocumentParser()
        if header[:8] == _MAGIC_PNG:
            return ImageDocumentParser()
        if header[:5] in _MAGIC_GIF:
            return ImageDocumentParser()
        if header[:2] == _MAGIC_BMP:
            return ImageDocumentParser()

        # 5. 판별 불가 → Vision AI 최후 방어선
        # 텍스트 추출기가 못 읽는 알 수 없는 포맷(예: 독자 규격 이미지)도
        # 일단 Base64로 만들어서 AI에게 맡겨보는 최후의 보루입니다.
        logger.warning(
            "  [MAGIC] 형식 판별 불가 (hint=%s, header=%s) → Vision AI fallback",
            filename_hint or "없음",
            header.hex(),
        )
        return ImageDocumentParser()
    