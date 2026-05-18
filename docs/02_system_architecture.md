# 02. 시스템 아키텍처

> **서비스명**: Biz-Up / 저장소명: biz-fund-ai / AI 챗봇: 비즈몽(BizMong)
>
> **문서 목적**: 코드를 보지 않고도 전체 시스템 구조와 데이터 파이프라인, 비즈몽 에이전트 흐름을 완벽히 이해할 수 있는 기술 청사진.
>
> **대상 독자**: 시니어 백엔드 엔지니어, LLM/RAG Engineer
>
> **최종 업데이트**: 2026-05-17

---

## 1. 기술 스택

### Backend

| 분류 | 기술 | 버전 | 역할 |
|:---|:---|:---|:---|
| 언어 | Python | 3.12 | 타입 힌트 + async/await 전체 적용 |
| 웹 프레임워크 | FastAPI | >=0.132.0 | 비동기 API 서버, OpenAPI 자동 문서화 |
| 데이터 검증 | Pydantic v2 | 2.x | 요청/응답 스키마 엄격한 타입 검증 |
| ORM | SQLAlchemy | 2.0 | 비동기 세션(`AsyncSession`) 기반 |
| DB 마이그레이션 | Alembic | >=1.18.4 | 스키마 버전 관리 |
| 패키지 관리 | uv | - | pip 대비 10~100배 빠른 의존성 해결 |

### AI / LLM

| 기술 | 모델 | 역할 |
|:---|:---|:---|
| OpenAI | gpt-4o-mini | Router 의도 분류, RAG 답변 생성, Batch 채점 |
| OpenAI | gpt-4o | PolicySyncAgent 정책 공고 구조화 |
| OpenAI | text-embedding-3-small | 정책 청크 임베딩 (1536-dim) |
| LangGraph | StateGraph | 비즈몽 멀티노드 오케스트레이션 |
| LangGraph | langgraph-checkpoint-postgres | 세션별 대화 상태 영속화 (PostgreSQL) |

### Database

| 기술 | 역할 |
|:---|:---|
| PostgreSQL 16 | 정형 데이터 (users, businesses, policies 등) + JSONB(target_logic) |
| pgvector 확장 | 벡터 유사도 검색 (policy_chunks.embedding) |

---

## 2. 전체 시스템 아키텍처

### 2.1 High-Level 구조

Biz-Up은 **소상공인 경영 합리화 AI 플랫폼**이며, 비즈몽(BizMong)은 그 안의 AI 상담 기능입니다.

```
[React 프론트엔드 — Biz-Up 서비스]
       │ HTTP/JSON
       ▼
[FastAPI 서버]
  ├── /api/v1/auth          ← JWT 인증 (Access 30분 + Refresh 7일 Dual Token)
  ├── /api/v1/businesses    ← 사업장 + 재무 CRUD + 국세청 API 연동 + OCR
  ├── /api/v1/chats         ← 비즈몽 에이전트 진입점 + 대화 세션 관리
  ├── /api/v1/diagnoses     ← 정밀 진단 (Hard Filter + LLM Evaluator)
  ├── /api/v1/policies      ← 정책 조회 / 검색 / 북마크
  ├── /api/v1/biz-picks     ← AI 큐레이션 카드 뉴스 (비즈-픽)
  ├── /api/v1/notifications ← 알림 목록 + 설정 (비즈-핑)
  ├── /api/v1/users         ← 사용자 프로필
  └── /api/v1/admin         ← 정책 동기화, 콘텐츠, 피드백, 모니터링
       │
       ▼
[비즈몽 AI (LangGraph StateGraph)]  ← AI 상담 핵심 (rag / stats / chitchat)
       │
       ▼
[PostgreSQL + pgvector]
```

### 2.2 보안 아키텍처

| 구분 | 전략 | 상세 |
|:---|:---|:---|
| 인증 | Dual Token | Access Token(30분, 메모리 저장) + Refresh Token(7일, HttpOnly 쿠키) |
| 권한 관리 | FastAPI Depends | `get_current_user`, `get_active_business` 의존성 주입 |
| 비밀번호 | BCrypt | bcrypt 알고리즘 솔팅 단방향 암호화 |
| 민감 정보 | 환경 변수 | python-dotenv, OPENAI_API_KEY / DATABASE_URL 분리 |
| CORS | FastAPI Middleware | 허용된 프론트엔드 도메인만 수락 |

---

## 3. 비AI 핵심 데이터 플로우

### 3.1 사용자 온보딩 플로우 (국세청 API 연동)

