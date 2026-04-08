# src/app/domains/policy/sync_service.py
"""기업마당(Bizinfo) API 연동 및 정책 공고 자동화 서비스."""

from datetime import date, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.core.config import BIZINFO_API_KEY
from src.app.domains.policy.model import Policy, PolicyStatus
from src.app.domains.policy.repository import PolicyRepository


class BizinfoSyncService:
    """기업마당 API 데이터를 우리 DB(policies)로 동기화하는 서비스입니다."""

    def __init__(self, session: AsyncSession, repo: PolicyRepository):
        self._session = session
        self._repo = repo
        self._api_url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"  # 기업마당 JSON API 엔드포인트

    def _parse_date(self, date_str: str) -> date | None:
        """'2024-12-31 18:00:00' 같은 문자열을 날짜(date) 객체로 바꿉니다."""
        if not date_str:
            return None
        try:
            # 시간 부분 자르고 날짜만 추출
            clean_str = date_str.split(" ")[0]
            return datetime.strptime(clean_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    async def sync_policies(self, display_count: int = 100) -> dict:
        """기업마당 API를 호출하여 데이터를 동기화합니다."""
        if not BIZINFO_API_KEY:
            return {
                "status": "error",
                "message": "BIZINFO_API_KEY가 설정되지 않았습니다.",
            }

        # API 호출 파라미터 셋팅
        params = {
            "crtfcKey": BIZINFO_API_KEY,
            "dataType": "json",
            "searchCnt": display_count,  # 한 번에 가져올 개수
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self._api_url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"🚨 기업마당 API 호출 실패: {e}")
                return {"status": "error", "message": str(e)}

        # 응답 데이터 중 실제 공고 목록 추출 (JSON 구조에 따라 다름)
        # 기업마당은 보통 jsonArray 형태로 리스트를 줍니다.
        json_array = data.get("jsonArray", [])
        if not json_array:
            return {
                "status": "success",
                "message": "새로운 공고가 없습니다.",
                "count": 0,
            }

        success_count = 0
        skip_count = 0

        for item in json_array:
            origin_id = item.get("pblancId")  # 기업마당 고유 공고 번호
            if not origin_id:
                continue

            # 1. 이미 DB에 있는 공고인지 확인 (origin_id 기준)
            existing_policy = await self._repo.get_policy_by_origin_id(origin_id)
            if existing_policy:
                skip_count += 1
                continue  # 일단 지금은 덮어쓰기 안 하고 스킵(Skip) 처리합니다.

            # 2. 날짜 파싱 및 상태값 결정
            start_dt = self._parse_date(item.get("reqstBeginDt", ""))
            end_dt = self._parse_date(item.get("reqstEndDt", ""))

            # 마감일이 없으면 9999-12-31(상시), 마감일이 지났으면 CLOSED
            today = datetime.now().date()
            if not end_dt:
                closed_at = date(9999, 12, 31)
                status = PolicyStatus.RECRUITING
            else:
                closed_at = end_dt
                status = (
                    PolicyStatus.CLOSED if end_dt < today else PolicyStatus.RECRUITING
                )

            # 3. 상세 내용을 하나로 합치기 (나중에 RAG가 읽을 원본 텍스트)
            # 지원대상, 지원내용을 텍스트로 합쳐서 content_raw에 저장합니다.
            target_desc = item.get("trgetNm", "지원대상 정보 없음")
            content_desc = item.get("pblancNm", "")
            raw_content = f"[지원대상]\n{target_desc}\n\n[주요내용]\n{content_desc}"

            # 4. DB에 새로 등록
            new_policy = Policy(
                origin_id=origin_id,
                title=item.get("pblancNm", "제목 없음"),
                agency_name=item.get("enfcGrcNm", "기관명 없음"),
                category=item.get("bsrnSeNm", "기타"),  # 지원분야
                region=item.get("jrsdInsttNm", "전국"),  # 소관부처/지역
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
            success_count += 1

        # DB에 일괄 저장 커밋
        await self._session.commit()

        return {
            "status": "success",
            "message": "동기화 완료",
            "added": success_count,
            "skipped": skip_count,
        }
