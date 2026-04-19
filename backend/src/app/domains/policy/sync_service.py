# src/app/domains/policy/sync_service.py
"""기업마당(Bizinfo) 정책 공고 수집 엔진.

설계 원칙:
  1. run_policy_sync 가 유일한 수집 파이프라인 진입점이다.
  2. 개별 공고 실패 격리 (savepoint 전략).
  3. BatchLog 즉시 커밋 전략.
  4. 데이터 무결성: AI 분석 성공시에만 해당 필드를 업데이트하여 기존 데이터를 보호한다.
  5. 병렬 처리: asyncio.Semaphore를 활용하여 수집 속도를 최적화한다.
"""

from __future__ import annotations

import logging
import math
import asyncio  # 병렬 처리를 위해 추가
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

_FILE_PRIORITY = (".pdf", ".hwp", ".hwpx")


class BizinfoSyncService:
    """기업마당 API 데이터를 PostgreSQL DB로 동기화하는 핵심 수집 엔진."""

    _API_URL = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"
    _CONCURRENCY_LIMIT = 5  # 동시 처리 세마포어 제한

    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
        agent: PolicySyncAgent,
    ) -> None:
        self._session = session
        self._repo = repo
        self._agent = agent

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
        if not BIZINFO_API_KEY:
            logger.error("[%s] BIZINFO_API_KEY 미설정 — 수집 중단", job_name)
            return {"status": "error", "message": "BIZINFO_API_KEY 미설정"}

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
            for page_no in range(page_start, page_end + 1):
                try:
                    raw_items = await self._fetch_single_page(
                        page_no=page_no,
                        rows_per_page=rows_per_page,
                        date_from=date_from,
                        date_to=date_to,
                    )
                except Exception as page_err:
                    error_log.append({"page": page_no, "error": str(page_err)})
                    continue

                if not raw_items:
                    break

                unique_items = list(
                    {
                        item["pblancId"]: item
                        for item in raw_items
                        if item.get("pblancId")
                    }.values()
                )
                total_items += len(unique_items)

                # --- [개선] 페이지 내 공고 병렬 처리 ---
                semaphore = asyncio.Semaphore(self._CONCURRENCY_LIMIT)

                async def sem_process(item):
                    async with semaphore:
                        return await self._process_single_item(
                            item=item,
                            with_ai=with_ai,
                            job_name=job_name,
                        )

                results = await asyncio.gather(*[sem_process(item) for item in unique_items])

                # 결과 집계
                for ai_status, db_ok, err_info in results:
                    if db_ok:
                        # DB 저장이 성공한 경우에만 성공 카운트
                        if with_ai:
                            if ai_status == "SUCCESS":
                                success_count += 1
                            elif ai_status == "PARSE_ERROR":
                                parse_error_count += 1
                            elif ai_status == "ANALYSIS_ERROR":
                                analysis_error_count += 1
                        else:
                            success_count += 1
                    else:
                        db_fail_count += 1
                        if err_info:
                            error_log.append(err_info)

                await self._session.flush()

            await self._session.commit()

            self._print_batch_report(
                job_name=job_name,
                total_items=total_items,
                success_count=success_count,
                parse_error_count=parse_error_count,
                analysis_error_count=analysis_error_count,
                db_fail_count=db_fail_count,
                with_ai=with_ai,
            )

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
                    error_details={"fatal_error": str(fatal_err)},
                    finished_at=datetime.utcnow(),
                )
            )
            await self._session.commit()
            return {"status": "error", "message": str(fatal_err)}

    async def _process_single_item(
        self,
        *,
        item: dict[str, Any],
        with_ai: bool,
        job_name: str,
        debug_mode: bool = False,
    ) -> tuple[str, bool, dict[str, Any] | None]:
        origin_id = item.get("pblancId", "UNKNOWN")
        title = item.get("pblancNm", "제목 없음")
        apply_url = item.get("pblancUrl") or ""

        # [1] 기본 필드 파싱
        start_dt, end_dt = self._parse_period(item.get("reqstBeginEndDe", ""))
        today = datetime.now().date()
        closed_at = end_dt if end_dt else date(9999, 12, 31)
        status = PolicyStatus.CLOSED if (end_dt and end_dt < today) else PolicyStatus.RECRUITING

        # [2] HTML 정제 및 Fallback 구성
        summary_clean = clean_html_text(item.get("bsnsSumryCn") or "")
        target = item.get("trgetNm") or "정보 없음"
        fallback_content_raw = f"[지원대상]\n{target}\n\n[상세내용]\n{summary_clean}"

        # [3] 파일 선택
        file_url, filename_hint = self._select_primary_file(
            print_flpth_nm=item.get("printFlpthNm"),
            print_file_nm=item.get("printFileNm"),
        )

        # [4] AI 에이전트 실행
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
                enriched = agent_state["structured_data"]
                content_raw = enriched.get("content_raw", fallback_content_raw)

        # [5] DB Upsert - 동적 필드 구성 (기존 데이터 보호 핵심)
        values = {
            "origin_id": origin_id,
            "title": title,
            "agency_name": item.get("jrsdInsttNm") or "기관명 없음",
            "category": item.get("pldirSportRealmLclasCodeNm") or "기타",
            "region": item.get("areaNm"),
            "support_type": item.get("bsnsSupportTypeCd"),
            "start_date": start_dt,
            "end_date": end_dt,
            "closed_at": closed_at,
            "status": status,
            "apply_url": apply_url,
            "content_raw": content_raw,
            "is_active": True,
        }

        # 업데이트 대상 필드 (공통 필드)
        update_set = {
            "title": title,
            "agency_name": values["agency_name"],
            "category": values["category"],
            "region": values["region"],
            "start_date": start_dt,
            "end_date": end_dt,
            "closed_at": closed_at,
            "status": status,
            "apply_url": apply_url,
            "content_raw": content_raw,
        }

        # AI 분석이 성공한 경우에만 AI 필드들을 업데이트 대상에 추가
        if ai_status == "SUCCESS":
            ai_fields = {
                "target_logic": enriched.get("target_logic"),
                "bonus_logic": enriched.get("bonus_logic"),
                "ai_summary": enriched.get("ai_summary"),
                "ai_full_explanation": enriched.get("ai_full_explanation"),
            }
            values.update(ai_fields)
            update_set.update(ai_fields)

        try:
            async with self._session.begin_nested():
                stmt = (
                    insert(Policy)
                    .values(**values)
                    .on_conflict_do_update(
                        index_elements=["origin_id"],
                        set_=update_set,
                    )
                )
                await self._session.execute(stmt)
            return ai_status, True, None
        except Exception as db_err:
            return ai_status, False, {"origin_id": origin_id, "error": str(db_err)}

    async def bootstrap_historical_policies(self, total_count: int = 1000, *, with_ai: bool = False) -> dict[str, Any]:
        page_end = math.ceil(total_count / 100)
        return await self.run_policy_sync(
            job_name="POLICY_BOOTSTRAP",
            page_start=1,
            page_end=page_end,
            rows_per_page=100,
            with_ai=with_ai,
        )

    async def sync_recent_policies(self) -> dict[str, Any]:
        return await self.run_policy_sync(
            job_name="POLICY_DAILY_SYNC",
            page_start=1,
            page_end=2,
            rows_per_page=100,
            with_ai=False,
        )

    async def test_sync_single_policy(self, page_no: int = 1) -> dict[str, Any]:
        raw_items = await self._fetch_single_page(page_no=page_no, rows_per_page=1, date_from=None, date_to=None)
        if not raw_items:
            return {"status": "no_items"}
        
        ai_status, db_ok, err_info = await self._process_single_item(
            item=raw_items[0], with_ai=True, job_name=f"TEST_{page_no}", debug_mode=True
        )
        return {"status": "success" if db_ok else "db_fail", "ai_status": ai_status, "db_saved": db_ok, "error": err_info}

    async def _fetch_single_page(self, *, page_no: int, rows_per_page: int, date_from: str | None, date_to: str | None) -> list[dict]:
        params = {"serviceKey": BIZINFO_API_KEY, "dataType": "json", "numOfRows": rows_per_page, "pageNo": page_no}
        if date_from: params["pblancBgnDe"] = date_from
        if date_to: params["pblancEndDe"] = date_to

        async with httpx.AsyncClient() as client:
            response = await client.get(self._API_URL, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return [items] if isinstance(items, dict) else (items if isinstance(items, list) else [])

    def _select_primary_file(self, *, print_flpth_nm: str | None, print_file_nm: str | None) -> tuple[str, str]:
        if not print_flpth_nm: return "", ""
        urls = [u.strip() for u in print_flpth_nm.split("@") if u.strip()]
        names = [n.strip() for n in (print_file_nm or "").split("@") if n.strip()]
        if not urls: return "", ""
        
        for ext in _FILE_PRIORITY:
            for i, name in enumerate(names):
                if name.lower().endswith(ext):
                    return urls[i], name
        return urls[0], names[0] if names else ""

    def _parse_period(self, period_str: str) -> tuple[date | None, date | None]:
        if "~" not in period_str: return None, None
        parts = period_str.split("~", 1)
        return self._parse_date(parts[0].strip()), self._parse_date(parts[1].strip())

    def _parse_date(self, date_str: str) -> date | None:
        if not date_str: return None
        try:
            return datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        except: return None

    @staticmethod
    def _print_batch_report(
        *, job_name: str, total_items: int, success_count: int, 
        parse_error_count: int, analysis_error_count: int, db_fail_count: int, with_ai: bool
    ) -> None:
        report = (
            f"\n{'=' * 50}\n[리포트] {job_name}\n{'=' * 50}\n"
            f"- 시도: {total_items}건\n"
            f"- 성공: {success_count}건\n"
        )
        if with_ai:
            report += f"- 파싱에러: {parse_error_count}건\n- 분석에러: {analysis_error_count}건\n"
        report += f"- DB실패: {db_fail_count}건\n{'=' * 50}"
        logger.info(report)