# src/app/domains/policy/embedding_service.py
"""정책 공고 청킹(Chunking) 및 pgvector 임베딩 서비스.

설계 원칙:
  - [계층] Router → (Admin/Sync)Service → EmbeddingService → Repository
  - 이 서비스는 '변환' 전용입니다. 비즈니스 판단 없이 텍스트→청크→벡터 변환과 DB 저장만 수행합니다.
  - DB 트랜잭션 커밋(commit)은 호출한 상위 계층에서 책임집니다.

청킹(Chunking) 전략:
  1. content_raw에서 정책 섹션 헤더(지원대상, 지원내용 등)를 정규식으로 탐지합니다.
  2. 헤더가 2개 이상 감지되면 섹션별로 분할합니다 (섹션당 최대 2,000자).
  3. 섹션이 부족하거나 섹션 본문이 너무 길면 800자 슬라이딩 윈도우(100자 오버랩)로 분할합니다.
  4. 50자 미만의 너무 짧은 청크는 제거합니다.

중복 처리 전략:
  - content_raw의 SHA-256 해시를 Policy.content_hash에 저장합니다.
  - 해시가 동일하면 임베딩 재계산 없이 스킵하여 OpenAI API 비용을 절감합니다.
  - 내용이 변경된 경우 기존 청크 전체를 삭제하고 새로 삽입합니다 (교체 전략).
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import OPENAI_API_KEY
from src.app.domains.policy.repository import PolicyRepository

logger = logging.getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────────────────────────────

_EMBEDDING_MODEL = "text-embedding-3-small"
_EMBEDDING_DIM = 1536          # text-embedding-3-small 기본 차원
_MAX_SECTION_CHARS = 2000      # 섹션 청크 최대 길이 (이보다 크면 슬라이딩 윈도우로 재분할)
_WINDOW_CHARS = 800            # 슬라이딩 윈도우 청크 크기
_WINDOW_OVERLAP = 100          # 슬라이딩 윈도우 오버랩 (문맥 연속성 유지)
_MIN_CHUNK_CHARS = 50          # 이보다 짧은 청크는 노이즈로 간주하여 제거
_OPENAI_BATCH_SIZE = 20        # 한 번에 임베딩할 최대 청크 수 (Rate Limit 방어)

# 정책 공고에 자주 등장하는 섹션 헤더 키워드 목록
# 앞에 □, ■, ●, ○, ▶, ◆, ※, 숫자., ①② 등 다양한 접두어가 올 수 있습니다.
_SECTION_KEYWORDS: list[str] = [
    "사업개요", "사업 개요", "추진배경", "사업목적", "추진목적",
    "지원대상", "지원 대상", "지원자격", "신청자격",
    "지원내용", "지원 내용", "지원혜택", "지원내역", "지원규모",
    "지원금액", "지원 금액", "지원한도",
    "신청방법", "신청 방법", "신청절차", "접수방법", "신청안내",
    "신청기간", "접수기간", "모집기간", "신청일정",
    "선정기준", "선정 기준", "평가기준", "평가 기준", "선정방법",
    "제출서류", "제출 서류", "구비서류", "필요서류",
    "유의사항", "주의사항", "공통사항",
    "문의처", "담당부서", "담당자",
    "기대효과", "지원절차", "지원일정", "사업기간",
]

# 섹션 헤더 정규식:
#   - 줄 시작 혹은 줄바꿈 뒤
#   - 선택적 접두어 (□ ■ ● ○ ▶ 숫자. ① 등)
#   - 키워드
#   - 이후 줄바꿈 (본문 시작 경계)
_SECTION_RE = re.compile(
    r"(?:^|\n)"
    r"(?:[□■●○▶◆◇★☆※◎①②③④⑤⑥⑦⑧⑨⑩]|\d+[.)．]|[가-하][.)]|[A-Z][.)]) ?"
    r"(?:"
    + "|".join(re.escape(kw) for kw in sorted(_SECTION_KEYWORDS, key=len, reverse=True))
    + r")"
    r"[ \t]*(?:\n|$)",
    re.MULTILINE,
)


# ── 내부 데이터 클래스 ─────────────────────────────────────────────────────────

@dataclass
class _Chunk:
    """청킹 결과 단위 (내부 전용)."""
    chunk_type: str   # 섹션명 (예: "지원대상") 또는 "본문_N"
    chunk_text: str   # 청크에 포함될 실제 텍스트


# ── 청킹 헬퍼 함수 (순수 함수, 부작용 없음) ────────────────────────────────────

def _sha256(text: str) -> str:
    """텍스트의 SHA-256 해시를 반환합니다."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sliding_window(text: str, type_prefix: str = "본문") -> list[_Chunk]:
    """
    [폴백] 섹션 헤더가 부족하거나 섹션 본문이 너무 클 때 사용하는 슬라이딩 윈도우 분할기.
    _WINDOW_OVERLAP만큼 앞 청크와 겹쳐서 문맥 연속성을 유지합니다.
    """
    chunks: list[_Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + _WINDOW_CHARS, len(text))
        segment = text[start:end].strip()
        if len(segment) >= _MIN_CHUNK_CHARS:
            chunks.append(_Chunk(chunk_type=f"{type_prefix}_{idx}", chunk_text=segment))
            idx += 1
        # 다음 윈도우는 _WINDOW_OVERLAP만큼 뒤로 물러나서 시작
        start += _WINDOW_CHARS - _WINDOW_OVERLAP
    return chunks