소상공인이 최초 서비스 등록 시 사업자등록번호의 유효성을 국세청 공공 API로 자동 검증합니다.

```
[사용자] 사업자번호 입력
        │
        ▼
[POST /api/v1/businesses/{id}/verify-biz-no]
        │
        ▼
[BusinessService.verify_biz_no()]
  ├── 국세청 사업자 상태 조회 API 호출
  ├── 반환값: biz_status (계속사업자 / 휴업자 / 폐업자)
  ├── 반환값: tax_type (부가가치세 일반과세자 등)
  └── 반환값: open_date (개업 일자)
        │
        ▼
[DB 저장]
  businesses.is_biz_no_verified = true
  businesses.biz_verified_status = "계속사업자"
  businesses.tax_type = "부가가치세 일반과세자"
  businesses.biz_verified_at = now()
```

---

### 3.2 서류 OCR 처리 플로우

사업자등록증, 재무제표 등 공식 서류를 업로드하면 OCR이 자동 추출하여 `business_financial_snapshots`에 반영합니다.

```
[사용자] 서류 업로드
        │
        ▼
[POST /api/v1/businesses/{id}/documents]
  ├── 파일 → 스토리지 저장
  └── documents 테이블 신규 행 생성
      documents.ocr_status = "PENDING"
        │
        ▼
[Background Task: OCR Worker]
  ├── 파일 다운로드
  ├── OCR 엔진 텍스트 추출
  ├── 추출 성공: documents.ocr_status = "COMPLETED"
  │             documents.ocr_result = { 추출된 필드 JSON }
  │             → business_financial_snapshots 자동 갱신
  │             → business_financial_snapshots.is_verified = true
  └── 추출 실패: documents.ocr_status = "FAILED"
        │
        ▼
[알림 발송]
  → notifications 테이블 신규 행 (type: "OCR_COMPLETE" / "OCR_FAILED")
```

---

## 4. 정책 데이터 파이프라인 — PolicySyncAgent

### 4.1 플로우

```
외부 공고 API (기업마당 등)
        │ 원문 URL + 메타데이터
        ▼
[PolicySyncAgent (LangGraph Self-Correction)]
  ├── Parser 노드: 문서 다운로드·파싱 / 실패 시 2회 재시도
  ├── Extractor 노드: GPT-4o 구조화 추출 / target_logic 생성
  └── Validator 노드: 필수 필드 검증 / 누락 시 재시도
        │ structured_data
        ▼
[PolicyService] → UPSERT → policies 테이블
        │
        ▼
[ChunkingService] → text-embedding-3-small → policy_chunks (pgvector, 1536-dim)
```

### 4.2 Self-Correction 전략

| 단계 | 실패 조건 | 재시도 횟수 | 최종 실패 처리 |
|:---|:---|:---|:---|
| Parser 단계 | 파일 다운로드 / 파싱 오류 | 최대 2회 | `status = PARSE_ERROR` |
| Extractor/Validator 단계 | 필수 필드 누락 | 최대 2회 | `status = ANALYSIS_ERROR` |

**Fail-Fast 최적화**: 파일 URL이 없는 경우 파싱 루프를 타지 않고 즉시 실패 처리하여 불필요한 GPT 호출 비용을 차단합니다.

---

## 5. BizMong 에이전트 — 핵심 설계

> **범위**: BizMong LangGraph 에이전트는 **일상 대화(chitchat), 정책 RAG 검색(rag), 동종업계 통계(stats)** 세 가지 노드로 구성됩니다.
> 정밀 진단(Hard Filter + LLM Evaluator)과 시뮬레이션은 별도 서비스(`/api/v1/diagnoses`)로 분리되어 있습니다.

### 5.1 State (전역 공유 상태)

LangGraph의 `StateGraph(dict)` 기반으로, 모든 노드가 하나의 State 딕셔너리를 공유합니다.  
`messages` 필드만 `add_messages` reducer로 **추가(append)**되고, 나머지 필드는 **덮어쓰기(shallow-overwrite)**됩니다.

```python
class BizMongState(dict):
    # 식별자
    user_id: str          # 로그인 사용자 UUID
    business_id: str      # 사업장 UUID
    room_id: str          # ChatRoom.id = LangGraph thread_id

    # 대화
    messages              # add_messages 리듀서로 누적 (append)

    # 데이터 (DB 기반)
    biz_info: dict        # Business 모델: 상호명, 지역, 설립일, 특허/벤처 여부 등
    financial_data: dict  # BusinessFinancialSnapshot: 매출, 인원, 부채 등

    # 에이전트 작업 공간
    current_agent: str    # "greeting" | "general_qa" | "rag" | "stats"
    stats_insight: dict   # stats_node 결과 — 동종업계 비교 인사이트

    # 제어
    is_error: bool
    error_message: str
```

