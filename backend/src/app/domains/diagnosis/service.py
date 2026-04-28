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
    pass


class DiagnosisService:
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
        return await self._repo.get_all_simulation_logs_for_admin(sim_type)

    async def get_log_detail_for_admin(self, diagnosis_id: uuid.UUID) -> Any:
        return await self._repo.get_simulation_log_for_admin(diagnosis_id)
