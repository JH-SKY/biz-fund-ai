# 📋 Biz-Fund-AI 전체 API 매뉴얼 테스트 가이드 (v1.0)
> **작성자:** DevLog-Ryan  
> **원칙:** 기록이 기억을 지배한다. (DB가 비어있는 상태에서 시작하는 빌드업 테스트)

---

## 1단계: 운영 준비 (Admin & Data Seeding)
*유저가 들어오기 전에 가게 문을 열고 물건(정책)을 진열하는 단계입니다.*

1. **관리자 로그인**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/admin/login`
   - **Check:** `access_token`이 발급되는지 확인. (이 토큰을 `bearerToken` 변수에 저장)

2. **정책 데이터 생성 (정책 입고)**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/admin/policies`
   - **Check:** 201 Created 응답 확인. 최소 3개 이상의 각기 다른 카테고리 정책을 등록하세요. (나중에 RAG 검색용)

3. **비즈픽 콘텐츠 발행**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/admin/contents`
   - **Check:** 유저들이 읽을 뉴스나 정보를 등록합니다. `status`를 `PUBLISHED`로 설정해야 유저에게 보입니다.

---

## 2단계: 유저 진입 및 온보딩 (Auth & Profile)
*신규 유저가 가입하고 자신을 소개하는 단계입니다.*

4. **네이버 로그인**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/auth/naver`
   - **Check:** 새로운 유저로 가입되는지 확인. `is_new_user: true`인지 체크하세요.

5. **내 프로필 조회 (최초)**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/users/me`
   - **Check:** `is_profile_completed: false` 상태인지 확인.

6. **프로필 업데이트 (관심분야 설정)**
   - **Method:** `PATCH`
   - **URL:** `{{base_url}}/api/v1/users/me`
   - **Check:** `interest_sectors` 등에 관심 분야를 넣고 `is_profile_completed`가 `true`로 바뀌는지 확인.

---

## 3단계: 사업장 등록 (ActiveBusiness 가드 뚫기)
*사업자 정보가 있어야 정책 추천과 AI 상담이 가능해집니다.*

7. **사업자 번호 진위 확인**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/onboarding/verify-biz`
   - **Check:** 국세청 DB 연동 확인 (테스트용은 목업 데이터 확인).

8. **사업장 등록**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/onboarding/register`
   - **Check:** 성공 시 `business_id` 발급 확인. (이 ID를 포스트맨 헤더 `X-Business-Id`에 담아야 함)

9. **재무 스냅샷 등록**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/businesses/finance`
   - **Check:** 매출액, 영업이익 등을 입력. (나중에 정밀 진단의 기초 자료가 됨)

---

## 4단계: 정책 탐색 및 정밀 진단 (Policy & Diagnosis)
*이제 진짜 유저에게 맞는 정보를 찾아주는 단계입니다.*

10. **전체 정책 목록 조회**
    - **Method:** `GET`
    - **URL:** `{{base_url}}/api/v1/policies`
    - **Check:** 아까 1단계에서 관리자가 등록한 정책들이 리스트에 나오는지 확인.

11. **맞춤 정책 추천 (신호등 로직)**
    - **Method:** `GET`
    - **URL:** `{{base_url}}/api/v1/policies/recommend`
    - **Check:** 내 사업장 정보와 매칭되는 정책들이 '적합/보통/부적합' 등급으로 나오는지 확인.

12. **가산점 시뮬레이션 실행**
    - **Method:** `POST`
    - **URL:** `{{base_url}}/api/v1/simulations`
    - **Check:** 특정 요건(특허 보유 등)을 선택했을 때 점수가 계산되어 나오는지 확인.

---

## 5단계: AI 에이전트 상담 (Chat & RAG)
*가장 핵심인 AI와 대화하며 궁금증을 해결하는 단계입니다.*

13. **채팅 세션 생성**
    - **Method:** `POST`
    - **URL:** `{{base_url}}/api/v1/chats/sessions`
    - **Check:** 새로운 상담창(`session_id`)이 열리는지 확인.

14. **AI 질문 보내기 (RAG 테스트)**
    - **Method:** `POST`
    - **URL:** `{{base_url}}/api/v1/chats/sessions/{{session_id}}/messages`
    - **Body:** `{"message": "내가 받을 수 있는 창업 지원금 알려줘"}`
    - **Check:** AI가 DB의 정책 데이터를 참고해서 답변을 주는지 확인.

15. **대화 내역 요약**
    - **Method:** `PATCH`
    - **URL:** `{{base_url}}/api/v1/chats/sessions/{{session_id}}/summary`
    - **Check:** 긴 대화 내용을 바탕으로 제목이 자동으로 생성되는지 확인.