**thread_id = room_id**: PostgreSQL 체크포인터(`langgraph-checkpoint-postgres`)가 동일 `room_id`에 대해 여러 요청 간 대화 맥락을 영속합니다. 서버 재시작 시에도 상태가 유지됩니다.

---

### 5.2 그래프 구조 및 라우팅

```
START
  ↓
router (의도 분류)
  ├── greeting    → chitchat → END
  ├── general_qa  → chitchat → END
  ├── rag         → rag      → END
  └── stats       → stats    → END
```

```python
builder = StateGraph(dict)
builder.add_node("router", _router)
builder.add_node("chitchat", _chitchat)
builder.add_node("rag", _rag)
builder.add_node("stats", _stats)

builder.set_entry_point("router")
builder.add_conditional_edges(
    "router",
    lambda state: state.get("current_agent", "general_qa"),
    {
        "greeting": "chitchat",
        "general_qa": "chitchat",
        "rag": "rag",
        "stats": "stats",
    },
)
builder.compile(checkpointer=get_langgraph_checkpointer())  # PostgreSQL
```

---

### 5.3 노드별 상세 설계

#### Node 0: Router Node (의도 분류)

```
입력: messages (대화 히스토리)
출력: current_agent = "greeting" | "general_qa" | "rag" | "stats"

1차: GPT-4o-mini로 JSON 분류 (max_tokens=20, temperature=0.0)
2차 폴백: 키워드 매칭
모호한 경우: general_qa 기본값
```

---

#### Node 1: Chitchat Node (일상 대화 / 일반 QA)

```
입력: messages, current_agent (greeting | general_qa)
처리: GPT-4o-mini로 일반 대화 응답 생성
출력: messages (assistant 응답 추가)
```

---

#### Node 2: RAG Node (Hybrid 정책 검색)

```python
# _run_rag 함수 흐름

Step 1: 마지막 사용자 메시지 추출
        biz_info.region_sido로 지역 필터 설정

Step 2: policy_rag_search(query, session, region_filter)
        ├── 벡터 검색 (pgvector cosine distance) — 상위 20개
        ├── FTS 검색 (ilike 키워드 매칭) — 상위 20개
        └── RRF 융합 (k=60) → top-5 policy_id

Step 3: 검색 결과 없으면 안내 메시지 반환 (fallback)

Step 4: 상위 3개 청크를 컨텍스트로 구성
        → GPT-4o-mini로 답변 생성 (temperature=0.2)

Step 5: _write_through로 RAG 결과 + 토큰 사용량 ChatLog 기록
```

**폴백 전략**: OpenAI 생성 실패 시 검색 결과 기반 요약 답변(`_build_rag_fallback_answer`)으로 대체합니다.

---

#### Node 3: Stats Node (동종업계 집계)

```
1. ksic_code(표준산업분류) 기반 동종 사업장 집계
   - 집계 지표: avg_revenue, avg_employees, avg_debt_ratio
   - 최소 샘플: MIN_PEER_COUNT = 5개
   - 미달 시: 전업종 평균으로 폴백

2. 백분위 간이 계산
   매출 / 평균매출 ≥ 3배 → 상위 10%
   매출 / 평균매출 ≥ 2배 → 상위 25%
   매출 / 평균매출 ≥ 1배 → 상위 50%
   매출 / 평균매출 < 1배 → 하위 25%

3. 인사이트 텍스트 생성 (LLM 없음, 순수 Python 문자열 조합)

4. _write_through로 stats 결과 ChatLog 기록
```

---

### 5.4 Write-through 관측 패턴

**목적**: 에이전트 내부 동작(RAG 검색 수, 통계 인사이트, 토큰 사용량 등)을 DB에 기록해 모니터링·비용 분석·디버깅에 활용합니다.

> 참고: 대화 상태 영속은 PostgreSQL 체크포인터가 담당합니다. Write-through는 추가 관측성(observability)을 위한 별도 레이어입니다.

```python
async def _write_through(state, node_name, result):
    # 별도 SessionLocal() 사용 → 메인 트랜잭션과 격리
    async with SessionLocal() as wt_session:
        log = ChatLog(
            user_id=user_uuid,
            room_id=room_uuid,
            role="system",
            content=_summarize_result(node_name, result),
            context_type="agent",
            tokens_in=...,   # RAG 노드의 경우 토큰 사용량 함께 기록
            tokens_out=...,
            model_name=...,
        )
        wt_session.add(log)
        await wt_session.commit()
    # 커밋 실패 시 warning 로그만 남기고 에이전트 실행 계속 (에이전트 중단 없음)
```

