# src/app/agents/biz_mong/nodes/llm_evaluator.py
"""Node 2: LLM Evaluator — GPT-4o-mini Batch 채점 (10개 단위 청킹).

채점 기준 (총 100점):
  - 기술력(40): has_patent(+20), is_ventured(+20)
  - 고용(30): employee_count 규모별 차등
  - 안정성(30): annual_revenue, debt_ratio

[핵심] Batch Chunking 전략:
  - Hard Filter 통과 정책이 10개 초과 시, CHUNK_SIZE(=10) 단위로 분할하여 순차 호출한다.
  - 각 청크는 단일 GPT-4o-mini 호출로 JSON 배열을 받아 결과를 누적한다.
  - 이렇게 하면 50개 정책이 와도 5번의 안전한 호출로 처리된다.

[비용 최적화]:
  - GPT-4o-mini: gpt-4o 대비 약 15배 저렴 (2026년 기준 입력 $0.15/1M tokens)
  - response_format=json_object 로 JSON 파싱 오류 방지
  - 정책 텍스트는 ai_summary(~200자) 만 전달, content_raw 미포함
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.types import Command
from openai import AsyncOpenAI

from src.app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

CHUNK_SIZE = 10          # 청크당 최대 정책 수 (토큰 한계 방어선)
MIN_PASS_SCORE = 40      # 최종 결과에 포함할 최소 점수


# ═══════════════════════════════════════════════════════════════════════════════
# 노드 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def llm_evaluator_node(
    state: dict,
    client: AsyncOpenAI | None = None,
) -> dict | Command:
    """Hard Filter 통과 정책을 GPT-4o-mini 로 일괄 채점한다.

    State 입력:
        candidate_policies: hard_filter 가 설정한 후보 정책 목록
        biz_info, financial_data: 사업장 프로필
        pending_intent: "simulator" 이면 채점 완료 후 시뮬레이터로 라우팅

    State 출력:
        diagnosis_report: {score, reason, advice, ranked_policies}
        candidate_policies: 점수 정렬된 정책 목록 (min_pass_score 이상만)
    """
    _client = client or AsyncOpenAI(api_key=OPENAI_API_KEY)

    candidates: list[dict] = state.get("candidate_policies") or []
    biz_info: dict = state.get("biz_info") or {}
    financial_data: dict = state.get("financial_data") or {}

    if not candidates:
        logger.info("[llm_evaluator] 후보 정책 없음 → 빈 진단 보고서 반환")
        report = _empty_report("Hard Filter 를 통과한 정책이 없습니다. 사업장 정보를 보완해 보세요.")
        return _build_return(state, report, [])

    # ── Batch Chunking 평가 ───────────────────────────────────────────────
    biz_profile = _build_biz_profile(biz_info, financial_data)
    scored: list[dict] = await _evaluate_all_chunks(_client, candidates, biz_profile)

    # 최소 점수 이하 정책 제거 및 내림차순 정렬
    scored = [p for p in scored if p.get("score", 0) >= MIN_PASS_SCORE]
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)

    # ── 진단 보고서 생성 ───────────────────────────────────────────────────
    report = _build_diagnosis_report(biz_profile, scored)

    logger.info("[llm_evaluator] 최종 채점 완료 — %d 개 정책 (통과: %d 개)", len(candidates), len(scored))

    return _build_return(state, report, scored)


# ═══════════════════════════════════════════════════════════════════════════════
# 내부 함수
# ═══════════════════════════════════════════════════════════════════════════════

async def _evaluate_all_chunks(
    client: AsyncOpenAI,
    policies: list[dict],
    biz_profile: dict,
) -> list[dict]:
    """정책 목록을 CHUNK_SIZE 단위로 분할하여 순차 평가하고 결과를 합친다."""
    all_results: list[dict] = []
    chunks = [policies[i:i + CHUNK_SIZE] for i in range(0, len(policies), CHUNK_SIZE)]

    for idx, chunk in enumerate(chunks):
        logger.debug("[llm_evaluator] 청크 %d/%d 처리 중 (%d 개)", idx + 1, len(chunks), len(chunk))
        try:
            chunk_results = await _call_llm_batch(client, chunk, biz_profile)
            all_results.extend(chunk_results)
        except Exception as exc:
            logger.warning("[llm_evaluator] 청크 %d LLM 호출 실패: %s", idx + 1, exc)
            # 실패한 청크 정책은 기본 점수로 채워 넣는다 (탈락 방지)
            for policy in chunk:
                all_results.append({
                    **policy,
                    "score": MIN_PASS_SCORE,
                    "score_breakdown": {"기술력": 0, "고용": 0, "안정성": 0},
                    "reason": "채점 중 오류가 발생했습니다.",
                    "evaluation_error": True,
                })

    return all_results


async def _call_llm_batch(
    client: AsyncOpenAI,
    chunk: list[dict],
    biz_profile: dict,
) -> list[dict]:
    """단일 GPT-4o-mini 호출로 chunk 정책 전체를 채점하고 JSON 배열로 반환한다."""

    policy_summaries = []
    for i, p in enumerate(chunk):
        policy_summaries.append(
            f"[{i}] 정책명: {p['title']}\n"
            f"    기관: {p['agency_name']}\n"
            f"    지원유형: {p.get('support_type', '미상')}\n"
            f"    요약: {p.get('ai_summary', '')[:200]}\n"
            f"    지원금액: {p.get('support_amount_desc', '미상')}"
        )

    system_prompt = _build_system_prompt()
    user_content = (
        f"[사업장 프로필]\n{json.dumps(biz_profile, ensure_ascii=False, indent=2)}\n\n"
        f"[평가 대상 정책 목록]\n" + "\n\n".join(policy_summaries)
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw = json.loads(response.choices[0].message.content)
    scores_list: list[dict] = raw.get("scores", [])

    # 원본 정책 dict 에 채점 결과 병합
    results: list[dict] = []
    for i, policy in enumerate(chunk):
        score_data = next((s for s in scores_list if s.get("index") == i), {})
        total_score = (
            score_data.get("기술력", 0)
            + score_data.get("고용", 0)
            + score_data.get("안정성", 0)
        )
        results.append({
            **policy,
            "score": min(100, max(0, total_score)),
            "score_breakdown": {
                "기술력": score_data.get("기술력", 0),
                "고용": score_data.get("고용", 0),
                "안정성": score_data.get("안정성", 0),
            },
            "reason": score_data.get("reason", ""),
            "recommendation": score_data.get("recommendation", ""),
        })

    return results


def _build_system_prompt() -> str:
    return """당신은 대한민국 중소기업/소상공인 정책 자금 전문가입니다.
