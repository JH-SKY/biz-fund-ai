## 📊 [비즈업] 서비스 데이터베이스 상세 정의서

### 0. 공통 규칙

- **ID**: Primary Key (UUID 또는 BIGINT 추천)
- **Time**: TIMESTAMP (Default: CURRENT_TIMESTAMP)
- **Soft Delete**: `is_active` 또는 `status` 컬럼을 통한 논리 삭제 적용

---

### 1. users (사용자 계정)

- **존재 이유**: 서비스 이용자 식별, 소셜 로그인 연동 및 개인화 매칭(비전공/군필 등)을 위한 기초 데이터 관리
- **관계성**: 1:N (user_tokens, businesses, chat_logs, chat_rooms, notifications, lead_requests)
- **상세 명세**:

| 구분     | 컬럼명              | 역할               | 타입/옵션       | 출처        | 비고                                      |
| :------- | :------------------ | :----------------- | :-------------- | :---------- | :---------------------------------------- |
| **PK**   | id                  | 사용자 고유 식별자 | UUID, N         | 시스템      | 기본값: uuid4                             |
| **일반** | email               | 이메일 주소        | VARCHAR(255), N | 소셜 연동   | Unique Index 적용                         |
| **일반** | name                | 실명               | VARCHAR(50), N  | 소셜 연동   | -                                         |
| **일반** | phone               | 전화번호           | VARCHAR(20), Y  | 사용자 입력 | -                                         |
| **일반** | nickname            | 활동명             | VARCHAR(50), Y  | 사용자 입력 | -                                         |
| **일반** | status              | 계정 상태          | VARCHAR(20), N  | 시스템      | 기본값: 'active'                          |
| **일반** | social_id           | 소셜 고유 고정 ID  | VARCHAR(255), N | 소셜 연동   | -                                         |
| **일반** | social_provider     | 소셜 제공자        | ENUM, N         | 소셜 연동   | KAKAO, NAVER (SocialProvider 클래스 연동) |
| **일반** | profile_image_url   | 프로필 사진 URL    | TEXT, Y         | 소셜 연동   | -                                         |
| **일반** | is_active           | 활성 계정 여부     | BOOLEAN, N      | 시스템      | 기본값: True (Soft Delete 스위치)         |
| **일반** | deleted_at          | 탈퇴 시각          | TIMESTAMP, Y    | 시스템      | 5년 후 물리 삭제를 위한 기록용 (UTC)      |
| **일반** | marketing_agreed_at | 마케팅 동의 일시   | TIMESTAMP, Y    | 시스템      | -                                         |
| **일반** | interest_sectors    | 관심 업종/분야     | JSONB, Y        | 사용자 입력 | 관심 업종/분야 리스트 (JSONB array)       |
| **일반** | military_service    | 군필 여부          | VARCHAR(30), Y  | 사용자 입력 | COMPLETED, EXEMPTED, IN_PROGRESS, NA 등   |
| **일반** | is_non_major        | 비전공 창업자 여부 | BOOLEAN, Y      | 사용자 입력 | 전공자/비전공자 구분 필터                 |
| **일반** | tech_stack          | 기술 스택          | JSONB, Y        | 사용자 입력 | 기술 스택 리스트 (JSONB array)            |
| **일반** | created_at          | 가입 일시          | TIMESTAMP, N    | 시스템      | Server Default: CURRENT_TIMESTAMP         |

---

### 1-2. user_tokens (인증 토큰 관리) - NEW

- **존재 이유**: 보안을 위한 Refresh Token 저장 및 로그아웃/탈퇴 시 토큰 무효화 처리
- **관계성**: N:1 (users)
- **상세 명세**:

| 구분     | 컬럼명     | 역할               | 타입/옵션    | 출처   | 비고                                                                |
| :------- | :--------- | :----------------- | :----------- | :----- | :------------------------------------------------------------------ |
| **PK**   | id         | 토큰 레코드 식별자 | UUID, N      | 시스템 | 기본값: uuid4                                                       |
| **FK**   | user_id    | 소유 사용자 ID     | UUID, N      | 시스템 | users.id 외래키                                                     |
| **일반** | token      | Refresh Token 값   | TEXT, N      | 시스템 | Unique Index 적용, opaque Refresh Token 원본값                      |
| **일반** | expires_at | 토큰 만료 일시     | TIMESTAMP, N | 시스템 | -                                                                   |
| **일반** | is_revoked | 무효화 여부        | BOOLEAN, N   | 시스템 | 기본값: False, 로그아웃·탈퇴 시 무효화 여부 (Server Default: false) |
| **일반** | created_at | 발급 일시          | TIMESTAMP, N | 시스템 | Server Default: CURRENT_TIMESTAMP                                   |

