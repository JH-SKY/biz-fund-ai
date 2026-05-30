from src.app.agents.biz_mong.graph import _build_rag_fallback_answer, _format_business_context


def test_format_business_context_includes_business_and_financial_fields():
    text = _format_business_context(
        {
            "biz_name": "도봉카페",
            "region_sido": "서울",
            "ksic_code": "I5622",
            "is_ventured": False,
        },
        {
            "snapshot_year": 2026,
            "annual_revenue": 120000000,
            "employee_count": 3,
            "tax_arrears_yn": False,
        },
    )

    assert "상호=도봉카페" in text
    assert "지역=서울" in text
    assert "업종코드=I5622" in text
    assert "연매출=120000000" in text
    assert "직원수=3" in text


def test_format_business_context_handles_empty_context():
    assert _format_business_context({}, {}) == "등록된 사업장/재무 정보 없음"


def test_build_rag_fallback_answer_includes_support_type():
    answer = _build_rag_fallback_answer(
        "내가 받을 수 있는 정책자금 뭐야?",
        [
            {
                "title": "전국 소상공인 운전자금",
                "region": "전국",
                "support_type": "운영자금",
                "support_amount_desc": "최대 1억원 운전자금",
                "ai_summary": "소상공인 운영비 부담 완화용 정책자금입니다.",
                "end_date": "2026-12-31",
            }
        ],
    )

    assert "운영자금" in answer
    assert "전국 소상공인 운전자금" in answer
