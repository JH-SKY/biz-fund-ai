# 03. 데이터 설계 명세 (DB 스키마 + API 전체 목록)

> **문서 목적**: 프론트엔드와 백엔드의 완벽한 통신 규약. 실제 코드와 100% 일치하는 DB 스키마와 API 엔드포인트 목록.  
> 프론트엔드 AI가 이 문서를 보고 즉시 타입 정의와 API 호출 코드를 작성할 수 있도록 상세히 기술합니다.
>
> **대상 독자**: 프론트엔드 개발자 (또는 프론트엔드 생성 AI), 백엔드 엔지니어  
> **최종 업데이트**: 2026-05-17

---

## 공통 규칙

### 공통 응답 포맷

모든 API는 `api_json()` 헬퍼를 통해 아래 구조로 응답합니다.

```json
{
  "status": 200,
  "message": "success",
  "data": { ... }
}
```

### ID 타입
모든 PK는 **UUID v4** (문자열 형식으로 응답)

### 시간 타입
모든 Timestamp는 **ISO 8601 UTC** (`"2026-04-19T12:00:00Z"` 형식)

### 인증
`Authorization: Bearer {ACCESS_TOKEN}` 헤더 필수 (명시 없는 엔드포인트는 공개)

### Soft Delete
`is_active = false`로 논리 삭제. 물리 삭제 없음.

---

## 1. DB 스키마

### 1.1 users (사용자 계정)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 사용자 고유 식별자 |
| email | VARCHAR(255) | NOT NULL, UNIQUE | 이메일 주소 |
| name | VARCHAR(50) | NOT NULL | 실명 |
| phone | VARCHAR(20) | NULL | 전화번호 |
| nickname | VARCHAR(50) | NULL | 활동명 |
| status | VARCHAR(20) | NOT NULL | 계정 상태 (기본: 'active') |
| social_id | VARCHAR(255) | NOT NULL | 소셜 고유 ID |
| social_provider | ENUM | NOT NULL | KAKAO \| NAVER |
| profile_image_url | TEXT | NULL | 프로필 이미지 URL |
| is_active | BOOLEAN | NOT NULL | Soft Delete 스위치 (기본: true) |
| deleted_at | TIMESTAMP | NULL | 탈퇴 일시 (5년 후 물리 삭제) |
| marketing_agreed_at | TIMESTAMP | NULL | 마케팅 동의 일시 |
| interest_sectors | JSONB | NULL | 관심 업종/분야 배열 |
| military_service | VARCHAR(30) | NULL | 군필 여부 (COMPLETED/EXEMPTED/IN_PROGRESS/NA) |
| is_non_major | BOOLEAN | NULL | 비전공 창업자 여부 |
| tech_stack | JSONB | NULL | 기술 스택 배열 |
| created_at | TIMESTAMP | NOT NULL | 가입 일시 |

### 1.2 user_tokens (인증 토큰)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | - |
| user_id | UUID | FK → users.id | - |
| token | TEXT | NOT NULL, UNIQUE | Refresh Token 원본값 |
| expires_at | TIMESTAMP | NOT NULL | 만료 일시 |
| is_revoked | BOOLEAN | NOT NULL | 무효화 여부 (기본: false) |
| created_at | TIMESTAMP | NOT NULL | 발급 일시 |

### 1.3 businesses (사업장 기본 정보)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 사업장 고유 식별자 |
| user_id | UUID | FK → users.id | 소유 사용자 |
| biz_name | VARCHAR(100) | NOT NULL | 상호명 |
| representative_name | VARCHAR(50) | NULL | 대표자명 |
| biz_no | VARCHAR(12) | NULL | 사업자등록번호 |
| ksic_code | VARCHAR(20) | NULL | 표준산업분류코드 (동종업계 비교용) |
| sector_code | VARCHAR(20) | NULL | 세부 업종 코드 |
| region_sido | VARCHAR(50) | NULL | 시·도 (정책 지역 필터용) |
| region_sigungu | VARCHAR(50) | NULL | 시·군·구 |
| region_code | VARCHAR(10) | NULL | 법정동 코드 |
| establishment_date | DATE | NULL | 설립 일자 (업력 계산용) |
| has_patent | BOOLEAN | NOT NULL | 특허 보유 여부 (기본: false) |
| is_female_ent | BOOLEAN | NOT NULL | 여성 기업 여부 (기본: false) |
| is_ventured | BOOLEAN | NOT NULL | 벤처 기업 여부 (기본: false) |
| profile_score | INTEGER | NOT NULL | 사업장 정보 완성도 0~100 (기본: 0) |
| is_biz_no_verified | BOOLEAN | NOT NULL | 국세청 API 진위 확인 완료 여부 |
| biz_verified_status | VARCHAR(30) | NULL | 국세청 반환 사업자 상태 (계속사업자/휴업자/폐업자) |
| tax_type | VARCHAR(50) | NULL | 과세 유형 (부가가치세 일반과세자 등) |
| biz_verified_at | TIMESTAMP | NULL | 국세청 API 마지막 검증 시각 |
| is_active | BOOLEAN | NOT NULL | 업장 활성 여부 (기본: true) |
| created_at | TIMESTAMP | NOT NULL | 등록 일시 |

### 1.4 business_financial_snapshots (연도별 재무 스냅샷)

