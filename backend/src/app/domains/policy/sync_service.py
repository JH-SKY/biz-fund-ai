# src/app/domains/policy/sync_service.py
"""기업마당(Bizinfo) API 연동 및 정책 공고 자동화 서비스."""

from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import BIZINFO_API_KEY
from src.app.domains.policy.model import Policy, PolicyStatus
from src.app.domains.policy.repository import PolicyRepository

# 시스템 도메인에서 batch_logs 모델 가져오기 (테이블 명세서 14번)
from src.app.domains.system.model import BatchLog


class BizinfoSyncService:
    """기업마당 API 데이터를 우리 DB로 동기화하는 핵심 서비스."""

    def __init__(self, session: AsyncSession, repo: PolicyRepository):
        self._session = session
        self._repo = repo
        self._api_url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"

    # ── [핵심 1] 초기 1회 대량 적재 (Bootstrap) ──────────────────────────────
    async def bootstrap_historical_policies(self, count: int = 1000) -> dict:
        """
        서비스 최초 세팅 시 사용. (관리자가 수동으로 버튼 클릭)
        과거 데이터를 최대한 많이(기본 1000개) 긁어와서 우리 DB에 넣습니다.
        """
        return await self._execute_sync_job(
            job_name="POLICY_BOOTSTRAP", search_cnt=count
        )

    # ── [핵심 2] 매일 스마트 동기화 (Sync) ────────────────────────────────────
    async def sync_recent_policies(self) -> dict:
        """
        매일 돌아가는 정기 동기화.
        마지막 성공 날짜 이후로 크게 변경점이 있을 만한 최근 100건만 가볍게 가져와서 비교합니다.
        """
        return await self._execute_sync_job(
            job_name="POLICY_DAILY_SYNC", search_cnt=100
        )

    # ── [핵심 3] 공통 실행 로직 & 배치 로그 저장 ───────────────────────────────
    async def _execute_sync_job(self, job_name: str, search_cnt: int) -> dict:
        """API를 찌르고, DB에 넣고, 배치 로그(batch_logs)를 남기는 공통 함수"""

        if not BIZINFO_API_KEY:
            return {
                "status": "error",
                "message": "BIZINFO_API_KEY가 설정되지 않았습니다.",
            }

        # 1. 배치 로그 시작 기록
        batch_log = BatchLog(
            job_name=job_name,
            status="RUNNING",
            total_count=0,
            success_count=0,
            fail_count=0,
        )
        self._session.add(batch_log)
        await self._session.flush()

        try:
            # 2. 기업마당 API 호출
            params = {
                "crtfcKey": BIZINFO_API_KEY,
                "dataType": "json",
                "searchCnt": search_cnt,
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(self._api_url, params=params, timeout=20.0)
                response.raise_for_status()
                data = response.json()

            json_array = data.get("jsonArray", [])
            total_items = len(json_array)
            batch_log.total_count = total_items

            if total_items == 0:
                batch_log.status = "SUCCESS"
                batch_log.finished_at = datetime.utcnow()
                await self._session.commit()
                return {
                    "status": "success",
                    "message": "새로운 공고가 없습니다.",
                    "count": 0,
                }

            # 3. 데이터 파싱 및 DB 반영 (Upsert)
            success_count, fail_count = await self._upsert_policies(json_array)

            # 4. 배치 로그 성공 기록 마무리
            batch_log.status = "SUCCESS"
            batch_log.success_count = success_count
            batch_log.fail_count = fail_count
            batch_log.finished_at = datetime.utcnow()
            await self._session.commit()

            return {
                "status": "success",
                "message": "동기화 완료",
                "total_api_items": total_items,
                "upserted_count": success_count,
                "failed_count": fail_count,
            }

        except Exception as e:
            # 실패 시 배치 로그에 에러 롤백 및 기록
            await self._session.rollback()
            batch_log.status = "FAILED"
            batch_log.error_details = {"error": str(e)}
            batch_log.finished_at = datetime.utcnow()
            self._session.add(batch_log)
            await self._session.commit()
            return {"status": "error", "message": str(e)}

    # ── [핵심 4] DB 저장 엔진 (Upsert & 컬럼 매핑) ─────────────────────────────
    async def _upsert_policies(self, items: list[dict[str, Any]]) -> tuple[int, int]:
        """새 공고는 Insert, 이미 있는 공고는 Update (컬럼 매핑 담당)"""
        success_cnt = 0
        fail_cnt = 0

        # 한 번에 찾기 위해 현재 API에서 받은 origin_id 리스트 추출
        origin_ids = [item.get("pblancId") for item in items if item.get("pblancId")]

        # DB에서 origin_id가 일치하는 정책들을 한꺼번에 가져옴 (조회 최적화)
        stmt = select(Policy).where(Policy.origin_id.in_(origin_ids))
        result = await self._session.execute(stmt)
        existing_policies = {p.origin_id: p for p in result.scalars().all()}

        for item in items:
            try:
                origin_id = item.get("pblancId")
                if not origin_id:
                    continue

                # 날짜 파싱 로직
                start_dt = self._parse_date(item.get("reqstBeginDt", ""))
                end_dt = self._parse_date(item.get("reqstEndDt", ""))

                today = datetime.now().date()
                if not end_dt:
                    closed_at = date(9999, 12, 31)
                    status = PolicyStatus.RECRUITING
                else:
                    closed_at = end_dt
                    status = (
                        PolicyStatus.CLOSED
                        if end_dt < today
                        else PolicyStatus.RECRUITING
                    )

                # 텍스트 가공 (AI/RAG가 읽기 좋게)
                target_desc = item.get("trgetNm", "정보 없음")
                content_desc = item.get("pblancNm", "")
                raw_content = f"[지원대상]\n{target_desc}\n\n[주요내용]\n{content_desc}"

                # 기존 공고가 있으면 업데이트 (Update)
                if origin_id in existing_policies:
                    policy = existing_policies[origin_id]
                    policy.title = item.get("pblancNm", "제목 없음")
                    policy.agency_name = item.get("enfcGrcNm", "기관명 없음")
                    policy.category = item.get("bsrnSeNm", "기타")
                    policy.region = item.get("jrsdInsttNm", "전국")
                    policy.start_date = start_dt
                    policy.end_date = end_dt
                    policy.closed_at = closed_at
                    policy.status = status
                    policy.apply_url = item.get("pblancUrl", "")
                    policy.content_raw = raw_content
                # 기존 공고가 없으면 새로 만들기 (Insert)
                else:
                    new_policy = Policy(
                        origin_id=origin_id,
                        title=item.get("pblancNm", "제목 없음"),
                        agency_name=item.get("enfcGrcNm", "기관명 없음"),
                        category=item.get("bsrnSeNm", "기타"),
                        region=item.get("jrsdInsttNm", "전국"),
                        start_date=start_dt,
                        end_date=end_dt,
                        closed_at=closed_at,
                        status=status,
                        apply_url=item.get("pblancUrl", ""),
                        content_raw=raw_content,
                        is_active=True,
                        view_count=0,
                    )
                    self._session.add(new_policy)

                success_cnt += 1
            except Exception as e:
                print(f"Upsert 에러 (ID: {item.get('pblancId')}): {e}")
                fail_cnt += 1

        # DB에 반영
        await self._session.flush()
        return success_cnt, fail_cnt

    def _parse_date(self, date_str: str) -> date | None:
        """유틸리티: 날짜 파싱"""
        if not date_str:
            return None
        try:
            clean_str = date_str.split(" ")[0]
            return datetime.strptime(clean_str, "%Y-%m-%d").date()
        except ValueError:
            return None