def _extract_keyword(header_raw: str) -> str:
    """헤더 원문(접두어 포함)에서 핵심 키워드만 추출합니다."""
    for kw in sorted(_SECTION_KEYWORDS, key=len, reverse=True):
        if kw in header_raw:
            return kw
    return header_raw.strip()


def chunk_text(content_raw: str) -> list[_Chunk]:
    """
    [핵심] content_raw를 섹션 단위로 청킹합니다.

    처리 흐름:
      [1] 정규식으로 섹션 헤더 위치를 탐지합니다.
      [2] 헤더가 2개 이상이면 섹션별로 분할합니다.
      [3] 헤더가 부족하면 전체 텍스트를 슬라이딩 윈도우로 분할합니다.
      [4] 각 섹션 본문이 _MAX_SECTION_CHARS 초과 시 재분할합니다.
    """
    if not content_raw or not content_raw.strip():
        return []

    matches = list(_SECTION_RE.finditer(content_raw))

    # [3] 섹션 헤더가 부족하면 슬라이딩 윈도우 사용
    if len(matches) < 2:
        return _sliding_window(content_raw)

    chunks: list[_Chunk] = []

    # [2a] 첫 번째 섹션 이전의 서문 처리
    preamble = content_raw[: matches[0].start()].strip()
    if len(preamble) >= _MIN_CHUNK_CHARS:
        chunks.extend(_sliding_window(preamble, type_prefix="서문"))

    # [2b] 각 섹션 본문 처리
    for i, match in enumerate(matches):
        keyword = _extract_keyword(match.group(0).strip())
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(content_raw)
        body = content_raw[body_start:body_end].strip()

        if not body:
            continue

        # [4] 섹션 본문이 너무 크면 재분할
        if len(body) > _MAX_SECTION_CHARS:
            chunks.extend(_sliding_window(body, type_prefix=keyword))
        elif len(body) >= _MIN_CHUNK_CHARS:
            # 섹션 헤더를 청크 텍스트에 포함시켜 검색 시 섹션 맥락을 보존합니다.
            chunks.append(_Chunk(chunk_type=keyword, chunk_text=f"[{keyword}]\n{body}"))

    return chunks


def build_embed_text(
    chunk: _Chunk,
    *,
    policy_title: str = "",
    agency_name: str = "",
    support_type: str = "",
) -> str:
    """
    [Contextual Embedding] 임베딩 전용 텍스트를 구성합니다.

    설계 의도 (Anthropic "Contextual Retrieval" 기법):
      - DB에 저장된 chunk_text는 원본 그대로 유지합니다 (디스플레이·RAG 답변 생성용).
      - OpenAI에 전송하는 텍스트에만 정책 메타데이터 prefix를 붙입니다.
      - "지원대상: IT 기업" 단독 임베딩보다 "[정책명: 서울 IT 중소기업 스마트화 지원사업]
        [기관: 중소벤처기업부] 지원대상: IT 기업"이 훨씬 정확한 벡터 표현을 가집니다.
      - 이를 통해 다른 지역·기관의 유사 섹션과 구분되어 엉뚱한 검색 결과를 방지합니다.

    Returns:
        prefix + chunk_text 형태의 임베딩 전용 문자열.
    """
    prefix_parts: list[str] = []
    if policy_title:
        prefix_parts.append(f"[정책명: {policy_title}]")
    if agency_name:
        prefix_parts.append(f"[기관: {agency_name}]")
    if support_type:
        prefix_parts.append(f"[지원유형: {support_type}]")

    if not prefix_parts:
        return chunk.chunk_text

    return "\n".join(prefix_parts) + "\n" + chunk.chunk_text


# ── 서비스 ─────────────────────────────────────────────────────────────────────

