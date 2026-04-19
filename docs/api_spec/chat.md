# API 명세서: 채팅 / BizMong 멀티 에이전트

> 이 문서는 BizMong AI 상담 시스템의 모든 API 엔드포인트를 정의합니다.  
> **`agent-message` 엔드포인트**가 핵심으로, LangGraph 멀티 에이전트의 최종 응답 JSON을 상세히 명세합니다.

**Base URL**: `/api/v1/chats`  
**인증**: 모든 요청에 `Authorization: Bearer {ACCESS_TOKEN}` 헤더 필요

---

## 1. 세션 생성 (Create Chat Session)

- **Method**: `POST`
- **Endpoint**: `/api/v1/chats/sessions`
- **설명**: BizMong과 새로운 상담 세션을 생성합니다. 세션 ID = LangGraph `thread_id`

**Request Body**:
```json
{
  "title": "정책자금 상담"
}
```

**Response** `201 Created`:
```json
{
  "status": 201,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "business_id": "uuid",
    "title": "정책자금 상담",
    "is_active": true,
    "created_at": "2026-04-19T12:00:00Z",
    "updated_at": "2026-04-19T12:00:00Z"
  }
}
```

**Error Codes**:
- `401 Unauthorized`: 인증 토큰 없음/만료
- `403 Forbidden`: 사업장 미등록 (온보딩 필요)

---

## 2. 세션 목록 조회 (Get Chat Sessions)

- **Method**: `GET`
- **Endpoint**: `/api/v1/chats/sessions`
- **설명**: 사업장 소유의 상담 세션 목록을 최신순으로 조회합니다.

**Response** `200 OK`:
```json
{
  "status": 200,
  "message": "success",
  "data": [
    {
      "id": "uuid",
      "business_id": "uuid",
      "title": "고용지원금 상담",
      "is_active": true,
      "created_at": "2026-04-19T12:00:00Z",
      "updated_at": "2026-04-19T12:30:00Z"
    }
  ]
}
```

---

## 3. 메시지 전송 (Send Message)

- **Method**: `POST`
- **Endpoint**: `/api/v1/chats/sessions/{session_id}/messages`
- **설명**: 기존 세션에 일반 메시지를 전송합니다. AI 에이전트 없이 ChatLog에만 저장.

**Request Body**:
```json
{
  "message": "안녕하세요"
}
```

**Response** `200 OK`:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "id": "uuid",
    "room_id": "uuid",
    "role": "assistant",
    "content": "안녕하세요 사장님! 무엇을 도와드릴까요?",
    "created_at": "2026-04-19T12:00:00Z"
  }
}
```

---

## 4. 대화 내역 조회 (Get Chat Messages)

- **Method**: `GET`
- **Endpoint**: `/api/v1/chats/sessions/{session_id}/messages`
- **설명**: 특정 세션의 전체 대화 내역을 조회합니다.

**Response** `200 OK`:
```json
{
  "status": 200,
  "message": "success",
  "data": [
    {
      "id": "uuid",
      "room_id": "uuid",
      "role": "user",
      "content": "어떤 정책자금을 받을 수 있나요?",
      "created_at": "2026-04-19T12:00:00Z"
    },
    {
      "id": "uuid",
      "room_id": "uuid",
      "role": "assistant",
      "content": "진단 완료! 현재 프로필 적합도 점수: 65.0점 ...",
      "created_at": "2026-04-19T12:00:05Z"
    }
  ]
}
```

---

## 5. 세션 제목 자동 요약 (Auto Summary)

- **Method**: `PATCH`
- **Endpoint**: `/api/v1/chats/sessions/{session_id}/summary`
- **설명**: 대화 내용을 바탕으로 GPT가 세션 제목을 자동 생성합니다.

**Response** `200 OK`:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "id": "uuid",
    "title": "소상공인 경영안정자금 진단 상담"
  }
}
```

---

## 6. 세션 삭제 (Delete Chat Session)

- **Method**: `DELETE`
- **Endpoint**: `/api/v1/chats/sessions/{session_id}`
- **설명**: 세션 Soft Delete (is_active=false 처리)

**Response** `204 No Content`

**Error Codes**:
- `403 Forbidden`: 타인의 세션 삭제 시도

---