---

### 2. businesses (사업장 기본 정보)

- **존재 이유**: 사장님의 업장 정보 관리 (1유저 다사업장 대응) 및 매칭 필터링의 핵심
- **관계성**:
  - **N:1**: users (사용자 계정)
  - **1:N**: financial_snapshots, match_logs, applications, documents, lead_requests, simulation_logs, chat_rooms, notifications, policy_bookmarks
- **상세 명세**:

| 구분     | 컬럼명              | 역할                 | 타입/옵션          | 출처          | 비고                                                     |
| :------- | :------------------ | :------------------- | :----------------- | :------------ | :------------------------------------------------------- |
| **PK**   | id                  | 사업장 식별자        | UUID, N            | 시스템        | 특정 사업장을 구분하는 고유 식별 키                      |
| **FK**   | user_id             | 소유주 ID            | UUID, N            | 시스템        | 어떤 사용자가 소유한 사업장인지 연결하는 연결 고리       |
| **일반** | biz_name            | 상호명               | VARCHAR(100), N    | 사용자 입력   | 사장님의 업체 이름으로 서비스 전반에 노출됨              |
| **일반** | representative_name | 대표자명             | VARCHAR(50), Y     | 사용자 입력   | 정책 자금 신청 서류 작성 시 필수 기입 정보               |
| **일반** | biz_no              | 사업자등록번호       | VARCHAR(12), Y     | **OCR/입력**  | 기업 실체 확인 및 중복 등록을 방지하는 핵심 키           |
| **일반** | ksic_code           | 표준산업분류코드     | VARCHAR(20), Y     | **자동 추출** | 산업 분류에 따른 정책 가용성 판단의 필수 기준            |
| **일반** | sector_code         | 업종 코드            | VARCHAR(20), Y     | **자동 추출** | 세부 업종별 맞춤형 정책 필터링을 위한 보조 코드          |
| **일반** | region_sido         | 시/도 (표시용)       | VARCHAR(50), Y     | **자동 추출** | 광역 지자체 단위의 정책 자금 매칭 기준                   |
| **일반** | region_sigungu      | 시/군/구 (표시용)    | VARCHAR(50), Y     | **자동 추출** | 시/군/구 단위의 세부 지역 자금 매칭 기준                 |
| **일반** | region_code         | 법정동 코드 (계산용) | VARCHAR(10), Y     | **자동 추출** | 시스템 내부적으로 지역을 정확하게 필터링하기 위한 코드   |
| **일반** | establishment_date  | 설립 일자            | DATE, Y            | **OCR/입력**  | 업력(3년/7년 이내 등)에 따른 지원 자격 판단 기준         |
| **일반** | has_patent          | 특허 보유 여부       | BOOLEAN, N         | 사용자 입력   | 기술성 가산점 및 특허 관련 정책 매칭을 위한 지표         |
| **일반** | is_female_ent       | 여성 기업 여부       | BOOLEAN, N         | 사용자 입력   | 여성 기업 우대 정책 매칭을 위한 필수 필터값              |
| **일반** | is_ventured         | 벤처 기업 여부       | BOOLEAN, N         | 사용자 입력   | 벤처 인증 기업 대상 고액 융자/지원금 매칭 기준           |
| **일반** | is_active           | 업장 활성 여부       | BOOLEAN, N         | 시스템        | 폐업 여부나 삭제 처리를 관리하는 물리적 스위치           |
| **일반** | profile_score       | 정보 입력 완성도     | INTEGER, DEFAULT 0 | 시스템        | 0~100점 사이의 점수로, 맞춤 정책 추천 정밀도의 기준이 됨 |
| **일반** | created_at          | 등록 일시            | TIMESTAMP, N       | 시스템        | 사업장 정보가 시스템에 최초 등록된 시각                  |

---

### 3. business_financial_snapshots (재무 상태 스냅샷)

- **존재 이유**: 사업장의 연도별/분기별 재무 상태를 기록하여 정책자금 지원 자격(매출, 부채비율, 영업이익 등)을 정밀하게 진단하고 AI 분석 리포트를 생성하기 위한 기초 자료로 활용함
- **관계성**: N:1 (businesses)
- **상세 명세**:

