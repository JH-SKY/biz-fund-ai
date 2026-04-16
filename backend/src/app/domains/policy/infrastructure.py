# src/app/domains/policy/infrastructure.py
"""정책 공고 수집 인프라 계층.

설계 원칙 (.cursorrules §1):
  Infrastructure 계층은 파일 파싱(PDF, HWP, 이미지)·외부 API 호출 등
  순수 "기술적 I/O"만 담당하며, 비즈니스 판단은 Service 계층에 위임한다.

바이너리 우선 파서 전략 (.cursorrules §2.1):
  기업마당 API의 printFlpthNm 은 항상 getImageFile.do?atchFileId=... 형태로 오기 때문에
  URL 만으로는 내부 파일 형식(PDF/HWP/HWPX/이미지)을 알 수 없다.
  따라서 파일을 먼저 다운로드한 뒤, 첫 몇 바이트(Magic Number)를 읽어 형식을 확정한다.
  이것이 URL 기반보다 바이너리 기반이 훨씬 신뢰성 높은 이유다.

파서 Fallback 체계:
  PDF 파싱 실패 또는 스캔본 → 이미지 변환 → Vision AI
  HWP 파싱 실패 → Vision AI
  Magic Number 판별 불가 → Vision AI (최후 방어선)

AI 구조화 책임 분리:
  문서 파싱(텍스트/이미지 추출)까지가 이 계층의 책임이다.
  GPT-4o 호출·Self-Correction 등 AI 분석 로직은 PolicySyncAgent 에 위임한다.
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
# 모든 이진 파일은 첫 몇 바이트에 파일 형식을 나타내는 고유 서명을 가진다.
# 예) %PDF-1.4 로 시작하는 파일은 무조건 PDF,
#     D0 CF 11 E0 로 시작하면 Microsoft OLE2 Compound Document (HWP 포함).
# URL 주소가 아무리 이상하게 생겨도 이 바이트는 속일 수 없다.
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
    """기업마당 API의 bsnsSumryCn 필드에서 HTML 태그를 제거하고 순수 텍스트를 반환한다.

    [왜 이 작업이 필요한가?]
    기업마당 API는 공고 요약(bsnsSumryCn)을 HTML 형식으로 제공한다.
    예: "<p>지원 대상입니다.</p>&nbsp;<br/>" 또는 "\\u003Cp\\u003E..."
    이를 그대로 GPT에 전달하면 태그 자체를 '텍스트'로 분석해 구조화 성능이 크게 떨어진다.
    파일 파싱이 실패했을 때 이 필드를 Fallback으로 사용하므로, 반드시 정제가 필요하다.

    처리 단계:
      1. html.unescape() — &amp; → &, &nbsp; → 공백, &#123; 스타일 수치 엔티티 처리
      2. <태그> 제거 — <p>, <br/>, <strong>, <span style="..."> 등 모두 제거
      3. 연속 공백/줄바꿈 정리 — 가독성 및 토큰 효율 향상
    """
    if not raw:
        return ""

    # 1. HTML 엔티티 → 유니코드 변환 (&nbsp; → 공백, &amp; → & 등)
    text = html_std.unescape(raw)

    # 2. HTML 태그 제거 (<p>, <br/>, <div class="...">, </span> 등)
    text = re.sub(r"<[^>]+>", " ", text)

    # 4. non-breaking space(\xa0) → 일반 공백 변환 (&nbsp; unescape 결과물 처리)
    text = text.replace("\xa0", " ")

    # 5. 탭·연속 공백 → 단일 공백
    text = re.sub(r"[ \t]+", " ", text)

    # 6. 3줄 이상 연속 줄바꿈 → 2줄로 압축 (단락 구분은 유지)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# [계층 1] 문서 파서 인터페이스 (IDocumentParser)
# ─────────────────────────────────────────────────────────────────────────────


class IDocumentParser(ABC):
    """파일 바이너리를 받아 AI가 소화할 수 있는 형태로 변환하는 파서 인터페이스.

    설계 의도: DocumentParserFactory 는 IDocumentParser만 알면 되므로,
    파서 구현체(PDF/HWP/이미지)를 교체해도 Enricher 코드는 변경할 필요가 없다.

    Returns:
        {"type": "text",   "data": str}          — 텍스트 추출 성공
        {"type": "images", "data": list[str]}     — Base64 인코딩 이미지 리스트
    """

    @abstractmethod
    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# [계층 2] 구체 파서 구현체
# ─────────────────────────────────────────────────────────────────────────────


class PDFDocumentParser(IDocumentParser):
    """PyMuPDF(fitz)를 활용한 PDF 파서.

    처리 전략:
      1. 텍스트 레이어가 있는 PDF → 직접 텍스트 추출 (빠름, 정확함)
      2. 스캔본(텍스트 100자 미만) → 첫 3페이지를 150 DPI 이미지로 변환 후 Vision AI 위임
      3. PDF 열기 자체가 실패 → ImageDocumentParser 로 fallback
    """

    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        try:
            with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
                text = "".join(page.get_text() for page in doc)

                # 1. 일반 텍스트 PDF
                if len(text.strip()) > 100:
                    if verbose:
                        logger.info("  [PDF] 텍스트 추출 완료 (%d자)", len(text))
                    return {"type": "text", "data": text}

                # 2. 스캔본 → Vision AI (첫 3페이지만 변환, 비용 방어)
                if verbose:
                    logger.info("  [PDF] 스캔본 감지 → Vision AI fallback (첫 3페이지)")
                images_b64: list[str] = []
                for page in doc[:3]:
                    pix = page.get_pixmap(dpi=150)
                    images_b64.append(base64.b64encode(pix.tobytes("png")).decode())
                return {"type": "images", "data": images_b64}

        except Exception as exc:
            # 3. PDF 열기 실패 → 이미지 파서 위임
            logger.warning("  [PDF] 파싱 실패(%s) → 이미지 파서로 재시도", exc)
            return await ImageDocumentParser().parse(content, verbose=verbose)


class HWPDocumentParser(IDocumentParser):
    """HWP(OLE2) 및 HWPX(ZIP-XML) 파일에서 텍스트를 추출하는 파서.

    HWP (2.x~5.x, OLE2 compound document):
      - 'PrvText' 스트림에 UTF-16 LE 인코딩 preview text 가 항상 저장됨
      - olefile 라이브러리로 스트림을 읽어 디코딩

    HWPX (HWP Open Format, ZIP 기반 XML):
      - 표준 ZIP 파일 내 BodyText/Section*.xml 의 <t> 요소에 텍스트 저장
      - Python 기본 zipfile + ElementTree 로 파싱 (추가 의존성 없음)

    두 형식 모두 파싱 실패 시 ImageDocumentParser 로 fallback.
    """

    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        # content의 첫 4바이트로 HWP vs HWPX 분기
        if content[:4] == _MAGIC_ZIP:
            text = self._parse_hwpx_zip(content)
            parser_type = "HWPX"
        else:
            text = self._parse_hwp_ole(content)
            parser_type = "HWP OLE2"

        if text:
            # --- [품질 검증 로직 추가] ---
            # 1. 문서가 너무 짧은지 확인 (500자 미만)
            is_too_short = len(text.strip()) < 500

            # 2. 문서가 중간에 끊겼는지 확인 (문서 끝에 주로 등장하는 키워드)
            end_keywords = [
                "문의",
                "연락처",
                "접수",
                "사이트",
                "홈페이지",
                "02-",
                "053-",
                "061-",
                "끝.",
            ]
            has_end_signal = any(kw in text[-300:] for kw in end_keywords)

            # 정상적으로 추출되었다고 판단되는 경우
            if not is_too_short and has_end_signal:
                if verbose:
                    logger.info(
                        "  [%s] 텍스트 추출 완료 (%d자)", parser_type, len(text)
                    )
                return {"type": "text", "data": text}

            # 잘린 것으로 의심되는 경우
            else:
                if verbose:
                    logger.warning(
                        "  [%s] 텍스트 유실(Truncation) 의심됨. 경고 표식을 추가합니다.",
                        parser_type,
                    )
                return {
                    "type": "text",
                    "data": f"[⚠️시스템 알림: 이 문서는 원문 파싱 중 하단부가 유실되었을 가능성이 높음]\n{text}",
                }

        # 텍스트 추출 자체가 아예 실패한 경우에만 이미지 파서(Vision AI) 시도
        # (주의: 이 경우 GPT가 HWP 바이너리를 읽지 못해 에러가 날 수 있으나
        #  기존 코드의 Fallback 체계를 존중하여 유지합니다)
        logger.warning("  [HWP] 텍스트 추출 실패 → Vision AI fallback 시도")
        return await ImageDocumentParser().parse(content, verbose=verbose)

    def _parse_hwpx_zip(self, content: bytes) -> str:
        """HWPX(ZIP-XML) 형식에서 텍스트 추출.

        HWPX 는 표준 ZIP 파일이며, 내부에 BodyText/Section0.xml, Section1.xml 등
        여러 섹션 XML 파일이 있다. 각 XML 의 <t> 태그가 실제 텍스트다.
        """
        texts: list[str] = []
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                section_files = sorted(
                    n for n in zf.namelist() if "BodyText" in n and n.endswith(".xml")
                )
                for name in section_files:
                    with zf.open(name) as f:
                        root = ET.parse(f).getroot()
                        for elem in root.iter():
                            local_tag = (
                                elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                            )
                            if local_tag == "t" and elem.text:
                                texts.append(elem.text)
        except Exception as exc:
            logger.debug("  [HWPX] ZIP-XML 파싱 실패: %s", exc)
        return "\n".join(texts)

    def _parse_hwp_ole(self, content: bytes) -> str:
        """HWP OLE2 형식의 PrvText 스트림에서 미리보기 텍스트 추출.

        PrvText 스트림은 HWP 5.x 이상에서 항상 포함되는 UTF-16 LE 평문 미리보기.
        완벽한 원문이 아닐 수 있지만, 핵심 텍스트 확보에 충분하다.
        """
        try:
            import olefile
        except ImportError:
            logger.warning("  [HWP] olefile 미설치 — HWP OLE 파싱 불가")
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
    """이미지 파일(JPG·PNG·GIF 등) 및 스캔 문서를 Base64로 인코딩하는 파서.

    인코딩 결과를 OpenAI GPT-4o Vision 모드로 전달한다.
    설계 의도: Vision AI는 '어떤 이미지든 읽을 수 있는 최후의 방어선'이다.
    이 파서에 도달한다는 것은 텍스트 추출 방법이 모두 실패했음을 의미하며,
    사람이 읽을 수 있는 문서라면 Vision AI 도 읽을 수 있다는 가정에 기반한다.
    """

    async def parse(self, content: bytes, *, verbose: bool = False) -> dict[str, Any]:
        if verbose:
            logger.info("  [IMAGE] 이미지 → Base64 인코딩 후 Vision AI 전달")
        b64 = base64.b64encode(content).decode()
        return {"type": "images", "data": [b64]}


# ─────────────────────────────────────────────────────────────────────────────
# [계층 3] 파서 팩토리 (DocumentParserFactory)
#
# [핵심 설계: 왜 URL이 아닌 바이너리(Magic Number) 기반으로 파서를 결정하는가?]
#
# 기업마당 API의 printFlpthNm 필드는 항상 아래와 같은 형태로 온다:
#   "https://www.bizinfo.go.kr/cmm/fms/getImageFile.do?atchFileId=FILE_001"
#
# URL 끝에 '.pdf' 나 '.hwp' 같은 확장자가 없기 때문에,
# URL 만 보고서는 내부에 무엇이 들어있는지 절대 알 수 없다.
# (실제로 이 URL이 PDF를 반환하기도 하고, HWP를 반환하기도 하고, 이미지를 반환하기도 한다)
#
# 반면, 모든 이진 파일은 첫 몇 바이트에 자신의 형식을 나타내는 '지문(Magic Number)'을 가진다.
# 이 지문을 직접 읽으면 어떤 URL에서 다운로드했든 정확하게 형식을 알 수 있다.
#
# → from_content()  : [권장] 다운로드 후 Magic Number 기반 — 정확도 최고
# → from_url()      : [보조] URL/파일명 기반 — 사전 스킵 판단 등 제한적 용도
# ─────────────────────────────────────────────────────────────────────────────


class DocumentParserFactory:
    """파서 인스턴스를 생성하는 팩토리."""

    @staticmethod
    def from_content(content: bytes, *, filename_hint: str = "") -> IDocumentParser:
        """[권장] 다운로드된 파일의 Magic Number 로 파서를 결정한다.

        Args:
            content:       다운로드된 파일 바이너리 전체
            filename_hint: printFileNm 필드값 (예: "공고문.hwp", "(공고)_사업안내.pdf")
                           Magic Number 만으로 판별이 모호한 경우(ZIP)에 보조 힌트로 사용

        판별 순서:
          1. %PDF          → PDFDocumentParser
          2. D0 CF 11 E0   → HWPDocumentParser (OLE2, 내부에서 HWP OLE 처리)
          3. PK 03 04      → ZIP 기반
               └ filename_hint 가 .hwpx → HWPDocumentParser (HWPX ZIP-XML 처리)
               └ 그 외        → ImageDocumentParser (Vision AI; ZIP 내 공고 내용 불명확)
          4. FF D8 FF      → ImageDocumentParser (JPEG)
          5. 89 50 4E 47   → ImageDocumentParser (PNG)
          6. GIF8x         → ImageDocumentParser (GIF)
          7. BM            → ImageDocumentParser (BMP)
          8. 판별 불가     → ImageDocumentParser (Vision AI 최후 방어선)
        """
        header = content[:8]  # 파서 결정에 필요한 최대 바이트는 8바이트면 충분

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
                # printFileNm 이 .hwpx 임을 확인 → HWPX 로 처리
                logger.debug(
                    "  [MAGIC] ZIP + filename_hint=.hwpx → HWPDocumentParser(HWPX)"
                )
                return HWPDocumentParser()
            # 그 외 ZIP: 사업신청서·양식 파일일 가능성이 높음 → Vision AI 시도
            # 설계 의도: 일반 ZIP은 공고 본문이 없는 경우가 많으므로
            #            무리하게 압축 해제하지 않고 Vision AI에 위임한다.
            logger.debug(
                "  [MAGIC] ZIP 감지 (hint=%s) → ImageDocumentParser(Vision AI)",
                filename_hint or "없음",
            )
            return ImageDocumentParser()

        # 4. 이미지 형식들
        if header[:3] == _MAGIC_JPEG:
            logger.debug("  [MAGIC] JPEG 감지 → ImageDocumentParser")
            return ImageDocumentParser()

        if header[:8] == _MAGIC_PNG:
            logger.debug("  [MAGIC] PNG 감지 → ImageDocumentParser")
            return ImageDocumentParser()

        if header[:5] in _MAGIC_GIF:
            logger.debug("  [MAGIC] GIF 감지 → ImageDocumentParser")
            return ImageDocumentParser()

        if header[:2] == _MAGIC_BMP:
            logger.debug("  [MAGIC] BMP 감지 → ImageDocumentParser")
            return ImageDocumentParser()

        # 5. 판별 불가 → Vision AI 최후 방어선
        # 설계 의도: "데이터가 없어서 못 가져오는 게 아니라 그릇이 다를 뿐"
        # 알 수 없는 형식도 Vision AI 가 이미지로 읽어낼 수 있다면 최선을 다한다.
        logger.warning(
            "  [MAGIC] 형식 판별 불가 (hint=%s, header=%s) → Vision AI fallback",
            filename_hint or "없음",
            header.hex(),
        )
        return ImageDocumentParser()

    @staticmethod
    def from_url(url: str) -> IDocumentParser:
        """[보조] URL/파일명 패턴 기반 파서 결정.

        from_content() 대비 정확도가 낮다.
        실제 수집 파이프라인에서는 from_content() 를 사용하고,
        이 메서드는 다운로드 전 사전 스킵 판단 등 제한적 용도로만 사용한다.
        예) flpthNm 에서 .zip 파일을 건너뛰고 싶을 때.
        """
        url_clean = url.lower().split("?")[0]

        _IMAGE_KEYWORDS = ("getimagefile", "getimgfile")
        _IMAGE_EXTS = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tif",
            ".tiff",
            ".webp",
        )
        _HWP_EXTS = (".hwpx", ".hwp")

        for kw in _IMAGE_KEYWORDS:
            if kw in url_clean:
                return ImageDocumentParser()
        for ext in _IMAGE_EXTS:
            if url_clean.endswith(ext):
                return ImageDocumentParser()
        for ext in _HWP_EXTS:
            if url_clean.endswith(ext):
                return HWPDocumentParser()

        return PDFDocumentParser()
