## 📊 [비즈업] 서비스 데이터베이스 상세 정의서

### 0. 공통 규칙

- **ID**: Primary Key (UUID 또는 BIGINT 추천)
- **Time**: TIMESTAMP (Default: CURRENT_TIMESTAMP)
- **Soft Delete**: `is_active` 또는 `status` 컬럼을 통한 논리 삭제 적용

---

### 1. users (사용자 계정)

- **존재 이유**: 서비스 이용자 식별 및 소셜 로그인 연동 관리
- **관계성**: 1:N (businesses, chat_logs, notifications, lead_requests)
- **상세 명세**:

| 구분     | 컬럼명            | 역할                      | 타입/옵션       | 출처        |
| :------- | :---------------- | :------------------------ | :-------------- | :---------- |
| **PK**   | id                | 사용자 고유 식별자        | UUID, N         | 시스템      |
| **일반** | email             | 이메일 주소               | VARCHAR(255), N | 소셜 연동   |
| **일반** | name              | 실명                      | VARCHAR(50), N  | 소셜 연동   |
| **일반** | phone             | 전화번호                  | VARCHAR(20), Y  | 사용자 입력 |
| **일반** | nickname          | 활동명                    | VARCHAR(50), Y  | 사용자 입력 |
| **일반** | status            | 계정 상태(active/deleted) | VARCHAR(20), N  | 시스템      |
| **일반** | social_id         | 소셜 고유 고정 ID         | VARCHAR(255), N | 소셜 연동   |
| **일반** | social_provider   | 소셜 제공자(KAKAO/NAVER)  | ENUM, N         | 소셜 연동   |
| **일반** | profile_image_url | 프로필 사진 URL           | TEXT, Y         | 소셜 연동   |
| **일반** | is_active         | 활성 계정 여부            | BOOLEAN, N      | 시스템      |
| **일반** | created_at        | 가입 일시                 | TIMESTAMP, N    | 시스템      |

---

### 2. businesses (사업장 기본 정보)

- **존재 이유**: 사장님의 업장 정보 관리 (1유저 다사업장 대응) 및 매칭 필터링의 핵심
- **관계성**: N:1 (users), 1:N (financial_snapshots, match_logs, applications, documents, lead_requests, simulation_logs)
- **상세 명세**:

| 구분     | 컬럼명              | 역할                 | 타입/옵션       | 출처          |
| :------- | :------------------ | :------------------- | :-------------- | :------------ |
| **PK**   | id                  | 사업장 식별자        | UUID, N         | 시스템        |
| **FK**   | user_id             | 소유주 ID            | UUID, N         | 시스템        |
| **일반** | biz_name            | 상호명               | VARCHAR(100), N | 사용자 입력   |
| **일반** | representative_name | 대표자명             | VARCHAR(50), Y  | 사용자 입력   |
| **일반** | biz_no              | 사업자등록번호       | VARCHAR(12), Y  | **OCR/입력**  |
| **일반** | ksic_code           | 표준산업분류코드     | VARCHAR(20), Y  | **자동 추출** |
| **일반** | sector_code         | 업종 코드            | VARCHAR(20), Y  | **자동 추출** |
| **일반** | region_sido         | 시/도 (표시용)       | VARCHAR(50), Y  | **자동 추출** |
| **일반** | region_sigungu      | 시/군/구 (표시용)    | VARCHAR(50), Y  | **자동 추출** |
| **일반** | region_code         | 법정동 코드 (계산용) | VARCHAR(10), Y  | **자동 추출** |
| **일반** | establishment_date  | 설립 일자            | DATE, Y         | **OCR/입력**  |
| **일반** | has_patent          | 특허 보유 여부       | BOOLEAN, N      | 사용자 입력   |
| **일반** | is_female_ent       | 여성 기업 여부       | BOOLEAN, N      | 사용자 입력   |
| **일반** | is_ventured         | 벤처 기업 여부       | BOOLEAN, N      | 사용자 입력   |
| **일반** | is_active           | 업장 활성 여부       | BOOLEAN, N      | 시스템        |
| **일반** | created_at          | 등록 일시            | TIMESTAMP, N    | 시스템        |

---

### 3. business_financial_snapshots (재무 상태 스냅샷)