**노드별 기록 내용**:

| 노드 | 기록 내용 |
|:---|:---|
| rag | `{node, results_count}` + tokens_in, tokens_out, model_name |
| stats | `{node, peer_count, avg_revenue}` |

---

## 6. 진단 서비스 — DiagnosisService (/api/v1/diagnoses)

> BizMong LangGraph 에이전트와 별도로, 정밀 진단과 시뮬레이션은 독립 서비스로 구현되어 있습니다.

### 6.1 Hard Filter (규칙 기반 필터링)

LLM 없이 순수 Python 규칙으로 정책을 사전 제거합니다.

**4가지 필터 룰**:

| 룰 | 조건 | 처리 |
|:---|:---|:---|
| R1 (세금 체납) | `tax_arrears_yn = True` | 전 정책 즉시 탈락 |
| R2 (지역 불일치) | `region_restricted=True` AND 사업장 지역 불일치 | 해당 정책 탈락 |
| R3 (업력 미달) | `min_business_age_months > 현재 업력` | 해당 정책 탈락 |
| R4 (규모 초과) | `max_revenue < 연매출` OR `max_employees < 직원수` | 해당 정책 탈락 |

**`parse_target_logic()` 정규화 파서**: `Policy.target_logic`은 GPT-4o가 생성한 JSONB라 스키마 일관성을 보장할 수 없습니다. 이 파서가 모든 타입 불일치와 키 누락을 방어적으로 처리합니다.

### 6.2 LLM Evaluator (AI 적합도 채점)

**채점 기준 (총 100점)**:

| 카테고리 | 배점 | 세부 기준 |
|:---|:---|:---|
| 기술력 | 40점 | 특허 보유(has_patent=true) +20점, 벤처기업 인증(is_ventured=true) +20점 |
| 고용 | 30점 | 10명 이상 +30, 5~9명 +20, 1~4명 +10, 0명 +0 |
| 안정성 | 30점 | 연매출 10억+ +30, 5억+ +20, 1억+ +10 / 부채비율 200% 초과 시 -10 |

**Batch Chunking 전략**:

```python
CHUNK_SIZE = 10   # 청크당 최대 정책 수
MIN_PASS_SCORE = 40  # 최종 포함 최소 점수

# 정책 N개를 10개 단위로 분할 → 청크당 단일 GPT-4o-mini 호출
# 청크 실패 시: MIN_PASS_SCORE로 채워 탈락 방지 (장애 허용)
# 결과 누적 후 점수 기준 내림차순 정렬
```

결과는 `MatchLog` 테이블에 저장됩니다 (`match_score`, `match_status G/Y/R`, `reason_json`).

---

## 7. API 계층 구조

### 7.1 FastAPI 라우터 구성

```
/api/v1/
├── /auth/          ← 소셜 로그인(카카오/네이버), 토큰 갱신/로그아웃
├── /users/         ← 사용자 프로필 조회/수정/탈퇴
├── /businesses/    ← 사업장 CRUD + 재무 스냅샷 + 서류 OCR
├── /chats/         ← 세션 관리 + BizMong 에이전트 메시지 (stream 포함)
│   └── /sessions/{id}/messages  ← 에이전트 실행 엔드포인트
├── /diagnoses/     ← 진단 요청/결과 조회 (Hard Filter + LLM Evaluator)
├── /policies/      ← 정책 조회/검색/북마크
├── /biz-picks/     ← 큐레이션 카드 뉴스 조회
├── /notifications/ ← 알림 목록/읽음 처리
└── /admin/         ← 정책 CRUD, 콘텐츠 관리, 피드백, 모니터링, 감사로그
```

---

## 8. 인프라 및 운영 환경

| 항목 | 기술/전략 |
|:---|:---|
| 버전 관리 | Git + GitHub (Feature Branch 전략) |
| 패키지 관리 | uv (Python) |
| 로깅 | Python logging 모듈 (각 노드마다 INFO/DEBUG 레벨 분리) |
| DB 마이그레이션 | Alembic (versions/ 하위 파일로 이력 관리) |
| 환경 변수 | python-dotenv (.env 분리, .gitignore 처리) |
| 에디터 | Visual Studio Code (Cursor IDE) |
| 스케줄링 | APScheduler (배치 작업) |