| 구분     | 컬럼명             | 역할                    | 타입/옵션       | 출처        | 비고                                            |
| :------- | :----------------- | :---------------------- | :-------------- | :---------- | :---------------------------------------------- |
| **PK**   | id                 | 재무 스냅샷 고유 식별자 | UUID, N         | 시스템      | 기본값: uuid4                                   |
| **FK**   | business_id        | 대상 사업장 ID          | UUID, N         | 시스템      | businesses.id 외래키 (UniqueConstraint 포함)    |
| **일반** | snapshot_year      | 재무제표 기준 연도      | INTEGER, N      | 사용자 입력 | business_id와 함께 복합 유니크 제약 적용        |
| **일반** | snapshot_period    | 기준 시기               | VARCHAR(10), N  | 사용자 입력 | 예: 1Q, 2Q, 상반기, 하반기 등                   |
| **일반** | term_type          | 공시 주기               | VARCHAR(10), N  | 사용자 입력 | 예: 연간, 분기 등                               |
| **일반** | annual_revenue     | 연매출액                | BIGINT, Y       | 사용자/OCR  | 단위: 원                                        |
| **일반** | operating_profit   | 영업이익                | BIGINT, Y       | 사용자/OCR  | 단위: 원 (음수 가능)                            |
| **일반** | net_income         | 당기순이익              | BIGINT, Y       | 사용자/OCR  | 단위: 원 (음수 가능)                            |
| **일반** | total_debt         | 총 부채액               | BIGINT, Y       | 사용자/OCR  | 단위: 원                                        |
| **일반** | capital            | 자본금                  | BIGINT, Y       | 사용자/OCR  | 단위: 원                                        |
| **일반** | debt_ratio         | 부채 비율               | NUMERIC(5,2), Y | 시스템      | 자동 계산 결과 (%)                              |
| **일반** | employee_count     | 직원 수                 | INTEGER, Y      | 사용자 입력 | -                                               |
| **일반** | tax_arrears_yn     | 세금 체납 여부          | BOOLEAN, N      | 사용자 입력 | 기본값: False (Server Default: false)           |
| **일반** | ai_analysis_report | AI 진단 결과            | JSONB, Y        | 시스템      | 비즈몽 재무 진단 상세 데이터 (JSON)             |
| **일반** | ocr_status         | 분석 진행 상태          | VARCHAR(20), N  | 시스템      | 대기, 완료 등 진행 상태 관리                    |
| **일반** | is_verified        | 서류 검증 여부          | BOOLEAN, N      | 시스템      | 기본값: False (공식 서류 대조 완료 여부)        |
| **일반** | is_active          | 활성 여부               | BOOLEAN, N      | 시스템      | 기본값: True (Soft Delete 적용, 감사 목적 보존) |
| **일반** | created_at         | 스냅샷 생성 일시        | TIMESTAMP, N    | 시스템      | Server Default: CURRENT_TIMESTAMP               |

- **데이터 무결성 제약 추가**: (business_id, snapshot_year) UNIQUE 제약 조건 적용

---

### 4. policies (정책 공고 데이터)

- **존재 이유**: 정부 및 지자체에서 공고하는 정책자금 데이터를 통합 관리하며, RAG 기반 AI 분석(요약, 해설)과 사업장 매칭 로직을 위한 원천 데이터를 제공함
- **관계성**: 1:N (match_logs, applications, chat_logs, bookmarks)
- **상세 명세**:

| 구분     | 컬럼명              | 역할               | 타입/옵션       | 출처      | 비고                                          |
| :------- | :------------------ | :----------------- | :-------------- | :-------- | :-------------------------------------------- |
| **PK**   | id                  | 정책 고유 식별자   | UUID, N         | 시스템    | 기본값: uuid4                                 |
| **일반** | title               | 공고 제목          | VARCHAR(255), N | 원문      | 검색 최적화 인덱스 적용                       |
| **일반** | agency_name         | 공고 기관명        | VARCHAR(100), N | 원문      | 주관 부처 검색용 인덱스 적용                  |
| **일반** | category            | 정책 카테고리      | VARCHAR(50), Y  | 시스템/AI | 금융, 바우처, R&D 등 분류                     |
| **일반** | support_type        | 지원 유형          | VARCHAR(50), Y  | 시스템/AI | 융자, 출연금, 보조금 등 구분                  |
| **일반** | region              | 지원 대상 지역     | VARCHAR(100), Y | 원문      | 전국, 서울 등 지역 필터용 인덱스              |
| **일반** | ai_summary          | 리스트용 요약      | TEXT, Y         | AI 가공   | AI가 생성한 3줄 요약 데이터                   |
| **일반** | ai_full_explanation | 상세용 쉬운 풀이   | TEXT, Y         | AI 가공   | 비전공자를 위한 AI 해설 텍스트                |
| **일반** | ai_metadata         | AI 추천 메타데이터 | JSONB, Y        | AI 가공   | 벡터 DB 참조 ID 및 추천 가중치 저장           |
| **일반** | content_raw         | 공고 원문 전체     | TEXT, N         | 원문      | RAG 엔진 분석용 원천 데이터                   |
| **일반** | max_support         | 최대 지원 금액     | BIGINT, Y       | 원문/AI   | 원 단위, 통계 및 정렬용 수치                  |
| **일반** | support_amount_desc | 지원 금액 텍스트   | VARCHAR(100), Y | 원문      | 사용자 노출용 문자열                          |
| **일반** | required_documents  | 신청 필수 서류     | JSONB, Y        | AI 가공   | AI가 원문에서 추출한 서류 리스트              |
| **일반** | start_date          | 접수 시작일        | DATE, Y         | 원문      | -                                             |
| **일반** | end_date            | 접수 종료일        | DATE, Y         | 원문      | 하위 호환성 유지용                            |
| **일반** | closed_at           | 최종 마감일        | DATE, N         | 시스템    | 기본값: 9999-12-31 (상시접수 대응), 정렬 핵심 |
| **일반** | status              | 공고 상태          | ENUM, N         | 시스템    | 예정, 접수중, 마감 등 (PolicyStatus 연동)     |
| **일반** | apply_url           | 원문 신청 URL      | TEXT, Y         | 원문      | 외부 신청 페이지 링크                         |
| **일반** | target_logic        | 매칭 필터 규칙     | JSONB, Y        | AI 가공   | 사업장 매칭을 위한 AI 판단 기준점             |
| **일반** | bonus_logic         | 가산점 계산 규칙   | JSONB, Y        | AI 가공   | 우대 사항 점수화 로직                         |
| **일반** | view_count          | 상세 조회 수       | INTEGER, N      | 시스템    | 기본값: 0, 인기 정책 산출용                   |
| **일반** | is_active           | 활성 여부          | BOOLEAN, N      | 시스템    | 기본값: True (Soft Delete 적용)               |
| **일반** | created_at          | 데이터 생성 시점   | TIMESTAMP, N    | 시스템    | Server Default: CURRENT_TIMESTAMP             |

---

### 5. match_logs (매칭 결과 기록)

- **존재 이유**: 사업장 데이터와 정책 간의 매칭 점수 및 근거 저장 (속도/알림용)
- **관계성**: N:1 (businesses, policies)
- **상세 명세**:

| 구분     | 컬럼명       | 역할                  | 타입/옵션      | 출처   | 비고                                       |
| :------- | :----------- | :-------------------- | :------------- | :----- | :----------------------------------------- |
| **PK**   | id           | 매칭 결과 고유 식별자 | UUID, N        | 시스템 | 기본값: uuid4                              |
| **FK**   | business_id  | 매칭 대상 사업장 ID   | UUID, N        | 시스템 | businesses.id 외래키                       |
| **FK**   | policy_id    | 매칭 대상 정책 ID     | UUID, N        | 시스템 | policies.id 외래키                         |
| **일반** | match_score  | 매칭 점수             | INTEGER, N     | 시스템 | 0~100 사이의 적합도 점수                   |
| **일반** | match_status | 신호등 상태           | VARCHAR(10), N | 시스템 | G(Green), Y(Yellow), R(Red) 등 가독성 지표 |
| **일반** | reason_json  | 점수 산정 근거        | JSONB, Y       | 시스템 | 매칭/불일치 사유에 대한 상세 데이터 (JSON) |
| **일반** | created_at   | 매칭 판정 일시        | TIMESTAMP, N   | 시스템 | Server Default: CURRENT_TIMESTAMP          |

---

### 6. chat_logs (비즈몽 대화 기록)

- **존재 이유**: 대화방 내에서 발생하는 개별 메시지를 기록하며, RAG(검색 증강 생성)에 사용된 참조 데이터와 LLM 추적(Tracing), 비용(Cost) 및 사용자 피드백을 상세히 관리함
- **관계성**: N:1 (users,chat_rooms, policies)
- **상세 명세**:

| 구분     | 컬럼명            | 역할               | 타입/옵션        | 출처        | 비고                                   |
| :------- | :---------------- | :----------------- | :--------------- | :---------- | :------------------------------------- |
| **PK**   | id                | 메시지 고유 식별자 | UUID, N          | 시스템      | 기본값: uuid4                          |
| **FK**   | user_id           | 대화 사용자 ID     | UUID, N          | 시스템      | users.id 외래키                        |
| **FK**   | ref_policy_id     | 참조 정책 ID       | UUID, Y          | 시스템      | policies.id 외래키 (일반 상담 시 NULL) |
| **FK**   | room_id           | 소속 대화방 ID     | UUID, N          | 시스템      | chat_rooms.id 외래키                   |
| **일반** | role              | 화자 구분          | VARCHAR(20), N   | 시스템      | user 또는 assistant                    |
| **일반** | content           | 메시지 본문        | TEXT, N          | 사용자/AI   | 실제 대화 내용                         |
| **일반** | context_type      | 발생 위치          | VARCHAR(20), Y   | 시스템      | 위젯, 특정 페이지 등 유입 경로         |
| **일반** | trace_id          | LLM 추적 ID        | VARCHAR(100), Y  | 시스템      | LangSmith 등 외부 모니터링 연동 ID     |
| **일반** | total_cost        | API 사용 비용      | NUMERIC(12,8), Y | 시스템      | 해당 메시지 생성에 소모된 USD 비용     |
| **일반** | referenced_chunks | RAG 참조 데이터    | JSONB, Y         | 시스템      | 답변 생성 시 참고한 문서 청크 (JSON)   |
| **일반** | is_disliked       | 싫어요 여부        | BOOLEAN, N       | 사용자 입력 | 기본값: False (Server Default: false)  |
| **일반** | feedback_code     | 피드백 코드        | VARCHAR(20), Y   | 사용자 입력 | 불만족 사유 분류 코드                  |
| **일반** | feedback_text     | 피드백 상세        | TEXT, Y          | 사용자 입력 | 사용자가 직접 작성한 피드백 내용       |
| **일반** | created_at        | 메시지 생성 일시   | TIMESTAMP, N     | 시스템      | Server Default: CURRENT_TIMESTAMP      |

---

### 7. applications (정책 신청 현황)

- **존재 이유**: 사용자가 관심을 보였거나 실제 신청 중인 공고 트래킹
- **관계성**: N:1 (businesses, policies)
- **상세 명세**:

| 구분     | 컬럼명      | 역할                  | 타입/옵션      | 출처          | 비고                                |
| :------- | :---------- | :-------------------- | :------------- | :------------ | :---------------------------------- |
| **PK**   | id          | 신청 기록 고유 식별자 | UUID, N        | 시스템        | 기본값: uuid4                       |
| **FK**   | business_id | 신청 사업장 ID        | UUID, N        | 시스템        | businesses.id 외래키                |
| **FK**   | policy_id   | 대상 정책 ID          | UUID, N        | 시스템        | policies.id 외래키                  |
| **일반** | status      | 신청 단계             | VARCHAR(20), N | 시스템/사용자 | 관심, 제출, 승인, 반려 등 상태 관리 |
| **일반** | applied_at  | 실제 신청 일시        | TIMESTAMP, Y   | 시스템        | 실제 '제출' 버튼을 누른 시점 기록   |
| **일반** | updated_at  | 상태 변경 일시        | TIMESTAMP, N   | 시스템        | Server Default: CURRENT_TIMESTAMP   |
| **일반** | memo        | 사용자 메모           | TEXT, Y        | 사용자 입력   | 신청 관련 특이사항 기록             |

---

### 8. documents (디지털 서류함)

- **존재 이유**: 사업자등록증 등 서류 파일 관리 및 OCR 연동
- **관계성**: N:1 (businesses)
- **상세 명세**:

| 구분     | 컬럼명      | 역할             | 타입/옵션      | 출처        | 비고                                          |
| :------- | :---------- | :--------------- | :------------- | :---------- | :-------------------------------------------- |
| **PK**   | id          | 서류 고유 식별자 | UUID, N        | 시스템      | 기본값: uuid4                                 |
| **FK**   | business_id | 소속 사업장 ID   | UUID, N        | 시스템      | businesses.id 외래키                          |
| **일반** | doc_type    | 서류 종류        | VARCHAR(50), N | 사용자 입력 | 예: 사업자등록증, 부가가치세과세표준증명 등   |
| **일반** | file_url    | 파일 저장 경로   | TEXT, N        | 시스템      | S3 등 외부 저장소 URL                         |
| **일반** | ocr_status  | OCR 분석 상태    | VARCHAR(20), N | 시스템      | PENDING(기본값), COMPLETED, FAILED            |
| **일반** | ocr_result  | OCR 추출 데이터  | JSONB, Y       | 시스템      | 비동기 분석 완료 시 추출된 원본 데이터 (JSON) |
| **일반** | is_active   | 활성 여부        | BOOLEAN, N     | 시스템      | 기본값: True (Soft Delete 적용, 법적 보존용)  |
| **일반** | issued_at   | 서류 발급 일자   | DATE, Y        | OCR/사용자  | 서류상의 공식 발급 날짜                       |
| **일반** | created_at  | 업로드 일시      | TIMESTAMP, N   | 시스템      | Server Default: CURRENT_TIMESTAMP             |

