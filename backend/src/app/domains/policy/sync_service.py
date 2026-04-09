"""기업마당(Bizinfo) API 연동 및 정책 공고 자동화 서비스."""

from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import BIZINFO_API_KEY
from src.app.domains.policy.model import Policy, PolicyStatus
from src.app.domains.policy.repository import PolicyRepository
from src.app.domains.system.model import BatchLog


class BizinfoSyncService:
    """기업마당 API 데이터를 우리 DB로 동기화하는 핵심 서비스."""

    def __init__(self, session: AsyncSession, repo: PolicyRepository):
        self._session = session
        self._repo = repo
        self._api_url = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"

    async def bootstrap_historical_policies(self, count: int = 1000) -> dict:
        """초기 1회 대량 적재용."""
        return await self._execute_sync_job(
            job_name="POLICY_BOOTSTRAP", search_cnt=count
        )

    async def sync_recent_policies(self) -> dict:
        """매일 정기 동기화용."""
        return await self._execute_sync_job(
            job_name="POLICY_DAILY_SYNC", search_cnt=100
        )

    async def _execute_sync_job(self, job_name: str, search_cnt: int) -> dict:
        """API 호출 및 배치 로그 기록 공통 로직."""
        if not BIZINFO_API_KEY:
            return {"status": "error", "message": "BIZINFO_API_KEY 설정 필요"}

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
            params = {
                "serviceKey": BIZINFO_API_KEY,
                "dataType": "json",
                "numOfRows": search_cnt,
                "pageNo": 1,
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(self._api_url, params=params, timeout=20.0)
                response.raise_for_status()
                data = response.json()

            # API 계층 구조 접근
            body = data.get("response", {}).get("body", {})
            items_wrapper = body.get("items", {})
            json_array = items_wrapper.get("item", [])

            if isinstance(json_array, dict):
                json_array = [json_array]

            total_items = len(json_array)
            batch_log.total_count = total_items

            if total_items == 0:
                batch_log.status = "SUCCESS"
                batch_log.finished_at = datetime.utcnow()
                await self._session.commit()
                return {"status": "success", "message": "새로운 공고 없음", "count": 0}

            # Upsert 실행
            unique_json_array = {item["pblancId"]: item for item in json_array}.values()
            success_count, fail_count = await self._upsert_policies(
                list(unique_json_array)
            )
            await self._session.commit()  # DB 저장

            batch_log.status = "SUCCESS"
            batch_log.success_count = success_count
            batch_log.fail_count = fail_count
            batch_log.finished_at = datetime.utcnow()
            await self._session.commit()

            return {
                "status": "success",
                "message": "동기화 완료",
                "total": total_items,
                "success": success_count,
                "fail": fail_count,
            }

        except Exception as e:
            await self._session.rollback()
            batch_log.status = "FAILED"
            batch_log.error_details = {"error": str(e)}
            batch_log.finished_at = datetime.utcnow()
            self._session.add(batch_log)
            await self._session.commit()
            return {"status": "error", "message": str(e)}

    async def _upsert_policies(self, items: list[dict[str, Any]]) -> tuple[int, int]:

        success_cnt = 0
        fail_cnt = 0

        input_dict = {item["pblancId"]: item for item in items if item.get("pblancId")}

        for origin_id, item in input_dict.items():
            try:
                # 날짜 파싱
                period_str = item.get("reqstBeginEndDe", "")
                start_dt, end_dt = None, None
                if "~" in period_str:
                    dates = period_str.split("~")
                    start_dt = self._parse_date(dates[0].strip())
                    end_dt = self._parse_date(dates[1].strip())

                today = datetime.now().date()
                closed_at = end_dt if end_dt else date(9999, 12, 31)
                status = (
                    PolicyStatus.CLOSED
                    if end_dt and end_dt < today
                    else PolicyStatus.RECRUITING
                )

                title = item.get("pblancNm", "제목 없음")
                agency = item.get("jrsdInsttNm", "기관명 없음")
                category = item.get("pldirSportRealmLclasCodeNm", "기타")
                target = item.get("trgetNm", "정보 없음")
                summary = item.get("bsnsSumryCn", "")
                raw_content = f"[지원대상]\n{target}\n\n[상세내용]\n{summary}"

                stmt = insert(Policy).values(
                    origin_id=origin_id,
                    title=title,
                    agency_name=agency,
                    category=category,
                    start_date=start_dt,
                    end_date=end_dt,
                    closed_at=closed_at,
                    status=status,
                    apply_url=item.get("pblancUrl", ""),
                    content_raw=raw_content,
                    is_active=True,
                    view_count=0,
                )

                stmt = stmt.on_conflict_do_update(
                    index_elements=["origin_id"],
                    set_={
                        "title": title,
                        "agency_name": agency,
                        "category": category,
                        "start_date": start_dt,
                        "end_date": end_dt,
                        "closed_at": closed_at,
                        "status": status,
                        "apply_url": item.get("pblancUrl", ""),
                        "content_raw": raw_content,
                    },
                )

                await self._session.execute(stmt)
                success_cnt += 1

            except Exception as e:
                print(f"Upsert 에러 (ID: {origin_id}): {e}")
                await self._session.rollback()
                fail_cnt += 1

        await self._session.flush()

        return success_cnt, fail_cnt

    def _parse_date(self, date_str: str) -> date | None:
        if not date_str:
            return None
        try:
            clean_str = date_str.split(" ")[0]
            return datetime.strptime(clean_str, "%Y-%m-%d").date()
        except (ValueError, IndexError):
            return None
