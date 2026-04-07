# src/app/api/v1/business_router.py
"""사업장 API 라우터 (business.md 전체 구현).

엔드포인트 접근 권한 구분:
  - CurrentUser만 필요 (로그인 필수, 온보딩 불필요):
      POST /onboarding/verify-biz   — 사업자번호 진위 확인
      POST /onboarding/register     — 온보딩 사업장 등록
      GET  /businesses/me           — 사업장 조회 (없으면 404)
      POST /businesses/validate     — 입력값 이상치 검증

  - ActiveBusiness 필요 (온보딩 가드, 403 → /onboarding 리다이렉트):
      PATCH  /businesses/me                — 사업장 수정
      POST   /businesses/finance           — 재무 스냅샷 등록
      GET    /businesses/finance/history   — 재무 이력 조회
      PATCH  /businesses/finance/{year}    — 재무 수정
      DELETE /businesses/finance/{year}    — 재무 영구 삭제
      POST   /documents                    — 서류 업로드
      GET    /documents                    — 서류 목록 조회
      GET    /documents/{document_id}      — 서류 상세 조회
      DELETE /documents/{document_id}      — 서류 파기
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from src.app.api.deps.business_deps import ActiveBusiness, BusinessServiceDep
from src.app.api.deps.user_auth import CurrentUser
from src.app.core.response import api_json
from src.app.domains.business.schema import (
    BusinessUpdateRequest,
    FinanceCreateRequest,
    FinanceUpdateRequest,
    OnboardingRegisterRequest,
    ValidateStatsRequest,
    VerifyBizNumberRequest,
)

router = APIRouter(tags=["사업장 (Business)"])


# ─────────────────────────────────────────────────────────────────────────────
# 온보딩 — 가드 미적용 (신규 가입 직후 접근 가능)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/onboarding/verify-biz",
    summary="사업자번호 진위 확인",
    description=(
        "입력된 사업자번호의 진위 및 휴폐업 여부를 외부 API로 확인합니다. "
        "현재는 Mock 응답을 반환하며, 국세청 API 연동 후 실제 데이터를 제공합니다. "
        "사업자번호는 10자리 숫자(하이픈 허용)여야 합니다."
    ),
)
async def verify_biz_number(
    body: VerifyBizNumberRequest,
    current_user: CurrentUser,
    svc: BusinessServiceDep,
) -> JSONResponse:
    data = await svc.verify_biz_number(body.biz_no)
    return api_json(http_status=200, data=data.model_dump())


@router.post(
    "/onboarding/register",
    summary="온보딩: 사업장 최초 등록",
    description=(
        "[PAGE 03] 신규 가입 유저의 사업장 기본 정보를 등록합니다. "
        "완료 후 대시보드(PAGE 04) 접근이 허용됩니다. "
        "employee_count 입력 시 현재 연도 재무 스냅샷이 자동 생성됩니다."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def register_business(
    body: OnboardingRegisterRequest,
    current_user: CurrentUser,
    svc: BusinessServiceDep,
) -> JSONResponse:
    data = await svc.register_business(current_user, body)
    return api_json(http_status=201, data=data.model_dump())


# ─────────────────────────────────────────────────────────────────────────────
# 사업장 정보 조회 / 수정
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/businesses/me",
    summary="사업장 정보 조회",
    description=(
        "로그인한 사용자의 활성 사업장 기본 정보를 조회합니다. "
        "온보딩 미완료(사업장 미등록) 유저는 404를 받습니다."
    ),
)
async def get_business_info(
    current_user: CurrentUser,
    svc: BusinessServiceDep,
) -> JSONResponse:
    data = await svc.get_my_business(current_user)
    return api_json(http_status=200, data=data.model_dump())


@router.patch(
    "/businesses/me",
    summary="사업장 정보 수정",
    description=(
        "사업장 기본 정보를 부분 수정합니다. "
        "수정 완료 후 profile_score가 자동 재계산됩니다. "
        "[온보딩 가드] 사업장이 없으면 403을 반환합니다."
    ),
)
async def update_business_info(
    body: BusinessUpdateRequest,
    user: CurrentUser,
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> JSONResponse:
    
    await svc.update_my_business(biz, body)
    return api_json(
        http_status=200,
        message="사업장 정보가 성공적으로 업데이트되었습니다.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 재무 스냅샷 — 온보딩 가드 적용
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/businesses/finance",
    summary="신규 재무 정보 등록",
    description="특정 연도의 재무 데이터를 최초 등록합니다. 같은 연도가 이미 존재하면 409를 반환합니다.",
    status_code=status.HTTP_201_CREATED,
)
async def create_finance(
    body: FinanceCreateRequest,
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> JSONResponse:
    data = await svc.create_financial_snapshot(biz, body)
    return api_json(http_status=201, data=data.model_dump())


@router.get(
    "/businesses/finance/history",
    summary="연도별 재무 이력 조회",
    description="등록된 모든 연도의 재무 및 고용 지표를 최신 연도 순으로 반환합니다.",
)
async def get_finance_history(
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> JSONResponse:
    data = await svc.get_financial_history(biz)
    return api_json(
        http_status=200,
        data=[d.model_dump() for d in data],
    )


@router.patch(
    "/businesses/finance/{year}",
    summary="재무 및 고용 정보 수정",
    description=(
        "이미 등록된 특정 연도의 재무 수치나 직원 수를 부분 수정합니다. "
        "부채 비율은 변경된 매출·부채 기준으로 자동 재계산됩니다."
    ),
)
async def update_finance(
    year: int,
    body: FinanceUpdateRequest,
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> JSONResponse:
    await svc.update_financial_snapshot(biz, year, body)
    return api_json(http_status=200, message="재무 및 고용 정보가 갱신되었습니다.")


@router.delete(
    "/businesses/finance/{year}",
    summary="재무 스냅샷 영구 삭제",
    description="잘못 입력된 특정 연도의 재무 레코드를 영구 삭제합니다.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_finance(
    year: int,
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> None:
    await svc.delete_financial_snapshot(biz, year)


# ─────────────────────────────────────────────────────────────────────────────
# 통계 검증 — 현재 사용자 인증만 필요 (사업장 미등록 유저도 호출 가능)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/businesses/validate",
    summary="매출/인원 입력값 실시간 검증",
    description=(
        "매출액 또는 고용 인원 입력 시 업종 평균 대비 이상치 여부를 판단합니다. "
        "type: REVENUE | EMPLOYEE_COUNT"
    ),
)
async def validate_stats(
    body: ValidateStatsRequest,
    current_user: CurrentUser,
    svc: BusinessServiceDep,
) -> JSONResponse:
    data = await svc.validate_stats(body)
    return api_json(http_status=200, data=data.model_dump())


# ─────────────────────────────────────────────────────────────────────────────
# 디지털 서류함 — 온보딩 가드 적용
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/documents",
    summary="서류 업로드",
    description=(
        "증빙 서류를 업로드합니다. 서버는 즉시 202를 반환하고 "
        "비동기로 OCR 분석을 수행합니다. "
        "document_type: BIZ_REG | VAT_CERT | FINANCIAL_STAT"
    ),
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
    file: UploadFile = File(..., description="PDF, JPG, PNG (최대 10MB)"),
    document_type: str = Form(
        ...,
        description="서류 종류 (BIZ_REG | VAT_CERT | FINANCIAL_STAT)",
    ),
) -> JSONResponse:
    data = await svc.upload_document(biz, file, document_type)
    return api_json(
        http_status=202,
        data={"document_id": data.document_id, "status": data.ocr_status},
    )


@router.get(
    "/documents",
    summary="내 서류함 조회",
    description="보관 중인 모든 서류 목록과 OCR 분석 진행 상태를 반환합니다.",
)
async def get_my_documents(
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> JSONResponse:
    docs = await svc.get_my_documents(biz)
    return api_json(
        http_status=200,
        data=[d.model_dump() for d in docs],
    )


@router.get(
    "/documents/{document_id}",
    summary="서류 상세 조회",
    description="특정 서류의 파일 URL과 OCR 결과를 반환합니다. 본인 소유 서류만 조회 가능합니다.",
)
async def get_document_detail(
    document_id: uuid.UUID,
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> JSONResponse:
    data = await svc.get_document_detail(biz, document_id)
    return api_json(http_status=200, data=data.model_dump())


@router.delete(
    "/documents/{document_id}",
    summary="서류 영구 삭제(파기)",
    description="서류를 저장소와 DB에서 모두 영구 삭제합니다. 본인 소유 서류만 삭제 가능합니다.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: uuid.UUID,
    biz: ActiveBusiness,
    svc: BusinessServiceDep,
) -> None:
    await svc.delete_document(biz, document_id)
