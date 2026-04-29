# src/app/domains/diagnosis/service.py
"""정밀진단(Diagnosis) 도메인 비즈니스 로직 및 트랜잭션 경계.

담당 유스케이스:
  - 진단 준비(prepare): 사업장 재무 스냅샷 존재 여부 확인 및 부족 항목 안내
  - 진단 실행(execute): AI/규칙 엔진으로 사업 건강도 진단 → 결과 저장
  - 시뮬레이션 실행: '만약 매출이 이렇다면?' 가상 조건 시뮬레이션
  - 진단/시뮬레이션 이력 조회·삭제

설계 원칙:
  - IDiagnosisEngine 인터페이스로 진단 엔진을 주입받아 교체 가능하게 설계.
  - 진단 결과 저장과 사업장 데이터 동기화는 반드시 같은 트랜잭션에서 처리.
  - 모든 DB 커밋은 이 Service에서만 발생한다 (Repository는 flush만 수행).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import ForbiddenException, NotFoundException
from src.app.domains.business.model import Business
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
    """진단 도메인 전용 예외 기반 클래스."""
    pass


class DiagnosisService:
    """정밀진단 도메인 유스케이스.

    외부 의존성:
      - DiagnosisRepository : 진단·시뮬레이션 로그 DB 접근
      - PolicyService       : 시뮬레이션 시 정책 정보 조회
      - BusinessService     : 진단 입력값 사업장·재무에 동기화
      - IDiagnosisEngine    : 실제 진단 계산 엔진 (규칙 기반/AI 교체 가능)
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: DiagnosisRepository,
        policy_service: PolicyService,
        business_service: BusinessService,
        engine: IDiagnosisEngine,
    ) -> None:
        self._session = session
        self._repo = repo
        self._policy_service = policy_service
        self._business_service = business_service
        self._engine = engine

    async def prepare_diagnosis(
        self, business: Business
    ) -> PrepareDiagnosisResponseData:
        """진단 실행 전 사업장 데이터 준비 상태를 점검한다.

        [로직]
        1. 가장 최근 재무 스냅샷 조회
        2. 연매출·직원 수 등 필수 항목 중 빠진 것을 missing_fields 에 담아 반환
        3. 국세청 미인증 사업장이면 재검증 안내 플래그 포함
        """
        snap = await self._business_service.get_latest_financial_snapshot_internal(
            business.id
        )

        if snap:
            snap_data = SnapshotData(
                revenue=snap.annual_revenue,
                employee_count=snap.employee_count,
                biz_sector=business.sector_code,
            )
        else:
            snap_data = SnapshotData()

        missing: list[str] = []
        if snap_data.revenue is None:
            missing.append("revenue")
        if snap_data.employee_count is None:
            missing.append("employee_count")

        return PrepareDiagnosisResponseData(
            current_snapshot=snap_data,
            missing_fields=missing,
            message="필수 정보가 일부 비어 있습니다. 보완 후 진단을 시작해 주세요."
            if missing
            else "모든 정보가 준비되었습니다.",
            suggest_nts_reverification=not business.is_biz_no_verified,
        )

    async def execute_diagnosis(
        self,
        business: Business,
        req: ExecuteDiagnosisRequest,
    ) -> ExecuteDiagnosisResponseData:
        """
        기업 진단 실행 서비스:
        입력된 기업 데이터를 바탕으로 AI 분석을 수행하고,
        그 결과를 DB 동기화 및 이력(Log)으로 남기는 핵심 비즈니스 로직입니다.
        """
        result = await self._engine.execute_diagnosis(
            business=business,
            year=req.year,
            inputs=req.final_inputs,
            use_ai=req.use_ai_analysis,
        )

        await self._business_service.sync_diagnosis_inputs_internal(
            business,
            year=req.year,
            annual_revenue=req.final_inputs.annual_revenue,
            total_debt=req.final_inputs.total_debt,
            debt_ratio=req.final_inputs.debt_ratio,
            employee_count=req.final_inputs.employee_count,
            has_tax_arrears=req.final_inputs.has_tax_arrears,
            has_patent=req.final_inputs.has_patent,
            is_female_ent=req.final_inputs.is_female_ent,
            is_ventured=req.final_inputs.is_ventured,
        )

        log = await self._repo.create_simulation_log(
            business_id=business.id,
            sim_type="DIAGNOSIS",
            input_data=req.final_inputs.model_dump(),
            output_data={
                "total_score": result.total_score,
                "grade": result.grade,
                "scores": result.scores,
                "summary": result.summary,
                "strengths": result.strengths,
                "risk_signals": result.risk_signals,
                "action_items": result.action_items,
                "traffic_light": result.traffic_light,
            },
            model_name="gpt-4o",
            trace_id=f"diag-{uuid.uuid4()}",
            cost=0.01,
        )
        await self._session.commit()

        return ExecuteDiagnosisResponseData(
            diagnosis_id=str(log.id),
            total_score=result.total_score,
            grade=result.grade,
            created_at=log.created_at,
            traffic_light=result.traffic_light,
        )

    async def get_diagnosis_detail(
        self,
        business: Business,
        diagnosis_id: uuid.UUID,
    ) -> DiagnosisDetailResponseData:
        """특정 진단 결과의 상세 내용을 조회한다.

        [로직]
        1. 해당 진단 로그 조회 (없거나 DIAGNOSIS 타입이 아니면 404)
        2. output_data JSONB에서 각 항목을 꺼내 응답 DTO로 조립
        """
        log = await self._repo.get_simulation_log(diagnosis_id, business.id)
        if not log or log.sim_type != "DIAGNOSIS":
            raise NotFoundException("진단 기록을 찾을 수 없습니다.")

        out = log.output_data
        return DiagnosisDetailResponseData(
            diagnosis_id=str(log.id),
            total_score=out.get("total_score", 0.0),
            grade=out.get("grade", "NORMAL"),
            traffic_light=out.get("traffic_light", "GREEN"),
            scores=DiagnosisScores(**out.get("scores", {})),
            summary=out.get("summary", ""),
            strengths=out.get("strengths", []),
            risk_signals=out.get("risk_signals", []),
            action_items=out.get("action_items", []),
            snapshot=log.input_data,
        )

    async def get_diagnosis_history(
        self, business: Business
    ) -> list[DiagnosisHistoryItem]:
        """사업장의 과거 진단 이력 목록을 최신순으로 반환한다."""
        logs = await self._repo.get_simulation_logs(business.id, "DIAGNOSIS")
        return [
            DiagnosisHistoryItem(
                diagnosis_id=str(log.id),
                score=log.output_data.get("total_score", 0.0),
                date=log.created_at.strftime("%Y-%m-%d"),
            )
            for log in logs
        ]

    async def delete_diagnosis(
        self, business: Business, diagnosis_id: uuid.UUID
    ) -> None:
        """진단 결과를 삭제한다 (물리 삭제).

        [보안] business_id 불일치 시 403 반환하여 타인 데이터 삭제 방지.
        """
        log = await self._repo.get_simulation_log(diagnosis_id, business.id)
        if not log:
            raise NotFoundException("진단 기록을 찾을 수 없습니다.")
        if log.business_id != business.id:
            raise ForbiddenException("삭제 권한이 없습니다.")

        await self._repo.delete_simulation_log(log)
        await self._session.commit()

    async def execute_simulation(
        self,
        business: Business,
        req: ExecuteSimulationRequest,
    ) -> ExecuteSimulationResponseData:
        """가상 조건 시뮬레이션을 실행한다.

        [로직]
        1. 현재 재무 스냅샷을 base_inputs 으로 사용
        2. virtual_conditions 를 base_inputs 에 덮어쓴 뒤 진단 엔진 실행
        3. 기존 점수(base_rate) vs 가상 점수(simulated_rate) 비교
        4. 특정 정책 ID 가 있으면 해당 정책 대비 매칭 점수도 시뮬레이션
        5. 결과를 simulation_logs 에 저장하고 매칭 로그도 함께 기록
        """
        snap = await self._business_service.get_latest_financial_snapshot_internal(
            business.id
        )
        base_inputs: dict[str, Any] = {
            "annual_revenue": snap.annual_revenue if snap else None,
            "total_debt": snap.total_debt if snap else None,
            "employee_count": snap.employee_count
            if snap
            else (business.employee_count or 0),
            "has_patent": business.has_patent,
            "is_female_ent": business.is_female_ent,
            "is_ventured": business.is_ventured,
            "has_tax_arrears": business.has_tax_arrears,
        }
        conditions = {
            "base_inputs": base_inputs,
            "virtual_conditions": req.virtual_conditions,
        }

        policy = None
        if req.policy_id is not None:
            policy = await self._policy_service.get_policy_by_id_internal(req.policy_id)
            if not policy:
                raise NotFoundException("정책을 찾을 수 없습니다.")

        result = await self._engine.execute_simulation(
            business=business,
            policy=policy,
            conditions=conditions,
        )

        input_data = {
            "policy_id": str(req.policy_id) if req.policy_id else None,
            "policy_title": policy.title if policy else "종합 점수 시뮬레이션",
            "virtual_conditions": req.virtual_conditions,
        }
        output_data = {
            "base_rate": result.base_rate,
            "simulated_rate": result.simulated_rate,
            "gain_factors": result.gain_factors,
        }
        log = await self._repo.create_simulation_log(
            business_id=business.id,
            sim_type="SIMULATION",
            input_data=input_data,
            output_data=output_data,
            model_name="rule-based",
            cost=0.0,
        )

        if policy is not None:
            await self._repo.create_match_log(
                business_id=business.id,
                policy_id=policy.id,
                match_score=int(result.simulated_rate),
                match_status="SIMULATED",
                reason_json={
                    "sim_log_id": str(log.id),
                    "gain_factors": result.gain_factors,
                },
            )

        await self._session.commit()
        return ExecuteSimulationResponseData(
            base_rate=result.base_rate,
            simulated_rate=result.simulated_rate,
            gain_factors=result.gain_factors,
        )

    async def get_simulation_history(
        self, business: Business
    ) -> list[SimulationHistoryItem]:
        """사업장의 시뮬레이션 이력 목록을 반환한다."""
        logs = await self._repo.get_simulation_logs(business.id, "SIMULATION")
        return [
            SimulationHistoryItem(
                policy_title=log.input_data.get("policy_title", "이름 없는 정책"),
                sim_rate=log.output_data.get("simulated_rate", 0.0),
                created_at=log.created_at.strftime("%Y-%m-%d"),
            )
            for log in logs
        ]

    async def get_all_logs_for_admin(self, sim_type: str | None = None) -> list:
        """[Admin] 시스템 전체 진단/시뮬레이션 로그를 조회한다."""
        return await self._repo.get_all_simulation_logs_for_admin(sim_type)

    async def get_log_detail_for_admin(self, diagnosis_id: uuid.UUID) -> Any:
        """[Admin] 특정 진단 로그 상세를 사업장 권한 체크 없이 조회한다 (CS 대응용)."""
        return await self._repo.get_simulation_log_for_admin(diagnosis_id)
