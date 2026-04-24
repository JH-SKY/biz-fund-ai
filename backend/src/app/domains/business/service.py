# src/app/domains/business/service.py
"""사업장 도메인 비즈니스 로직 및 트랜잭션 경계.

설계 원칙:
  - 외부 서비스(국세청 API, S3, 통계 검증)는 인터페이스(interfaces.py)를 통해
    주입받는다. Service는 구현체를 모른다 → 갈아끼워도 이 파일은 건드리지 않는다.
  - RAG/LangGraph 연동 준비: sector_code, business_id 같은 컨텍스트 정보를
    외부 서비스 호출 시 항상 전달할 수 있는 구조를 유지한다.
  - 모든 DB 커밋은 Service에서만 발생한다 (Repository는 flush만).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.domains.auth.model import User
from src.app.domains.business.exception import (
    biz_no_api_unavailable,
    biz_no_closed,
    biz_no_suspended,
    business_already_registered,
    business_not_found,
    document_forbidden,
    document_not_found,
    finance_already_exists,
    finance_not_found,
)
from src.app.domains.business.interfaces import (
    IBizVerificationService,
    IFileStorageService,
    IStatsValidationService,
    NTS_ERR_TIMEOUT,
    NTS_ERR_API_ERROR,
    NTS_ERR_SERVER_CONFIG,
)
from src.app.domains.business.model import Business, BusinessFinancialSnapshot
from src.app.domains.business.repository import BusinessRepository
from src.app.domains.business.schema import (
    BusinessInfoResponseData,
    BusinessUpdateRequest,
    DocumentDetailResponseData,
    DocumentListItemData,
    FinanceCreateRequest,
    FinanceSnapshotResponseData,
    FinanceUpdateRequest,
    OnboardingRegisterRequest,
    OnboardingRegisterResponseData,
    ValidateStatsRequest,
    ValidateStatsResponseData,
    VerifyBizNumberResponseData,
)

# ── 내부 유틸 ──────────────────────────────────────────────────────────────


def _compute_profile_score(biz: Business) -> int:
    """사업장 정보 완성도 점수 계산 (0~100점).

    완성도가 높을수록 정책 매칭 정밀도가 올라간다.
    """
    score = 0
    if biz.biz_no:
        score += 20
    if biz.ksic_code:
        score += 20
    if biz.region_sido:
        score += 10
    if biz.region_sigungu:
        score += 5
    if biz.establishment_date:
        score += 15
    if biz.representative_name:
        score += 10
    if biz.has_patent:
        score += 10
    if biz.is_female_ent:
        score += 5
    if biz.is_ventured:
        score += 5
    return min(score, 100)


def _compute_debt_ratio(
    total_debt: Optional[int],
    annual_revenue: Optional[int],
) -> Optional[float]:
    """부채 비율 자동 계산: (총부채 / 연매출) × 100."""
    if total_debt is None or annual_revenue is None or annual_revenue == 0:
        return None
    return round(total_debt / annual_revenue * 100, 2)


def _to_info_response(biz: Business) -> BusinessInfoResponseData:
    return BusinessInfoResponseData(
        biz_id=str(biz.id),
        biz_name=biz.biz_name,
        biz_no=biz.biz_no,
        representative_name=biz.representative_name,
        region_sido=biz.region_sido,
        region_sigungu=biz.region_sigungu,
        establishment_date=biz.establishment_date,
        ksic_code=biz.ksic_code,
        sector_code=biz.sector_code,
        has_patent=biz.has_patent,
        is_female_ent=biz.is_female_ent,
        is_ventured=biz.is_ventured,
        profile_score=biz.profile_score,
        created_at=biz.created_at,
    )


def _to_finance_response(
    snap: BusinessFinancialSnapshot,
) -> FinanceSnapshotResponseData:
    return FinanceSnapshotResponseData(
        finance_id=str(snap.id),
        snapshot_year=snap.snapshot_year,
        snapshot_period=snap.snapshot_period,
        annual_revenue=snap.annual_revenue,
        operating_profit=snap.operating_profit,
        net_income=snap.net_income,
        total_debt=snap.total_debt,
        capital=snap.capital,
        debt_ratio=float(snap.debt_ratio) if snap.debt_ratio is not None else None,
        employee_count=snap.employee_count,
        tax_arrears_yn=snap.tax_arrears_yn,
        is_verified=snap.is_verified,
        created_at=snap.created_at,
    )


# ── Service ────────────────────────────────────────────────────────────────


class BusinessService:
    """사업장 도메인 유스케이스.

    외부 서비스는 생성자 주입으로 받는다 — 테스트·교체 시 여기만 변경.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: BusinessRepository,
        biz_verification: IBizVerificationService,
        stats_validation: IStatsValidationService,
        file_storage: IFileStorageService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._biz_verification = biz_verification
        self._stats_validation = stats_validation
        self._file_storage = file_storage

    # ── 온보딩 ────────────────────────────────────────────────────────────

    async def verify_biz_number(self, biz_no: str) -> VerifyBizNumberResponseData:
        """[온보딩 2단계] 국세청 진위 확인 API 호출 (상태 조회).

        이 메서드는 프론트엔드 실시간 확인 전용이다. DB 저장은 하지 않는다.
        최종 등록 시 register_business 에서 검증 결과가 DB에 반영된다.
        """
        result = await self._biz_verification.verify(biz_no)
        return VerifyBizNumberResponseData(
            is_valid=result.is_valid,
            biz_status=result.biz_status,
            tax_type=result.tax_type,
            error_code=result.error_code,
        )

    async def register_business(
        self,
        user: User,
        body: OnboardingRegisterRequest,
    ) -> OnboardingRegisterResponseData:
        """온보딩: 사업장 최초 등록.

        [로직 순서]
        1. 사업자번호 중복 체크 (이미 등록된 활성 사업장)
        2. 국세청 API 호출하여 상태 확인
           - is_manual=True 이면 스킵 (API 점검 중 수동 등록 허용)
           - 이미 동일 biz_no 가 is_biz_no_verified=True 로 DB에 존재하면 재호출 생략
           - 폐업/휴업 상태면 등록 차단
           - API 호출 실패(타임아웃·오류) 시 503 반환 → 프론트가 is_manual=True 재시도 유도
        3. 사업장 생성 + 검증 결과 즉시 저장
        4. employee_count 입력 시 현재 연도 재무 스냅샷 자동 생성
        5. profile_score 자동 계산
        """
        # [1] 중복 체크
        existing = await self._repo.get_business_by_biz_no(body.biz_no)
        if existing is not None:
            raise business_already_registered()

        # [2] 국세청 검증 (is_manual=False 일 때만 수행)
        is_biz_no_verified = False
        biz_verified_status: str | None = None
        tax_type_val: str | None = None
        verified_at: datetime | None = None

        if not body.is_manual:
            # 동일 biz_no 에 대해 이미 검증한 이력이 있으면 재호출 생략
            cached = await self._repo.get_verified_business_by_biz_no(body.biz_no)
            if cached is not None:
                is_biz_no_verified = True
                biz_verified_status = cached.biz_verified_status
                tax_type_val = cached.tax_type
                verified_at = cached.biz_verified_at
            else:
                result = await self._biz_verification.verify(body.biz_no)

                # API 자체 실패 (타임아웃·HTTP 오류·서버 설정 오류) → 503
                if result.error_code in (
                    NTS_ERR_TIMEOUT,
                    NTS_ERR_API_ERROR,
                    NTS_ERR_SERVER_CONFIG,
                ):
                    raise biz_no_api_unavailable()

                # 폐업 사업자 — 정책 지원 불가, 등록 차단
                if result.biz_status == "폐업자":
                    raise biz_no_closed()

                # 휴업 사업자 — 정책 지원 불가, 등록 차단
                if result.biz_status == "휴업자":
                    raise biz_no_suspended()

                is_biz_no_verified = result.is_valid
                biz_verified_status = result.biz_status
                tax_type_val = result.tax_type
                verified_at = datetime.now(timezone.utc) if result.is_valid else None

        # [3] 사업장 생성 (검증 결과 포함)
        biz = await self._repo.create_business(
            user_id=user.id,
            biz_name=body.biz_name,
            biz_no=body.biz_no,
            representative_name=body.representative_name,
            ksic_code=body.ksic_code,
            sector_code=body.sector_code,
            region_sido=body.region_sido,
            region_sigungu=body.region_sigungu,
            establishment_date=body.establishment_date,
            has_patent=body.has_patent,
            is_female_ent=body.is_female_ent,
            is_ventured=body.is_ventured,
            profile_score=0,
            is_biz_no_verified=is_biz_no_verified,
            biz_verified_status=biz_verified_status,
            tax_type=tax_type_val,
            biz_verified_at=verified_at,
        )

        # [4] employee_count 입력 시 현재 연도 재무 스냅샷 자동 생성
        if body.employee_count is not None:
            current_year = datetime.now(timezone.utc).year
            await self._repo.create_financial_snapshot(
                business_id=biz.id,
                snapshot_year=current_year,
                snapshot_period="ANNUAL",
                term_type="ANNUAL",
                annual_revenue=None,
                operating_profit=None,
                net_income=None,
                total_debt=None,
                capital=None,
                debt_ratio=None,
                employee_count=body.employee_count,
                tax_arrears_yn=False,
            )

        # [5] profile_score 자동 계산
        score = _compute_profile_score(biz)
        await self._repo.update_business(biz, profile_score=score)
        await self._session.commit()

        return OnboardingRegisterResponseData(
            biz_id=str(biz.id),
            biz_name=biz.biz_name,
            biz_no=biz.biz_no or "",
            is_manual=body.is_manual,
            profile_score=score,
        )

    # ── 사업장 조회 / 수정 ────────────────────────────────────────────────

    async def get_my_business(self, user: User) -> BusinessInfoResponseData:
        """CurrentUser 기반 조회 — 온보딩 미완료 시 404 반환."""
        biz = await self._repo.get_active_business_by_user_id(user.id)
        if biz is None:
            raise business_not_found()
        return _to_info_response(biz)

    async def get_business_info(self, biz: Business) -> BusinessInfoResponseData:
        """ActiveBusiness(이미 조회된 사업장) 기반 DTO 변환 — 이중 쿼리 방지."""
        return _to_info_response(biz)

    async def update_my_business(
        self,
        biz: Business,
        body: BusinessUpdateRequest,
    ) -> None:
        """사업장 기본 정보 수정 후 profile_score 자동 재계산.

        [도메인 규칙 4.3]: 사업장 정보 수정 시 매칭 로직 재실행 트리거 대상.
        현재는 score 재계산만 수행, 추후 match_logs 갱신 작업으로 확장.
        """
        await self._repo.update_business(
            biz,
            biz_name=body.biz_name,
            representative_name=body.representative_name,
            region_sido=body.region_sido,
            region_sigungu=body.region_sigungu,
            establishment_date=body.establishment_date,
            ksic_code=body.ksic_code,
            sector_code=body.sector_code,
            has_patent=body.has_patent,
            is_female_ent=body.is_female_ent,
            is_ventured=body.is_ventured,
        )
        score = _compute_profile_score(biz)
        await self._repo.update_business(biz, profile_score=score)
        await self._session.commit()

    # ── 재무 스냅샷 ───────────────────────────────────────────────────────

    async def create_financial_snapshot(
        self,
        biz: Business,
        body: FinanceCreateRequest,
    ) -> FinanceSnapshotResponseData:
        existing = await self._repo.get_financial_snapshot_by_year(
            biz.id, body.snapshot_year
        )

        debt_ratio = _compute_debt_ratio(body.total_debt, body.annual_revenue)

        if existing is not None:
            if existing.annual_revenue is None and existing.is_verified is False:
                await self._repo.update_financial_snapshot(
                    existing,
                    annual_revenue=body.annual_revenue,
                    operating_profit=body.operating_profit,
                    net_income=body.net_income,
                    total_debt=body.total_debt,
                    capital=body.capital,
                    debt_ratio=debt_ratio,
                    employee_count=body.employee_count
                    if body.employee_count is not None
                    else existing.employee_count,
                    tax_arrears_yn=body.tax_arrears_yn,
                )
                await self._session.commit()
                return _to_finance_response(existing)
            else:
                raise finance_already_exists(body.snapshot_year)

        snap = await self._repo.create_financial_snapshot(
            business_id=biz.id,
            snapshot_year=body.snapshot_year,
            snapshot_period=body.snapshot_period,
            term_type=body.term_type,
            annual_revenue=body.annual_revenue,
            operating_profit=body.operating_profit,
            net_income=body.net_income,
            total_debt=body.total_debt,
            capital=body.capital,
            debt_ratio=debt_ratio,
            employee_count=body.employee_count,
            tax_arrears_yn=body.tax_arrears_yn,
        )
        await self._session.commit()
        return _to_finance_response(snap)

    async def update_financial_snapshot(
        self,
        biz: Business,
        year: int,
        body: FinanceUpdateRequest,
    ) -> None:
        snap = await self._repo.get_financial_snapshot_by_year(biz.id, year)
        if snap is None:
            raise finance_not_found(year)

        new_revenue = (
            body.annual_revenue
            if body.annual_revenue is not None
            else snap.annual_revenue
        )
        new_debt = body.total_debt if body.total_debt is not None else snap.total_debt
        debt_ratio = _compute_debt_ratio(new_debt, new_revenue)

        await self._repo.update_financial_snapshot(
            snap,
            annual_revenue=body.annual_revenue,
            operating_profit=body.operating_profit,
            net_income=body.net_income,
            total_debt=body.total_debt,
            capital=body.capital,
            debt_ratio=debt_ratio,
            employee_count=body.employee_count,
            tax_arrears_yn=body.tax_arrears_yn,
        )
        await self._session.commit()

    async def get_financial_history(
        self, biz: Business
    ) -> list[FinanceSnapshotResponseData]:
        snaps = await self._repo.get_financial_history(biz.id)
        return [_to_finance_response(s) for s in snaps]

    async def delete_financial_snapshot(self, biz: Business, year: int) -> None:
        snap = await self._repo.get_financial_snapshot_by_year(biz.id, year)
        if snap is None:
            raise finance_not_found(year)
        await self._repo.soft_delete_financial_snapshot(snap)
        await self._session.commit()

    # ── 통계 검증 ─────────────────────────────────────────────────────────

    async def validate_stats(
        self, body: ValidateStatsRequest, sector_code: str | None = None
    ) -> ValidateStatsResponseData:
        """업종 평균 대비 이상치 검증.

        sector_code: 추후 AI 엔진 연결 시 컨텍스트로 전달 (현재 Mock에서는 미사용).
        """
        result = await self._stats_validation.validate(
            stat_type=body.type,
            value=body.value,
            sector_code=sector_code,
        )
        return ValidateStatsResponseData(
            is_valid=result.is_valid,
            message=result.message,
        )

    # ── 디지털 서류함 ─────────────────────────────────────────────────────

    async def upload_document(
        self,
        biz: Business,
        file: UploadFile,
        doc_type: str,
    ) -> DocumentListItemData:
        """서류 업로드 → 즉시 202 반환, 비동기 OCR은 IFileStorageService에서 처리.

        [도메인 규칙 Async First]: OCR 분석은 무거운 작업이므로 비동기 처리.
        실제 구현 시 IFileStorageService.upload() 내부에서 Celery/ARQ 태스크 디스패치.
        """
        file_bytes = await file.read()
        filename = f"{biz.id}/{uuid.uuid4()}_{file.filename or 'document'}"
        file_url = await self._file_storage.upload(
            file_bytes=file_bytes,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
        )
        doc = await self._repo.create_document(
            business_id=biz.id,
            doc_type=doc_type,
            file_url=file_url,
            ocr_status="PENDING",
        )
        await self._session.commit()
        return DocumentListItemData(
            document_id=str(doc.id),
            doc_type=doc.doc_type,
            ocr_status=doc.ocr_status,
            created_at=doc.created_at,
        )

    async def get_my_documents(self, biz: Business) -> list[DocumentListItemData]:
        docs = await self._repo.get_documents_by_business_id(biz.id)
        return [
            DocumentListItemData(
                document_id=str(d.id),
                doc_type=d.doc_type,
                ocr_status=d.ocr_status,
                created_at=d.created_at,
            )
            for d in docs
        ]

    async def get_document_detail(
        self,
        biz: Business,
        document_id: uuid.UUID,
    ) -> DocumentDetailResponseData:
        doc = await self._repo.get_document_by_id(document_id)
        if doc is None:
            raise document_not_found()
        if doc.business_id != biz.id:
            raise document_forbidden()
        return DocumentDetailResponseData(
            document_id=str(doc.id),
            doc_type=doc.doc_type,
            file_url=doc.file_url,
            ocr_status=doc.ocr_status,
            ocr_result=doc.ocr_result,
            issued_at=doc.issued_at,
            created_at=doc.created_at,
        )

    async def delete_document(
        self,
        biz: Business,
        document_id: uuid.UUID,
    ) -> None:
        doc = await self._repo.get_document_by_id(document_id)
        if doc is None:
            raise document_not_found()
        if doc.business_id != biz.id:
            raise document_forbidden()
        await self._repo.soft_delete_document(doc)
        await self._session.commit()

    # ── 타 도메인 지원용 (Internal) ───────────────────────────────────────────

    async def get_latest_financial_snapshot_internal(
        self, business_id: uuid.UUID
    ) -> BusinessFinancialSnapshot | None:
        """
        [Internal] 정밀진단(Diagnosis) 도메인에서 '진단 준비(Pre-check)' 단계 수행 시
        사업장의 가장 최근 재무 데이터를 가져오기 위해 호출하는 브릿지 인터페이스입니다.
        """
        return await self._repo.get_latest_financial_snapshot_internal(business_id)

    async def deactivate_all_businesses_by_user_internal(
        self, user_id: uuid.UUID
    ) -> None:
        """[Internal] Auth 도메인에서 회원 탈퇴 시 호출"""
        await self._repo.deactivate_all_businesses_by_user_internal(user_id)