## ★ 7. BizMong 에이전트 메시지 (Agent Message) — 핵심 엔드포인트

- **Method**: `POST`
- **Endpoint**: `/api/v1/chats/sessions/{session_id}/agent-message`
- **설명**: 사용자 메시지를 LangGraph 멀티 에이전트로 처리합니다.  
  내부적으로 의도 분류 → 해당 에이전트 실행 → 결과 반환까지 모두 처리합니다.

**에이전트 타입별 동작**:
| `agent_type` | 트리거 예시 | 동작 |
|:---|:---|:---|
| `diagnosis` | "어떤 지원금 받을 수 있나요?", "진단해 줘" | Hard Filter → Batch 채점 → diagnosis_report |
| `simulator` | "특허 취득하면?", "직원 5명 더 뽑으면?" | 가상 변수 추출 → 점수 재계산 → simulation_report |
| `rag` | "청년창업패키지가 뭔가요?", "신청 방법" | Hybrid RAG 검색 → GPT 답변 → rag_results |
| `stats` | "같은 업종 평균 매출은?", "동종업계 비교" | DB 집계 → 백분위 계산 → stats_insight |

**Request Body**:
```json
{
  "message": "어떤 정책자금을 받을 수 있나요?"
}
```

**Response** `200 OK` — `agent_type: "diagnosis"` 예시:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "role": "assistant",
    "content": "진단 완료! 현재 프로필 적합도 점수: 65.0점\n추천 정책: 소상공인 경영안정자금 (총 12개 매칭)\n일부 정책에 적합합니다. 벤처 인증이나 특허 취득 시 더 많은 기회가 생깁니다.",
    "agent_type": "diagnosis",
    "diagnosis_report": {
      "score": 65.0,
      "top_policy": "소상공인 경영안정자금",
      "top_score": 80,
      "reason": "매출 규모와 고용 인원이 정책 기준을 충족하며, 서울 소재 사업장으로 지역 요건도 만족합니다.",
      "advice": "일부 정책에 적합합니다. 벤처 인증이나 특허 취득 시 더 많은 기회가 생깁니다.",
      "ranked_policies": [
        {
          "policy_id": "uuid",
          "title": "소상공인 경영안정자금",
          "agency_name": "소상공인시장진흥공단",
          "category": "융자",
          "support_type": "대출",
          "region": "전국",
          "max_support": 70000000,
          "min_support": 10000000,
          "support_amount_desc": "1천만원 ~ 7천만원",
          "end_date": "2026-12-31",
          "apply_url": "https://www.sbiz.or.kr",
          "score": 80,
          "score_breakdown": {
            "기술력": 20,
            "고용": 30,
            "안정성": 30
          },
          "reason": "직원 수와 매출 규모가 정책 기준을 충족하며 안정성 점수가 높습니다.",
          "recommendation": "신청 시 최근 1년 재무제표와 사업자등록증을 미리 준비하세요."
        }
      ],
      "total_candidates": 12
    },
    "simulation_report": null,
    "stats_insight": null,
    "rag_results": null,
    "created_at": "2026-04-19T12:00:05Z"
  }
}
```

**Response** `200 OK` — `agent_type: "simulator"` 예시:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "session_id": "uuid",
    "message_id": "uuid",
    "role": "assistant",
    "content": "시뮬레이션 결과: 50.0점 → 70.0점 (+20.0점)\n\n• 특허 취득 시 기술력 점수가 20점 올라 3개의 신규 정책에 접근 가능해집니다.\n• 현재 신청 가능한 중소기업 R&D 지원 사업의 최소 점수(60점)를 초과하게 됩니다.\n• 벤처기업 인증과 함께 진행하면 추가로 20점이 더 올라 상위 5개 정책 모두 신청 가능합니다.",
    "agent_type": "simulator",
    "diagnosis_report": null,
    "simulation_report": {
      "original_score": 50.0,
      "virtual_score": 70.0,
      "diff": 20.0,
      "virtual_state": {
        "has_patent": true
      },
      "benefit_amount": null,
      "insights": [
        "특허 취득 시 기술력 점수가 20점 올라 3개의 신규 정책에 접근 가능해집니다.",
        "현재 신청 가능한 중소기업 R&D 지원 사업의 최소 점수(60점)를 초과하게 됩니다.",
        "벤처기업 인증과 함께 진행하면 추가로 20점이 더 올라 상위 5개 정책 모두 신청 가능합니다."
      ],
      "changed_variables": ["has_patent"]
    },
    "stats_insight": null,
    "rag_results": null,
    "created_at": "2026-04-19T12:00:08Z"
  }
}
```