**제약**: `(business_id, snapshot_year)` UNIQUE

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | - |
| business_id | UUID | FK → businesses.id | - |
| snapshot_year | INTEGER | NOT NULL | 재무제표 기준 연도 |
| snapshot_period | VARCHAR(10) | NOT NULL | 기준 시기 (1Q, 2Q 등) |
| term_type | VARCHAR(10) | NOT NULL | 공시 주기 (연간/분기) |
| annual_revenue | BIGINT | NULL | 연매출액 (원) |
| operating_profit | BIGINT | NULL | 영업이익 (원, 음수 가능) |
| net_income | BIGINT | NULL | 당기순이익 (원, 음수 가능) |
| total_debt | BIGINT | NULL | 총 부채액 (원) |
| capital | BIGINT | NULL | 자본금 (원) |
| debt_ratio | NUMERIC(5,2) | NULL | 부채 비율 (%) |
| employee_count | INTEGER | NULL | 직원 수 |
| tax_arrears_yn | BOOLEAN | NOT NULL | 세금 체납 여부 (기본: false) |
| ai_analysis_report | JSONB | NULL | AI 재무 진단 결과 |
| ocr_status | VARCHAR(20) | NOT NULL | OCR 진행 상태 (PENDING/COMPLETED/FAILED) |
| is_verified | BOOLEAN | NOT NULL | 공식 서류 기반 검증 여부 |
| is_active | BOOLEAN | NOT NULL | Soft Delete (기본: true) |
| created_at | TIMESTAMP | NOT NULL | 생성 일시 |

### 1.5 documents (서류 파일)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 서류 식별자 |
| business_id | UUID | FK → businesses.id | 소속 사업장 |
| doc_type | VARCHAR(50) | NOT NULL | 서류 종류 (사업자등록증 등) |
| file_url | TEXT | NOT NULL | S3 등 파일 경로 |
| ocr_status | VARCHAR(20) | NOT NULL | PENDING/COMPLETED/FAILED (기본: PENDING) |
| ocr_result | JSONB | NULL | OCR 추출 원본 데이터 |
| is_active | BOOLEAN | NOT NULL | Soft Delete (기본: true) |
| issued_at | DATE | NULL | 서류 발급 일자 |
| created_at | TIMESTAMP | NOT NULL | 업로드 일시 |

### 1.6 policies (정책 공고)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 정책 식별자 |
| origin_id | VARCHAR(100) | NULL | 원본 공고 ID (중복 방지용) |
| title | VARCHAR(255) | NOT NULL | 공고명 |
| agency_name | VARCHAR(100) | NULL | 주관 기관명 |
| category | VARCHAR(50) | NULL | 정책 카테고리 |
| support_type | VARCHAR(50) | NULL | 지원 유형 (대출/보조금/보증) |
| region | VARCHAR(255) | NULL | 지원 지역 |
| max_support | BIGINT | NULL | 최대 지원 금액 (원) |
| min_support | BIGINT | NULL | 최소 지원 금액 (원) |
| support_amount_desc | VARCHAR(255) | NULL | 지원금액 텍스트 설명 |
| apply_url | TEXT | NULL | 신청 URL |
| opened_at | DATE | NULL | 접수 시작일 |
| closed_at | DATE | NULL | 접수 마감일 |
| ai_summary | TEXT | NULL | GPT 생성 요약 (~200자) |
| ai_full_explanation | TEXT | NULL | GPT 생성 상세 설명 |
| target_logic | JSONB | NULL | 자격 요건 구조화 JSON |
| bonus_logic | JSONB | NULL | 가점 항목 구조화 JSON |
| status | ENUM | NOT NULL | RECRUITING/CLOSED/SCHEDULED |
| is_active | BOOLEAN | NOT NULL | 활성 여부 |
| view_count | INTEGER | NOT NULL | 조회수 (FTS 정렬 기준) |
| created_at | TIMESTAMP | NOT NULL | 등록 일시 |

### 1.7 policy_chunks (정책 임베딩 청크)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 청크 식별자 |
| policy_id | UUID | FK → policies.id | 소속 정책 |
| chunk_index | INTEGER | NOT NULL | 청크 순서 (0부터) |
| chunk_text | TEXT | NOT NULL | 청크 텍스트 |
| embedding | VECTOR(1536) | NULL | text-embedding-3-small 벡터 |
| created_at | TIMESTAMP | NOT NULL | 생성 일시 |

### 1.8 chat_rooms (AI 상담 세션)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 세션 ID = LangGraph thread_id |
| business_id | UUID | FK → businesses.id | 소속 사업장 |
| user_id | UUID | FK → users.id | 세션 소유자 |
| title | VARCHAR(255) | NULL | 세션 제목 (자동 요약 가능) |
| user_feedback | BOOLEAN | NULL | 사용자 만족도 (좋아요/싫어요) |
| status | VARCHAR(20) | NOT NULL | 상담 진행 상태 (active/closed 등, 기본: active) |
| created_at | TIMESTAMP | NOT NULL | 생성 일시 |