---

## 6단계: 부가 기능 및 정리 (Engagement & Withdrawal)

16. **알림 목록 조회**
    - **Method:** `GET`
    - **URL:** `{{base_url}}/api/v1/notifications`
    - **Check:** 시스템 알림이나 채팅 답변 알림이 와 있는지 확인.

17. **회원 탈퇴 (Soft Delete)**
    - **Method:** `DELETE`
    - **URL:** `{{base_url}}/api/v1/users/withdraw`
    - **Check:** 204 No Content 확인 후, 다시 로그인 시도 시 막히는지 확인.

## 2순위 점검: 도메인별 상세 기능 및 관리자 운영 (전수 검사)
*핵심 흐름 외에 서비스의 디테일과 데이터 수정/삭제, 관리자 기능을 검증합니다.*

### 📂 [Admin] 관리자 센터 전용 기능
1. **정책 수정 (PATCH)**
   - **URL:** `PATCH {{base_url}}/api/v1/admin/policies/{policy_id}`
   - **Check:** 등록된 정책의 제목이나 내용을 수정했을 때 잘 반영되는지 확인.
2. **정책 삭제 (DELETE)**
   - **URL:** `DELETE {{base_url}}/api/v1/admin/policies/{policy_id}`
   - **Check:** 정책이 목록에서 사라지는지 확인.
3. **콘텐츠 수정 및 발행 관리**
   - **URL:** `PATCH {{base_url}}/api/v1/admin/contents/{content_id}`
   - **Check:** 비즈픽 내용 수정 및 `status` 변경 테스트.
4. **배치 작업 상태 조회**
   - **URL:** `GET {{base_url}}/api/v1/admin/batch/status`
   - **Check:** RAG 학습이나 데이터 수집 배치 작업 현황 확인.
5. **배치 상세 로그 확인**
   - **URL:** `GET {{base_url}}/api/v1/admin/batch/logs/{job_id}`
   - **Check:** 특정 작업이 실패했다면 어떤 에러가 났는지 로그 확인.
6. **유저 목록 관리 (Paging)**
   - **URL:** `GET {{base_url}}/api/v1/admin/users?page=1&size=20`
   - **Check:** 가입된 전체 유저가 잘 나오는지, 페이징 처리가 되는지 확인.

### 📂 [Business & Documents] 사업장 및 서류 상세
7. **사업장 정보 수정**
   - **URL:** `PATCH {{base_url}}/api/v1/businesses/me`
   - **Check:** 주소나 업종 변경 시 잘 저장되는지 확인.
8. **재무 데이터 수정/삭제**
   - **URL:** `PATCH/DELETE {{base_url}}/api/v1/businesses/finance/{year}`
   - **Check:** 입력된 연도별 재무 정보를 수정하거나 영구 삭제 시 응답 확인.
9. **서류 상세 조회 및 OCR 결과**
   - **URL:** `GET {{base_url}}/api/v1/documents/{document_id}`
   - **Check:** 업로드한 서류의 파일 경로와 OCR 분석 텍스트가 잘 나오는지 확인.
10. **서류 파기**
    - **URL:** `DELETE {{base_url}}/api/v1/documents/{document_id}`
    - **Check:** 서류함에서 데이터가 삭제되는지 확인.

### 📂 [Policy & Biz-Pick] 탐색 및 인게이지먼트
11. **정책 키워드 검색**
    - **URL:** `GET {{base_url}}/api/v1/policies/search?keyword=창업`
    - **Check:** 특정 단어가 포함된 정책만 필터링되는지 확인.
12. **북마크 목록 조회**
    - **URL:** `GET {{base_url}}/api/v1/policies/bookmarks`
    - **Check:** 내가 '찜'한 정책들만 모아서 나오는지 확인.
13. **비즈픽 카테고리 목록**
    - **URL:** `GET {{base_url}}/api/v1/contents/categories`
    - **Check:** 제공되는 콘텐츠 카테고리(뉴스, 가이드 등) 리스트 확인.
14. **비즈픽 좋아요(Like) 토글**
    - **URL:** `POST {{base_url}}/api/v1/contents/{content_id}/like`
    - **Check:** 처음 누르면 좋아요(+1), 다시 누르면 취소(-1)되는지 확인.

### 📂 [Diagnosis & Simulation] 분석 기능
15. **정밀진단 이력 조회**
    - **URL:** `GET {{base_url}}/api/v1/diagnoses`
    - **Check:** 과거에 실행했던 진단 리포트 목록 확인.
16. **진단 기록 삭제**
    - **URL:** `DELETE {{base_url}}/api/v1/diagnoses/{diagnosis_id}`
    - **Check:** 불필요한 진단 결과 삭제 확인.

