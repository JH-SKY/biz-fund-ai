"""정밀진단 DB 리포지토리."""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# [삭제] BusinessFinancialSnapshot: 타 도메인 모델 직접 참조 제거 (도메인 격리 원칙)
from src.app.domains.diagnosis.model import MatchLog, SimulationLog


class DiagnosisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # [삭제된 함수 안내]
    # get_latest_financial_snapshot: 
    # 이 함수는 Business 도메인의 데이터를 조회하므로 BusinessRepository로 이동해야 합니다.
    # DiagnosisService에서는 BusinessService를 통해 데이터를 가져오는 것이 실무 표준 아키텍처입니다.

    async def create_match_log(
        self,
        business_id: uuid.UUID,
        policy_id: uuid.UUID,
        match_score: int,
        match_status: str,
        reason_json: Dict[str, Any],
    ) -> MatchLog:
        """
        1. 기능: 진단 결과(매칭 로그) 생성.
        2. 설계 의도: 특정 시점의 사업장 상태와 정책 간의 매칭 결과를 '박제'하여 히스토리를 보존합니다.
        """
        log = MatchLog(
            business_id=business_id,
            policy_id=policy_id,
            match_score=match_score,
            match_status=match_status,
            reason_json=reason_json,
        )
        self._session.add(log)
        await self._session.flush() # ID 확정을 위해 flush 수행
        return log

    async def create_simulation_log(
        self,
        business_id: uuid.UUID,
        sim_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        **_kwargs: Any,
    ) -> SimulationLog:
        """시뮬레이션 로그 생성."""
        log = SimulationLog(
            business_id=business_id,
            sim_type=sim_type,
            input_data=input_data,
            output_data=output_data,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def get_simulation_log(
        self,
        log_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> Optional[SimulationLog]:
        """
        1. 기능: 특정 시뮬레이션 로그 단건 조회.
        2. 메커니즘: 요청자의 business_id를 필터에 포함하여 타인 데이터 접근을 원천 차단(Isolation)합니다.
        """
        stmt = select(SimulationLog).where(
            SimulationLog.id == log_id,
            SimulationLog.business_id == business_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_simulation_logs(
        self,
        business_id: uuid.UUID,
        sim_type: str,
    ) -> List[SimulationLog]:
        """
        1. 기능: 특정 사업장의 시뮬레이션 이력 목록 조회.
        2. 설계 의도: 사용자가 본인의 과거 시뮬레이션 기록을 최신순으로 확인할 수 있게 합니다.
        """
        stmt = (
            select(SimulationLog)
            .where(
                SimulationLog.business_id == business_id,
                SimulationLog.sim_type == sim_type,
            )
            .order_by(SimulationLog.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_simulation_log(self, log: SimulationLog) -> None:
        """
        1. 기능: 로그 물리 삭제.
        2. 설계 의도: 사용자가 명시적으로 파기를 요청한 진단 데이터는 DB에서 즉시 제거합니다.
        """
        await self._session.delete(log)
        await self._session.flush()

    # ---------------------------------------------------------
    # [신규 추가] 관리자(Admin) 전용 기능
    # ---------------------------------------------------------

    async def get_all_simulation_logs_for_admin(
        self, 
        sim_type: Optional[str] = None
    ) -> List[SimulationLog]:
        """
        1. 기능: [관리자] 시스템 전체 시뮬레이션/진단 이력 전수 조사.
        2. 설계 의도: 특정 사업장에 종속되지 않고 전체 서비스의 이용 현황 및 AI 비용 발생량을 모니터링합니다.
        """
        stmt = select(SimulationLog)
        if sim_type:
            stmt = stmt.where(SimulationLog.sim_type == sim_type)
        
        stmt = stmt.order_by(SimulationLog.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_simulation_log_for_admin(
        self, 
        log_id: uuid.UUID
    ) -> Optional[SimulationLog]:
        """
        1. 기능: [관리자] ID 기반 로그 단건 조회.
        2. 설계 의도: CS 대응 등을 위해 사업장 ID 권한 체크 없이 특정 로그 상세 내용을 확인합니다.
        """
        stmt = select(SimulationLog).where(SimulationLog.id == log_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()