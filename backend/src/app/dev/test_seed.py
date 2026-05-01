from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

import src.app.domains.auth.model  # noqa: F401
import src.app.domains.business.model  # noqa: F401
import src.app.domains.chat.model  # noqa: F401
import src.app.domains.diagnosis.model  # noqa: F401
import src.app.domains.notification.model  # noqa: F401
import src.app.domains.policy.model  # noqa: F401
import src.app.domains.system.model  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domains.auth.model import SocialProvider
from src.app.domains.auth.repository import AuthRepository
from src.app.domains.business.repository import BusinessRepository
from src.app.domains.policy.model import PolicyStatus
from src.app.domains.policy.repository import PolicyRepository


@dataclass(frozen=True)
class TestScenario:
    key: str
    name: str
    email: str
    social_id: str
    provider: SocialProvider
    business_name: str
    representative_name: str
    biz_no: str
    ksic_code: str
    ksic_name: str
    sector_code: str
    region_sido: str
    region_sigungu: str
    establishment_date: date
    employee_count: int
    annual_revenue: int
    total_debt: int
    debt_ratio: float
    tax_arrears: bool
    is_female_ent: bool
    is_ventured: bool
    has_patent: bool
    funding_purpose: str
    profile_score: int
    summary: str


@dataclass(frozen=True)
class TestPolicy:
    origin_id: str
    title: str
    agency_name: str
    category: str
    region: str
    support_type: str
    support_amount_desc: str
    max_support: int
    closed_at: date
    required_documents: list[str]
    target_logic: dict
    bonus_logic: dict
    ai_summary: str
    ai_full_explanation: str
    content_raw: str
    apply_url: str