### 1.9 chat_logs (대화 기록)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 메시지 식별자 |
| user_id | UUID | FK → users.id | - |
| ref_policy_id | UUID | FK → policies.id, NULL | RAG 응답 시 참조한 정책 ID |
| room_id | UUID | FK → chat_rooms.id | 소속 세션 |
| role | VARCHAR(20) | NOT NULL | user / assistant / system |
| content | TEXT | NOT NULL | 메시지 내용 |
| context_type | VARCHAR(20) | NULL | 발생 위치 (widget / page / direct) |
| trace_id | VARCHAR(100) | NULL | LangSmith 모니터링 추적 ID |
| total_cost | NUMERIC(12,8) | NULL | API 토큰 비용 (USD) |
| tokens_in | INTEGER | NULL | 입력 토큰 수 |
| tokens_out | INTEGER | NULL | 출력 토큰 수 |
| model_name | VARCHAR(100) | NULL | 사용된 LLM 모델명 |
| response_time_ms | INTEGER | NULL | 응답 소요시간 (ms) |
| referenced_chunks | JSONB | NULL | RAG 참조 청크 데이터 |
| is_disliked | BOOLEAN | NOT NULL | 사용자 비추천(싫어요) 여부 (기본: false) |
| feedback_code | VARCHAR(20) | NULL | 피드백 사유 코드 (INACCURATE / UNFRIENDLY 등) |
| feedback_text | TEXT | NULL | 피드백 상세 텍스트 |
| created_at | TIMESTAMP | NOT NULL | 생성 일시 |

### 1.10 applications (정책 신청·관심 이력)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 신청(관심) 기록 고유 식별자 |
| business_id | UUID | FK → businesses.id | 신청 사업장 |
| policy_id | UUID | FK → policies.id | 대상 정책 |
| status | VARCHAR(20) | NOT NULL | 신청 단계 (INTERESTED / SUBMITTED / APPROVED / REJECTED) |
| applied_at | TIMESTAMP | NULL | 실제 신청(제출) 일시 |
| updated_at | TIMESTAMP | NOT NULL | 상태 마지막 변경 일시 |
| memo | TEXT | NULL | 사용자 메모 |

### 1.11 policy_bookmarks (정책 북마크)

**제약**: `(business_id, policy_id)` UNIQUE — 동일 정책 중복 찜 방지

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 북마크 식별자 |
| business_id | UUID | FK → businesses.id | 북마크 주인 사업장 |
| policy_id | UUID | FK → policies.id | 북마크 대상 정책 |
| created_at | TIMESTAMP | NOT NULL | 북마크 클릭 시점 |

### 1.12 notifications (알림)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 알림 고유 식별자 |
| user_id | UUID | FK → users.id | 수신 사용자 |
| business_id | UUID | FK → businesses.id, NULL | 연관 사업장 (사업장 무관 알림은 NULL) |
| type | VARCHAR(20) | NOT NULL | 알림 유형 (POLICY_MATCH / CHAT_ANSWER / DEADLINE / SYSTEM 등) |
| title | VARCHAR(255) | NOT NULL | 알림 제목 (사용자에게 노출될 요약) |
| message | TEXT | NOT NULL | 알림 본문 |
| is_read | BOOLEAN | NOT NULL | 읽음 여부 (기본: false) |
| link_url | TEXT | NULL | 클릭 시 이동 URL |
| created_at | TIMESTAMP | NOT NULL | 알림 생성 일시 |

### 1.13 match_logs (매칭 진단 결과 로그)

> **설계 의도**: 비즈몽 에이전트가 생성한 사업장↔정책 적합도 점수를 영구 보존. 재진단 없이도 과거 결과 재조회가 가능하며, 추후 ML 학습 데이터로 활용 가능.

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 매칭 결과 고유 식별자 |
| business_id | UUID | FK → businesses.id | 매칭 대상 사업장 |
| policy_id | UUID | FK → policies.id | 매칭 대상 정책 |
| match_score | INTEGER | NOT NULL | 매칭 점수 (0~100) |
| match_status | VARCHAR(10) | NOT NULL | 신호등 상태 (G / Y / R) |
| reason_json | JSONB | NULL | 점수 산정 근거 (score_breakdown 등 JSON) |
| created_at | TIMESTAMP | NOT NULL | 매칭 판정 일시 |

### 1.14 simulation_logs (시뮬레이션 결과 로그)

> **설계 의도**: 비즈몽 시뮬레이션 노드의 가상 시나리오 입력/출력 기록. 사용자가 "특허 취득 시 점수 변화"를 확인한 이력을 보존.

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 시뮬레이션 로그 고유 식별자 |
| business_id | UUID | FK → businesses.id | 기준 사업장 |
| sim_type | VARCHAR(50) | NOT NULL | 시뮬레이션 종류 (ADD_POINT / ROI_PREDICT 등) |
| input_data | JSONB | NOT NULL | 사용자 입력 조건 (가상 변수 JSON) |
| output_data | JSONB | NOT NULL | 계산·예측 결과 (점수 변화, 이자 절감액 등 JSON) |
| created_at | TIMESTAMP | NOT NULL | 실행 일시 |

### 1.15 lead_requests (파트너 상담 연결 요청)

> **설계 의도**: 사용자가 세무사·로봇세무 연결을 요청할 때 발생하는 리드(Lead) 데이터를 관리.

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 리드 요청 고유 식별자 |
| user_id | UUID | FK → users.id | 신청 사용자 |
| business_id | UUID | FK → businesses.id | 상담 대상 사업장 |
| lead_type | VARCHAR(50) | NOT NULL | 상담 종류 (로봇세무 / 세무사 연결 등) |
| status | VARCHAR(20) | NOT NULL | 처리 상태 (PENDING / REVIEWED / CONNECTED / CANCELLED) |
| created_at | TIMESTAMP | NOT NULL | 신청 일시 |