**Response** `200 OK` — `agent_type: "rag"` 예시:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "session_id": "uuid",
    "message_id": "uuid",
    "role": "assistant",
    "content": "소상공인 경영안정자금은 소상공인시장진흥공단에서 운영하는 정책 융자 상품으로...",
    "agent_type": "rag",
    "diagnosis_report": null,
    "simulation_report": null,
    "stats_insight": null,
    "rag_results": [
      {
        "policy_id": "uuid",
        "title": "소상공인 경영안정자금",
        "agency_name": "소상공인시장진흥공단",
        "ai_summary": "소상공인의 경영 안정을 위한 저금리 정책 융자 상품입니다.",
        "support_amount_desc": "최대 7천만원",
        "max_support": 70000000,
        "region": "전국",
        "end_date": "2026-12-31",
        "apply_url": "https://www.sbiz.or.kr",
        "rrf_score": 0.0312,
        "relevant_chunk": "신청 자격: 사업자등록증을 보유한 소상공인으로서 업력 6개월 이상인 자..."
      }
    ],
    "created_at": "2026-04-19T12:00:04Z"
  }
}
```

**Response** `200 OK` — `agent_type: "stats"` 예시:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "session_id": "uuid",
    "message_id": "uuid",
    "role": "assistant",
    "content": "업종(G47) 동종 사업장 42개 기준: 평균 연매출 1.2억원, 평균 직원 수 2.3명\n\n현재 매출은 동종업계 상위 25% 수준입니다. 평균(1.2억원) 대비 8천만원 높습니다.",
    "agent_type": "stats",
    "diagnosis_report": null,
    "simulation_report": null,
    "stats_insight": {
      "peer_count": 42,
      "ksic_code": "G47",
      "avg_revenue": 120000000,
      "avg_employees": 2.3,
      "avg_debt_ratio": 85.5,
      "percentile": {
        "revenue_percentile": 25.0,
        "employee_percentile": 50.0
      },
      "market_trend": "업종(G47) 동종 사업장 42개 기준: 평균 연매출 1.2억원, 평균 직원 수 2.3명",
      "peer_comparison": "현재 매출은 동종업계 상위 25% 수준입니다. 평균(1.2억원) 대비 8천만원 높습니다. 직원 수는 동종업계 상위 50% 수준입니다."
    },
    "rag_results": null,
    "created_at": "2026-04-19T12:00:03Z"
  }
}
```

**Error Codes**:
- `403 Forbidden`: 세션 소유권 불일치 (`"세션에 접근 권한이 없습니다."`)
- `404 Not Found`: 존재하지 않는 세션 ID
- `500 Internal Server Error`: 에이전트 실행 오류

---

## 구현 가이드라인

### 프론트엔드 렌더링 전략

1. **agent_type 기반 분기**: `agent_type` 값에 따라 다른 컴포넌트를 렌더링합니다.
   - `diagnosis` → `DiagnosisCard` 컴포넌트
   - `simulator` → `SimulationCard` 컴포넌트
   - `rag` → `RagAnswerCard` 컴포넌트
   - `stats` → `StatsChart` 컴포넌트

2. **content 필드**: 모든 에이전트 타입에서 항상 존재. 채팅 말풍선에 바로 표시.

3. **구조화 데이터**: `diagnosis_report`, `simulation_report` 등 해당 타입 외엔 `null`.  
   렌더링 전 반드시 null 체크 필요.

4. **대화 맥락 유지**: 동일 `session_id`로 연속 요청 시 LangGraph MemorySaver가 자동으로 이전 대화를 참조합니다. 프론트엔드에서 별도 히스토리 전달 불필요.

### 에러 처리

```typescript
// 에이전트 오류 응답 예시 (is_error=true 케이스)
{
  "status": 500,
  "message": "에이전트 실행 중 오류가 발생했습니다.",
  "data": null
}
```