class PolicyEmbeddingService:
    """
    정책 공고 텍스트를 청킹하고 OpenAI 임베딩 벡터를 생성·저장합니다.

    사용 흐름:
      1. sync_policy_chunks(policy_id, content_raw) — 단일 정책 임베딩
      2. sync_all_unembedded(limit)                — 관리자 배치 임베딩
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
    ) -> None:
        self._session = session
        self._repo = repo
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def sync_policy_chunks(
        self,
        *,
        policy_id: uuid.UUID,
        content_raw: str,
        policy_title: str = "",
        agency_name: str = "",
        support_type: str = "",
        force: bool = False,
    ) -> bool:
        """
        [핵심] 단일 정책의 청크·임베딩을 생성합니다.

        Contextual Embedding 전략:
          - DB chunk_text: 원본 텍스트 그대로 저장 (답변 생성·디스플레이용).
          - OpenAI 전송 텍스트: "[정책명: OOO]\n[기관: OOO]\n{chunk_text}" 형태로 전송.
          - 이렇게 하면 "지원대상" 섹션 하나만으로도 어떤 정책의 섹션인지 벡터에 인코딩됩니다.

        중복 처리:
          - force=False(기본)이면 content_hash를 비교해 변경 없는 경우 스킵합니다.
          - 변경된 경우 기존 청크를 전부 삭제하고 새로 삽입합니다 (교체 전략).

        Returns:
            True  — 청크가 새로 생성됨.
            False — 내용 변경 없어 스킵됨.
        """
        if not content_raw or not content_raw.strip():
            logger.warning("[임베딩] %s — content_raw가 비어있어 스킵", policy_id)
            return False

        new_hash = _sha256(content_raw)

        # [1] 변경 여부 확인 — API 비용 절감의 핵심
        if not force:
            policy = await self._repo.get_policy_by_id(policy_id)
            if policy and policy.content_hash == new_hash:
                logger.debug("[임베딩] %s — content_hash 동일, 스킵", policy_id)
                return False

        # [2] 청킹
        raw_chunks = chunk_text(content_raw)
        if not raw_chunks:
            logger.warning("[임베딩] %s — 청킹 결과 없음, 스킵", policy_id)
            return False

        logger.info("[임베딩] %s — %d개 청크 생성 완료", policy_id, len(raw_chunks))

        # [3] 배치 임베딩 — DB 저장용 원본과 별개로 메타데이터 prefix를 붙인 텍스트를 전송
        #     chunk_text(원본)은 그대로 DB에 저장, embed_text(prefix 포함)만 OpenAI로 전송
        embed_texts = [
            build_embed_text(
                c,
                policy_title=policy_title,
                agency_name=agency_name,
                support_type=support_type,
            )
            for c in raw_chunks
        ]

        all_embeddings: list[list[float]] = []
        for batch_start in range(0, len(embed_texts), _OPENAI_BATCH_SIZE):
            batch = embed_texts[batch_start : batch_start + _OPENAI_BATCH_SIZE]
            all_embeddings.extend(await self._embed_texts(batch))

        # [4] 기존 청크 삭제 → 새 청크 삽입 (원자적 교체)
        await self._repo.delete_chunks_by_policy_id(policy_id)
        for idx, (chunk, embedding) in enumerate(zip(raw_chunks, all_embeddings)):
            await self._repo.create_chunk(
                policy_id=policy_id,
                chunk_index=idx,
                chunk_type=chunk.chunk_type,
                chunk_text=chunk.chunk_text,  # DB에는 원본 텍스트 저장
                embedding=embedding,
            )

        # [5] content_hash 업데이트 — 다음 실행 시 스킵 여부 판단 기준
        await self._repo.update_content_hash(policy_id, new_hash)
        await self._session.flush()

        logger.info("[임베딩] %s — 저장 완료 (%d청크)", policy_id, len(raw_chunks))
        return True

    async def sync_all_unembedded(self, limit: int = 500) -> dict[str, Any]:
        """
        content_hash가 없거나 내용이 변경된 정책을 일괄 재임베딩합니다.
        관리자 배치 작업 전용 — 호출 후 반드시 상위 계층에서 commit()합니다.
        """
        policies = await self._repo.get_policies_without_hash(limit=limit)
        success = skipped = failed = 0

        for policy in policies:
            if not policy.content_raw:
                skipped += 1
                continue
            try:
                changed = await self.sync_policy_chunks(
                    policy_id=policy.id,
                    content_raw=policy.content_raw,
                    policy_title=policy.title or "",
                    agency_name=policy.agency_name or "",
                    support_type=policy.support_type or "",
                )
                if changed:
                    success += 1
                else:
                    skipped += 1
            except Exception as exc:
                failed += 1
                logger.warning("[임베딩] %s — 실패: %s", policy.id, exc)

        await self._session.commit()
        return {
            "total": len(policies),
            "success": success,
            "skipped": skipped,
            "failed": failed,
        }

    # ── 내부 헬퍼 ──────────────────────────────────────────────────────────────

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        OpenAI Embeddings API를 호출합니다.
        응답은 입력 순서와 다를 수 있으므로 index 기준으로 정렬하여 반환합니다.
        """
        response = await self._client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=texts,
        )
        # API 응답의 index 필드로 입력 순서를 복원합니다.
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