---

### 9. biz_picks (콘텐츠/이슈 관리)

- **존재 이유**: 정책 이슈, 꿀팁 등 정보성 콘텐츠 관리
- **관계성**: 독립 (JSON 내 policy_ids 참조)
- **상세 명세**:

| 구분     | 컬럼명        | 역할               | 타입/옵션       | 출처        | 비고                                                            |
| :------- | :------------ | :----------------- | :-------------- | :---------- | :-------------------------------------------------------------- |
| **PK**   | id            | 콘텐츠 고유 ID     | UUID, N         | 시스템      | 기본값: uuid4                                                   |
| **일반** | title         | 콘텐츠 제목        | VARCHAR(255), N | 관리자 입력 | -                                                               |
| **일반** | category      | 콘텐츠 카테고리    | VARCHAR(50), N  | 관리자 입력 | 세무, 정책자금 등 분류 (Index 적용)                             |
| **일반** | content_html  | HTML 본문          | TEXT, N         | 관리자 입력 | 관리자 도구에서 작성된 원본 HTML 데이터                         |
| **일반** | thumbnail_url | 썸네일 이미지 주소 | TEXT, Y         | 관리자 입력 | 콘텐츠 목록에 노출될 이미지 경로                                |
| **일반** | is_published  | 공개 여부          | BOOLEAN, N      | 관리자 설정 | 기본값: True (준비 중인 콘텐츠 숨김 처리, Server Default: true) |
| **일반** | view_count    | 조회수             | INTEGER, N      | 시스템      | 기본값: 0 (Server Default: 0)                                   |
| **일반** | like_count    | 좋아요 수          | INTEGER, N      | 시스템      | 기본값: 0 (인기 콘텐츠 정렬 기준, Server Default: 0)            |
| **일반** | created_at    | 발행 시점          | TIMESTAMP, N    | 시스템      | Server Default: CURRENT_TIMESTAMP                               |

---

### 10. notifications (알림 기록)

- **존재 이유**: 정책 매칭, 채팅 답변 등 서비스 내 주요 이벤트를 사용자에게 실시간/비동기로 안내하며, 읽음 상태 관리를 통해 앱 내 알림 센터 및 뱃지 UI의 기초 데이터로 활용함
- **관계성**: N:1 (users, businesses)
- **상세 명세**:

| 구분     | 컬럼명      | 역할             | 타입/옵션       | 출처        | 비고                                                  |
| :------- | :---------- | :--------------- | :-------------- | :---------- | :---------------------------------------------------- |
| **PK**   | id          | 알림 고유 식별자 | UUID, N         | 시스템      | 기본값: uuid4 (충돌 방지 우편물 번호)                 |
| **FK**   | user_id     | 수신 사용자 ID   | UUID, N         | 시스템      | users.id 외래키 (필수 수신인 주소)                    |
| **FK**   | business_id | 연관 사업장 ID   | UUID, Y         | 시스템      | businesses.id 외래키 (특정 업장 관련 시 기록)         |
| **일반** | type        | 알림 유형        | VARCHAR(20), N  | 시스템      | 예: POLICY_MATCH, CHAT_ANSWER (아이콘 구분용)         |
| **일반** | title       | 알림 제목        | VARCHAR(255), N | 시스템      | 기본값: '새로운 알림' (사용자 노출 요약 문구)         |
| **일반** | message     | 알림 본문        | TEXT, N         | 시스템      | 상세 안내 문구가 담기는 그릇                          |
| **일반** | is_read     | 읽음 여부        | BOOLEAN, N      | 사용자 입력 | 기본값: False (확인 도장 역할, Server Default: false) |
| **일반** | link_url    | 이동 URL         | TEXT, Y         | 시스템      | 클릭 시 특정 페이지로 안내하는 지름길                 |
| **일반** | created_at  | 알림 생성 일시   | TIMESTAMP, N    | 시스템      | Server Default: CURRENT_TIMESTAMP (Timezone 포함)     |

