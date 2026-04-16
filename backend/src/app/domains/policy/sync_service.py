# src/app/domains/policy/sync_service.py
"""기업마당(Bizinfo) 정책 공고 수집 엔진.

설계 원칙:
  1. run_policy_sync 가 유일한 수집 파이프라인 진입점이다.
     - 스케줄러(새벽 3시 자동)와 관리자 API(수동 트리거) 모두 이 메서드를 호출한다.
     - bootstrap / daily / test 는 모두 얇은 래퍼(thin wrapper)다.

  2. 개별 공고 실패 격리 (savepoint 전략):
     - 각 공고의 DB INSERT 는 begin_nested() 세이브포인트 안에서 실행된다.
     - 특정 공고가 실패해도 세이브포인트만 롤백되므로 이전 성공 건은 보존된다.

  3. BatchLog 즉시 커밋 전략:
     - BatchLog 는 수집 시작 직후 즉시 커밋한다.
     - 이후 치명적 오류로 전체 롤백이 발생해도 BatchLog 기록은 유지된다.

  4. 다중 파일 처리 (@ 구분자):
     - printFlpthNm 이 "@" 로 연결된 여러 URL 을 포함할 수 있다.
     - _select_primary_file() 로 핵심 공고문 파일 하나를 우선 선택한다.

  5. AI 에이전트 Self-Correction 연동:
     - with_ai=True 시 PolicySyncAgent 를 통해 파싱·구조화·검증 3단계 실행.
     - 에이전트 반환 status 에 따라 parse_error_count / analysis_error_count 집계.
     - SUCCESS 인 경우에만 AI 분석 필드를 DB에 저장 (데이터 무결성).
     - PARSE_ERROR / ANALYSIS_ERROR 는 fallback content_raw 로만 DB 저장.

  6. 데이터 무결성 (AI 필드 보호):
     - status != SUCCESS 이면 target_logic / bonus_logic / ai_summary / ai_full_explanation
       을 NULL 로 유지하여 잘못된 부분 데이터가 DB에 들어가지 않도록 한다.

  7. 로그 추적:
     - 모든 공고 처리 로그에 origin_id 를 포함하여 대량 병렬 처리 시에도 추적 가능.
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

from src.app.agents.policy_sync_agent import PolicySyncAgent
from src.app.core.config import BIZINFO_API_KEY
from src.app.domains.policy.infrastructure import clean_html_text
from src.app.domains.policy.model import Policy, PolicyStatus
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.system.model import BatchLog

logger = logging.getLogger(__name__)

# ── 파일 우선순위 (핵심 공고문 선택 기준) ──────────────────────────────────────
_FILE_PRIORITY = (".pdf", ".hwp", ".hwpx")


class BizinfoSyncService:
    """기업마당 API 데이터를 PostgreSQL DB로 동기화하는 핵심 수집 엔진."""

    _API_URL = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"

    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
        agent: PolicySyncAgent,
    ) -> None:
        self._session = session
        self._repo = repo
        self._agent = agent

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
            date_from:     API 날짜 필터 시작일 (YYYYMMDD 형식)
            date_to:       API 날짜 필터 종료일 (YYYYMMDD 형식)
        """
        if not BIZINFO_API_KEY:
            logger.error("[%s] BIZINFO_API_KEY 미설정 — 수집 중단", job_name)
            return {"status": "error", "message": "BIZINFO_API_KEY 미설정"}

        logger.info(
            "[%s] 수집 시작 | 페이지: %d~%d | rows/page: %d | AI: %s",
            job_name,
            page_start,
            page_end,
            rows_per_page,
            with_ai,
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
        parse_error_count = 0
        analysis_error_count = 0
        db_fail_count = 0
        error_log: list[dict] = []

        try:
            # ── [STEP 2] 페이지 순회 ─────────────────────────────────────
            for page_no in range(page_start, page_end + 1):
                logger.info(
                    "[%s] 페이지 %d / %d 호출 중...",
                    job_name,
                    page_no,
                    page_end,
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
                        "[%s] 페이지 %d API 호출 실패: %s",
                        job_name,
                        page_no,
                        page_err,
                    )
                    error_log.append({"page": page_no, "error": str(page_err)})
                    continue

                if not raw_items:
                    logger.info(
                        "[%s] 페이지 %d: 항목 없음 — 순회 조기 종료",
                        job_name,
                        page_no,
                    )
                    break

                # origin_id 기준 중복 제거
                unique_items = list(
                    {
                        item["pblancId"]: item
                        for item in raw_items
                        if item.get("pblancId")
                    }.values()
                )
                total_items += len(unique_items)

                logger.info(
                    "[%s] 페이지 %d: %d건 처리 시작",
                    job_name,
                    page_no,
                    len(unique_items),
                )

                # ── [STEP 3] 공고별 개별 처리 ────────────────────────────
                for item in unique_items:
                    ai_status, db_ok, err_info = await self._process_single_item(
                        item=item,
                        with_ai=with_ai,
                        job_name=job_name,
                        debug_mode=False,
                    )
                    # AI 파이프라인 상태 집계
                    if ai_status == "SUCCESS":
                        success_count += 1
                    elif ai_status == "PARSE_ERROR":
                        parse_error_count += 1
                    elif ai_status == "ANALYSIS_ERROR":
                        analysis_error_count += 1
                    elif with_ai is False:
                        # AI 없이 기본 저장 → 성공으로 간주
                        success_count += 1

                    if not db_ok and err_info:
                        db_fail_count += 1
                        error_log.append(err_info)

                await self._session.flush()

            # ── [STEP 4] 전체 커밋 ──────────────────────────────────────
            await self._session.commit()

            # ── [STEP 5] 배치 리포트 출력 (with_ai 여부와 무관하게 항상 출력) ──
            self._print_batch_report(
                job_name=job_name,
                total_items=total_items,
                success_count=success_count,
                parse_error_count=parse_error_count,
                analysis_error_count=analysis_error_count,
                db_fail_count=db_fail_count,
                with_ai=with_ai,
            )

            # ── [STEP 6] BatchLog 완료 처리 ─────────────────────────────
            fail_count = parse_error_count + analysis_error_count + db_fail_count
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

            return {
                "status": "success",
                "job_name": job_name,
                "total": total_items,
                "success": success_count,
                "parse_error": parse_error_count,
                "analysis_error": analysis_error_count,
                "db_fail": db_fail_count,
            }

        except Exception as fatal_err:
            await self._session.rollback()
            logger.error("[%s] 치명적 오류 — 트랜잭션 롤백: %s", job_name, fatal_err)

            fail_count = parse_error_count + analysis_error_count + db_fail_count
            await self._session.execute(
                sa_update(BatchLog)
                .where(BatchLog.id == batch_id)
                .values(
                    status="FAILED",
                    total_count=total_items,
                    success_count=success_count,
                    fail_count=fail_count,
                    error_details={
                        "fatal_error": str(fatal_err),
                        "errors": error_log[:20],
                    },
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

    async def test_sync_single_policy(self, page_no: int = 1) -> dict[str, Any]:
        """[TEST] 특정 페이지의 공고 1건을 가져와 AI 파이프라인 + 디버그 파일 생성 검증.

        debug_mode=True 로 에이전트를 실행하여 3개의 디버그 파일을 생성한다:
          debug_1_api_raw.json       — API 원본 응답
          debug_2_extracted_text.txt — 파서 추출 텍스트
          debug_3_ai_result.json     — AI 구조화 결과
        """
        logger.info("=" * 60)
        logger.info("[TEST] %d페이지의 공고 동기화 테스트 시작 (debug_mode=True)", page_no)
        logger.info("=" * 60)

        # 단일 아이템 직접 처리 (debug_mode=True)
        raw_items = await self._fetch_single_page(
            page_no=page_no,
            rows_per_page=1,
            date_from=None,
            date_to=None,
        )
        if not raw_items:
            logger.warning("[TEST] 페이지 %d: 항목 없음", page_no)
            return {"status": "no_items", "page_no": page_no}

        item = raw_items[0]
        origin_id = item.get("pblancId", "UNKNOWN")

        ai_status, db_ok, err_info = await self._process_single_item(
            item=item,
            with_ai=True,
            job_name=f"POLICY_TEST_PAGE_{page_no}",
            debug_mode=True,
        )

        logger.info("=" * 60)
        return {
            "status": "success" if db_ok else "db_fail",
            "origin_id": origin_id,
            "ai_status": ai_status,
            "db_saved": db_ok,
            "error": err_info,
            "page_no": page_no,
        }

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

        if isinstance(items_raw, dict):
            return [items_raw]
        return items_raw if isinstance(items_raw, list) else []

    async def _process_single_item(
        self,
        *,
        item: dict[str, Any],
        with_ai: bool,
        job_name: str,
        debug_mode: bool = False,
    ) -> tuple[str, bool, dict[str, Any] | None]:
        """단일 공고 아이템을 처리하고 DB에 upsert 한다.

        처리 순서:
          1. API 응답 기본 필드 파싱 (날짜, 상태, 기관명 등)
          2. bsnsSumryCn HTML 태그 제거 → fallback content_raw 구성
          3. printFlpthNm/@printFileNm 에서 핵심 파일 URL 선택
          4. with_ai=True 이면 PolicySyncAgent 실행 (파싱 → 구조화 → 검증)
          5. begin_nested() 세이브포인트 안에서 INSERT … ON CONFLICT DO UPDATE

        데이터 무결성 원칙:
          - ai_status == SUCCESS 인 경우에만 AI 분석 필드(target_logic, bonus_logic,
            ai_summary, ai_full_explanation)를 DB에 기록한다.
          - PARSE_ERROR / ANALYSIS_ERROR 는 fallback content_raw 만 저장하고
            AI 필드는 None 으로 유지한다.

        Returns:
            (ai_status, db_ok, err_info)
            - ai_status: 에이전트 실행 결과 ("SUCCESS"/"PARSE_ERROR"/"ANALYSIS_ERROR"/"N/A")
            - db_ok:     DB upsert 성공 여부
            - err_info:  실패 시 에러 컨텍스트 dict (성공이면 None)
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
        target = item.get("trgetNm") or "정보 없음"
        summary_raw = item.get("bsnsSumryCn") or ""
        summary_clean = clean_html_text(summary_raw)
        fallback_content_raw = f"[지원대상]\n{target}\n\n[상세내용]\n{summary_clean}"

        # ── [3] 핵심 공고문 파일 선택 (@ 다중 파일 처리) ────────────────
        file_url, filename_hint = self._select_primary_file(
            print_flpth_nm=item.get("printFlpthNm"),
            print_file_nm=item.get("printFileNm"),
        )

        # ── [4] AI 에이전트 실행 (선택적) ────────────────────────────────
        ai_status = "N/A"
        content_raw = fallback_content_raw
        enriched: dict[str, Any] = {}

        if with_ai:
            agent_state = await self._agent.run(
                raw_api_data=item,
                file_url=file_url,
                filename_hint=filename_hint,
                original_summary=summary_clean,
                origin_id=origin_id,
                debug_mode=debug_mode,
            )
            ai_status = agent_state["status"]

            if ai_status == "SUCCESS":
                # 데이터 무결성: SUCCESS 인 경우에만 AI 필드 반영
                enriched = agent_state["structured_data"]
                content_raw = enriched.get("content_raw", fallback_content_raw)
                logger.debug("[%s] AI 분석 성공: [%s]", job_name, origin_id)
            else:
                # PARSE_ERROR / ANALYSIS_ERROR: fallback 데이터로만 저장
                logger.warning(
                    "[%s] AI 파이프라인 %s — [%s] fallback content_raw 로 저장",
                    job_name,
                    ai_status,
                    origin_id,
                )

        # ── [5] DB Upsert — 세이브포인트 격리 ───────────────────────────
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
                        # AI 필드: SUCCESS 인 경우에만 채움, 나머지는 None
                        target_logic=enriched.get("target_logic") if ai_status == "SUCCESS" else None,
                        bonus_logic=enriched.get("bonus_logic") if ai_status == "SUCCESS" else None,
                        ai_summary=enriched.get("ai_summary") if ai_status == "SUCCESS" else None,
                        ai_full_explanation=enriched.get("ai_full_explanation") if ai_status == "SUCCESS" else None,
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
                            "target_logic": enriched.get("target_logic") if ai_status == "SUCCESS" else None,
                            "bonus_logic": enriched.get("bonus_logic") if ai_status == "SUCCESS" else None,
                            "ai_summary": enriched.get("ai_summary") if ai_status == "SUCCESS" else None,
                            "ai_full_explanation": enriched.get("ai_full_explanation") if ai_status == "SUCCESS" else None,
                        },
                    )
                )
                await self._session.execute(stmt)

            return ai_status, True, None

        except Exception as db_err:
            logger.error(
                "[%s] DB 저장 실패: [%s] %s | apply_url=%s | 오류: %s",
                job_name,
                origin_id,
                title[:30],
                apply_url,
                db_err,
            )
            return ai_status, False, {
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

        Returns:
            (file_url, filename_hint)
        """
        if not print_flpth_nm or not print_flpth_nm.strip():
            return "", ""

        urls = [u.strip() for u in print_flpth_nm.split("@") if u.strip()]
        names = [n.strip() for n in (print_file_nm or "").split("@") if n.strip()]

        if not urls:
            return "", ""

        pairs: list[tuple[str, str]] = [
            (urls[i], names[i] if i < len(names) else "") for i in range(len(urls))
        ]

        for ext in _FILE_PRIORITY:
            for url, name in pairs:
                if name.lower().endswith(ext):
                    logger.debug("  [SELECT] 우선순위 매칭: %s (hint=%s)", url[-50:], name)
                    return url, name

        logger.debug("  [SELECT] 우선순위 매칭 없음 → 첫 번째 파일 사용: %s", pairs[0][0][-50:])
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

    @staticmethod
    def _print_batch_report(
        *,
        job_name: str,
        total_items: int,
        success_count: int,
        parse_error_count: int,
        analysis_error_count: int,
        db_fail_count: int,
        with_ai: bool,
    ) -> None:
        """수집 작업 종료 리포트를 터미널에 출력한다."""
        if with_ai:
            report = (
                f"\n{'=' * 50}\n"
                f"[수집 작업 종료 리포트] {job_name}\n"
                f"{'=' * 50}\n"
                f"- 전체 시도 건수:                {total_items:,}건\n"
                f"- 최종 성공(SUCCESS):            {success_count:,}건\n"
                f"- 텍스트 추출 불량(PARSE_ERROR): {parse_error_count:,}건\n"
                f"- AI 분석 및 검증 실패(ANALYSIS_ERROR): {analysis_error_count:,}건\n"
                f"- DB 저장 실패:                  {db_fail_count:,}건\n"
                f"{'=' * 50}"
            )
        else:
            fail_count = db_fail_count
            report = (
                f"\n{'=' * 50}\n"
                f"[수집 작업 종료 리포트] {job_name}\n"
                f"{'=' * 50}\n"
                f"- 전체 시도 건수: {total_items:,}건\n"
                f"- 성공:           {success_count:,}건\n"
                f"- DB 저장 실패:   {fail_count:,}건\n"
                f"{'=' * 50}"
            )
        logger.info(report)