### 1.16 batch_logs (배치 작업 실행 이력)

> **설계 의도**: PolicySyncAgent가 정책 크롤링·동기화를 수행할 때마다 결과를 기록. 오류 발생 시 admin 대시보드에서 실패 원인 추적 가능.

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 배치 실행 로그 고유 식별자 |
| job_name | VARCHAR(100) | NOT NULL | 작업 명칭 (예: POLICY_CRAWLING) |
| status | VARCHAR(20) | NOT NULL | 실행 상태 (SUCCESS / FAILED / RUNNING) |
| total_count | INTEGER | NOT NULL | 처리 대상 전체 건수 |
| success_count | INTEGER | NOT NULL | 성공 반영 건수 |
| fail_count | INTEGER | NOT NULL | 실패 건수 합산 |
| api_error_count | INTEGER | NOT NULL | API 요청 실패 건수 |
| parse_error_count | INTEGER | NOT NULL | 첨부파일 텍스트 추출 실패 건수 |
| analysis_error_count | INTEGER | NOT NULL | AI 분석·검증 실패 건수 |
| db_fail_count | INTEGER | NOT NULL | DB upsert 실패 건수 |
| error_details | JSONB | NULL | 단계별 에러 요약 및 항목 목록 |
| started_at | TIMESTAMP | NOT NULL | 작업 시작 일시 |
| finished_at | TIMESTAMP | NULL | 작업 종료 일시 |

### 1.17 admins (관리자 계정)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 관리자 고유 식별자 |
| login_id | VARCHAR(50) | NOT NULL, UNIQUE | 관리자 로그인 ID |
| password | TEXT | NOT NULL | 비밀번호 해시 |
| role | ENUM | NOT NULL | MASTER \| OPERATOR \| CS |
| is_active | BOOLEAN | NOT NULL | 계정 활성 여부 (기본: true) |
| created_at | TIMESTAMP | NOT NULL | 계정 생성 일시 |

### 1.18 admin_audit_logs (관리자 작업 이력)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 감사 로그 고유 식별자 |
| admin_id | UUID | FK → admins.id | 작업 수행 관리자 |
| action_type | VARCHAR(50) | NOT NULL | 작업 유형 (POLICY_UPDATE 등) |
| target_id | UUID | NULL | 대상 엔티티 PK |
| changes | JSONB | NULL | 변경 전·후 스냅샷 |
| ip_address | VARCHAR(45) | NULL | 요청 IP |
| created_at | TIMESTAMP | NOT NULL | 작업 발생 일시 |

### 1.19 correction_notes (피드백 정정 노트)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 정정 노트 고유 식별자 |
| feedback_id | UUID | FK → chat_logs.id CASCADE | 대상 피드백 ChatLog ID |
| created_by_admin_id | UUID | FK → admins.id SET NULL, NULL | 작성 관리자 ID |
| question_pattern | TEXT | NULL | 정정이 필요한 질문 패턴 |
| expected_answer | TEXT | NULL | 기대하는 정답/답변 |
| applies_to_agent | VARCHAR(50) | NULL | 적용 대상 에이전트 노드 |
| is_active | BOOLEAN | NOT NULL | 활성 여부 (기본: true) |
| created_at | TIMESTAMP | NOT NULL | 작성 일시 |

### 1.20 agent_run_logs (에이전트 턴 관측 로그)

> **설계 의도**: BizMong 에이전트가 한 번 실행될 때(1 turn = 사용자 메시지 1개) 전체 실행 지표를 기록한다. Admin 대시보드 모니터링 용도.

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 실행 로그 고유 식별자 |
| room_id | UUID | FK → chat_rooms.id | 소속 대화방 |
| user_id | UUID | FK → users.id | 발화 사용자 |
| business_id | UUID | FK → businesses.id | 사업장 |
| user_message_log_id | UUID | FK → chat_logs.id, NULL | 사용자 메시지 ChatLog ID |
| assistant_message_log_id | UUID | FK → chat_logs.id, NULL | 어시스턴트 응답 ChatLog ID |
| route_intent | VARCHAR(50) | NULL | router_node 분류 결과 |
| final_agent | VARCHAR(50) | NULL | 최종 실행 노드 (chitchat/rag/stats 등) |
| prompt_version | VARCHAR(100) | NULL | 프롬프트 버전 |
| graph_version | VARCHAR(100) | NULL | LangGraph 그래프 버전 |
| rag_strategy_version | VARCHAR(100) | NULL | RAG 전략 버전 |
| model_name | VARCHAR(100) | NULL | 사용된 LLM 모델명 |
| status | VARCHAR(20) | NOT NULL | 실행 상태 (SUCCESS/FAILED 등, 기본: SUCCESS) |
| fallback_mode | VARCHAR(50) | NULL | 폴백 적용 여부 및 종류 |
| fallback_reason | TEXT | NULL | 폴백 원인 설명 |
| question_preview | TEXT | NULL | 사용자 질문 앞 100자 |
| started_at | TIMESTAMP | NOT NULL | 실행 시작 일시 |
| completed_at | TIMESTAMP | NULL | 실행 완료 일시 |
| total_latency_ms | INTEGER | NULL | 전체 응답 시간 (ms) |
| first_token_latency_ms | INTEGER | NULL | 첫 토큰까지 지연시간 (ms) |
| tokens_in | INTEGER | NULL | 입력 토큰 수 |
| tokens_out | INTEGER | NULL | 출력 토큰 수 |
| total_cost_usd | NUMERIC(12,8) | NULL | 총 API 비용 (USD) |
| rag_hit_count | INTEGER | NULL | RAG 검색 결과 수 |
| error_code | VARCHAR(100) | NULL | 오류 코드 |
| error_message | TEXT | NULL | 오류 메시지 |
| extra | JSONB | NULL | 기타 메타데이터 |
| created_at | TIMESTAMP | NOT NULL | 레코드 생성 일시 |

