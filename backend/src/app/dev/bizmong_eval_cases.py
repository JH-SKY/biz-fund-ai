from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BizMongEvalCase:
    scenario_key: str
    question: str
    expected_route: str
    expected_policies: tuple[str, ...] = field(default_factory=tuple)
    expected_answer_keywords: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""


EVAL_CASES: tuple[BizMongEvalCase, ...] = (
    BizMongEvalCase(
        scenario_key="BIZ-01",
        question="내가 받을 수 있는 정책자금 뭐야?",
        expected_route="rag",
        expected_policies=("전국 소상공인 운전자금", "서울 초기창업 지원자금"),
        expected_answer_keywords=("정책", "서울", "운전자금"),
        note="서울 초기창업/운영자금 기본 추천",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-01",
        question="서울 초기창업 지원자금은 왜 추천돼?",
        expected_route="rag",
        expected_policies=("서울 초기창업 지원자금",),
        expected_answer_keywords=("추천", "서울", "창업"),
        note="근거 설명형 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-01",
        question="요즘 가스비랑 전기세가 너무 올라서 장사하기 팍팍하네. 나라에서 푼돈이라도 좀 보태주는 거 없나?",
        expected_route="rag",
        expected_policies=("전국 소상공인 운전자금",),
        expected_answer_keywords=("정책", "운전자금"),
        note="운영난/고정비 우회 표현",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-02",
        question="설비 바꾸려는데 제조업 시설자금 같은 거 있어?",
        expected_route="rag",
        expected_policies=("경기 제조업 설비개선 자금",),
        expected_answer_keywords=("설비", "제조업"),
        note="시설자금 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-03",
        question="여성기업이라 받을 수 있는 부산 지원사업 있어?",
        expected_route="rag",
        expected_policies=("부산 여성기업 성장 지원",),
        expected_answer_keywords=("부산", "여성기업"),
        note="여성기업 특화 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-04",
        question="벤처랑 특허 있는 IT 회사인데 기술창업 쪽 지원 있어?",
        expected_route="rag",
        expected_policies=("대구 기술창업 혁신자금",),
        expected_answer_keywords=("기술", "벤처", "특허"),
        note="벤처/특허 특화 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-05",
        question="관광객 줄어서 힘든데 강원도에서 관광업 살려주는 거 있어?",
        expected_route="rag",
        expected_policies=("강원 관광업 회복 지원",),
        expected_answer_keywords=("강원", "관광"),
        note="지역/업종 복합 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-06",
        question="재무 상태가 좀 안 좋은데 그래도 받을 만한 운영자금이 있을까?",
        expected_route="rag",
        expected_policies=("전국 소상공인 운전자금",),
        expected_answer_keywords=("운전자금", "정책"),
        note="고부채 사업자 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-07",
        question="세금 체납이 있으면 정책자금 신청이 어려워?",
        expected_route="rag",
        expected_policies=(),
        expected_answer_keywords=("체납", "확인"),
        note="체납 리스크 안내",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-01",
        question="직원 한 명 더 뽑으려고 하는데, 월급 지원해 주는 고용 지원금이랑 가게 보증금 대출받을 수 있는 정책자금 각각 하나씩만 추천해줘.",
        expected_route="rag",
        expected_policies=("고용확대 우대 정책자금", "전국 소상공인 운전자금"),
        expected_answer_keywords=("고용", "대출", "정책"),
        note="복합 목적 추천 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-01",
        question="동종업계 평균 매출과 비교해줘",
        expected_route="stats",
        expected_policies=(),
        expected_answer_keywords=("평균", "매출"),
        note="통계 비교 질문",
    ),
    BizMongEvalCase(
        scenario_key="BIZ-01",
        question="운전자금이 정확히 뭐야? 시설자금이랑 어떻게 달라?",
        expected_route="general_qa",
        expected_policies=(),
        expected_answer_keywords=("운전자금", "시설자금"),
        note="용어 해석 질문",
    ),
)
