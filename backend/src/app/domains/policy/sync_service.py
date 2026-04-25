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

import asyncio  # 병렬 처리를 위해 추가
import json
import logging
import math
import os
import random
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.agents.policy_sync_agent import PolicySyncAgent
from src.app.core.config import BIZINFO_API_KEY
from src.app.domains.policy.embedding_service import PolicyEmbeddingService
from src.app.domains.policy.infrastructure import clean_html_text
from src.app.domains.policy.model import Policy, PolicyStatus
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.system.model import BatchLog

logger = logging.getLogger(__name__)

_FILE_PRIORITY = (".pdf", ".hwp", ".hwpx")


class BizinfoSyncService:
    """기업마당 API 데이터를 PostgreSQL DB로 동기화하는 핵심 수집 엔진."""

    _API_URL = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"
    _CONCURRENCY_LIMIT = 2  # 동시 처리 세마포어 제한 (OpenAI TPM 30,000 기준 안전값)

    def __init__(
        self,
        session: AsyncSession,
        repo: PolicyRepository,
        agent: PolicySyncAgent,
        embedding_service: PolicyEmbeddingService | None = None,
    ) -> None:
        self._session = session
        self._repo = repo
        self._agent = agent
        self._embedding_service = embedding_service

    async def run_policy_sync(
        self,
        *,
        job_name: str = "POLICY_SYNC",
        page_start: int = 1,
        page_end: int = 1,
        rows_per_page: int = 100,
        with_ai: bool = False,
        with_embedding: bool = False,
        date_from: str | None = None,
        date_to: str | None = None,
        known_total: int | None = None,
    ) -> dict[str, Any]:
        if not BIZINFO_API_KEY:
            logger.error("[%s] BIZINFO_API_KEY 미설정 — 수집 중단", job_name)
            return {"status": "error", "message": "BIZINFO_API_KEY 미설정"}

        batch = BatchLog(
            job_name=job_name,
            status="RUNNING",
            total_count=known_total or 0,
            success_count=0,
            fail_count=0,
            api_error_count=0,
            parse_error_count=0,
            analysis_error_count=0,
            db_fail_count=0,
        )
        self._session.add(batch)
        await self._session.commit()
        batch_id = batch.id

        total_items = 0
        success_count = 0
        api_error_count = 0
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
                    api_error_count += 1
                    error_log.append(
                        {"stage": "API", "page": page_no, "reason": str(page_err)}
                    )
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
                        result = await self._process_single_item(
                            item=item,
                            with_ai=with_ai,
                            with_embedding=with_embedding,
                            job_name=job_name,
                        )
                        if with_ai:
                            # OpenAI TPM 제한(30,000) 초과 방지를 위해 공고 간 딜레이
                            await asyncio.sleep(3)
                        return result

                results = await asyncio.gather(
                    *[sem_process(item) for item in unique_items]
                )

                # 결과 집계 — DB 성공 여부와 무관하게 AI 실패도 error_log에 기록
                for ai_status, db_ok, err_info in results:
                    if db_ok:
                        if with_ai:
                            if ai_status == "SUCCESS":
                                success_count += 1
                            elif ai_status == "PARSE_ERROR":
                                parse_error_count += 1
                                if err_info:
                                    error_log.append(err_info)
                            elif ai_status == "ANALYSIS_ERROR":
                                analysis_error_count += 1
                                if err_info:
                                    error_log.append(err_info)
                        else:
                            success_count += 1
                    else:
                        db_fail_count += 1
                        if err_info:
                            error_log.append(err_info)

                # 페이지 완료마다 commit + BatchLog progress 갱신 (실시간 모니터링용)
                await self._session.execute(
                    sa_update(BatchLog)
                    .where(BatchLog.id == batch_id)
                    .values(
                        processed_count=total_items,
                        success_count=success_count,
                        fail_count=(db_fail_count + parse_error_count + analysis_error_count + api_error_count),
                    )
                )
                await self._session.commit()

            # 루프 완료 후 최종 상태 확정 (SUCCESS / FAILED는 아래 블록에서 처리)

            self._print_batch_report(
                job_name=job_name,
                total_items=total_items,
                success_count=success_count,
                parse_error_count=parse_error_count,
                analysis_error_count=analysis_error_count,
                db_fail_count=db_fail_count,
                with_ai=with_ai,
            )

            fail_count = (
                api_error_count
                + parse_error_count
                + analysis_error_count
                + db_fail_count
            )
            error_details = (
                {
                    "summary": {
                        "api": api_error_count,
                        "parse": parse_error_count,
                        "analysis": analysis_error_count,
                        "db": db_fail_count,
                    },
                    "items": error_log[:100],
                }
                if error_log
                else None
            )
            await self._session.execute(
                sa_update(BatchLog)
                .where(BatchLog.id == batch_id)
                .values(
                    status="SUCCESS",
                    total_count=total_items,
                    success_count=success_count,
                    fail_count=fail_count,
                    api_error_count=api_error_count,
                    parse_error_count=parse_error_count,
                    analysis_error_count=analysis_error_count,
                    db_fail_count=db_fail_count,
                    error_details=error_details,
                    finished_at=datetime.utcnow(),
                )
            )
            await self._session.commit()

            return {
                "status": "success",
                "total": total_items,
                "success": success_count,
                "api_error": api_error_count,
                "parse_error": parse_error_count,
                "analysis_error": analysis_error_count,
                "db_fail": db_fail_count,
            }

        except Exception as fatal_err:
            await self._session.rollback()
            logger.error("[%s] 치명적 오류 — 트랜잭션 롤백: %s", job_name, fatal_err)

            fail_count = (
                api_error_count
                + parse_error_count
                + analysis_error_count
                + db_fail_count
            )
            await self._session.execute(
                sa_update(BatchLog)
                .where(BatchLog.id == batch_id)
                .values(
                    status="FAILED",
                    total_count=total_items,
                    success_count=success_count,
                    fail_count=fail_count,
                    api_error_count=api_error_count,
                    parse_error_count=parse_error_count,
                    analysis_error_count=analysis_error_count,
                    db_fail_count=db_fail_count,
                    error_details={
                        "summary": {
                            "api": api_error_count,
                            "parse": parse_error_count,
                            "analysis": analysis_error_count,
                            "db": db_fail_count,
                        },
                        "fatal_error": str(fatal_err),
                        "items": error_log[:100],
                    },
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
        with_embedding: bool = False,
        job_name: str,
        debug_mode: bool = False,
    ) -> tuple[str, bool, dict[str, Any] | None]:
        origin_id = item.get("pblancId", "UNKNOWN")
        title = item.get("pblancNm", "제목 없음")
        apply_url = item.get("pblancUrl") or ""

        # [1] 기본 필드 파싱
        start_dt, end_dt = self._parse_period(item.get("reqstBeginEndDe", ""))
        today = datetime.now().date()
        base_closed_at = end_dt if end_dt else date(9999, 12, 31)  # noqa: F841
        _status = (
            PolicyStatus.CLOSED
            if (end_dt and end_dt < today)
            else PolicyStatus.RECRUITING
        )

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
        ai_err_info: dict[str, Any] | None = None

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
            elif ai_status == "PARSE_ERROR":
                retry_count = agent_state.get("parse_retry_count", 0)
                ai_err_info = {
                    "stage": "PARSE",
                    "origin_id": origin_id,
                    "title": title,
                    "reason": f"첨부파일 텍스트 추출 실패 ({retry_count}회 시도) — fallback 저장",
                }
            elif ai_status == "ANALYSIS_ERROR":
                validation_errors = agent_state.get("validation_errors") or []
                ai_err_info = {
                    "stage": "ANALYSIS",
                    "origin_id": origin_id,
                    "title": title,
                    "reason": ", ".join(validation_errors)
                    if validation_errors
                    else "AI 검증 실패 (최대 재시도 초과)",
                }

        ai_fields: dict[str, Any] = {}
        if ai_status == "SUCCESS":
            ai_fields = self._extract_ai_policy_fields(enriched)

        resolved_title = ai_fields.get("title") or title
        resolved_agency_name = ai_fields.get("agency_name") or item.get("jrsdInsttNm") or "기관명 없음"
        resolved_category = ai_fields.get("category") or item.get("pldirSportRealmLclasCodeNm") or "기타"
        resolved_support_type = ai_fields.get("support_type") or item.get("bsnsSupportTypeCd")
        resolved_region = ai_fields.get("region") or item.get("areaNm")
        resolved_start_dt = ai_fields.get("start_date") or start_dt
        resolved_end_dt = ai_fields.get("end_date") or end_dt
        resolved_closed_at = resolved_end_dt if resolved_end_dt else date(9999, 12, 31)
        resolved_status = (
            PolicyStatus.CLOSED
            if (resolved_end_dt and resolved_end_dt < today)
            else PolicyStatus.RECRUITING
        )

        # [5] with_ai 모드에서 파싱/분석 실패한 공고는 저장하지 않고 스킵
        # 포트폴리오용 데이터 품질 보장 — 잘못된 데이터로 DB를 오염시키지 않음
        if with_ai and ai_status in ("PARSE_ERROR", "ANALYSIS_ERROR"):
            logger.info(
                "[%s] %s — DB 저장 스킵 (with_ai=True 품질 기준 미달)",
                origin_id, ai_status,
            )
            return ai_status, False, ai_err_info

        # [6] DB Upsert - 동적 필드 구성 (기존 데이터 보호 핵심)
        values = {
            "origin_id": origin_id,
            "title": resolved_title,
            "agency_name": resolved_agency_name,
            "category": resolved_category,
            "region": resolved_region,
            "support_type": resolved_support_type,
            "start_date": resolved_start_dt,
            "end_date": resolved_end_dt,
            "closed_at": resolved_closed_at,
            "status": resolved_status,
            "apply_url": apply_url,
            "content_raw": content_raw,
            "is_active": True,
        }

        # 업데이트 대상 필드 (공통 필드)
        update_set = {
            "title": values["title"],
            "agency_name": values["agency_name"],
            "category": values["category"],
            "region": values["region"],
            "support_type": values["support_type"],
            "start_date": values["start_date"],
            "end_date": values["end_date"],
            "closed_at": values["closed_at"],
            "status": values["status"],
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
                "required_documents": enriched.get("required_documents"),
                "max_support": self._coerce_int((enriched.get("support_amount") or {}).get("max")),
                "min_support": self._coerce_int((enriched.get("support_amount") or {}).get("min")),
                "support_amount_desc": (enriched.get("support_amount") or {}).get("description"),
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

                # [6] 임베딩 트리거 — DB 저장 성공 후, 내용이 변경된 경우에만 실행
                # savepoint 내부에서 실행하여 실패 시 upsert도 롤백되도록 격리합니다.
                if with_embedding and self._embedding_service is not None:
                    policy = await self._repo.get_policy_by_origin_id(origin_id)
                    if policy:
                        try:
                            await self._embedding_service.sync_policy_chunks(
                                policy_id=policy.id,
                                content_raw=content_raw,
                                policy_title=title,
                                agency_name=values.get("agency_name", ""),
                                support_type=values.get("support_type", ""),
                            )
                        except Exception as emb_err:
                            # 임베딩 실패는 경고 로그만 남기고 DB 저장은 유지합니다.
                            logger.warning(
                                "[%s] 임베딩 실패 (DB 저장은 유지됨): %s",
                                origin_id,
                                emb_err,
                            )

            return ai_status, True, ai_err_info
        except Exception as db_err:
            return (
                ai_status,
                False,
                {
                    "stage": "DB",
                    "origin_id": origin_id,
                    "title": title,
                    "reason": str(db_err),
                },
            )

    async def run_policy_sync_full(
        self,
        *,
        with_ai: bool = False,
        rows_per_page: int = 100,
    ) -> dict[str, Any]:
        """기업마당 전체 공고를 totalCount 기반으로 누락 없이 수집합니다.

        totalCount를 먼저 조회하여 실제 전체 페이지 수를 계산하고,
        첫 페이지부터 마지막 페이지까지 전수 수집합니다.
        """
        total = await self._fetch_total_count()
        if total <= 0:
            return {"status": "error", "message": "기업마당 totalCount 조회 실패"}

        page_end = math.ceil(total / rows_per_page)
        logger.info("[전수수집] 전체 %d건 / %d페이지 수집 시작", total, page_end)
        return await self.run_policy_sync(
            job_name="POLICY_FULL_SYNC",
            page_start=1,
            page_end=page_end,
            rows_per_page=rows_per_page,
            with_ai=with_ai,
            known_total=total,
        )

    async def bootstrap_historical_policies(
        self, total_count: int = 1000, *, with_ai: bool = False
    ) -> dict[str, Any]:
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

    async def test_sync_single_policy(self) -> dict[str, Any]:
        """기업마당 전체 공고 중 랜덤 1건을 선택해 파이프라인을 검증합니다.

        1. totalCount를 조회하여 실제 전체 공고 수를 파악합니다.
        2. 전체 범위에서 랜덤 페이지를 선택합니다.
        3. 해당 공고 1건에 대해 전체 파이프라인(파싱 → AI → DB)을 실행합니다.
        4. debug_output/{origin_id}/ 폴더에 단계별 파일을 저장합니다.
        """
        # [1] 전체 공고 수 조회 후 랜덤 페이지 선택
        total_count = await self._fetch_total_count()
        if total_count <= 0:
            return {"status": "error", "message": "기업마당 API totalCount 조회 실패"}

        # numOfRows=1 기준 각 페이지가 공고 1건이므로 pageNo = 공고 인덱스
        random_page = random.randint(1, min(total_count, 9999))
        logger.info("[TEST] 전체 공고 %d건 중 랜덤 선택 → pageNo=%d", total_count, random_page)

        raw_items = await self._fetch_single_page(
            page_no=random_page, rows_per_page=1, date_from=None, date_to=None
        )
        if not raw_items:
            return {"status": "no_items", "tested_page": random_page}

        item = raw_items[0]
        origin_id = item.get("pblancId", "UNKNOWN")

        ai_status, db_ok, err_info = await self._process_single_item(
            item=item,
            with_ai=True,
            with_embedding=True,
            job_name=f"TEST_{random_page}",
            debug_mode=True,
        )

        debug_output_dir = None
        if db_ok:
            await self._session.commit()
            await self._save_debug_db_snapshot(origin_id)
            debug_output_dir = os.path.join("debug_output", origin_id)

        return {
            "status": "success" if db_ok else "db_fail",
            "ai_status": ai_status,
            "db_saved": db_ok,
            "total_count": total_count,
            "tested_page": random_page,
            "origin_id": origin_id,
            "error": err_info,
            "debug_output_dir": debug_output_dir,
        }

    async def _save_debug_db_snapshot(self, origin_id: str) -> None:
        """DB에 실제 저장된 policy 레코드를 4_db_saved.json으로 스냅샷합니다."""
        try:
            policy = await self._repo.get_policy_by_origin_id(origin_id)
            if policy is None:
                logger.warning(
                    "[DEBUG] DB 스냅샷 실패 — origin_id=%s 조회 결과 없음", origin_id
                )
                return

            snapshot = {
                "id": str(policy.id),
                "origin_id": policy.origin_id,
                "title": policy.title,
                "agency_name": policy.agency_name,
                "category": policy.category,
                "support_type": policy.support_type,
                "region": policy.region,
                "start_date": str(policy.start_date) if policy.start_date else None,
                "end_date": str(policy.end_date) if policy.end_date else None,
                "closed_at": str(policy.closed_at),
                "status": policy.status.value if policy.status else None,
                "apply_url": policy.apply_url,
                "content_raw": policy.content_raw,
                "ai_summary": policy.ai_summary,
                "ai_full_explanation": policy.ai_full_explanation,
                "target_logic": policy.target_logic,
                "bonus_logic": policy.bonus_logic,
                "required_documents": policy.required_documents,
                "max_support": policy.max_support,
                "min_support": policy.min_support,
                "support_amount_desc": policy.support_amount_desc,
                "is_active": policy.is_active,
                "view_count": policy.view_count,
                "created_at": str(policy.created_at) if policy.created_at else None,
            }

            debug_dir = os.path.join("debug_output", origin_id)
            os.makedirs(debug_dir, exist_ok=True)
            filepath = os.path.join(debug_dir, "4_db_saved.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=4)
            logger.info("[DEBUG] DB 스냅샷 저장 완료: %s", filepath)
        except Exception as exc:
            logger.warning(
                "[DEBUG] DB 스냅샷 저장 실패 (origin_id=%s): %s", origin_id, exc
            )

    async def _fetch_total_count(self) -> int:
        """기업마당 API에서 전체 공고 수(totalCount)를 조회합니다."""
        params = {
            "serviceKey": BIZINFO_API_KEY,
            "dataType": "json",
            "numOfRows": 1,
            "pageNo": 1,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._API_URL, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
            total = int(
                data.get("response", {}).get("body", {}).get("totalCount", 0)
            )
            logger.info("[totalCount] 기업마당 전체 공고 수: %d", total)
            return total
        except Exception as exc:
            logger.warning("[totalCount] 조회 실패: %s", exc)
            return 0

    async def _fetch_single_page(
        self,
        *,
        page_no: int,
        rows_per_page: int,
        date_from: str | None,
        date_to: str | None,
    ) -> list[dict]:
        params = {
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

        items = (
            data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        )
        return (
            [items]
            if isinstance(items, dict)
            else (items if isinstance(items, list) else [])
        )

    def _select_primary_file(
        self, *, print_flpth_nm: str | None, print_file_nm: str | None
    ) -> tuple[str, str]:
        if not print_flpth_nm:
            return "", ""
        urls = [u.strip() for u in print_flpth_nm.split("@") if u.strip()]
        names = [n.strip() for n in (print_file_nm or "").split("@") if n.strip()]
        if not urls:
            return "", ""

        for ext in _FILE_PRIORITY:
            for i, name in enumerate(names):
                if name.lower().endswith(ext):
                    return urls[i], name
        return urls[0], names[0] if names else ""

    def _parse_period(self, period_str: str) -> tuple[date | None, date | None]:
        if "~" not in period_str:
            return None, None
        parts = period_str.split("~", 1)
        return self._parse_date(parts[0].strip()), self._parse_date(parts[1].strip())

    def _parse_date(self, date_str: str) -> date | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        except Exception:
            return None

    def _extract_ai_policy_fields(self, enriched: dict[str, Any]) -> dict[str, Any]:
        """AI 구조화 결과를 Policy 테이블 컬럼 기준으로 정규화한다."""
        dates = enriched.get("dates") or {}
        return {
            "title": enriched.get("title"),
            "agency_name": enriched.get("agency_name"),
            "category": enriched.get("category"),
            "support_type": enriched.get("support_type"),
            "region": enriched.get("region"),
            "start_date": self._parse_date(dates.get("start_date")),
            "end_date": self._parse_date(dates.get("end_date")),
        }

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value.replace(",", "").strip()))
            except ValueError:
                return None
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
        report = (
            f"\n{'=' * 50}\n[리포트] {job_name}\n{'=' * 50}\n"
            f"- 시도: {total_items}건\n"
            f"- 성공: {success_count}건\n"
        )
        if with_ai:
            report += f"- 파싱에러: {parse_error_count}건\n- 분석에러: {analysis_error_count}건\n"
        report += f"- DB실패: {db_fail_count}건\n{'=' * 50}"
        logger.info(report)