### 1.21 agent_node_logs (에이전트 노드 단위 로그)

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | 노드 로그 고유 식별자 |
| run_id | UUID | FK → agent_run_logs.id CASCADE | 소속 턴 실행 로그 |
| node_name | VARCHAR(100) | NOT NULL | 노드 이름 (router/chitchat/rag/stats) |
| sequence | INTEGER | NOT NULL | 노드 실행 순서 |
| status | VARCHAR(20) | NOT NULL | SUCCESS / FAILED (기본: SUCCESS) |
| model_name | VARCHAR(100) | NULL | 노드에서 사용한 LLM 모델명 |
| started_at | TIMESTAMP | NULL | 노드 실행 시작 |
| completed_at | TIMESTAMP | NULL | 노드 실행 완료 |
| latency_ms | INTEGER | NULL | 노드 처리 시간 (ms) |
| tokens_in | INTEGER | NULL | 입력 토큰 수 |
| tokens_out | INTEGER | NULL | 출력 토큰 수 |
| cost_usd | NUMERIC(12,8) | NULL | 노드 API 비용 (USD) |
| error_code | VARCHAR(100) | NULL | 오류 코드 |
| error_message | TEXT | NULL | 오류 메시지 |
| metadata | JSONB | NULL | 노드별 추가 메타데이터 |
| created_at | TIMESTAMP | NOT NULL | 레코드 생성 일시 |

### 1.22 agent_cta_logs (에이전트 CTA 클릭 기록)

> **설계 의도**: BizMong 응답 후 제시된 CTA 버튼(진단 바로가기·정책 상세 등)의 클릭 전환을 추적한다.

| 컬럼 | 타입 | 제약 | 설명 |
|:---|:---|:---|:---|
| id | UUID | PK | CTA 로그 고유 식별자 |
| run_id | UUID | FK → agent_run_logs.id SET NULL, NULL | 소속 턴 실행 로그 |
| room_id | UUID | FK → chat_rooms.id CASCADE | 소속 대화방 |
| user_id | UUID | FK → users.id CASCADE | 클릭 사용자 |
| business_id | UUID | FK → businesses.id CASCADE | 사업장 |
| assistant_message_log_id | UUID | FK → chat_logs.id SET NULL, NULL | 응답 메시지 로그 |
| cta_type | VARCHAR(50) | NOT NULL | CTA 유형 (DIAGNOSIS / POLICY_DETAIL 등) |
| target_path | VARCHAR(255) | NOT NULL | 이동 대상 경로 |
| ref_policy_id | UUID | FK → policies.id SET NULL, NULL | 연관 정책 ID |
| metadata | JSONB | NULL | 추가 컨텍스트 데이터 |
| created_at | TIMESTAMP | NOT NULL | 클릭 일시 |

---

## 1-A. 테이블 관계도 (ER 요약)

```
users (1) ─────────────── (N) user_tokens
users (1) ─────────────── (N) businesses
users (1) ─────────────── (N) notifications
users (1) ─────────────── (N) lead_requests
users (1) ─────────────── (N) chat_rooms
users (1) ─────────────── (N) chat_logs
users (1) ─────────────── (N) agent_run_logs
users (1) ─────────────── (N) agent_cta_logs

businesses (1) ─────────── (N) business_financial_snapshots
businesses (1) ─────────── (N) documents
businesses (1) ─────────── (N) applications
businesses (1) ─────────── (N) policy_bookmarks
businesses (1) ─────────── (N) match_logs
businesses (1) ─────────── (N) simulation_logs
businesses (1) ─────────── (N) chat_rooms
businesses (1) ─────────── (N) lead_requests
businesses (1) ─────────── (N) notifications
businesses (1) ─────────── (N) agent_run_logs
businesses (1) ─────────── (N) agent_cta_logs

policies (1) ──────────── (N) policy_chunks        [CASCADE DELETE]
policies (1) ──────────── (N) policy_bookmarks     [CASCADE DELETE]
policies (1) ──────────── (N) applications
policies (1) ──────────── (N) match_logs
policies (1) ──────────── (N) agent_cta_logs       [SET NULL]

chat_rooms (1) ──────────── (N) chat_logs
chat_rooms (1) ──────────── (N) agent_run_logs
chat_rooms (1) ──────────── (N) agent_cta_logs

agent_run_logs (1) ──────── (N) agent_node_logs    [CASCADE DELETE]
agent_run_logs (1) ──────── (N) agent_cta_logs     [SET NULL]

admins (1) ──────────────── (N) admin_audit_logs
admins (1) ──────────────── (N) correction_notes   [SET NULL]

chat_logs (1) ───────────── (N) correction_notes   [CASCADE DELETE]

[Unique Constraints]
  business_financial_snapshots: (business_id, snapshot_year)
  policy_bookmarks: (business_id, policy_id)
```

