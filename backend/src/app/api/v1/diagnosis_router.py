"""정밀진단 API 라우터."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.app.api.deps.business_deps import ActiveBusiness
from src.app.api.deps.diagnosis_deps import DiagnosisServiceDep
from src.app.core.response import api_json
from src.app.domains.diagnosis.schema import (
    ExecuteDiagnosisRequest,
    ExecuteSimulationRequest,
)

router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


@router.get("/prepare")
async def prepare_diagnosis(
    svc: DiagnosisServiceDep,
    biz: ActiveBusiness,
):
    """정밀진단 준비 - 데이터 세팅 및 부족한 필드 파악."""
    data = await svc.prepare_diagnosis(biz)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.post("")
async def execute_diagnosis(
    req: ExecuteDiagnosisRequest,
    svc: DiagnosisServiceDep,
    biz: ActiveBusiness,
):
    """정밀진단 실행 및 결과 저장."""
    data = await svc.execute_diagnosis(biz, req)
    return api_json(
        http_status=status.HTTP_201_CREATED,
        data=data.model_dump(),
        message="success",
    )


@router.get("/{diagnosis_id}")
async def get_diagnosis_detail(
    diagnosis_id: uuid.UUID,
    svc: DiagnosisServiceDep,
    biz: ActiveBusiness,
):
    """진단 상세 조회."""
    data = await svc.get_diagnosis_detail(biz, diagnosis_id)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@router.get("")
async def get_diagnosis_history(
    svc: DiagnosisServiceDep,
    biz: ActiveBusiness,
):
    """진단 이력 조회."""
    data = await svc.get_diagnosis_history(biz)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=[d.model_dump() for d in data],
        message="success",
    )


@router.delete("/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diagnosis(
    diagnosis_id: uuid.UUID,
    svc: DiagnosisServiceDep,
    biz: ActiveBusiness,
):
    """진단 기록 삭제."""
    await svc.delete_diagnosis(biz, diagnosis_id)


# 시뮬레이션 라우터는 같은 파일에 /simulations 로 prefix를 나눌 수도 있지만,
# API 스펙상 분리된 경로이므로 별도 라우터 생성 또는 prefix 조정
sim_router = APIRouter(prefix="/simulations", tags=["simulations"])


@sim_router.post("")
async def execute_simulation(
    req: ExecuteSimulationRequest,
    svc: DiagnosisServiceDep,
    biz: ActiveBusiness,
):
    """가산점 시뮬레이션 실행."""
    data = await svc.execute_simulation(biz, req)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=data.model_dump(),
        message="success",
    )


@sim_router.get("/history")
async def get_simulation_history(
    svc: DiagnosisServiceDep,
    biz: ActiveBusiness,
):
    """시뮬레이션 이력 조회."""
    data = await svc.get_simulation_history(biz)
    return api_json(
        http_status=status.HTTP_200_OK,
        data=[d.model_dump() for d in data],
        message="success",
    )