TEST_SCENARIOS: tuple[TestScenario, ...] = (
    TestScenario(
        key="BIZ-01",
        name="서울 초기 외식업",
        email="dev.biz01@bizmong.local",
        social_id="dev-biz-01",
        provider=SocialProvider.NAVER,
        business_name="서울별빛카페",
        representative_name="김별빛",
        biz_no="100-11-00001",
        ksic_code="56111",
        ksic_name="한식 음식점업",
        sector_code="FOOD",
        region_sido="서울",
        region_sigungu="마포구",
        establishment_date=date(2025, 3, 15),
        employee_count=2,
        annual_revenue=80_000_000,
        total_debt=20_000_000,
        debt_ratio=35.0,
        tax_arrears=False,
        is_female_ent=False,
        is_ventured=False,
        has_patent=False,
        funding_purpose="OPERATING",
        profile_score=76,
        summary="서울 소재 초기 창업 카페. 초기창업과 전국 소상공인 정책 검증용 계정",
    ),
    TestScenario(
        key="BIZ-02",
        name="경기 성장 제조업",
        email="dev.biz02@bizmong.local",
        social_id="dev-biz-02",
        provider=SocialProvider.NAVER,
        business_name="경기정밀테크",
        representative_name="박정밀",
        biz_no="100-11-00002",
        ksic_code="29261",
        ksic_name="금속 가공기계 제조업",
        sector_code="MANUFACTURING",
        region_sido="경기",
        region_sigungu="수원시",
        establishment_date=date(2021, 4, 1),
        employee_count=12,
        annual_revenue=400_000_000,
        total_debt=100_000_000,
        debt_ratio=82.0,
        tax_arrears=False,
        is_female_ent=False,
        is_ventured=False,
        has_patent=False,
        funding_purpose="FACILITY",
        profile_score=84,
        summary="경기 제조업 5년차. 설비개선 자금과 고용 확대 정책 검증용 계정",
    ),
    TestScenario(
        key="BIZ-03",
        name="부산 여성 서비스업",
        email="dev.biz03@bizmong.local",
        social_id="dev-biz-03",
        provider=SocialProvider.NAVER,
        business_name="부산해봄컨설팅",
        representative_name="이해봄",
        biz_no="100-11-00003",
        ksic_code="70209",
        ksic_name="경영 컨설팅업",
        sector_code="SERVICE",
        region_sido="부산",
        region_sigungu="해운대구",
        establishment_date=date(2023, 2, 10),
        employee_count=4,
        annual_revenue=150_000_000,
        total_debt=30_000_000,
        debt_ratio=40.0,
        tax_arrears=False,
        is_female_ent=True,
        is_ventured=False,
        has_patent=False,
        funding_purpose="OPERATING",
        profile_score=80,
        summary="부산 여성기업 서비스업. 여성기업 우대 정책 검증용 계정",
    ),
    TestScenario(
        key="BIZ-04",
        name="대구 벤처 IT",
        email="dev.biz04@bizmong.local",
        social_id="dev-biz-04",
        provider=SocialProvider.NAVER,
        business_name="대구넥스트AI",
        representative_name="최넥스트",
        biz_no="100-11-00004",
        ksic_code="62010",
        ksic_name="컴퓨터 프로그래밍 서비스업",
        sector_code="IT",
        region_sido="대구",
        region_sigungu="수성구",
        establishment_date=date(2024, 1, 5),
        employee_count=6,
        annual_revenue=220_000_000,
        total_debt=40_000_000,
        debt_ratio=28.0,
        tax_arrears=False,
        is_female_ent=False,
        is_ventured=True,
        has_patent=True,
        funding_purpose="WORKING",
        profile_score=88,
        summary="대구 벤처 IT 기업. 기술창업 혁신자금과 특허/벤처 우대 검증용 계정",
    ),
    TestScenario(
        key="BIZ-05",
        name="강원 관광 소상공인",
        email="dev.biz05@bizmong.local",
        social_id="dev-biz-05",
        provider=SocialProvider.NAVER,
        business_name="강원하늘스테이",
        representative_name="정하늘",
        biz_no="100-11-00005",
        ksic_code="55101",
        ksic_name="호텔업",
        sector_code="TOURISM",
        region_sido="강원",
        region_sigungu="강릉시",
        establishment_date=date(2018, 7, 1),
        employee_count=5,
        annual_revenue=90_000_000,
        total_debt=60_000_000,
        debt_ratio=120.0,
        tax_arrears=False,
        is_female_ent=False,
        is_ventured=False,
        has_patent=False,
        funding_purpose="OPERATING",
        profile_score=74,
        summary="강원 숙박업 소상공인. 지역특화 관광 정책 검증용 계정",
    ),
    TestScenario(
        key="BIZ-06",
        name="인천 고부채 사업자",
        email="dev.biz06@bizmong.local",
        social_id="dev-biz-06",
        provider=SocialProvider.NAVER,
        business_name="인천온누리상사",
        representative_name="한온누리",
        biz_no="100-11-00006",
        ksic_code="46311",
        ksic_name="상품 종합 도매업",
        sector_code="RETAIL",
        region_sido="인천",
        region_sigungu="남동구",
        establishment_date=date(2022, 6, 20),
        employee_count=3,
        annual_revenue=180_000_000,
        total_debt=250_000_000,
        debt_ratio=320.0,
        tax_arrears=False,
        is_female_ent=False,
        is_ventured=False,
        has_patent=False,
        funding_purpose="WORKING",
        profile_score=62,
        summary="인천 도소매업 고부채 케이스. 재무건전성 제한과 리스크 안내 검증용 계정",
    ),
    TestScenario(
        key="BIZ-07",
        name="광주 체납 사업자",
        email="dev.biz07@bizmong.local",
        social_id="dev-biz-07",
        provider=SocialProvider.NAVER,
        business_name="광주한빛산업",
        representative_name="윤한빛",
        biz_no="100-11-00007",
        ksic_code="25929",
        ksic_name="기타 금속가공 제품 제조업",
        sector_code="MANUFACTURING",
        region_sido="광주",
        region_sigungu="광산구",
        establishment_date=date(2020, 9, 1),
        employee_count=9,
        annual_revenue=300_000_000,
        total_debt=90_000_000,
        debt_ratio=95.0,
        tax_arrears=True,
        is_female_ent=False,
        is_ventured=False,
        has_patent=False,
        funding_purpose="OPERATING",
        profile_score=70,
        summary="광주 제조업 체납 케이스. 제외 조건과 감점 규칙 검증용 계정",
    ),
    TestScenario(
        key="BIZ-08",
        name="전국 표준 사업자",
        email="dev.biz08@bizmong.local",
        social_id="dev-biz-08",
        provider=SocialProvider.NAVER,
        business_name="전국표준기업",
        representative_name="오표준",
        biz_no="100-11-00008",
        ksic_code="75999",
        ksic_name="그 외 기타 전문 서비스업",
        sector_code="SERVICE",
        region_sido="충남",
        region_sigungu="천안시",
        establishment_date=date(2021, 10, 15),
        employee_count=7,
        annual_revenue=200_000_000,
        total_debt=50_000_000,
        debt_ratio=45.0,
        tax_arrears=False,
        is_female_ent=False,
        is_ventured=False,
        has_patent=False,
        funding_purpose="OPERATING",
        profile_score=78,
        summary="특화 조건이 없는 기준형 사업자. 전국 공통 정책 비교 기준용 계정",
    ),
)