---

## 2. API 엔드포인트 전체 목록

### 2.1 인증 (Auth)

| Method | Endpoint | 설명 | 인증 필요 |
|:---|:---|:---|:---|
| POST | `/api/v1/auth/social-login` | 소셜 로그인 (카카오/네이버) | 없음 |
| POST | `/api/v1/auth/refresh` | Access Token 갱신 | Refresh Cookie |
| POST | `/api/v1/auth/logout` | 로그아웃 (Refresh Token 무효화) | Bearer |
| DELETE | `/api/v1/auth/withdraw` | 회원 탈퇴 (Soft Delete) | Bearer |

### 2.2 사용자 (Users)

| Method | Endpoint | 설명 | 인증 필요 |
|:---|:---|:---|:---|
| GET | `/api/v1/users/me` | 내 프로필 조회 | Bearer |
| PATCH | `/api/v1/users/profile` | 추가 프로필 설정 (군필·관심분야·기술스택) | Bearer |
| DELETE | `/api/v1/users/withdraw` | 회원 탈퇴 (Soft Delete) | Bearer |

### 2.3 사업장 (Business) — `business.md` 참조

| Method | Endpoint | 설명 | 가드 |
|:---|:---|:---|:---|
| POST | `/api/v1/onboarding/verify-biz` | 사업자번호 진위 확인 (국세청 API 연동, 현재 Mock) | CurrentUser |
| POST | `/api/v1/onboarding/register` | 온보딩 사업장 최초 등록 | CurrentUser |
| GET | `/api/v1/businesses/me` | 사업장 정보 조회 | CurrentUser |
| POST | `/api/v1/businesses/validate` | 입력값 이상치 검증 | CurrentUser |
| PATCH | `/api/v1/businesses/me` | 사업장 정보 수정 | ActiveBusiness |
| POST | `/api/v1/businesses/finance` | 재무 스냅샷 등록 | ActiveBusiness |
| GET | `/api/v1/businesses/finance/history` | 재무 이력 조회 | ActiveBusiness |
| PATCH | `/api/v1/businesses/finance/{year}` | 재무 수정 | ActiveBusiness |
| DELETE | `/api/v1/businesses/finance/{year}` | 재무 삭제 (Soft Delete) | ActiveBusiness |
| POST | `/api/v1/documents` | 서류 업로드 | ActiveBusiness |
| GET | `/api/v1/documents` | 서류 목록 조회 | ActiveBusiness |
| GET | `/api/v1/documents/{document_id}` | 서류 상세 조회 | ActiveBusiness |
| DELETE | `/api/v1/documents/{document_id}` | 서류 파기 (Soft Delete) | ActiveBusiness |

### 2.4 채팅 / BizMong 에이전트 (Chat) — `chat.md` 참조

| Method | Endpoint | 설명 | 비고 |
|:---|:---|:---|:---|
| POST | `/api/v1/chats/sessions` | AI 상담 세션 생성 | - |
| GET | `/api/v1/chats/sessions` | 세션 목록 조회 | - |
| POST | `/api/v1/chats/sessions/{id}/messages` | 일반 메시지 전송 (동기) | - |
| GET | `/api/v1/chats/sessions/{id}/messages` | 대화 내역 조회 | - |
| PATCH | `/api/v1/chats/sessions/{id}/summary` | 세션 제목 자동 요약 | GPT |
| DELETE | `/api/v1/chats/sessions/{id}` | 세션 삭제 (Soft Delete) | - |
| **POST** | **`/api/v1/chats/sessions/{id}/agent-message`** | **BizMong 에이전트 (동기)** | **핵심** |
| POST | `/api/v1/chats/sessions/{id}/stream` | BizMong 에이전트 (SSE 스트리밍) | 핵심 |
| POST | `/api/v1/chats/sessions/{id}/cta-events` | CTA 버튼 클릭 이벤트 기록 | - |

### 2.5 정책 (Policies) — `policies.md` 참조

| Method | Endpoint | 설명 |
|:---|:---|:---|
| GET | `/api/v1/policies` | 정책 목록 조회 (필터/검색) |
| GET | `/api/v1/policies/{id}` | 정책 상세 조회 |
| POST | `/api/v1/policies/{id}/bookmark` | 정책 북마크 토글 |
| GET | `/api/v1/policies/bookmarks` | 북마크한 정책 목록 |

### 2.6 비즈-픽 (Biz-Pick) — `biz_pick.md` 참조

| Method | Endpoint | 설명 |
|:---|:---|:---|
| GET | `/api/v1/biz-picks` | 큐레이션 카드 뉴스 목록 |
| GET | `/api/v1/biz-picks/{id}` | 카드 뉴스 상세 |

### 2.7 알림 (Notification) — `notification.md` 참조

| Method | Endpoint | 설명 |
|:---|:---|:---|
| GET | `/api/v1/notifications` | 알림 목록 조회 |
| PATCH | `/api/v1/notifications/{id}/read` | 알림 읽음 처리 |
| GET | `/api/v1/notifications/settings` | 알림 설정 조회 |
| PATCH | `/api/v1/notifications/settings` | 알림 설정 변경 |