- **존재 이유**: 시점별 재무 지표 기록 및 비즈몽의 AI 재무 진단 근거
- **관계성**: N:1 (businesses)
- **상세 명세**:

| 구분     | 컬럼명             | 역할                 | 타입/옵션       | 출처          |
| :------- | :----------------- | :------------------- | :-------------- | :------------ |
| **PK**   | id                 | 스냅샷 식별자        | UUID, N         | 시스템        |
| **FK**   | business_id        | 사업장 ID            | UUID, N         | 시스템        |
| **일반** | snapshot_year      | 기준 연도            | INT, N          | **OCR/입력**  |
| **일반** | snapshot_period    | 기준 시기(1Q, 2Q 등) | VARCHAR(10), N  | **OCR/입력**  |
| **일반** | term_type          | 공시 주기(연간/분기) | VARCHAR(10), N  | **OCR/입력**  |
| **일반** | annual_revenue     | 연매출액             | BIGINT, Y       | **OCR/입력**  |
| **일반** | net_income         | 당기순이익           | BIGINT, Y       | **OCR/입력**  |
| **일반** | total_debt         | 총 부채액            | BIGINT, Y       | **OCR/입력**  |
| **일반** | debt_ratio         | 부채 비율            | DECIMAL(5,2), Y | **자동 계산** |
| **일반** | employee_count     | 직원 수              | INT, Y          | **OCR/입력**  |
| **일반** | tax_arrears_yn     | 체납 여부            | BOOLEAN, N      | **OCR/입력**  |
| **일반** | ai_analysis_report | 비즈몽 재무 진단     | JSONB, Y        | **AI 생성**   |
| **일반** | ocr_status         | 분석 상태(대기/완료) | VARCHAR(20), N  | 시스템        |
| **일반** | created_at         | 기록 일시            | TIMESTAMP, N    | 시스템        |

---

### 4. policies (정책 공고 데이터)

- **존재 이유**: 수집된 정책 자금 공고의 마스터 데이터
- **관계성**: 1:N (match_logs, applications, chat_logs)
- **상세 명세**:

| 구분     | 컬럼명              | 역할              | 타입/옵션       | 출처          |
| :------- | :------------------ | :---------------- | :-------------- | :------------ |
| **PK**   | id                  | 정책 식별자       | UUID, N         | 시스템        |
| **일반** | title               | 공고 제목         | VARCHAR(255), N | 크롤링/관리자 |
| **일반** | agency_name         | 공고 기관명       | VARCHAR(100), N | 크롤링/관리자 |
| **일반** | support_type        | 지원 유형         | VARCHAR(50), Y  | 크롤링/관리자 |
| **일반** | ai_summary          | 리스트용 3줄 요약 | TEXT, Y         | **AI 생성**   |
| **일반** | ai_full_explanation | 상세용 쉬운 풀이  | TEXT, Y         | **AI 생성**   |
| **일반** | content_raw         | 공고 원문 내용    | TEXT, N         | 크롤링/관리자 |
| **일반** | max_support         | 최대 지원 금액    | BIGINT, Y       | 크롤링/관리자 |
| **일반** | start_date          | 접수 시작일       | DATE, Y         | 크롤링/관리자 |
| **일반** | end_date            | 접수 종료일       | DATE, Y         | 크롤링/관리자 |
| **일반** | is_closed           | 조기 마감 여부    | BOOLEAN, N      | 관리자        |
| **일반** | apply_url           | 원문 신청 링크    | TEXT, Y         | 크롤링/관리자 |
| **일반** | target_logic        | 매칭 필터링 로직  | JSONB, Y        | 시스템        |
| **일반** | bonus_logic         | 가산점 계산 로직  | JSONB, Y        | 시스템        |

---

### 5. match_logs (매칭 결과 기록)

- **존재 이유**: 사업장 데이터와 정책 간의 매칭 점수 및 근거 저장 (속도/알림용)
- **관계성**: N:1 (businesses, policies)
- **상세 명세**:

| 구분     | 컬럼명       | 역할              | 타입/옵션      | 출처        |
| :------- | :----------- | :---------------- | :------------- | :---------- |
| **PK**   | id           | 매칭 식별자       | UUID, N        | 시스템      |
| **FK**   | business_id  | 사업장 ID         | UUID, N        | 시스템      |
| **FK**   | policy_id    | 정책 ID           | UUID, N        | 시스템      |
| **일반** | match_score  | 매칭 점수 (0~100) | INT, N         | 시스템      |
| **일반** | match_status | 신호등(G/Y/R)     | VARCHAR(10), N | 시스템      |
| **일반** | reason_json  | 점수 산정 근거    | JSONB, Y       | **AI 생성** |
| **일반** | created_at   | 판정 일시         | TIMESTAMP, N   | 시스템      |

---

### 6. chat_logs (비즈몽 대화 기록)

- **존재 이유**: AI 상담 히스토리 관리 및 개인화된 RAG 성능 향상
- **관계성**: N:1 (users, policies)
- **상세 명세**:

| 구분     | 컬럼명        | 역할                   | 타입/옵션      | 출처      |
| :------- | :------------ | :--------------------- | :------------- | :-------- |
| **PK**   | id            | 대화 식별자            | UUID, N        | 시스템    |
| **FK**   | user_id       | 사용자 ID              | UUID, N        | 시스템    |
| **FK**   | ref_policy_id | 참조한 정책 ID         | UUID, Y        | 시스템    |
| **일반** | role          | 화자 (user/assistant)  | VARCHAR(20), N | 시스템    |
| **일반** | content       | 대화 내용              | TEXT, N        | 사용자/AI |
| **일반** | context_type  | 발생 위치(위젯/페이지) | VARCHAR(20), Y | 시스템    |
| **일반** | created_at    | 대화 일시              | TIMESTAMP, N   | 시스템    |

---

### 7. applications (정책 신청 현황)

- **존재 이유**: 사용자가 관심을 보였거나 실제 신청 중인 공고 트래킹
- **관계성**: N:1 (businesses, policies)
- **상세 명세**:

| 구분     | 컬럼명      | 역할                 | 타입/옵션      | 출처          |
| :------- | :---------- | :------------------- | :------------- | :------------ |
| **PK**   | id          | 신청 기록 식별자     | UUID, N        | 시스템        |
| **FK**   | business_id | 사업장 ID            | UUID, N        | 시스템        |
| **FK**   | policy_id   | 정책 ID              | UUID, N        | 시스템        |
| **일반** | status      | 상태(관심/제출/승인) | VARCHAR(20), N | 사용자/시스템 |
| **일반** | applied_at  | 신청 일시            | TIMESTAMP, Y   | 사용자 입력   |
| **일반** | updated_at  | 상태 변경 일시       | TIMESTAMP, N   | 시스템        |
| **일반** | memo        | 사용자 개인 메모     | TEXT, Y        | 사용자 입력   |

---

### 8. documents (디지털 서류함)

- **존재 이유**: 사업자등록증 등 서류 파일 관리 및 OCR 연동
- **관계성**: N:1 (businesses)
- **상세 명세**:

| 구분     | 컬럼명      | 역할           | 타입/옵션      | 출처         |
| :------- | :---------- | :------------- | :------------- | :----------- |
| **PK**   | id          | 서류 식별자    | UUID, N        | 시스템       |
| **FK**   | business_id | 사업장 ID      | UUID, N        | 시스템       |
| **일반** | doc_type    | 서류 종류      | VARCHAR(50), N | 사용자 선택  |
| **일반** | file_url    | S3 저장 경로   | TEXT, N        | 시스템       |
| **일반** | issued_at   | 서류 발급 일자 | DATE, Y        | **OCR/입력** |
| **일반** | created_at  | 업로드 일시    | TIMESTAMP, N   | 시스템       |

---

### 9. biz_picks (콘텐츠/이슈 관리)

- **존재 이유**: 정책 이슈, 꿀팁 등 정보성 콘텐츠 관리
- **관계성**: 독립 (JSON 내 policy_ids 참조)
- **상세 명세**:

| 구분     | 컬럼명     | 역할          | 타입/옵션       | 출처   |
| :------- | :--------- | :------------ | :-------------- | :----- |
| **PK**   | id         | 콘텐츠 식별자 | UUID, N         | 시스템 |
| **일반** | title      | 콘텐츠 제목   | VARCHAR(255), N | 관리자 |
| **일반** | category   | 카테고리      | VARCHAR(50), N  | 관리자 |
| **일반** | content_md | 마크다운 본문 | TEXT, N         | 관리자 |
| **일반** | created_at | 작성 일시     | TIMESTAMP, N    | 시스템 |

