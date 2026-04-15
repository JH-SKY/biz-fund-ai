# src/app/domains/policy/sync_service.py
"""기업마당(Bizinfo) 정책 공고 수집 엔진.

설계 원칙:
  1. run_policy_sync 가 유일한 수집 파이프라인 진입점이다.
     - 스케줄러(새벽 3시 자동)와 관리자 API(수동 트리거) 모두 이 메서드를 호출한다.
     - bootstrap / daily / test 는 모두 얇은 래퍼(thin wrapper)다.

  2. 개별 공고 실패 격리 (savepoint 전략):
     - 각 공고의 DB INSERT 는 begin_nested() 세이브포인트 안에서 실행된다.
     - 특정 공고가 실패해도 세이브포인트만 롤백되므로 이전 성공 건은 보존된다.
     - 에러 컨텍스트(origin_id, apply_url, 에러 메시지)를 로그에 기록한다.

  3. BatchLog 즉시 커밋 전략:
     - BatchLog 는 수집 시작 직후 즉시 커밋한다.
     - 이후 치명적 오류로 전체 롤백이 발생해도 BatchLog 기록은 유지된다.
     - 완료 시 sa_update 로 status / count 를 업데이트한다.

  4. 다중 파일 처리 (@ 구분자):
     - printFlpthNm 이 "@" 로 연결된 여러 URL 을 포함할 수 있다.
     - _select_primary_file() 로 핵심 공고문 파일 하나를 우선 선택한다.
     - filename_hint (printFileNm) 를 enricher 에 전달하여 파서 결정 정확도를 높인다.

  5. HTML 정제 (bsnsSumryCn Fallback):
     - 파일 파싱 실패 시 bsnsSumryCn 을 fallback 텍스트로 사용한다.
     - 이 필드는 HTML 태그를 포함하므로, clean_html_text() 로 정제 후 저장·전달한다.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import BIZINFO_API_KEY
from src.app.domains.policy.infrastructure import clean_html_text
from src.app.domains.policy.interfaces import IPolicyEnricher
from src.app.domains.policy.model import Policy, PolicyStatus
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.system.model import BatchLog

logger = logging.getLogger(__name__)

# ── 파일 우선순위 (핵심 공고문 선택 기준) ──────────────────────────────────────
# 다중 파일이 있을 때 어떤 파일을 먼저 파싱할지 우선순위를 정의한다.
# 공고 본문은 대부분 PDF 또는 HWP 형태이므로 ZIP(양식·첨부) 보다 앞에 둔다.
_FILE_PRIORITY = (".pdf", ".hwp", ".hwpx")


class BizinfoSyncService:
    """기업마당 API 데이터를 PostgreSQL DB로 동기화하는 핵심 수집 엔진."""

    _API_URL = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"

    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
        enricher: IPolicyEnricher,
    ) -> None:
        self._session = session
        self._repo = repo
        self._enricher = enricher

    # ─────────────────────────────────────────────────────────────────────────
    # [공개 API] 외부에서 호출하는 진입점들
    # ─────────────────────────────────────────────────────────────────────────

    async def run_policy_sync(
        self,
        *,
        job_name: str = "POLICY_SYNC",
        page_start: int = 1,
        page_end: int = 1,
        rows_per_page: int = 100,
        with_ai: bool = False,
        verbose: bool = False,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """중앙 수집 파이프라인. 스케줄러·관리자 API 모두 이 메서드를 사용한다.

        Args:
            job_name:      BatchLog 에 기록될 작업명
            page_start:    수집 시작 페이지 번호 (1-based)
            page_end:      수집 종료 페이지 번호 (포함)
            rows_per_page: 페이지당 공고 수 (기업마당 API 권장 최대: 100)
            with_ai:       True 이면 첨부파일 파싱 + GPT-4o 구조화 실행
            verbose:       True 이면 AI 파이프라인 단계별 로그 출력
            date_from:     API 날짜 필터 시작일 (YYYYMMDD 형식)
            date_to:       API 날짜 필터 종료일 (YYYYMMDD 형식)
        """
        if not BIZINFO_API_KEY:
            logger.error("[%s] BIZINFO_API_KEY 미설정 — 수집 중단", job_name)
            return {"status": "error", "message": "BIZINFO_API_KEY 미설정"}

        logger.info(
            "[%s] 🚀 수집 시작 | 페이지: %d~%d | rows/page: %d | AI: %s",
            job_name, page_start, page_end, rows_per_page, with_ai,
        )

        # ── [STEP 1] BatchLog 즉시 커밋 (이후 롤백에도 기록 유지) ──────────
        batch = BatchLog(
            job_name=job_name,
            status="RUNNING",
            total_count=0,
            success_count=0,
            fail_count=0,
        )
        self._session.add(batch)
        await self._session.commit()
        batch_id = batch.id

        total_items = 0
        success_count = 0
        fail_count = 0
        error_log: list[dict] = []

        try:
            # ── [STEP 2] 페이지 순회 ─────────────────────────────────────
            for page_no in range(page_start, page_end + 1):
                logger.info(
                    "[%s] 📄 페이지 %d / %d 호출 중...",
                    job_name, page_no, page_end,
                )

                try:
                    raw_items = await self._fetch_single_page(
                        page_no=page_no,
                        rows_per_page=rows_per_page,
                        date_from=date_from,
                        date_to=date_to,
                    )
                except Exception as page_err:
                    logger.error(
                        "[%s] ❌ 페이지 %d API 호출 실패: %s",
                        job_name, page_no, page_err,
                    )
                    error_log.append({"page": page_no, "error": str(page_err)})
                    continue

                if not raw_items:
                    logger.info(
                        "[%s] 페이지 %d: 항목 없음 — 순회 조기 종료",
                        job_name, page_no,
                    )
                    break

                # origin_id 기준 중복 제거
                unique_items = list(
                    {item["pblancId"]: item for item in raw_items if item.get("pblancId")}.values()
                )
                total_items += len(unique_items)

                logger.info(
                    "[%s] 페이지 %d: %d건 처리 시작",
                    job_name, page_no, len(unique_items),
                )

                # ── [STEP 3] 공고별 개별 처리 ────────────────────────────
                for item in unique_items:
                    ok, err_info = await self._process_single_item(
                        item=item,
                        with_ai=with_ai,
                        verbose=verbose,
                        job_name=job_name,
                    )
                    if ok:
                        success_count += 1
                    else:
                        fail_count += 1
                        if err_info:
                            error_log.append(err_info)

                await self._session.flush()

            # ── [STEP 4] 전체 커밋 ──────────────────────────────────────
            await self._session.commit()

            # ── [STEP 5] BatchLog 완료 처리 ─────────────────────────────
            await self._session.execute(
                sa_update(BatchLog)
                .where(BatchLog.id == batch_id)
                .values(
                    status="SUCCESS",
                    total_count=total_items,
                    success_count=success_count,
                    fail_count=fail_count,
                    error_details={"errors": error_log[:50]} if error_log else None,
                    finished_at=datetime.utcnow(),
                )
            )
            await self._session.commit()

            logger.info(
                "[%s] ✅ 완료 | 전체: %d | 성공: %d | 실패: %d",
                job_name, total_items, success_count, fail_count,
            )
            return {
                "status": "success",
                "job_name": job_name,
                "total": total_items,
                "success": success_count,
                "fail": fail_count,
            }

        except Exception as fatal_err:
            await self._session.rollback()
            logger.error("[%s] 🚨 치명적 오류 — 트랜잭션 롤백: %s", job_name, fatal_err)

            await self._session.execute(
                sa_update(BatchLog)
                .where(BatchLog.id == batch_id)
                .values(
                    status="FAILED",
                    total_count=total_items,
                    success_count=success_count,
                    fail_count=fail_count,
                    error_details={"fatal_error": str(fatal_err), "errors": error_log[:20]},
                    finished_at=datetime.utcnow(),
                )
            )
            await self._session.commit()

            return {"status": "error", "message": str(fatal_err)}

    async def bootstrap_historical_policies(
        self,
        total_count: int = 1000,
        *,
        with_ai: bool = False,
    ) -> dict[str, Any]:
        """과거 데이터 대량 적재 — 최초 세팅 또는 전체 재수집 시 사용."""
        page_end = math.ceil(total_count / 100)
        return await self.run_policy_sync(
            job_name="POLICY_BOOTSTRAP",
            page_start=1,
            page_end=page_end,
            rows_per_page=100,
            with_ai=with_ai,
        )

    async def sync_recent_policies(self) -> dict[str, Any]:
        """일일 자동 동기화 — 최신 공고 2페이지(200건) 수집."""
        return await self.run_policy_sync(
            job_name="POLICY_DAILY_SYNC",
            page_start=1,
            page_end=2,
            rows_per_page=100,
            with_ai=False,
        )

    async def test_sync_single_policy(self) -> dict[str, Any]:
        """[TEST] 공고 1건 전체 파이프라인 검증 (with_ai=True, verbose=True)."""
        logger.info("=" * 60)
        logger.info("🚀 [TEST] 단일 정책 동기화 파이프라인 테스트")
        logger.info("=" * 60)

        result = await self.run_policy_sync(
            job_name="POLICY_TEST_SINGLE",
            page_start=1,
            page_end=1,
            rows_per_page=1,
            with_ai=True,
            verbose=True,
        )

        logger.info("=" * 60)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # [내부 헬퍼] 외부에서 직접 호출 금지
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_single_page(
        self,
        *,
        page_no: int,
        rows_per_page: int,
        date_from: str | None,
        date_to: str | None,
    ) -> list[dict[str, Any]]:
        """기업마당 API 단일 페이지를 호출하고 공고 리스트를 반환한다."""
        params: dict[str, Any] = {
            "serviceKey": BIZINFO_API_KEY,
            "dataType": "json",
            "numOfRows": rows_per_page,
            "pageNo": page_no,
        }
        if date_from:
            params["pblancBgnDe"] = date_from
        if date_to:
            params["pblancEndDe"] = date_to

        async with httpx.AsyncClient() as client:
            response = await client.get(self._API_URL, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        body = data.get("response", {}).get("body", {})
        items_raw = body.get("items", {}).get("item", [])

        # API 는 결과가 1건일 때 dict, 여러 건일 때 list 를 반환한다.
        if isinstance(items_raw, dict):
            return [items_raw]
        return items_raw if isinstance(items_raw, list) else []

    async def _process_single_item(
        self,
        *,
        item: dict[str, Any],
        with_ai: bool,
        verbose: bool,
        job_name: str,
    ) -> tuple[bool, dict[str, Any] | None]:
        """단일 공고 아이템을 처리하고 DB에 upsert 한다.

        처리 순서:
          1. API 응답 기본 필드 파싱 (날짜, 상태, 기관명 등)
          2. bsnsSumryCn HTML 태그 제거 → fallback content_raw 구성
          3. printFlpthNm/@printFileNm 에서 핵심 파일 URL 선택
          4. with_ai=True 이면 파일 다운로드 → Magic Number 파서 결정 → AI 구조화
          5. begin_nested() 세이브포인트 안에서 INSERT … ON CONFLICT DO UPDATE

        [Fallback 복구 흐름]
          파일 URL 이 없거나 파싱/AI 가 실패해도 중단하지 않는다.
          clean_html_text(bsnsSumryCn) 를 content_raw 로 DB에 저장한다.
          "데이터가 없어서 못 가져오는 게 아니라 그릇이 다를 뿐"
        """
        origin_id = item.get("pblancId", "UNKNOWN")
        title = item.get("pblancNm", "제목 없음")
        apply_url = item.get("pblancUrl") or ""

        logger.debug("[%s] 처리 중: [%s] %s", job_name, origin_id, title[:40])

        # ── [1] 기본 필드 파싱 ────────────────────────────────────────────
        start_dt, end_dt = self._parse_period(item.get("reqstBeginEndDe", ""))
        today = datetime.now().date()
        closed_at = end_dt if end_dt else date(9999, 12, 31)
        status = (
            PolicyStatus.CLOSED
            if (end_dt and end_dt < today)
            else PolicyStatus.RECRUITING
        )

        # ── [2] HTML 정제 → Fallback content_raw 구성 ──────────────────
        # bsnsSumryCn 에는 <p>, <br/> 같은 HTML 태그가 포함되어 있다.
        # 이를 그대로 GPT 에 전달하면 태그 자체를 분석해 구조화 성능이 저하된다.
        # clean_html_text() 로 순수 텍스트만 추출하여 사용한다.
        target = item.get("trgetNm") or "정보 없음"
        summary_raw = item.get("bsnsSumryCn") or ""
        summary_clean = clean_html_text(summary_raw)
        content_raw = f"[지원대상]\n{target}\n\n[상세내용]\n{summary_clean}"
        enriched: dict[str, Any] = {}

        # ── [3] 핵심 공고문 파일 선택 (@ 다중 파일 처리) ────────────────
        # printFlpthNm 이 "URL1@URL2" 형태일 수 있다.
        # printFileNm 은 실제 파일명(확장자 포함)으로, 파서 결정의 힌트가 된다.
        file_url, filename_hint = self._select_primary_file(
            print_flpth_nm=item.get("printFlpthNm"),
            print_file_nm=item.get("printFileNm"),
        )

        # ── [4] AI 보강 (선택적) ─────────────────────────────────────────
        if with_ai:
            if file_url:
                try:
                    logger.debug(
                        "[%s] AI 분석 시작: [%s] URL=%s hint=%s",
                        job_name, origin_id, file_url, filename_hint or "없음",
                    )
                    enriched = await self._enricher.extract_and_structure(
                        file_url=file_url,
                        original_summary=summary_clean,  # HTML 제거 완료 버전 전달
                        filename_hint=filename_hint,
                        verbose=verbose,
                    )
                    # AI 가 파싱한 원문이 있으면 API 요약보다 더 풍부한 정보 포함
                    content_raw = enriched.get("content_raw", content_raw)
                    logger.debug("[%s] AI 분석 성공: [%s]", job_name, origin_id)
                except Exception as ai_err:
                    # AI 실패는 Warning 수준 — fallback content_raw 로 DB 저장 진행
                    logger.warning(
                        "[%s] ⚠️ AI 분석 실패: [%s] URL=%s hint=%s | 오류: %s",
                        job_name, origin_id, file_url, filename_hint or "없음", ai_err,
                    )
            else:
                # 첨부파일 URL 이 없는 경우 — API 요약으로만 저장
                logger.debug(
                    "[%s] AI 스킵: [%s] (printFlpthNm 없음)", job_name, origin_id
                )

        # ── [5] DB Upsert — 세이브포인트 격리 ───────────────────────────
        # begin_nested(): PostgreSQL SAVEPOINT 생성.
        # 이 블록에서 실패해도 외부 트랜잭션(이전 성공 건)은 보존된다.
        try:
            async with self._session.begin_nested():
                stmt = (
                    insert(Policy)
                    .values(
                        origin_id=origin_id,
                        title=title,
                        agency_name=item.get("jrsdInsttNm") or "기관명 없음",
                        category=item.get("pldirSportRealmLclasCodeNm") or "기타",
                        region=item.get("areaNm"),
                        support_type=item.get("bsnsSupportTypeCd"),
                        start_date=start_dt,
                        end_date=end_dt,
                        closed_at=closed_at,
                        status=status,
                        apply_url=apply_url,
                        content_raw=content_raw,
                        target_logic=enriched.get("target_logic"),
                        bonus_logic=enriched.get("bonus_logic"),
                        ai_summary=enriched.get("ai_summary"),
                        ai_full_explanation=enriched.get("ai_full_explanation"),
                        is_active=True,
                        view_count=0,
                    )
                    .on_conflict_do_update(
                        index_elements=["origin_id"],
                        set_={
                            "title": title,
                            "agency_name": item.get("jrsdInsttNm") or "기관명 없음",
                            "category": item.get("pldirSportRealmLclasCodeNm") or "기타",
                            "region": item.get("areaNm"),
                            "start_date": start_dt,
                            "end_date": end_dt,
                            "closed_at": closed_at,
                            "status": status,
                            "apply_url": apply_url,
                            "content_raw": content_raw,
                            "target_logic": enriched.get("target_logic"),
                            "bonus_logic": enriched.get("bonus_logic"),
                            "ai_summary": enriched.get("ai_summary"),
                            "ai_full_explanation": enriched.get("ai_full_explanation"),
                        },
                    )
                )
                await self._session.execute(stmt)

            return True, None

        except Exception as db_err:
            logger.error(
                "[%s] ❌ DB 저장 실패: [%s] %s | apply_url=%s | 오류: %s",
                job_name, origin_id, title[:30], apply_url, db_err,
            )
            return False, {
                "origin_id": origin_id,
                "title": title[:50],
                "apply_url": apply_url,
                "error": str(db_err),
            }

    def _select_primary_file(
        self,
        *,
        print_flpth_nm: str | None,
        print_file_nm: str | None,
    ) -> tuple[str, str]:
        """printFlpthNm 과 printFileNm 에서 핵심 공고문 파일을 선택한다.

        [왜 이 로직이 필요한가?]
        기업마당 API의 printFlpthNm 필드는 "@" 로 연결된 여러 URL 을 포함할 수 있다.
        예: "https://bizinfo.go.kr/...fileSn=0@https://bizinfo.go.kr/...fileSn=1"

        같은 방식으로 printFileNm 도 "@" 구분자를 사용한다.
        예: "1. (공고문) 2026년 공고.hwp@2. (사업신청서식).hwp"

        이때 printFileNm 의 확장자를 보면 각 URL 이 어떤 파일인지 알 수 있다.
        우리가 원하는 것은 '공고 본문'이므로, PDF > HWP > HWPX 순으로 우선 선택한다.
        (양식 파일이나 일반 ZIP 은 파서로 처리하기 어렵고, 공고 내용도 없다)

        [방어 코드]
        - print_flpth_nm 이 None 이거나 공백이면 즉시 빈 문자열을 반환한다.
        - URL 이 없으면 HTTP 요청을 시도하지 않는다.
        - URL 과 파일명 개수가 다를 수 있으므로 인덱스 범위를 안전하게 처리한다.

        Returns:
            (file_url, filename_hint)
            - file_url:      선택된 다운로드 URL (없으면 "")
            - filename_hint: 선택된 파일의 실제 파일명 (파서 결정 힌트용, 없으면 "")
        """
        # 방어: None 이거나 공백 → HTTP 요청 없이 즉시 반환
        if not print_flpth_nm or not print_flpth_nm.strip():
            return "", ""

        # @ 구분자로 분리 (공백 제거, 빈 문자열 필터링)
        urls = [u.strip() for u in print_flpth_nm.split("@") if u.strip()]
        names = [n.strip() for n in (print_file_nm or "").split("@") if n.strip()]

        if not urls:
            return "", ""

        # URL 과 파일명을 인덱스 기준으로 쌍으로 묶기
        # names 가 urls 보다 짧을 수 있으므로 인덱스 범위를 안전하게 처리한다.
        pairs: list[tuple[str, str]] = [
            (urls[i], names[i] if i < len(names) else "")
            for i in range(len(urls))
        ]

        # 우선순위 순서로 파일명 확장자 매칭
        # printFileNm 이 실제 파일명(예: "공고문.hwp")을 갖고 있으므로 신뢰도가 높다.
        for ext in _FILE_PRIORITY:
            for url, name in pairs:
                if name.lower().endswith(ext):
                    logger.debug(
                        "  [SELECT] 우선순위 매칭: %s (hint=%s)", url[-50:], name
                    )
                    return url, name

        # 우선순위 해당 파일 없음 → 첫 번째 URL 사용 (Magic Number 로 파서가 결정함)
        logger.debug(
            "  [SELECT] 우선순위 매칭 없음 → 첫 번째 파일 사용: %s", pairs[0][0][-50:]
        )
        return pairs[0]

    def _parse_period(self, period_str: str) -> tuple[date | None, date | None]:
        """'YYYY-MM-DD ~ YYYY-MM-DD' 형식의 기간 문자열을 파싱한다."""
        if "~" not in period_str:
            return None, None
        parts = period_str.split("~", 1)
        return self._parse_date(parts[0].strip()), self._parse_date(parts[1].strip())

    def _parse_date(self, date_str: str) -> date | None:
        """날짜 문자열을 date 객체로 변환한다. 실패 시 None 반환."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        except (ValueError, IndexError):
            return None
