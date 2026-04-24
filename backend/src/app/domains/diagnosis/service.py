"""정밀진단 도메인 비즈니스 로직."""

import uuid
from typing import Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import NotFoundException, ForbiddenException
from src.app.domains.business.model import Business
# [추가] 타 도메인 데이터 조회를 위해 BusinessService 추가
from src.app.domains.business.service import BusinessService 
from src.app.domains.diagnosis.interfaces import IDiagnosisEngine
from src.app.domains.diagnosis.repository import DiagnosisRepository
from src.app.domains.diagnosis.schema import (
    DiagnosisDetailResponseData,
    DiagnosisHistoryItem,
    DiagnosisScores,
    ExecuteDiagnosisRequest,
    ExecuteDiagnosisResponseData,
    ExecuteSimulationRequest,
    ExecuteSimulationResponseData,
    PrepareDiagnosisResponseData,
    SimulationHistoryItem,
    SnapshotData,
)
from src.app.domains.policy.service import PolicyService


class DiagnosisException(Exception):
    pass


class DiagnosisService:
    def __init__(
        self,
        session: AsyncSession,
        repo: DiagnosisRepository,
        policy_service: PolicyService,
        business_service: BusinessService, # [주입] 타 도메인 서비스 협력을 위해 추가
        engine: IDiagnosisEngine,
    ) -> None:
        self._session = session
        self._repo = repo
        self._policy_service = policy_service
        self._business_service = business_service # [할당]
        self._engine = engine

    async def prepare_diagnosis(self, business: Business) -> PrepareDiagnosisResponseData:
        """
        1. 기능: 정밀진단 전 기초 데이터 로드 및 누락 필드 파악.
        2. 설계 의도: 사용자가 진단 폼을 채울 때 기존 재무 데이터를 불러와 편의성을 높입니다.
        3. 수정 사항: DiagnosisRepository가 아닌 BusinessService를 통해 재무 스냅샷을 가져옵니다. (도메인 격리)
        """
        # [변경] 타 도메인(Business)의 Repository에 직접 접근하지 않고 서비스를 통해 요청
        snap = await self._business_service.get_latest_financial_snapshot_internal(business.id)

        if snap:
            snap_data = SnapshotData(
                revenue=snap.annual_revenue,
                employee_count=snap.employee_count,
                biz_sector=business.sector_code,
            )
        else:
            snap_data = SnapshotData()

        missing = []
        if snap_data.revenue is None:
            missing.append("revenue")
        if snap_data.employee_count is None:
            missing.append("employee_count")

        return PrepareDiagnosisResponseData(
            current_snapshot=snap_data,
            missing_fields=missing,
            message="필수 정보가 일부 누락되었습니다. 보완 후 진단을 시작하세요." if missing else "모든 정보가 준비되었습니다.",
        )

    async def execute_diagnosis(
        self,
        business: Business,
        req: ExecuteDiagnosisRequest,
    ) -> ExecuteDiagnosisResponseData:
        """
        1. 기능: 엔진을 통한 정밀진단 수행 및 결과 로깅.
        2. 설계 의도: 진단 결과물과 함께 AI 엔진의 추적 정보(Model, Trace ID)를 기록합니다.
        """
        result = await self._engine.execute_diagnosis(
            business=business,
            year=req.year,
            inputs=req.final_inputs,
            use_ai=req.use_ai_analysis,
        )

        # [변경] Repository 업데이트에 따른 AI 추적 필드 전달
        log = await self._repo.create_simulation_log(
            business_id=business.id,
            sim_type="DIAGNOSIS",
            input_data=req.final_inputs,
            output_data={
                "total_score": result.total_score,
                "grade": result.grade,
                "scores": result.scores,
                "ai_comment": result.ai_comment,
            },
            model_name="gpt-4o", # [예시] 실무에서는 엔진 설정값에서 가져옴
            trace_id=f"diag-{uuid.uuid4()}", # 추적용 ID 생성
            cost=0.01 # [예시] 예상 비용 기록
        )
        await self._session.commit()

        return ExecuteDiagnosisResponseData(
            diagnosis_id=str(log.id),
            total_score=result.total_score,
            grade=result.grade,
            created_at=log.created_at,
        )

    async def get_diagnosis_detail(
        self,
        business: Business,
        diagnosis_id: uuid.UUID,
    ) -> DiagnosisDetailResponseData:
        """
        1. 기능: 특정 진단 기록의 상세 내용 조회.
        2. 설계 의도: 조회 시 business.id를 필수로 검증하여 데이터 접근 권한을 보장합니다.
        """
        log = await self._repo.get_simulation_log(diagnosis_id, business.id)
        if not log or log.sim_type != "DIAGNOSIS":
            raise NotFoundException("진단 기록을 찾을 수 없습니다.")

        out = log.output_data
        return DiagnosisDetailResponseData(
            diagnosis_id=str(log.id),
            scores=DiagnosisScores(**out.get("scores", {})),
            ai_comment=out.get("ai_comment", ""),
            snapshot=log.input_data,
        )

    async def get_diagnosis_history(
        self, business: Business
    ) -> List[DiagnosisHistoryItem]:
        """
        1. 기능: 사업장의 과거 정밀진단 전체 이력 목록 반환.
        """
        logs = await self._repo.get_simulation_logs(business.id, "DIAGNOSIS")
        return [
            DiagnosisHistoryItem(
                diagnosis_id=str(log.id),
                score=log.output_data.get("total_score", 0.0),
                date=log.created_at.strftime("%Y-%m-%d"),
            )
            for log in logs
        ]

    async def delete_diagnosis(self, business: Business, diagnosis_id: uuid.UUID) -> None:
        """
        1. 기능: 진단 기록 물리 삭제.
        2. 메커니즘: 본인 확인 절차를 거친 후 Repository의 물리 삭제 명령을 호출합니다.
        """
        log = await self._repo.get_simulation_log(diagnosis_id, business.id)
        if not log:
            raise NotFoundException("진단 기록을 찾을 수 없습니다.")
        
        # [검토] get_simulation_log 내부에서 이미 business.id로 조회하므로 
        # 추가 Forbidden 검증은 방어적 차원에서 유지하거나 신뢰할 수 있습니다.
        if log.business_id != business.id:
            raise ForbiddenException("삭제 권한이 없습니다.")

        await self._repo.delete_simulation_log(log)
        await self._session.commit()

    async def execute_simulation(
        self,
        business: Business,
        req: ExecuteSimulationRequest,
    ) -> ExecuteSimulationResponseData:
        """
        1. 기능: 특정 정책에 대한 가산점 시뮬레이션 실행 및 결과 전파.
        2. 설계 의도: 시뮬레이션 결과를 매칭 로그(match_logs)에도 동기화하여 대시보드에 노출합니다.
        """
        policy = await self._policy_service.get_policy_by_id_internal(req.policy_id)
        if not policy:
            raise NotFoundException("정책을 찾을 수 없습니다.")

        result = await self._engine.execute_simulation(
            business=business,
            policy=policy,
            conditions=req.virtual_conditions,
        )

        input_data = {
            "policy_id": str(policy.id),
            "policy_title": policy.title,
            "virtual_conditions": req.virtual_conditions,
        }
        output_data = {
            "base_rate": result.base_rate,
            "simulated_rate": result.simulated_rate,
            "gain_factors": result.gain_factors,
        }

        # [변경] Repository 업데이트에 따른 AI 추적 필드 반영
        log = await self._repo.create_simulation_log(
            business_id=business.id,
            sim_type="SIMULATION",
            input_data=input_data,
            output_data=output_data,
            model_name="gpt-4o", # 시뮬레이션에 사용된 모델 기록
            cost=0.005
        )

        # match_logs 에도 삽입 (시뮬레이션된 매칭 점수)
        await self._repo.create_match_log(
            business_id=business.id,
            policy_id=policy.id,
            match_score=int(result.simulated_rate),
            match_status="SIMULATED",
            reason_json={"sim_log_id": str(log.id), "gain_factors": result.gain_factors},
        )

        await self._session.commit()

        return ExecuteSimulationResponseData(
            base_rate=result.base_rate,
            simulated_rate=result.simulated_rate,
            gain_factors=result.gain_factors,
        )

    async def get_simulation_history(
        self, business: Business
    ) -> List[SimulationHistoryItem]:
        """
        1. 기능: 사업장의 과거 가산점 시뮬레이션 이력 목록 반환.
        """
        logs = await self._repo.get_simulation_logs(business.id, "SIMULATION")
        return [
            SimulationHistoryItem(
                policy_title=log.input_data.get("policy_title", "알 수 없는 정책"),
                sim_rate=log.output_data.get("simulated_rate", 0.0),
                created_at=log.created_at.strftime("%Y-%m-%d"),
            )
            for log in logs
        ]
    
    # ── Admin 전용 (Internal) ─────────────────────────────────────────────

    async def get_all_logs_for_admin(self, sim_type: str | None = None) -> list:
        """[Internal] 관리자 모니터링용: 시스템 전체 시뮬레이션/진단 이력 전수 조회"""
        return await self._repo.get_all_simulation_logs_for_admin(sim_type)

    async def get_log_detail_for_admin(self, diagnosis_id: uuid.UUID) -> Any:
        """[Internal] 관리자 모니터링용: ID 기반 로그 단건 상세 조회"""
        return await self._repo.get_simulation_log_for_admin(diagnosis_id)