---

### 10. notifications (알림 기록)

- **존재 이유**: 사용자별 푸시/앱 내 알림 히스토리 관리
- **관계성**: N:1 (users)
- **상세 명세**:

| 구분     | 컬럼명     | 역할                 | 타입/옵션      | 출처   |
| :------- | :--------- | :------------------- | :------------- | :----- |
| **PK**   | id         | 알림 식별자          | UUID, N        | 시스템 |
| **FK**   | user_id    | 대상 사용자 ID       | UUID, N        | 시스템 |
| **일반** | type       | 알림 유형(매칭/공지) | VARCHAR(20), N | 시스템 |
| **일반** | message    | 알림 본문            | TEXT, N        | 시스템 |
| **일반** | is_read    | 읽음 여부            | BOOLEAN, N     | 시스템 |
| **일반** | link_url   | 이동할 링크 URL      | TEXT, Y        | 시스템 |
| **일반** | created_at | 발송 일시            | TIMESTAMP, N   | 시스템 |

---

### 11. lead_requests (상담 리드/수익화)

- **존재 이유**: 로봇, 컨설팅 등 외부 파트너사와 사장님 연결 기록 관리
- **관계성**: N:1 (users, businesses)
- **상세 명세**:

| 구분     | 컬럼명      | 역할                    | 타입/옵션      | 출처        |
| :------- | :---------- | :---------------------- | :------------- | :---------- |
| **PK**   | id          | 리드 식별자             | UUID, N        | 시스템      |
| **FK**   | user_id     | 신청 사용자 ID          | UUID, N        | 시스템      |
| **FK**   | business_id | 신청 사업장 ID          | UUID, N        | 시스템      |
| **일반** | lead_type   | 상담 종류(로봇/세무 등) | VARCHAR(50), N | 사용자 선택 |
| **일반** | status      | 처리 상태               | VARCHAR(20), N | 시스템      |
| **일반** | created_at  | 신청 일시               | TIMESTAMP, N   | 시스템      |

---

### 12. simulation_logs (가산점 시뮬레이션)

- **존재 이유**: 사용자가 직접 가상 데이터를 넣어본 결과 기록 보존
- **관계성**: N:1 (businesses)
- **상세 명세**:

| 구분     | 컬럼명      | 역할               | 타입/옵션      | 출처          |
| :------- | :---------- | :----------------- | :------------- | :------------ |
| **PK**   | id          | 로그 식별자 (추가) | UUID, N        | 시스템        |
| **FK**   | business_id | 대상 사업장 ID     | UUID, N        | 시스템        |
| **일반** | sim_type    | 시뮬레이션 종류    | VARCHAR(50), N | 사용자 선택   |
| **일반** | input_data  | 입력값(특허 등)    | JSONB, N       | 사용자 입력   |
| **일반** | output_data | 예상 결과값        | JSONB, N       | **AI/시스템** |
| **일반** | created_at  | 실행 일시          | TIMESTAMP, N   | 시스템        |

---

### 13. biz_pick_policies (비즈픽-정책 연결 중계 테이블)

- **존재 이유**: 비즈픽(콘텐츠)과 관련 정책 간의 N:M(다대다) 관계를 해소하고 쌍방향 조회를 최적화하기 위함
- **관계성**: N:1 (biz_picks), N:1 (policies)
- **상세 명세**:

| 구분      | 컬럼명      | 역할           | 타입/옵션    | 출처   |
| :-------- | :---------- | :------------- | :----------- | :----- |
| **PK/FK** | biz_pick_id | 참조 비즈픽 ID | UUID, N      | 시스템 |
| **PK/FK** | policy_id   | 참조 정책 ID   | UUID, N      | 시스템 |
| **일반**  | created_at  | 연결 생성 일시 | TIMESTAMP, N | 시스템 |

- **참고사항**: `biz_pick_id`와 `policy_id`를 묶어서 **복합키(Composite PK)**로 설정하여 동일한 연결이 중복으로 생성되는 것을 원천 차단
