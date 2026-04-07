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
from typing import Any, Optional, Type, TypeVar

from sqlalchemy import select, Select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.business.model import (
    Business,
    BusinessFinancialSnapshot,
    Document,
)

# 제네릭 타입 설정 (Base Query 재사용 용도)
T = TypeVar("T")

class BusinessRepository:
    """사업장 도메인 Repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self, model: Type[T]) -> Select:
        """[실무 팁] 모든 조회의 기본 통로. 
        
        1. 활성 데이터 가드: is_active=True인 데이터만 가져오도록 강제하여 삭제된 데이터 유출 방지.
        2. 유지보수 효율: 나중에 전역 필터 로직이 바뀌어도 이 곳만 수정하면 전체 쿼리에 반영됨.
        """
        return select(model).where(model.is_active.is_(True))

    # ── Business ───────────────────────────────────────────────────────────

    async def get_active_business_by_user_id(
        self, user_id: uuid.UUID
    ) -> Business | None:
        """1. 유저의 메인 사업장 찾기:
        가장 먼저 등록된(created_at.asc) 활성 사업장을 '기본 사업장'으로 간주하여 반환해요.
        """
        stmt = (
            self._base_query(Business)
            .where(Business.user_id == user_id)
            .order_by(Business.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_business_by_biz_no(self, biz_no: str) -> Business | None:
        """2. 사업자번호 중복 검사:
        이미 우리 서비스에 가입된 '살아있는' 사업자인지 확인하는 출입증 검사 로직이에요.
        """
        stmt = self._base_query(Business).where(Business.biz_no == biz_no)
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
        """3. 새 사업장 그릇 만들기:
        사장님이 입력한 정보를 바탕으로 새로운 사업장 레코드를 생성하고 '활성(True)' 상태로 저장해요.
        """
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
        **kwargs
    ) -> None:
        """4. 정보 수정 배달원:
        변경된 정보만 골라서 업데이트해요. (Service에서 검증된 값들만 전달받음)
        """
        for key, value in kwargs.items():
            if hasattr(biz, key) and value is not None:
                setattr(biz, key, value)
        await self._session.flush()

    # ── BusinessFinancialSnapshot ──────────────────────────────────────────

    async def get_financial_snapshot_by_year(
        self,
        business_id: uuid.UUID,
        year: int,
    ) -> BusinessFinancialSnapshot | None:
        """5. 연도별 장부 찾기:
        특정 연도의 재무 상태 스냅샷을 가져와요. 삭제된 데이터는 자동으로 필터링됩니다.
        """
        stmt = self._base_query(BusinessFinancialSnapshot).where(
            BusinessFinancialSnapshot.business_id == business_id,
            BusinessFinancialSnapshot.snapshot_year == year,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_financial_history(
        self,
        business_id: uuid.UUID,
    ) -> list[BusinessFinancialSnapshot]:
        """6. 재무 이력 정렬하기:
        사장님의 과거 재무 기록을 최신순(year.desc)으로 나열하여 대시보드에 보여줄 준비를 해요.
        """
        stmt = (
            self._base_query(BusinessFinancialSnapshot)
            .where(BusinessFinancialSnapshot.business_id == business_id)
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
        """7. 재무 데이터 기록:
        수기 입력이나 OCR로 파싱된 재무 지표를 DB에 영구 보관해요.
        """
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

    async def soft_delete_financial_snapshot(
        self,
        snap: BusinessFinancialSnapshot,
    ) -> None:
        """8. 데이터 숨기기 (Soft Delete):
        사장님이 삭제를 눌러도 기록은 남겨둬요(나중에 사고 발생 시 확인용). 서비스에서는 안 보이게 처리합니다.
        """
        snap.is_active = False
        await self._session.flush()

    # ── Document ───────────────────────────────────────────────────────────

    async def get_documents_by_business_id(
        self,
        business_id: uuid.UUID,
    ) -> list[Document]:
        """9. 서류함 조회:
        우리 사업장에 등록된 활성 서류 목록을 최신순으로 가져와요.
        """
        stmt = (
            self._base_query(Document)
            .where(Document.business_id == business_id)
            .order_by(Document.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_document_by_id(
        self,
        document_id: uuid.UUID,
    ) -> Document | None:
        """10. 서류 단건 상세 조회:
        특정 서류의 상세 정보(OCR 결과 등)를 조회해요. (보안을 위해 is_active 여부는 Service에서 최종 판단)
        """
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
        """11. 업로드 서류 등록:
        S3에 올라간 파일의 주소와 OCR 진행 상태를 기록하여 분석을 시작할 준비를 해요.
        """
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
        """12. OCR 작업 메모:
        비동기로 돌아가던 AI 작업이 끝나면, 그 결과를 서류 레코드에 '나중에 할 일 메모'처럼 업데이트해요.
        """
        doc.ocr_status = ocr_status
        if ocr_result is not None:
            doc.ocr_result = ocr_result
        await self._session.flush()

    async def soft_delete_document(self, doc: Document) -> None:
        """13. 서류 파기(논리):
        서류를 삭제 처리하지만, 법적 증빙을 위해 원본 데이터와 파일 경로는 DB에 남겨둡니다.
        """
        doc.is_active = False
        await self._session.flush()

    # ── 타 도메인 지원용 (Internal) ───────────────────────────────────────────

    async def get_latest_financial_snapshot_internal(
        self, business_id: uuid.UUID
    ) -> BusinessFinancialSnapshot | None:
        """
        [Internal] 정밀 진단(Diagnosis) 등 타 도메인에서 가장 최신 연도의 재무 데이터를 요구할 때 사용합니다.
        """
        stmt = (
            self._base_query(BusinessFinancialSnapshot)
            .where(BusinessFinancialSnapshot.business_id == business_id)
            .order_by(BusinessFinancialSnapshot.snapshot_year.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def deactivate_all_businesses_by_user_internal(self, user_id: uuid.UUID) -> None:
        """[Internal] 유저 탈퇴 시 연관된 모든 사업장을 논리 삭제(Soft Delete)합니다."""
        from sqlalchemy import update
        stmt = (
            update(Business)
            .where(Business.user_id == user_id, Business.is_active == True)
            .values(is_active=False)
        )
        await self._session.execute(stmt)