### 📂 [Notification & Settings] 알림 및 설정
17. **알림 설정 조회 및 수정**
    - **URL:** `GET/PATCH {{base_url}}/api/v1/notifications/settings`
    - **Check:** 푸시 알림 수신 동의 상태를 변경하고 저장되는지 확인.
18. **개별 알림 읽음 처리**
    - **URL:** `PATCH {{base_url}}/api/v1/notifications/{noti_id}/read`
    - **Check:** 특정 알림의 `is_read` 상태가 true로 변하는지 확인.

---

## 2.5순위 점검: 누락된 비즈니스 로직 및 상세 검증 (Router 전수 조사 결과)
*파일 분석을 통해 발견된, 사용자 경험과 데이터 정확성을 결정짓는 추가 API들입니다.*

### 📂 [Business] 입력값 이상치 검증 (Validation)
1. **사업장 데이터 유효성 체크**
   - **Method:** `POST`
   - **URL:** `{{base_url}}/api/v1/businesses/validate`
   - **Check:** 재무 상태나 사업장 정보를 실제 등록하기 전, 서버의 검증 로직이 이상치(예: 매출액 0원 이하 등)를 잘 잡아내는지 확인.

2. **재무 이력 전체 조회**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/businesses/finance/history`
   - **Check:** 9번에서 등록한 스냅샷들이 연도별 리스트로 정확히 출력되는지 확인.

### 📂 [Policy & Biz-Pick] 특수 큐레이션 및 상세 조회
3. **오늘의 픽 (Today's Picks) 조회**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/contents/todays`
   - **Check:** 관리자가 등록한 콘텐츠 중 오늘 날짜에 맞는 추천 콘텐츠가 상단에 노출되는지 확인.

4. **정책 상세 보기 (비로그인/로그인 비교)**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/policies/{policy_id}`
   - **Check 1 (비로그인):** `X-Business-Id` 없이 호출 시 기본 정보만 오는지 확인.
   - **Check 2 (로그인):** `X-Business-Id` 포함 호출 시 내 사업장과의 매칭 데이터 및 북마크 여부가 포함되는지 확인.

### 📂 [Diagnosis] 진단 프로세스 세분화
5. **정밀진단 준비 (Pre-check)**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/diagnoses/prepare`
   - **Check:** 진단을 시작하기 전, 현재 내 사업장 정보에서 누락된 필드가 무엇인지 서버가 정확히 짚어주는지 확인. (이게 되어야 11번 추천이 정확해짐)

### 📂 [Chat] 대화 내역 관리
6. **특정 세션 대화 히스토리 전체 조회**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/chats/sessions/{session_id}/messages`
   - **Check:** 14번에서 나눈 대화들이 순서대로(Timeline) 잘 저장되어 불러와지는지 확인.

7. **상담 세션 목록 조회**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/chats/sessions`
   - **Check:** 내가 지금까지 AI와 상담한 방(Session)들이 리스트로 잘 나오는지 확인.

---

## 3순위 점검: 예외 상황 및 보안 (Edge Case)
*정상적인 흐름 외에 '안 되는 상황'을 테스트하여 서버의 견고함을 확인합니다.*

1. **권한 없는 접근 테스트**
   - **Method:** `POST /api/v1/admin/policies` (일반 유저 토큰 사용)
   - **Check:** `403 Forbidden`이 정확히 뜨는지 확인.
2. **사업장 미등록 유저의 접근**
   - **Method:** `POST /api/v1/chats/sessions` (X-Business-Id 없이 호출)
   - **Check:** `403` 또는 온보딩 리다이렉트 응답 확인 (`ActiveBusiness` 가드).
3. **유효하지 않은 데이터 입력 (Validation)**
   - **Method:** `POST /api/v1/onboarding/verify-biz` (잘못된 사업자번호 형식)
   - **Check:** `422 Unprocessable Entity` 응답 확인.
4. **존재하지 않는 자원 요청**
   - **Method:** `GET /api/v1/policies/{랜덤UUID}`
   - **Check:** `404 Not Found` 확인.

---

 ## 3.5순위 점검: 시스템 및 메타데이터 (System Meta)

1. **콘텐츠 카테고리 마스터 조회**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/contents/categories`
   - **Check:** 프론트엔드에서 카테고리 탭을 그릴 때 사용하는 마스터 데이터가 정상 응답되는지 확인.

2. **알림 설정 현황 조회**
   - **Method:** `GET`
   - **URL:** `{{base_url}}/api/v1/notifications/settings`
   - **Check:** 유저별 알림 ON/OFF 상태값이 기본값으로 잘 세팅되어 있는지 확인.