### 2.8 관리자 (Admin)

모든 엔드포인트는 AdminAuth 가드 적용.

**정책 관리**

| Method | Endpoint | 설명 |
|:---|:---|:---|
| POST | `/api/v1/admin/login` | 관리자 토큰 발급 |
| POST | `/api/v1/admin/policies` | 정책 수동 생성 |
| PATCH | `/api/v1/admin/policies/{id}` | 정책 수동 수정 |
| POST | `/api/v1/admin/policies/sync/bootstrap` | 과거 정책 대량 적재 (백그라운드) |
| POST | `/api/v1/admin/policies/sync/daily` | 일일 최신 정책 동기화 (백그라운드) |
| POST | `/api/v1/admin/policies/sync/run` | 수집 범위 직접 지정 실행 (백그라운드) |
| POST | `/api/v1/admin/policies/sync/full` | 전수 수집 — totalCount 기반 (백그라운드) |
| POST | `/api/v1/admin/policies/{id}/embed` | 특정 정책 단건 재벡터화 |
| POST | `/api/v1/admin/policies/embed/all` | 미임베딩 정책 일괄 벡터화 |

**콘텐츠 관리 (Biz-Pick)**

| Method | Endpoint | 설명 |
|:---|:---|:---|
| POST | `/api/v1/admin/contents` | 콘텐츠 게시 |
| GET | `/api/v1/admin/contents` | 콘텐츠 목록 |
| GET | `/api/v1/admin/contents/{id}` | 콘텐츠 상세 |
| PATCH | `/api/v1/admin/contents/{id}` | 콘텐츠 수정 |
| DELETE | `/api/v1/admin/contents/{id}` | 콘텐츠 삭제 |

**모니터링**

| Method | Endpoint | 설명 |
|:---|:---|:---|
| GET | `/api/v1/admin/stats/dashboard` | 대시보드 통계 |
| GET | `/api/v1/admin/monitoring/health` | 시스템 헬스 체크 |
| GET | `/api/v1/admin/monitoring/latency` | 응답 지연 통계 (`?range=24h`) |
| GET | `/api/v1/admin/monitoring/cost` | API 비용 통계 (`?date=YYYY-MM-DD`) |
| GET | `/api/v1/admin/monitoring/agent-overview` | 에이전트 전체 실행 현황 |
| GET | `/api/v1/admin/monitoring/agent-nodes` | 노드 단위 실행 현황 |
| GET | `/api/v1/admin/monitoring/agent-runs` | 에이전트 실행 이력 목록 |
| GET | `/api/v1/admin/monitoring/agent-runs/{id}` | 에이전트 실행 상세 |

**채팅·피드백**

| Method | Endpoint | 설명 |
|:---|:---|:---|
| GET | `/api/v1/admin/chats/logs` | 대화 로그 조회 (`?user_id=`) |
| GET | `/api/v1/admin/feedback` | 싫어요 피드백 목록 |
| GET | `/api/v1/admin/feedback/{id}/context` | 피드백 문맥 조회 |
| POST | `/api/v1/admin/feedback/{id}/correction` | 정정 노트 작성 |
| GET | `/api/v1/admin/corrections` | 정정 노트 목록 |

**사용자 관리·인사이트**

| Method | Endpoint | 설명 |
|:---|:---|:---|
| GET | `/api/v1/admin/users` | 사용자 목록 |
| PATCH | `/api/v1/admin/users/{id}/active` | 사용자 활성/비활성 토글 |
| GET | `/api/v1/admin/insights/unmet-demand` | 미충족 수요 분석 |
| GET | `/api/v1/admin/insights/conversion` | CTA 전환 통계 |
| GET | `/api/v1/admin/audit-logs` | 관리자 작업 감사 로그 |

**배치·디버그**

| Method | Endpoint | 설명 |
|:---|:---|:---|
| GET | `/api/v1/admin/batch/status` | 배치 작업 현황 |
| GET | `/api/v1/admin/batch/logs/{id}` | 배치 작업 상세 |
| GET | `/api/v1/admin/diagnose-files` | 첨부파일 형식 분포 분석 |
| POST | `/api/v1/admin/test-sync-one` | 랜덤 공고 1건 파이프라인 검증 |
| GET | `/api/v1/admin/debug-output` | 파이프라인 테스트 이력 목록 |
| GET | `/api/v1/admin/debug-output/{origin_id}` | 특정 공고 파이프라인 단계별 파일 |

### 2.9 정밀진단 (Diagnoses)

| Method | Endpoint | 설명 | 가드 |
|:---|:---|:---|:---|
| GET | `/api/v1/diagnoses/prepare` | 진단 가능 여부 확인 및 부족 항목 안내 | ActiveBusiness |
| POST | `/api/v1/diagnoses` | 진단 실행 및 결과 저장 | ActiveBusiness |
| GET | `/api/v1/diagnoses/{id}` | 진단 상세 조회 | ActiveBusiness |
| GET | `/api/v1/diagnoses` | 진단 이력 목록 | ActiveBusiness |
| DELETE | `/api/v1/diagnoses/{id}` | 진단 기록 삭제 | ActiveBusiness |

### 2.10 시뮬레이션 (Simulations)

| Method | Endpoint | 설명 | 가드 |
|:---|:---|:---|:---|
| POST | `/api/v1/simulations` | 가상 조건 시뮬레이션 실행 | ActiveBusiness |
| GET | `/api/v1/simulations/history` | 시뮬레이션 이력 목록 | ActiveBusiness |