TEST_POLICIES: tuple[TestPolicy, ...] = (
    TestPolicy(
        origin_id="POL-01",
        title="전국 소상공인 운전자금",
        agency_name="중소벤처기업부",
        category="운영자금",
        region="전국",
        support_type="운영자금",
        support_amount_desc="최대 1억원 운전자금",
        max_support=100_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "최근 부가세 신고서", "매출 증빙서류"],
        target_logic={"max_revenue": 1_000_000_000, "max_employees": 20},
        bonus_logic={"preferred_flags": ["소상공인", "초기사업자"]},
        ai_summary="전국 소상공인을 대상으로 운영자금을 지원하는 기본형 정책입니다.",
        ai_full_explanation="전국 소상공인이 폭넓게 검토할 수 있는 기본 정책으로 운영자금 수요가 있는 사업장에 적합합니다.",
        content_raw="전국 소상공인 대상 운영자금 정책입니다. 매출 10억원 이하, 상시근로자 20명 이하 사업장이 신청할 수 있으며 운영자금 용도의 대출을 지원합니다.",
        apply_url="https://bizmong.local/policies/POL-01",
    ),
    TestPolicy(
        origin_id="POL-02",
        title="서울 초기창업 지원자금",
        agency_name="서울신용보증재단",
        category="창업지원",
        region="서울",
        support_type="창업운영",
        support_amount_desc="최대 7천만원 창업 운영자금",
        max_support=70_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "창업사실 증빙", "사업계획서"],
        target_logic={"region_restricted": True, "allowed_regions": ["서울"], "max_revenue": 500_000_000, "max_employees": 10},
        bonus_logic={"preferred_flags": ["초기창업"]},
        ai_summary="서울 지역 초기 창업 소상공인을 위한 창업 지원 자금입니다.",
        ai_full_explanation="서울에서 창업 초기 단계에 있는 소상공인이 운영 안정화를 위해 활용할 수 있는 정책입니다.",
        content_raw="서울 소재 사업장 중 창업 3년 이내 소상공인을 대상으로 운영 및 창업 안정화 자금을 지원합니다. 지역은 서울로 제한됩니다.",
        apply_url="https://bizmong.local/policies/POL-02",
    ),
    TestPolicy(
        origin_id="POL-03",
        title="경기 제조업 설비개선 자금",
        agency_name="경기도경제과학진흥원",
        category="시설자금",
        region="경기",
        support_type="시설개선",
        support_amount_desc="최대 2억원 설비개선 자금",
        max_support=200_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "공장등록증", "설비 견적서"],
        target_logic={"region_restricted": True, "allowed_regions": ["경기"], "sectors": ["제조", "금속", "기계"], "min_business_age_years": 3},
        bonus_logic={"preferred_flags": ["제조업", "시설투자"]},
        ai_summary="경기 지역 제조업 사업장을 위한 설비개선 정책입니다.",
        ai_full_explanation="경기도 제조업 기업이 생산성 향상과 설비 교체를 위해 검토할 수 있는 시설자금 정책입니다.",
        content_raw="경기 지역 제조업 사업장을 대상으로 설비 개선과 공장 생산성 향상을 위한 시설자금을 지원합니다. 업력 3년 이상 기업이 우대됩니다.",
        apply_url="https://bizmong.local/policies/POL-03",
    ),
    TestPolicy(
        origin_id="POL-04",
        title="부산 여성기업 성장 지원",
        agency_name="부산경제진흥원",
        category="성장지원",
        region="부산",
        support_type="성장자금",
        support_amount_desc="최대 8천만원 성장 지원 자금",
        max_support=80_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "여성기업 확인서", "최근 재무제표"],
        target_logic={"region_restricted": True, "allowed_regions": ["부산"], "sectors": ["서비스", "제조"], "max_revenue": 300_000_000},
        bonus_logic={"preferred_flags": ["여성기업"]},
        ai_summary="부산 지역 여성기업의 성장 단계 자금 수요를 지원하는 정책입니다.",
        ai_full_explanation="여성기업 확인서를 보유한 부산 사업장이 성장 자금을 확보할 때 우선 검토할 수 있는 정책입니다.",
        content_raw="부산 지역 서비스업 또는 제조업 여성기업을 대상으로 성장 자금을 지원합니다. 여성기업 확인서가 필요합니다.",
        apply_url="https://bizmong.local/policies/POL-04",
    ),
    TestPolicy(
        origin_id="POL-05",
        title="대구 기술창업 혁신자금",
        agency_name="대구디지털혁신진흥원",
        category="기술개발",
        region="대구",
        support_type="기술개발",
        support_amount_desc="최대 1억5천만원 기술 혁신 자금",
        max_support=150_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "특허/지재권 증빙", "기술사업화 계획서"],
        target_logic={"region_restricted": True, "allowed_regions": ["대구"], "sectors": ["IT", "기술", "프로그래밍"], "require_ventured": True},
        bonus_logic={"preferred_flags": ["벤처기업", "특허보유"]},
        ai_summary="대구 지역 기술창업 기업을 위한 혁신 자금입니다.",
        ai_full_explanation="벤처 인증과 기술 역량을 갖춘 대구 소재 기술창업 기업이 검토할 수 있는 정책입니다.",
        content_raw="대구 지역 기술, IT, 소프트웨어 분야 벤처기업을 대상으로 기술개발 자금을 지원합니다. 특허나 지식재산권 보유 기업이 우대됩니다.",
        apply_url="https://bizmong.local/policies/POL-05",
    ),
    TestPolicy(
        origin_id="POL-06",
        title="강원 관광업 회복 지원",
        agency_name="강원관광재단",
        category="회복지원",
        region="강원",
        support_type="운영회복",
        support_amount_desc="최대 6천만원 관광업 회복 자금",
        max_support=60_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "숙박/관광업 증빙", "매출 감소 자료"],
        target_logic={"region_restricted": True, "allowed_regions": ["강원"], "sectors": ["숙박", "관광", "호텔"], "max_revenue": 200_000_000},
        bonus_logic={"preferred_flags": ["관광업", "지역특화"]},
        ai_summary="강원 지역 관광/숙박 소상공인을 지원하는 회복 정책입니다.",
        ai_full_explanation="강원권 관광과 숙박업 소상공인이 회복 자금을 확보할 때 활용할 수 있는 지역특화 정책입니다.",
        content_raw="강원 지역 숙박업, 관광업 소상공인을 대상으로 운영 회복 자금을 지원합니다. 관광업과 숙박업 사업장이 주요 대상입니다.",
        apply_url="https://bizmong.local/policies/POL-06",
    ),
    TestPolicy(
        origin_id="POL-07",
        title="고용확대 우대 정책자금",
        agency_name="소상공인시장진흥공단",
        category="고용지원",
        region="전국",
        support_type="운영확장",
        support_amount_desc="최대 1억2천만원 고용확대 우대 자금",
        max_support=120_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "4대보험 사업장 가입자 명부", "급여대장"],
        target_logic={"min_employees": 5, "max_employees": 50},
        bonus_logic={"preferred_flags": ["고용확대"]},
        ai_summary="직원 수가 일정 수준 이상인 사업장에 유리한 고용확대 우대 정책입니다.",
        ai_full_explanation="고용 규모가 확보된 사업장이 운영 확대나 추가 고용 계획과 함께 검토할 수 있는 정책입니다.",
        content_raw="상시근로자 5명 이상 사업장을 대상으로 고용확대 우대 자금을 지원합니다. 고용 유지와 확장 계획이 있는 기업에 적합합니다.",
        apply_url="https://bizmong.local/policies/POL-07",
    ),
    TestPolicy(
        origin_id="POL-08",
        title="재무건전성 제한 정책자금",
        agency_name="중소기업진흥공단",
        category="재무진단",
        region="전국",
        support_type="운영자금",
        support_amount_desc="최대 9천만원 재무건전성 기반 자금",
        max_support=90_000_000,
        closed_at=date(2026, 12, 31),
        required_documents=["사업자등록증", "최근 재무제표", "국세 납세증명서"],
        target_logic={"max_debt_ratio": 150, "max_revenue": 500_000_000},
        bonus_logic={"preferred_flags": ["재무건전성"]},
        ai_summary="부채 비율과 체납 여부를 중점적으로 보는 재무건전성 중심 정책입니다.",
        ai_full_explanation="재무 건전성이 비교적 안정적인 사업장이 우선 검토할 수 있는 자금으로, 부채 비율이 높으면 제외될 수 있습니다.",
        content_raw="재무 건전성이 양호한 소상공인을 대상으로 운영자금을 지원합니다. 부채비율이 높거나 체납 이력이 있으면 심사에서 불리하거나 제외될 수 있습니다.",
        apply_url="https://bizmong.local/policies/POL-08",
    ),
)


