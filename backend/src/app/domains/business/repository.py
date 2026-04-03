# src/app/domains/business/repository.py
"""사업장 도메인 DB 접근 계층.

원칙:
  - 비즈니스 판단(예외 발생, 조건 분기)은 Service에서, I/O만 여기에.
  - [도메인 규칙 0: Data Persistence] 삭제는 모두 Soft Delete(is_active=False).
    물리 삭제(Hard Delete)는 법적 보존 기간 만료 후 별도 배치 작업에서만 수행.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.model import (
    Business,
    BusinessFinancialSnapshot,
    Document,
)


class BusinessRepository:
    """사업장 도메인 Repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Business ───────────────────────────────────────────────────────────

    async def get_active_business_by_user_id(
        self, user_id: uuid.UUID
    ) -> Business | None:
        """유저의 첫 번째 활성 사업장 반환 (단일 컨텍스트 기준).

        [도메인 규칙 2.2]: X-Business-Id 헤더 기반 다중 사업장 지원은
        향후 확장 포인트. 현재는 가장 먼저 등록된 활성 사업장을 기본으로 사용.
        """
        stmt = (
            select(Business)
            .where(
                Business.user_id == user_id,
                Business.is_active.is_(True),
            )
            .order_by(Business.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_business_by_biz_no(self, biz_no: str) -> Business | None:
        """사업자번호 중복 등록 방지용 조회."""
        stmt = select(Business).where(
            Business.biz_no == biz_no,
            Business.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_business(
        self,
        *,
        user_id: uuid.UUID,
        biz_name: str,
        biz_no: Optional[str],
        representative_name: Optional[str],
        ksic_code: Optional[str],
        sector_code: Optional[str],
        region_sido: Optional[str],
        region_sigungu: Optional[str],
        establishment_date: Optional[date],
        has_patent: bool,
        is_female_ent: bool,
        is_ventured: bool,
        profile_score: int,
    ) -> Business:
        biz = Business(
            user_id=user_id,
            biz_name=biz_name,
            biz_no=biz_no,
            representative_name=representative_name,
            ksic_code=ksic_code,
            sector_code=sector_code,
            region_sido=region_sido,
            region_sigungu=region_sigungu,
            establishment_date=establishment_date,
            has_patent=has_patent,
            is_female_ent=is_female_ent,
            is_ventured=is_ventured,
            profile_score=profile_score,
            is_active=True,
        )
        self._session.add(biz)
        await self._session.flush()
        await self._session.refresh(biz)
        return biz

    async def update_business(
        self,
        biz: Business,
        *,
        biz_name: Optional[str] = None,
        representative_name: Optional[str] = None,
        region_sido: Optional[str] = None,
        region_sigungu: Optional[str] = None,
        establishment_date: Optional[date] = None,
        ksic_code: Optional[str] = None,
        sector_code: Optional[str] = None,
        has_patent: Optional[bool] = None,
        is_female_ent: Optional[bool] = None,
        is_ventured: Optional[bool] = None,
        profile_score: Optional[int] = None,
    ) -> None:
        if biz_name is not None:
            biz.biz_name = biz_name
        if representative_name is not None:
            biz.representative_name = representative_name
        if region_sido is not None:
            biz.region_sido = region_sido
        if region_sigungu is not None:
            biz.region_sigungu = region_sigungu
        if establishment_date is not None:
            biz.establishment_date = establishment_date
        if ksic_code is not None:
            biz.ksic_code = ksic_code
        if sector_code is not None:
            biz.sector_code = sector_code
        if has_patent is not None:
            biz.has_patent = has_patent
        if is_female_ent is not None:
            biz.is_female_ent = is_female_ent
        if is_ventured is not None:
            biz.is_ventured = is_ventured
        if profile_score is not None:
            biz.profile_score = profile_score
        await self._session.flush()

    # ── BusinessFinancialSnapshot ──────────────────────────────────────────

    async def get_financial_snapshot_by_year(
        self,
        business_id: uuid.UUID,
        year: int,
    ) -> BusinessFinancialSnapshot | None:
        """활성(is_active=True) 스냅샷만 조회 — Soft Delete 필터 적용."""
        stmt = select(BusinessFinancialSnapshot).where(
            BusinessFinancialSnapshot.business_id == business_id,
            BusinessFinancialSnapshot.snapshot_year == year,
            BusinessFinancialSnapshot.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_financial_history(
        self,
        business_id: uuid.UUID,
    ) -> list[BusinessFinancialSnapshot]:
        """활성(is_active=True) 스냅샷 전체 — 연도 내림차순."""
        stmt = (
            select(BusinessFinancialSnapshot)
            .where(
                BusinessFinancialSnapshot.business_id == business_id,
                BusinessFinancialSnapshot.is_active.is_(True),
            )
            .order_by(BusinessFinancialSnapshot.snapshot_year.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_financial_snapshot(
        self,
        *,
        business_id: uuid.UUID,
        snapshot_year: int,
        snapshot_period: str,
        term_type: str,
        annual_revenue: Optional[int],
        operating_profit: Optional[int],
        net_income: Optional[int],
        total_debt: Optional[int],
        capital: Optional[int],
        debt_ratio: Optional[float],
        employee_count: Optional[int],
        tax_arrears_yn: bool,
    ) -> BusinessFinancialSnapshot:
        snap = BusinessFinancialSnapshot(
            business_id=business_id,
            snapshot_year=snapshot_year,
            snapshot_period=snapshot_period,
            term_type=term_type,
            annual_revenue=annual_revenue,
            operating_profit=operating_profit,
            net_income=net_income,
            total_debt=total_debt,
            capital=capital,
            debt_ratio=debt_ratio,
            employee_count=employee_count,
            tax_arrears_yn=tax_arrears_yn,
            ocr_status="MANUAL",
            is_verified=False,
            is_active=True,
        )
        self._session.add(snap)
        await self._session.flush()
        await self._session.refresh(snap)
        return snap

    async def update_financial_snapshot(
        self,
        snap: BusinessFinancialSnapshot,
        *,
        annual_revenue: Optional[int] = None,
        operating_profit: Optional[int] = None,
        net_income: Optional[int] = None,
        total_debt: Optional[int] = None,
        capital: Optional[int] = None,
        debt_ratio: Optional[float] = None,
        employee_count: Optional[int] = None,
        tax_arrears_yn: Optional[bool] = None,
    ) -> None:
        if annual_revenue is not None:
            snap.annual_revenue = annual_revenue
        if operating_profit is not None:
            snap.operating_profit = operating_profit
        if net_income is not None:
            snap.net_income = net_income
        if total_debt is not None:
            snap.total_debt = total_debt
        if capital is not None:
            snap.capital = capital
        if debt_ratio is not None:
            snap.debt_ratio = debt_ratio
        if employee_count is not None:
            snap.employee_count = employee_count
        if tax_arrears_yn is not None:
            snap.tax_arrears_yn = tax_arrears_yn
        await self._session.flush()

    async def soft_delete_financial_snapshot(
        self,
        snap: BusinessFinancialSnapshot,
    ) -> None:
        """[도메인 규칙: 데이터 보존 정책 준수] Soft Delete.

        is_active=False 처리 — 원장 데이터는 보존하여 감사(Audit) 추적을 유지한다.
        """
        snap.is_active = False
        await self._session.flush()

    # ── Document ───────────────────────────────────────────────────────────

    async def get_documents_by_business_id(
        self,
        business_id: uuid.UUID,
    ) -> list[Document]:
        """활성(is_active=True) 서류만 반환."""
        stmt = (
            select(Document)
            .where(
                Document.business_id == business_id,
                Document.is_active.is_(True),
            )
            .order_by(Document.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_document_by_id(
        self,
        document_id: uuid.UUID,
    ) -> Document | None:
        """id 기준 단건 조회 — is_active 필터 없음(소유권 확인 후 Service에서 판단)."""
        stmt = select(Document).where(Document.id == document_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_document(
        self,
        *,
        business_id: uuid.UUID,
        doc_type: str,
        file_url: str,
        ocr_status: str = "PENDING",
    ) -> Document:
        doc = Document(
            business_id=business_id,
            doc_type=doc_type,
            file_url=file_url,
            ocr_status=ocr_status,
            is_active=True,
        )
        self._session.add(doc)
        await self._session.flush()
        await self._session.refresh(doc)
        return doc

    async def update_document_status(
        self,
        doc: Document,
        *,
        ocr_status: str,
        ocr_result: Optional[dict[str, Any]] = None,
    ) -> None:
        """비동기 OCR 작업 완료 콜백용 상태 + 결과 한 번에 업데이트.

        사용 흐름:
          PENDING → COMPLETED (ocr_result 채워짐)
          PENDING → FAILED    (ocr_result=None 또는 에러 정보)
        """
        doc.ocr_status = ocr_status
        if ocr_result is not None:
            doc.ocr_result = ocr_result
        await self._session.flush()

    async def soft_delete_document(self, doc: Document) -> None:
        """[도메인 규칙: 데이터 보존 정책 준수] Soft Delete.

        is_active=False 처리 — S3 파일 경로(file_url)를 포함한 레코드를 보존한다.
        법적 보존 기간(최대 5년) 만료 후 배치 작업에서 Hard Delete.
        """
        doc.is_active = False
        await self._session.flush()