---

## 3. BizMong 에이전트 응답 상세 스키마

`POST /api/v1/chats/sessions/{session_id}/agent-message` 의 `data` 필드 전체 타입 정의.  
프론트엔드 AI는 이 섹션을 기반으로 TypeScript 타입을 즉시 정의할 수 있습니다.

### 3.1 AgentMessageResponse (최상위)

> BizMong LangGraph 에이전트 응답. 정밀진단·시뮬레이션은 별도 REST API(`/diagnoses`, `/simulations`)를 사용한다.

```typescript
interface AgentMessageResponse {
  session_id: string;       // UUID
  message_id: string;       // UUID (ChatLog.id)
  role: "assistant";
  content: string;          // 사용자에게 보여줄 한국어 응답 텍스트
  agent_type: "chitchat" | "general_qa" | "rag" | "stats";
  stats_insight: StatsInsight | null;   // agent_type === "stats" 시
  rag_results: RagResult[] | null;      // agent_type === "rag" 시
  created_at: string;       // ISO 8601
}
```

### 3.2 StatsInsight

```typescript
interface StatsInsight {
  peer_count: number;       // 비교 대상 동종 사업장 수
  ksic_code: string | null; // 비교에 사용된 업종 코드
  avg_revenue: number | null;    // 동종업계 평균 연매출 (원)
  avg_employees: number | null;  // 동종업계 평균 직원 수
  avg_debt_ratio: number | null; // 동종업계 평균 부채비율 (%)
  percentile: {
    revenue_percentile: number | null;   // 매출 상위 % (10/25/50/75)
    employee_percentile: number | null;  // 직원수 상위 %
  };
  market_trend: string;     // 시장 동향 텍스트
  peer_comparison: string;  // 동종업계 대비 현재 위치 텍스트
}
```

### 3.3 RagResult

```typescript
interface RagResult {
  policy_id: string;        // UUID
  title: string;            // 공고명
  agency_name: string;      // 주관 기관
  ai_summary: string;       // GPT 생성 요약
  support_amount_desc: string; // 지원금액 설명
  max_support: number | null;  // 최대 지원금액 (원)
  region: string;           // 지원 지역
  end_date: string;         // 마감일
  apply_url: string;        // 신청 URL
  rrf_score: number;        // RRF 융합 점수 (랭킹 참고용)
  relevant_chunk: string;   // 검색에 매칭된 청크 텍스트 (출처 표시용)
}
```

### 3.4 DiagnosisResponse (`POST /api/v1/diagnoses`)

```typescript
interface DiagnosisResponse {
  id: string;               // UUID (진단 기록 ID)
  total_score: number;      // 사업 건강도 총점 (0~100, 소수점 1자리)
  grade: string;            // "EXCELLENT" | "GOOD" | "NORMAL" | "RISK"
  traffic_light: string;    // "GREEN" | "YELLOW" | "RED"
  scores: {
    financial_health: number;      // 재무건전성 (0~100)
    growth_potential: number;      // 성장잠재력 (0~100)
    operational_stability: number; // 운영안정성 (0~100)
    risk_management: number;       // 리스크관리 (0~100)
  };
  summary: string;          // 1~2문장 진단 요약
  strengths: string[];      // 강점 목록 (최대 4개)
  risk_signals: string[];   // 리스크 신호 목록 (최대 4개)
  action_items: string[];   // 개선 액션 목록 (최대 4개)
  created_at: string;       // ISO 8601
}
```

### 3.5 SimulationResponse (`POST /api/v1/simulations`)

```typescript
interface SimulationResponse {
  base_rate: number;        // 현재 진단 점수
  simulated_rate: number;   // 가상 조건 적용 후 점수
  gain_factors: string[];   // 점수 변화 원인 설명 (최대 6개)
}
```

---

## 4. Request 스키마 (주요 엔드포인트)

### 4.1 에이전트 메시지 요청

```typescript
// POST /api/v1/chats/sessions/{id}/agent-message
interface SendMessageRequest {
  message: string;  // 사용자 자연어 입력
}
```

### 4.2 사업장 온보딩 등록

```typescript
// POST /api/v1/onboarding/register
interface OnboardingRegisterRequest {
  biz_name: string;
  biz_no?: string;
  representative_name?: string;
  ksic_code?: string;
  region_sido?: string;
  region_sigungu?: string;
  establishment_date?: string;  // "YYYY-MM-DD"
  has_patent?: boolean;
  is_female_ent?: boolean;
  is_ventured?: boolean;
  employee_count?: number;
}
```

### 4.3 재무 스냅샷 등록

```typescript
// POST /api/v1/businesses/finance
interface FinanceCreateRequest {
  snapshot_year: number;
  snapshot_period: string;       // "1Q" | "2Q" | "3Q" | "4Q" | "연간"
  term_type: string;             // "연간" | "분기"
  annual_revenue?: number;       // 연매출 (원)
  operating_profit?: number;     // 영업이익 (원)
  net_income?: number;           // 당기순이익 (원)
  total_debt?: number;           // 총 부채 (원)
  capital?: number;              // 자본금 (원)
  employee_count?: number;       // 직원 수
  tax_arrears_yn?: boolean;      // 세금 체납 여부
}
```