def get_dev_account_options() -> list[dict[str, str]]:
    return [
        {
            "scenario_key": item.key,
            "display_name": item.name,
            "email": item.email,
            "business_name": item.business_name,
            "summary": item.summary,
        }
        for item in TEST_SCENARIOS
    ]


async def seed_test_scenarios(session: AsyncSession) -> dict[str, int]:
    auth_repo = AuthRepository(session)
    business_repo = BusinessRepository(session)
    policy_repo = PolicyRepository(session)
    now = datetime.now(timezone.utc)
    counters = {
        "users_created": 0,
        "users_updated": 0,
        "businesses_created": 0,
        "businesses_updated": 0,
        "snapshots_created": 0,
        "snapshots_updated": 0,
        "policies_created": 0,
        "policies_updated": 0,
    }

    for scenario in TEST_SCENARIOS:
        user = await auth_repo.get_by_email(scenario.email)
        if user is None:
            user = await auth_repo.create_user(
                email=scenario.email,
                name=scenario.name,
                social_id=scenario.social_id,
                social_provider=scenario.provider,
                profile_image_url=None,
            )
            counters["users_created"] += 1
        else:
            user.name = scenario.name
            user.social_id = scenario.social_id
            user.social_provider = scenario.provider
            user.status = "active"
            user.is_active = True
            user.deleted_at = None
            counters["users_updated"] += 1
            await session.flush()

        business = await business_repo.get_active_business_by_user_id(user.id)
        if business is None:
            business = await business_repo.create_business(
                user_id=user.id,
                biz_name=scenario.business_name,
                biz_no=scenario.biz_no,
                representative_name=scenario.representative_name,
                ksic_code=scenario.ksic_code,
                ksic_name=scenario.ksic_name,
                sector_code=scenario.sector_code,
                region_sido=scenario.region_sido,
                region_sigungu=scenario.region_sigungu,
                establishment_date=scenario.establishment_date,
                has_patent=scenario.has_patent,
                is_female_ent=scenario.is_female_ent,
                is_ventured=scenario.is_ventured,
                profile_score=scenario.profile_score,
                is_biz_no_verified=True,
                biz_verified_status="계속사업자",
                tax_type="부가가치세 일반과세자",
                biz_verified_at=now,
                employee_count=scenario.employee_count,
                funding_purpose=scenario.funding_purpose,
                has_tax_arrears=scenario.tax_arrears,
            )
            counters["businesses_created"] += 1
        else:
            await business_repo.update_business(
                business,
                biz_name=scenario.business_name,
                biz_no=scenario.biz_no,
                representative_name=scenario.representative_name,
                ksic_code=scenario.ksic_code,
                ksic_name=scenario.ksic_name,
                sector_code=scenario.sector_code,
                region_sido=scenario.region_sido,
                region_sigungu=scenario.region_sigungu,
                establishment_date=scenario.establishment_date,
                has_patent=scenario.has_patent,
                is_female_ent=scenario.is_female_ent,
                is_ventured=scenario.is_ventured,
                employee_count=scenario.employee_count,
                funding_purpose=scenario.funding_purpose,
                has_tax_arrears=scenario.tax_arrears,
                profile_score=scenario.profile_score,
                is_biz_no_verified=True,
                biz_verified_status="계속사업자",
                tax_type="부가가치세 일반과세자",
                biz_verified_at=now,
                is_active=True,
            )
            counters["businesses_updated"] += 1

        snapshot = await business_repo.get_financial_snapshot_by_year(business.id, 2025)
        snapshot_payload = {
            "snapshot_period": "ANNUAL",
            "term_type": "ANNUAL",
            "annual_revenue": scenario.annual_revenue,
            "operating_profit": max(int(scenario.annual_revenue * 0.12), 0),
            "net_income": max(int(scenario.annual_revenue * 0.08), 0),
            "total_debt": scenario.total_debt,
            "capital": max(int(scenario.annual_revenue * 0.2), 10_000_000),
            "debt_ratio": scenario.debt_ratio,
            "employee_count": scenario.employee_count,
            "tax_arrears_yn": scenario.tax_arrears,
        }
        if snapshot is None:
            await business_repo.create_financial_snapshot(
                business_id=business.id,
                snapshot_year=2025,
                **snapshot_payload,
            )
            counters["snapshots_created"] += 1
        else:
            await business_repo.update_financial_snapshot(
                snapshot,
                **snapshot_payload,
                ocr_status="MANUAL",
                is_verified=False,
                is_active=True,
            )
            counters["snapshots_updated"] += 1

    for policy_seed in TEST_POLICIES:
        policy = await policy_repo.get_policy_by_origin_id(policy_seed.origin_id)
        if policy is None:
            policy = await policy_repo.create_policy(
                origin_id=policy_seed.origin_id,
                title=policy_seed.title,
                content_raw=policy_seed.content_raw,
                category=policy_seed.category,
                agency_name=policy_seed.agency_name,
                apply_url=policy_seed.apply_url,
                status=PolicyStatus.RECRUITING,
                closed_at=policy_seed.closed_at,
                target_logic=policy_seed.target_logic,
                bonus_logic=policy_seed.bonus_logic,
                ai_summary=policy_seed.ai_summary,
                ai_full_explanation=policy_seed.ai_full_explanation,
                required_documents=policy_seed.required_documents,
            )
            counters["policies_created"] += 1
        else:
            counters["policies_updated"] += 1

        await policy_repo.patch_policy_internal(
            policy,
            title=policy_seed.title,
            agency_name=policy_seed.agency_name,
            category=policy_seed.category,
            region=policy_seed.region,
            support_type=policy_seed.support_type,
            support_amount_desc=policy_seed.support_amount_desc,
            max_support=policy_seed.max_support,
            apply_url=policy_seed.apply_url,
            status=PolicyStatus.RECRUITING,
            closed_at=policy_seed.closed_at,
            is_active=True,
            content_raw=policy_seed.content_raw,
            required_documents=policy_seed.required_documents,
            target_logic=policy_seed.target_logic,
            bonus_logic=policy_seed.bonus_logic,
            ai_summary=policy_seed.ai_summary,
            ai_full_explanation=policy_seed.ai_full_explanation,
        )

    return counters
