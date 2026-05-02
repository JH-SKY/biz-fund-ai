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

TEST_POLICY_IDS: tuple[str, ...] = tuple(policy.origin_id for policy in TEST_POLICIES)


def build_test_policy_content(policy_seed: TestPolicy) -> str:
    sections = _policy_sections_for(policy_seed)
    documents = "\n".join(
        f"- {doc}: {sections['document_guidance'].get(doc, '정확한 발급본 또는 최신 작성본을 제출해야 합니다.')}"
        for doc in policy_seed.required_documents
    )
    lines = [
        f"정책명\n{policy_seed.title}",
        f"정책 개요\n{policy_seed.ai_summary}\n\n{sections['overview']}",
        f"지원 대상\n{sections['target']}",
        f"지원 지역\n{sections['region']}",
        f"업종 조건\n{sections['sector']}",
        f"업력 조건\n{sections['age']}",
        f"매출 / 고용 조건\n{sections['revenue_employee']}",
        f"우대 조건\n{sections['preferred']}",
        f"제외 조건\n{sections['excluded']}",
        "제출 서류\n" + documents,
        f"신청 절차\n{sections['procedure']}",
        f"문의처\n{sections['contact']}",
    ]
    return "\n\n".join(lines)


def _policy_sections_for(policy_seed: TestPolicy) -> dict[str, str]:
    sections: dict[str, dict[str, str]] = {
        "POL-01": {
            "overview": (
                "본 공고는 경기 둔화와 고정비 상승으로 자금 운용에 어려움을 겪는 소상공인의 단기 유동성 부담을 완화하고, "
                "운영 정상화를 지원하기 위해 마련된 전국 단위 운전자금 지원사업이다. 임차료, 원재료 매입비, 인건비, "
                "공공요금 등 경상적 운영비 수요가 있는 사업장을 중심으로 심사하며, 신청 기업의 최근 재무 흐름과 상환 가능성을 종합 검토한다."
            ),
            "target": (
                "사업자등록을 완료하고 실제 영업 중인 전국 소상공인 및 영세 사업장을 대상으로 한다. "
                "음식점업, 도소매업, 서비스업, 제조업 등 업종 제한은 없으나, 신청일 기준 휴·폐업 상태가 아니어야 하며 최근 1년 내 매출 활동이 확인되어야 한다."
            ),
            "region": (
                "전국 단위 사업으로 서울, 경기, 인천을 포함한 수도권과 비수도권 사업장 모두 신청 가능하다. "
                "다만 동일 사업장 기준으로 타 지역 전용 정책과 중복 지원 여부는 별도 확인이 필요하다."
            ),
            "sector": (
                "업종 제한은 없으나 소상공인 보호 및 지원에 관한 법률상 소상공인 요건을 충족해야 한다. "
                "사행성 업종, 부동산 투기성 업종, 금융·보험업 등 정책자금 제한 업종은 심사 대상에서 제외될 수 있다."
            ),
            "age": (
                "업력 제한은 없으며 창업 초기 사업장과 업력 3년 이상 안정화 단계 사업장 모두 신청 가능하다. "
                "다만 업력 1년 미만 사업장은 매출 증빙과 향후 운영 계획서를 추가로 요구할 수 있다."
            ),
            "revenue_employee": (
                "연매출 10억원 이하, 상시근로자 20명 이하 사업장을 기본 대상으로 본다. "
                "최근 결산 기준 매출 감소 또는 원가 상승으로 운영자금 수요가 발생한 사실이 확인되면 심사 시 반영한다."
            ),
            "preferred": (
                "임차료, 인건비, 원재료비 부담이 급증한 사업장과 자금 사용 목적이 명확한 사업장을 우선 검토한다. "
                "정책자금 미수혜 사업장, 창업 초기 운영 안정화가 필요한 사업장, 지역 상권 회복과 연계된 사업장은 가점 검토가 가능하다."
            ),
            "excluded": (
                "국세 또는 지방세 체납 사업장, 휴·폐업 상태 사업장, 최근 3개월 내 심각한 연체 이력이 확인된 사업장, "
                "허위 자료 제출 사업장은 제외한다. 동일 목적의 타 정책자금으로 이미 중복 지원을 받은 경우에도 감액 또는 제외될 수 있다."
            ),
            "document_guidance": {
                "사업자등록증": "신청 사업장의 업종, 개업일, 대표자 정보를 확인하기 위한 기본 서류입니다.",
                "최근 부가세과세표준증명": "최근 매출 규모와 매출 변동을 확인하기 위한 자료로 사용됩니다.",
                "매출 감소 또는 비용 증가 증빙": "운전자금 필요성을 입증하기 위해 카드매출, 세금계산서, 임대료 고지서 등을 제출합니다.",
                "통장 사본": "지원금 또는 대출 실행 계좌를 확인하기 위해 필요합니다.",
            },
            "procedure": (
                "1단계로 공고문과 지원 조건을 확인한 뒤 온라인 신청 페이지에서 기본 정보를 입력한다. "
                "2단계에서는 사업자등록증, 매출 증빙, 자금 사용 계획서를 업로드한다. "
                "3단계에서는 상담 또는 서면 보완 요청이 진행되며, 적격 판정 시 약정 체결 후 운전자금이 실행된다."
            ),
            "contact": (
                "중소벤처기업부 정책자금 상담센터 1357 / 평일 09:00~18:00. "
                "신청 시스템 오류나 서류 제출 문의는 소상공인시장진흥공단 지역센터를 통해 추가 안내받을 수 있다."
            ),
        },
        "POL-02": {
            "overview": (
                "서울시 내 창업 초기 소상공인의 시장 안착과 초기 운영 리스크 완화를 위해 운영 안정화 자금을 지원하는 사업이다. "
                "창업 후 3년 이내 사업장을 중심으로 임차료, 초도 물품 구입비, 홍보비, 소규모 시설보완비 등 초기 자금 수요를 지원한다."
            ),
            "target": (
                "서울시에 사업장을 두고 실제 영업 중인 창업 초기 소상공인을 대상으로 한다. "
                "특히 카페, 음식점, 생활서비스업, 소규모 리테일 등 초기 고객 확보가 중요한 업종을 주요 대상으로 본다."
            ),
            "region": (
                "사업자등록상 본점 또는 주사업장이 서울특별시에 소재해야 하며, 현장 점검 시 실제 영업 장소가 서울 내에 확인되어야 한다. "
                "서울 외 지역 이전 예정 또는 타 지역 실영업 사업장은 지원 대상에서 제외한다."
            ),
            "sector": (
                "업종 제한은 크지 않으나 서울시 내 생활밀착형 소상공인 업종을 우선 검토한다. "
                "유흥업, 투기성 업종, 무점포 단순 중개업은 제한될 수 있으며, 오프라인 영업 기반을 가진 창업 사업장을 우대한다."
            ),
            "age": (
                "신청일 기준 업력 3년 이하 사업장을 기본 대상으로 한다. "
                "업력 1년 미만 사업장은 사업계획의 구체성, 상권 적합성, 초기 매출 발생 여부를 함께 심사한다."
            ),
            "revenue_employee": (
                "연매출 5억원 이하, 상시근로자 10명 이하 사업장을 기준으로 한다. "
                "초기 창업 특성상 매출이 크지 않더라도 월별 매출 흐름과 자금 소진 계획이 명확하면 평가에 유리하다."
            ),
            "preferred": (
                "창업 후 1년 이내 사업장, 지역 상권 활성화와 연계된 업종, 청년 또는 재창업 초기 사업장, "
                "상권 분석과 매출 계획이 구체적인 사업장은 우대 검토한다."
            ),
            "excluded": (
                "국세 체납 사업장, 서울 외 지역 사업장, 업력 3년 초과 사업장, 최근 동일 목적의 서울시 창업 운영자금을 수혜한 사업장은 제외할 수 있다."
            ),
            "document_guidance": {
                "사업자등록증": "서울 소재 창업 여부와 개업일 확인을 위한 필수 서류입니다.",
                "임대차계약서": "실제 영업장 확보 여부와 임차료 부담을 확인하기 위한 자료입니다.",
                "사업계획서": "초기 창업자의 시장 진입 전략과 자금 사용 계획을 평가하는 핵심 문서입니다.",
                "매출 증빙자료": "카드매출, 현금영수증, 매출전표 등 초기 매출 발생 여부를 보여주는 자료를 제출합니다.",
            },
            "procedure": (
                "온라인 신청서 접수 후 사업 개요, 영업장 정보, 자금 사용 목적을 입력한다. "
                "이후 사업계획서와 임대차계약서, 매출 증빙을 제출하면 서류 심사와 필요 시 전화 또는 현장 인터뷰가 진행된다. "
                "최종 승인 시 약정 체결 후 자금 집행 일정이 안내된다."
            ),
            "contact": (
                "서울신용보증재단 고객센터 1577-6119 / 서울시 소상공인 지원 부서 연계 상담 가능. "
                "창업 교육 이수 여부, 보증 연계 여부 등 세부 절차는 자치구별 안내에 따를 수 있다."
            ),
        },
        "POL-03": {
            "overview": (
                "경기도 내 제조기업의 생산성 향상과 공정 개선을 지원하기 위해 설비개선 및 자동화 투자 자금을 지원하는 사업이다. "
                "노후 설비 교체, 생산 라인 효율화, 안전설비 보강, 소규모 스마트공장 전환 준비 등 시설성 투자 계획을 가진 기업에 적합하다."
            ),
            "target": (
                "경기도에 공장 또는 주사업장을 두고 실제 제조 활동을 영위하는 중소 제조사업장을 대상으로 한다. "
                "금속가공, 기계부품, 전자부품, 생활용품 제조 등 실물 생산 기반 업종을 주요 검토 대상으로 본다."
            ),
            "region": (
                "경기도 내 본점 또는 사업장, 공장등록이 확인되는 제조기업만 신청할 수 있다. "
                "도 외 지역 공장 중심 기업은 대상에서 제외되며, 도내 투자 집행 계획이 명확해야 한다."
            ),
            "sector": (
                "제조업을 기본으로 하며 금속가공, 기계, 부품, 조립, 생활소비재 제조 등 실질적 생산 공정이 있는 업종을 우선 검토한다. "
                "단순 유통업, 도소매업, 서비스업은 설비개선 목적과 무관하므로 신청 대상이 아니다."
            ),
            "age": (
                "업력 3년 이상 사업장을 기본 대상으로 하며, 최소 2개년 이상의 재무 흐름과 생산 실적을 확인할 수 있어야 한다. "
                "업력이 짧더라도 제조시설과 납품 실적이 명확한 경우 예외 검토가 가능하다."
            ),
            "revenue_employee": (
                "매출 상한은 별도로 두지 않으나 최근 결산 재무제표 제출이 가능해야 한다. "
                "상시근로자 수가 너무 적지 않고 설비 투자 이후 생산성 향상 또는 고용 유지 효과를 설명할 수 있는 기업이 유리하다."
            ),
            "preferred": (
                "노후 생산설비 교체, 자동화 장비 도입, 불량률 감소, 작업환경 개선, 에너지 절감 효과가 예상되는 투자 계획은 우대 검토한다. "
                "협력사 납품 안정화와 지역 제조업 경쟁력 강화에 기여하는 계획도 긍정적으로 평가한다."
            ),
            "excluded": (
                "체납 사업장, 경기도 외 지역 사업장, 제조업이 아닌 사업장, 이미 동일 설비 목적의 공공지원 자금을 중복 수혜 중인 사업장은 제외한다."
            ),
            "document_guidance": {
                "사업자등록증": "경기도 내 제조사업장 여부와 기본 업종 정보를 확인합니다.",
                "공장등록증 또는 제조시설 증빙": "실제 제조 기반 사업장인지 판단하기 위한 핵심 서류입니다.",
                "설비투자계획서": "도입 설비의 목적, 비용, 기대 효과를 구체적으로 설명해야 합니다.",
                "최근 재무제표": "투자 여력과 상환 가능성, 최근 경영 흐름을 검토하는 데 사용됩니다.",
            },
            "procedure": (
                "기업은 온라인 신청 후 설비개선 필요성과 투자 일정을 포함한 계획서를 제출한다. "
                "이후 적격성 검토, 기술성·사업성 평가, 필요 시 현장 확인이 진행되며, 선정 시 자금 지원 또는 연계 보증 절차가 이어진다."
            ),
            "contact": (
                "경기도경제과학진흥원 기업성장팀 031-259-6000 / 도내 제조혁신 상담창구 연계 가능. "
                "공장등록 여부, 투자 집행 가능 항목, 장비 견적서 요건은 별도 안내문을 참고한다."
            ),
        },
        "POL-04": {
            "overview": (
                "부산 지역 여성기업의 성장 기반 확충과 초기 경영 안정화를 지원하기 위한 성장자금 사업이다. "
                "마케팅, 제품 고도화, 인력 확충, 운영비 보완 등 사업 확장 단계에서 필요한 자금을 지원하며 여성기업 특화 지원정책의 테스트용 대표 공고로 설계되었다."
            ),
            "target": (
                "부산시에 사업장을 두고 여성기업 확인서를 보유한 사업장을 대상으로 한다. "
                "대표자가 여성이고 실질적으로 경영에 참여하는 기업을 기본 대상으로 하며, 소규모 서비스업과 제조업 모두 신청 가능하다."
            ),
            "region": (
                "부산광역시 내 본점 또는 주사업장이 소재해야 하고, 부산 내 영업 실체가 확인되어야 한다. "
                "단순 주소지만 부산인 경우가 아니라 실제 사업 운영이 부산에서 이루어지는지가 심사 대상이 된다."
            ),
            "sector": (
                "서비스업 또는 제조업을 기본 대상으로 하며, 생활서비스, 교육서비스, 컨설팅, 식품제조, 공예·생활소비재 제조 등 여성기업이 많이 진출한 업종을 폭넓게 포함한다. "
                "정책 제한 업종은 신청 대상에서 제외될 수 있다."
            ),
            "age": (
                "업력 제한은 없으나 창업 초기 여성기업과 성장 전환 단계 사업장을 모두 포괄한다. "
                "다만 업력 1년 미만 사업장은 사업 운영 실적과 향후 성장 전략을 추가 설명해야 한다."
            ),
            "revenue_employee": (
                "연매출 3억원 이하 사업장을 중심으로 검토하며, 소규모 조직 운영 기업에 적합하다. "
                "고용 인원 수는 절대 조건은 아니지만 향후 고용 확대 계획 또는 현재 인력 유지 계획이 있으면 긍정적으로 볼 수 있다."
            ),
            "preferred": (
                "여성기업 확인서 보유 기업을 기본 우대하며, 여성 고용 비중이 높거나 지역 상권·산업 생태계와 연계된 성장 계획이 있는 경우 추가 가점 검토가 가능하다. "
                "브랜딩 개선, 판로 확대, 제품 고도화 계획이 구체적인 기업도 우대한다."
            ),
            "excluded": (
                "체납 사업장, 부산 외 지역 사업장, 여성기업 확인서 미보유 사업장, 허위 명의 또는 실질 경영 주체가 확인되지 않는 경우는 제외한다."
            ),
            "document_guidance": {
                "사업자등록증": "부산 지역 사업장 여부와 업종 정보를 확인합니다.",
                "여성기업 확인서": "본 공고의 핵심 자격요건을 판단하는 필수 서류입니다.",
                "최근 재무자료": "매출 규모와 경영 상태를 확인하고 성장 가능성을 검토합니다.",
                "성장계획서": "마케팅, 판로, 제품 개선 등 자금 활용 방향을 구체적으로 작성해야 합니다.",
            },
            "procedure": (
                "신청 기업은 온라인 접수 후 여성기업 확인서와 성장계획서를 제출한다. "
                "이후 서류 심사에서 여성기업 자격, 부산 내 사업 영위 여부, 자금 활용 타당성을 검토하며 필요 시 인터뷰 또는 보완 제출을 요청한다."
            ),
            "contact": (
                "부산경제진흥원 기업지원센터 1833-3665 / 여성기업 전담 상담창구 운영. "
                "여성기업 확인서 발급 절차와 병행 문의가 필요한 경우 중소기업 유관기관 연계를 지원한다."
            ),
        },
        "POL-05": {
            "overview": (
                "대구 지역 기술창업 기업의 사업화 속도와 기술 경쟁력 강화를 지원하기 위한 혁신자금 사업이다. "
                "AI, 소프트웨어, 데이터 기반 서비스, 디지털 전환 솔루션 등 기술형 스타트업이 연구개발 이후 시장 진입 단계에서 필요한 자금을 확보하도록 설계되었다."
            ),
            "target": (
                "대구 지역에서 기술창업을 영위하는 벤처기업 또는 벤처 인증 예정 기업을 주요 대상으로 한다. "
                "소프트웨어 개발, AI 서비스, 디지털 솔루션, 기술서비스업 등 지식기반 업종에 적합하다."
            ),
            "region": (
                "대구광역시 내 본점 또는 연구개발·주사업장이 확인되는 기업만 신청 가능하다. "
                "대구 외 지역 기업은 대상이 아니며, 대구 지역 내 사업화 또는 인력 운영 계획이 있어야 한다."
            ),
            "sector": (
                "IT, 기술서비스, 소프트웨어, 데이터 분석, AI 솔루션, 플랫폼 기술 등 기술기반 업종을 대상으로 한다. "
                "일반 도소매업이나 비기술형 영업사업은 본 공고의 취지와 맞지 않아 제외된다."
            ),
            "age": (
                "업력 7년 이하 기술창업 기업을 중심으로 하며, 창업 초기부터 스케일업 전환 단계까지 포괄한다. "
                "기술개발 실적이나 사업화 진척도가 명확한 기업이 유리하다."
            ),
            "revenue_employee": (
                "매출 상한은 두지 않지만 기술개발 또는 사업화 계획이 반드시 있어야 한다. "
                "소규모 인력 구조라도 기술 인력 비중, 개발 로드맵, 고객 검증 여부를 설명할 수 있어야 한다."
            ),
            "preferred": (
                "벤처기업 인증, 특허·프로그램 저작권·지식재산권 보유, 기술보증 또는 실증사업 이력이 있는 기업은 우대한다. "
                "지역 산업과 연계된 디지털 전환 서비스나 고부가가치 기술 솔루션은 추가 가점 검토가 가능하다."
            ),
            "excluded": (
                "체납 사업장, 기술창업 요건이 불명확한 일반 사업장, 벤처 또는 지식재산 기반 설명이 없는 경우, 대구 외 지역 운영 기업은 제외한다."
            ),
            "document_guidance": {
                "사업자등록증": "대구 소재 여부와 기술업종 등록 상태를 확인합니다.",
                "벤처기업 확인서 또는 관련 증빙": "기술형 기업 여부를 객관적으로 보여주는 핵심 자료입니다.",
                "특허·지식재산권 증빙": "우대 조건 및 기술 경쟁력 판단에 사용됩니다.",
                "기술사업화 계획서": "개발 내용, 목표 시장, 수익화 계획을 구체적으로 설명해야 합니다.",
            },
            "procedure": (
                "온라인 신청 후 기술사업화 계획서와 지식재산 증빙을 제출한다. "
                "1차 서류 심사에서 기술성, 시장성, 지역 정착 가능성을 검토하고, 2차에서는 발표 또는 인터뷰 심사를 통해 최종 지원 여부를 결정한다."
            ),
            "contact": (
                "대구디지털혁신진흥원 기술창업지원실 053-655-5600. "
                "벤처 인증, 특허 증빙, 기술자료 비공개 제출 방식 등은 별도 FAQ를 통해 안내받을 수 있다."
            ),
        },
        "POL-06": {
            "overview": (
                "강원 지역 관광·숙박업 소상공인의 회복과 운영 정상화를 지원하기 위한 지역특화 정책자금이다. "
                "관광 수요 변동, 비수기 매출 감소, 시설 유지비 부담 등으로 어려움을 겪는 숙박·관광 사업자의 운영 회복을 목표로 한다."
            ),
            "target": (
                "강원특별자치도 내 관광업, 숙박업, 호텔업, 게스트하우스 등 관광객 대상 서비스를 운영하는 소상공인을 대상으로 한다. "
                "실제 관광객 대상 매출이 발생하는 사업장인지 여부를 주요 판단 기준으로 본다."
            ),
            "region": (
                "강원특별자치도 소재 사업장만 신청할 수 있으며, 지역 관광산업 회복과의 연계성이 중요하다. "
                "도내 영업 실체가 확인되어야 하고, 관광객 유입에 따른 매출 구조를 설명할 수 있어야 한다."
            ),
            "sector": (
                "관광업, 숙박업, 호텔업, 펜션, 체험형 관광 서비스업 등 관광 연계 업종을 대상으로 한다. "
                "일반 제조업, 무관한 서비스업, 상시 관광객 대상 영업이 아닌 업종은 지원 취지와 맞지 않는다."
            ),
            "age": (
                "업력 제한은 두지 않으나 최근 영업 실적이 확인되어야 한다. "
                "오래 운영된 사업장뿐 아니라 지역 관광 신규 브랜드를 시도하는 소규모 사업장도 검토 대상이 될 수 있다."
            ),
            "revenue_employee": (
                "연매출 2억원 이하 사업장을 중심으로 검토하며, 고정비 비중이 높아 운영 회복 자금이 필요한 사업장에 적합하다. "
                "상시근로자 수는 제한 요건은 아니지만 지역 일자리 유지 효과가 있으면 긍정적으로 본다."
            ),
            "preferred": (
                "성수기 대비 시설 유지비 부담이 큰 사업장, 매출 감소가 확인되는 사업장, 지역 관광 회복 프로그램과 연계할 계획이 있는 사업장을 우대한다. "
                "숙박 품질 개선, 예약 채널 고도화, 체험형 상품 연계 계획도 평가 요소가 된다."
            ),
            "excluded": (
                "체납 사업장, 강원 외 지역 사업장, 관광·숙박 연계성이 낮은 업종, 실제 영업 중단 상태 사업장은 제외한다."
            ),
            "document_guidance": {
                "사업자등록증": "강원 지역 사업장 여부와 업종을 확인합니다.",
                "숙박업 신고증 또는 관광업 등록증": "관광·숙박업 자격을 판단하는 핵심 증빙입니다.",
                "최근 매출 증빙자료": "관광 수요 변동과 회복 필요성을 확인하기 위해 제출합니다.",
                "운영회복 계획서": "자금 사용 목적과 회복 전략을 설명하는 문서입니다.",
            },
            "procedure": (
                "신청인은 공고 확인 후 온라인 신청서와 매출 증빙, 업종 등록 증빙을 제출한다. "
                "이후 매출 감소 여부, 운영 회복 필요성, 지역 관광 연계 가능성을 중심으로 서류 심사가 진행되며 필요 시 보완 서류를 요청한다."
            ),
            "contact": (
                "강원관광재단 소상공인지원 담당 033-249-3300 / 지역 관광 연계 프로그램 상담 가능. "
                "숙박업 신고와 관광상품 연계 계획 작성 방법은 별도 안내문을 통해 제공한다."
            ),
        },
        "POL-07": {
            "overview": (
                "상시근로자 고용을 일정 수준 이상 유지하거나 추가 채용 계획이 있는 소상공인·중소사업장을 대상으로 운영 및 확장 자금을 지원하는 정책이다. "
                "고용 유지를 통해 지역경제에 기여하는 사업장을 우대하기 위해 설계되었으며, 고용 관련 매칭 테스트를 위해 중요한 공고다."
            ),
            "target": (
                "전국 사업장 중 상시근로자를 일정 규모 이상 고용하고 있는 사업장을 대상으로 한다. "
                "단순 1인 사업장보다 조직 운영 단계에 진입해 인건비와 운영비 부담을 동시에 관리하는 사업장에 적합하다."
            ),
            "region": (
                "전국 단위 신청이 가능하나, 실제 고용 인원이 4대보험 또는 급여대장 등으로 확인되어야 한다. "
                "지역 고용 안정 기여도가 있는 사업장은 추가 참고 요소로 볼 수 있다."
            ),
            "sector": (
                "업종 제한은 크지 않지만 실제 인력 운영이 필요한 업종에 적합하다. "
                "제조업, 숙박업, 외식업, 서비스업 등 상시근로자 유지가 사업 운영에 중요한 업종을 폭넓게 포함한다."
            ),
            "age": (
                "업력 제한은 없으나 고용 유지 실적을 판단할 수 있는 최근 인력 운영 이력이 확인되어야 한다. "
                "창업 초기 사업장이라도 일정 인원을 고용하고 있거나 채용 계획이 구체적이면 심사 가능하다."
            ),
            "revenue_employee": (
                "상시근로자 5명 이상 50명 이하 사업장을 기준으로 한다. "
                "매출 상한은 별도로 두지 않으나 인건비 부담과 고용 유지 계획을 설명할 수 있어야 하며, 고용 확대에 따른 자금 수요가 명확해야 한다."
            ),
            "preferred": (
                "최근 6개월 이상 고용을 안정적으로 유지한 사업장, 추가 채용 계획이 있는 사업장, 청년·지역인재 채용과 연계된 계획이 있는 사업장은 우대 검토한다."
            ),
            "excluded": (
                "체납 사업장, 상시근로자 5명 미만 사업장, 허위 고용자료 제출 사업장, 고용보험 체납 또는 인력 운영 자료 미제출 사업장은 제외한다."
            ),
            "document_guidance": {
                "사업자등록증": "기본 사업 정보와 업종 확인을 위한 서류입니다.",
                "4대보험 사업장 가입자 명부": "상시근로자 수와 고용 유지 현황을 확인하는 핵심 증빙입니다.",
                "최근 급여대장": "실제 인건비 집행 여부를 검토하는 데 사용됩니다.",
                "고용유지 또는 채용계획서": "지원 필요성과 향후 고용 효과를 설명하는 자료입니다.",
            },
            "procedure": (
                "신청자는 공고 확인 후 온라인으로 접수하고, 사업자 정보와 고용현황, 자금 활용 계획을 입력한다. "
                "이후 4대보험 명부와 급여대장 등 고용 증빙을 제출하면 고용 유지 성과와 자금 수요 타당성을 중심으로 심사가 진행된다."
            ),
            "contact": (
                "소상공인시장진흥공단 정책자금센터 1357 / 고용 연계 정책 상담 가능. "
                "근로자 수 산정 기준과 제외 업종 여부는 지침서 부속서류를 확인해야 한다."
            ),
        },
        "POL-08": {
            "overview": (
                "재무건전성이 양호한 소상공인을 중심으로 선별 지원하는 운영자금 공고로, 부채 수준과 체납 여부를 중점적으로 심사한다. "
                "단순 추천뿐 아니라 재무 리스크 조건이 어떻게 추천 결과에 반영되는지 검증하기 위한 테스트용 공고로도 활용된다."
            ),
            "target": (
                "전국 소상공인 중 최근 재무자료 제출이 가능하고, 과도한 부채나 체납 없이 안정적인 운영 흐름을 보이는 사업장을 대상으로 한다. "
                "특히 추가 차입보다 정상 운영과 단기 자금 보완이 필요한 사업장에 적합하다."
            ),
            "region": (
                "전국 사업장 신청이 가능하며, 지역 제한은 없으나 지역 특화사업과 중복 지원 여부는 별도 검토한다. "
                "주된 심사 포인트는 지역보다 재무 상태와 납세 이력이다."
            ),
            "sector": (
                "업종 제한은 없지만 정책상 제한 업종은 제외된다. "
                "정상 영업 중이며 최근 재무자료 제출이 가능한 사업장을 대상으로 하고, 현금흐름 파악이 어려운 사업장은 불리할 수 있다."
            ),
            "age": (
                "업력 제한은 없으나 최소 1개 회계연도 이상의 재무자료를 제출할 수 있어야 한다. "
                "창업 초기 사업장은 재무자료가 부족하면 별도 보완자료를 요구받을 수 있다."
            ),
            "revenue_employee": (
                "연매출 5억원 이하 사업장을 기본 검토 대상으로 하며, 규모보다는 재무자료의 충실성과 부채 수준이 중요하다. "
                "고용 인원은 절대 기준은 아니지만 인건비 부담 대비 현금흐름이 안정적인지 함께 본다."
            ),
            "preferred": (
                "부채비율이 낮고, 납세 이력이 양호하며, 최근 1년간 연체나 체납 이슈가 없는 사업장은 우대 검토한다. "
                "자기자본 기반이 안정적이거나 자금 사용 목적이 보수적으로 설계된 사업장도 상대적으로 유리하다."
            ),
            "excluded": (
                "체납 사업장, 부채비율 150% 초과 사업장, 최근 심각한 연체 이력이 확인된 사업장, 재무자료 허위 제출 사업장은 제외한다. "
                "따라서 고부채 사업자나 체납 사업자가 왜 추천되지 않는지 설명하는 테스트에 활용할 수 있다."
            ),
            "document_guidance": {
                "사업자등록증": "기본 사업자 정보와 업종 확인용 서류입니다.",
                "최근 재무제표": "매출, 부채, 자본 구조를 검토하는 핵심 서류입니다.",
                "부가세과세표준증명": "매출 흐름과 신고 일관성을 확인하기 위해 요구됩니다.",
                "국세 및 지방세 납세증명서": "체납 여부와 납세 건전성을 확인하는 필수 자료입니다.",
            },
            "procedure": (
                "온라인 접수 후 재무제표, 부가세과세표준증명, 납세증명서를 제출한다. "
                "서류 검토 단계에서 부채 수준과 납세 상태를 먼저 확인하고, 적격 판정 시 운영 안정성 및 상환 가능성 중심의 추가 심사가 이루어진다."
            ),
            "contact": (
                "중소기업진흥공단 정책자금 상담창구 1811-3655. "
                "재무자료 제출 범위, 부채비율 산정 기준, 체납 해소 후 재신청 가능 여부는 상담센터를 통해 확인할 수 있다."
            ),
        },
    }
    return sections[policy_seed.origin_id]


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
        content_raw = build_test_policy_content(policy_seed)
        policy = await policy_repo.get_policy_by_origin_id(policy_seed.origin_id)
        if policy is None:
            policy = await policy_repo.create_policy(
                origin_id=policy_seed.origin_id,
                title=policy_seed.title,
                content_raw=content_raw,
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
            content_raw=content_raw,
            required_documents=policy_seed.required_documents,
            target_logic=policy_seed.target_logic,
            bonus_logic=policy_seed.bonus_logic,
            ai_summary=policy_seed.ai_summary,
            ai_full_explanation=policy_seed.ai_full_explanation,
        )

    return counters