사업장 프로필과 정책 목록을 분석하여 각 정책에 대한 적합도 점수를 산출하세요.

[채점 기준 — 총 100점]
- 기술력(40점): 특허 보유(has_patent=true) +20점, 벤처기업 인증(is_ventured=true) +20점
- 고용(30점): 직원 수 기반 (10명 이상 +30, 5~9명 +20, 1~4명 +10, 0명 +0)
- 안정성(30점): 매출 및 부채비율 종합 판단
  - 매출 1억 이상 +10, 5억 이상 +20, 10억 이상 +30
  - 부채비율 100% 이하는 감점 없음, 200% 초과 시 최대 -10점

[응답 형식 — 반드시 아래 JSON 구조를 따르세요]
{
  "scores": [
    {
      "index": 0,
      "기술력": 20,
      "고용": 20,
      "안정성": 20,
      "reason": "이 정책이 이 사업장에 적합한 이유 (1~2문장)",
      "recommendation": "신청 시 주의사항 또는 준비 사항 (1문장)"
    }
  ]
}

주의사항:
- index 는 입력된 정책의 순서 번호([0], [1], ...)입니다.
- 모든 정책에 대해 점수를 반드시 반환하세요.
- reason 과 recommendation 은 소상공인이 이해하기 쉬운 평범한 한국어로 작성하세요."""


def _build_biz_profile(biz_info: dict, financial_data: dict) -> dict:
    """LLM 에 전달할 사업장 프로필 dict 를 구성한다."""
    return {
        "상호명": biz_info.get("biz_name", "미상"),
        "지역": f"{biz_info.get('region_sido', '')} {biz_info.get('region_sigungu', '')}".strip(),
        "업종코드": biz_info.get("ksic_code", "미상"),
        "설립일": biz_info.get("establishment_date", "미상"),
        "특허보유": biz_info.get("has_patent", False),
        "벤처기업": biz_info.get("is_ventured", False),
        "여성기업": biz_info.get("is_female_ent", False),
        "연매출": _fmt_amount(financial_data.get("annual_revenue")),
        "직원수": financial_data.get("employee_count", 0),
        "부채비율": f"{financial_data.get('debt_ratio', 0):.1f}%",
        "체납여부": financial_data.get("tax_arrears_yn", False),
    }


def _build_diagnosis_report(biz_profile: dict, scored: list[dict]) -> dict:
    """진단 보고서 dict 를 생성한다."""
    if not scored:
        return _empty_report("현재 프로필로는 적합한 정책을 찾지 못했습니다.")

    top = scored[0]
    avg_score = sum(p.get("score", 0) for p in scored) / len(scored)

    if avg_score >= 70:
        advice = "현재 프로필이 우수합니다. 상위 정책부터 적극적으로 신청을 검토하세요."
    elif avg_score >= 50:
        advice = "일부 정책에 적합합니다. 벤처 인증이나 특허 취득 시 더 많은 기회가 생깁니다."
    else:
        advice = "현재 프로필로는 기회가 제한적입니다. 시뮬레이션으로 개선 방향을 확인해 보세요."

    return {
        "score": round(avg_score, 1),
        "top_policy": top.get("title", ""),
        "top_score": top.get("score", 0),
        "reason": top.get("reason", ""),
        "advice": advice,
        "ranked_policies": scored[:10],  # 상위 10개만 저장
        "total_candidates": len(scored),
    }


def _empty_report(reason: str) -> dict:
    return {
        "score": 0,
        "top_policy": "",
        "top_score": 0,
        "reason": reason,
        "advice": "사업장 정보(매출, 직원 수 등)를 먼저 등록해 주세요.",
        "ranked_policies": [],
        "total_candidates": 0,
    }


def _build_return(state: dict, report: dict, scored: list[dict]) -> dict | Command:
    """pending_intent 에 따라 Command 또는 일반 dict 를 반환한다."""
    update = {
        "diagnosis_report": report,
        "candidate_policies": scored,
    }
    if state.get("pending_intent") == "simulator":
        return Command(
            goto="simulator",
            update={**update, "pending_intent": None},
        )
    return update


def _fmt_amount(val: Any) -> str:
    if val is None:
        return "미상"
    if val >= 1_0000_0000:
        return f"{val / 1_0000_0000:.1f}억원"
    if val >= 1_0000:
        return f"{val // 1_0000}만원"
    return f"{val:,}원"