---

### 11. lead_requests (상담 리드/수익화)

- **존재 이유**: 로봇, 컨설팅 등 외부 파트너사와 사장님 연결 기록 관리
- **관계성**: N:1 (users, businesses)
- **상세 명세**:

| 구분     | 컬럼명      | 역할                  | 타입/옵션      | 출처          | 비고                                  |
| :------- | :---------- | :-------------------- | :------------- | :------------ | :------------------------------------ |
| **PK**   | id          | 리드 요청 고유 식별자 | UUID, N        | 시스템        | 기본값: uuid4                         |
| **FK**   | user_id     | 신청 사용자 ID        | UUID, N        | 시스템        | users.id 외래키                       |
| **FK**   | business_id | 대상 사업장 ID        | UUID, N        | 시스템        | businesses.id 외래키                  |
| **일반** | lead_type   | 상담 종류             | VARCHAR(50), N | 사용자 선택   | 로봇 도입, 세무 상담 등 파트너 유형   |
| **일반** | status      | 처리 상태             | VARCHAR(20), N | 시스템/관리자 | 신청, 검토, 연결완료 등 프로세스 상태 |
| **일반** | created_at  | 신청 일시             | TIMESTAMP, N   | 시스템        | Server Default: CURRENT_TIMESTAMP     |

---

### 12. simulation_logs (가산점 시뮬레이션)

- **존재 이유**: 사용자가 직접 가상 데이터를 넣어본 결과 기록 보존
- **관계성**: N:1 (businesses)
- **상세 명세**:

| 구분     | 컬럼명      | 역할                   | 타입/옵션      | 출처        | 비고                                             |
| :------- | :---------- | :--------------------- | :------------- | :---------- | :----------------------------------------------- |
| **PK**   | id          | 시뮬레이션 로그 식별자 | UUID, N        | 시스템      | 기본값: uuid4                                    |
| **FK**   | business_id | 기준 사업장 ID         | UUID, N        | 시스템      | businesses.id 외래키                             |
| **일반** | sim_type    | 시뮬레이션 종류        | VARCHAR(50), N | 시스템      | 가산점 시뮬레이션, ROI 예측 등 구분              |
| **일반** | input_data  | 사용자 입력 조건       | JSONB, N       | 사용자 입력 | 시뮬레이션을 위해 입력한 가상 환경 데이터 (JSON) |
| **일반** | output_data | 계산·예측 결과         | JSONB, N       | 시스템      | 산출된 시뮬레이션 결과값 (JSON)                  |
| **일반** | created_at  | 실행 일시              | TIMESTAMP, N   | 시스템      | Server Default: CURRENT_TIMESTAMP                |

---

### 13. chat_rooms (비즈몽 대화방 세션)

- **존재 이유**: 개별 메시지들을 하나의 상담 주제(세션)로 묶어 관리하고, 답변 속도 최적화 및 만족도 측정을 위함
- **관계성**: N:1 (users, businesses), 1:N (chat_logs)
- **상세 명세**:

| 구분     | 컬럼명        | 역할                | 타입/옵션       | 출처        | 비고                                 |
| :------- | :------------ | :------------------ | :-------------- | :---------- | :----------------------------------- |
| **PK**   | id            | 대화방 고유 식별자  | UUID, N         | 시스템      | 기본값: uuid4                        |
| **FK**   | user_id       | 상담 시작 사용자 ID | UUID, N         | 시스템      | users.id 외래키                      |
| **FK**   | business_id   | 선택된 사업장 ID    | UUID, N         | 시스템      | businesses.id 외래키 (데이터 격리용) |
| **일반** | title         | 대화방 제목         | VARCHAR(255), Y | 시스템      | AI 요약 또는 첫 질문 기반 생성       |
| **일반** | user_feedback | 사용자 만족도       | BOOLEAN, Y      | 사용자 입력 | 좋아요/싫어요 등 피드백 기록         |
| **일반** | status        | 상담 진행 상태      | VARCHAR(20), N  | 시스템      | 진행 중, 종료 등 세션 상태 관리      |
| **일반** | created_at    | 대화방 생성 일시    | TIMESTAMP, N    | 시스템      | Server Default: CURRENT_TIMESTAMP    |

---

### 14. batch_logs (데이터 수집 및 동기화 이력)

- **존재 이유**: 정책 공고 크롤링 및 외부 API 동기화 작업의 성공/실패 여부와 히스토리 관리
- **관계성**: 독립적 (시스템 운영 로그)
- **상세 명세**:

| 구분     | 컬럼명        | 역할                  | 타입/옵션       | 출처   | 비고                                  |
| :------- | :------------ | :-------------------- | :-------------- | :----- | :------------------------------------ |
| **PK**   | id            | 배치 실행 로그 식별자 | UUID, N         | 시스템 | 기본값: uuid4                         |
| **일반** | job_name      | 작업 명칭             | VARCHAR(100), N | 시스템 | 예: POLICY_CRAWLING, DATA_SYNC 등     |
| **일반** | status        | 실행 상태             | VARCHAR(20), N  | 시스템 | SUCCESS, FAILED, RUNNING 등 상태 관리 |
| **일반** | total_count   | 전체 건수             | INTEGER, N      | 시스템 | 배치 작업이 처리해야 할 총 데이터 수  |
| **일반** | success_count | 성공 건수             | INTEGER, N      | 시스템 | 성공적으로 반영된 데이터 수           |
| **일반** | fail_count    | 실패 건수             | INTEGER, N      | 시스템 | 처리 중 오류가 발생한 데이터 수       |
| **일반** | error_details | 오류 상세             | JSONB, Y        | 시스템 | 실패 원인 및 스택 트레이스 (JSON)     |
| **일반** | started_at    | 작업 시작 일시        | TIMESTAMP, N    | 시스템 | Server Default: CURRENT_TIMESTAMP     |
| **일반** | finished_at   | 작업 종료 일시        | TIMESTAMP, Y    | 시스템 | 작업이 최종 완료(또는 중단)된 시점    |

### 15. admins (관리자 계정)

- **존재 이유**: 관리자 페이지 접속 권한 관리 및 작업 주체 식별
- **관계성**: 1:N (admin_audit_logs)
- **상세 명세**:

| 구분     | 컬럼명     | 역할               | 타입/옵션      | 출처        | 비고                                                         |
| :------- | :--------- | :----------------- | :------------- | :---------- | :----------------------------------------------------------- |
| **PK**   | id         | 관리자 고유 식별자 | UUID, N        | 시스템      | 기본값: uuid4                                                |
| **일반** | login_id   | 관리자 로그인 ID   | VARCHAR(50), N | 관리자 생성 | Unique Index 적용                                            |
| **일반** | password   | 비밀번호 해시      | TEXT, N        | 관리자 생성 | 보안을 위해 해싱된 암호값 저장                               |
| **일반** | role       | 권한 등급          | ENUM, N        | 시스템      | MASTER, OPERATOR, CS 등 (AdminRole 연동)                     |
| **일반** | is_active  | 계정 활성 여부     | BOOLEAN, N     | 시스템      | 기본값: True (퇴사·차단 시 False 변경, Server Default: true) |
| **일반** | created_at | 계정 생성 일시     | TIMESTAMP, N   | 시스템      | Server Default: CURRENT_TIMESTAMP                            |

---

### 16. admin_audit_logs (관리자 활동 로그)

- **존재 이유**: 시스템 보안 및 추적성을 위해 관리자가 수행한 주요 작업(정책 업데이트, 데이터 수정 등)의 이력을 기록하고 관리함
- **관계성**: N:1 (admins)
- **상세 명세**:

| 구분     | 컬럼명      | 역할                  | 타입/옵션      | 출처   | 비고                                |
| :------- | :---------- | :-------------------- | :------------- | :----- | :---------------------------------- |
| **PK**   | id          | 감사 로그 고유 식별자 | UUID, N        | 시스템 | 기본값: uuid4                       |
| **FK**   | admin_id    | 작업 수행 관리자 ID   | UUID, N        | 시스템 | admins.id 외래키                    |
| **일반** | action_type | 작업 유형             | VARCHAR(50), N | 시스템 | 예: POLICY_UPDATE, USER_BAN 등      |
| **일반** | target_id   | 대상 엔티티 PK        | UUID, Y        | 시스템 | 변경 대상이 된 데이터의 고유 식별자 |
| **일반** | changes     | 변경 내역 스냅샷      | JSONB, Y       | 시스템 | 변경 전·후 데이터 비교 정보 (JSON)  |
| **일반** | ip_address  | 요청 IP 주소          | VARCHAR(45), Y | 시스템 | 작업자의 IPv4/IPv6 주소 기록        |
| **일반** | created_at  | 작업 발생 일시        | TIMESTAMP, N   | 시스템 | Server Default: CURRENT_TIMESTAMP   |
