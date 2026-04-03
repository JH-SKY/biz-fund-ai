# 📂 비즈업(Biz-Up) API 상세 명세서: [07. 관리자 센터]

본 문서는 서비스 운영진을 위한 정책/콘텐츠 관리 및 시스템 모니터링 가이드라인입니다. 모든 API는 관리자 권한(`is_admin=True`) 확인이 필수이며, 운영 효율성을 위해 검색 및 페이징 기능을 포함합니다.

---

## 1. 신규 정책 등록 (Create Raw Policy)
- **Method:** `POST`
- **Endpoint:** `/api/v1/admin/policies`
- **Description:** 공공 데이터 외에 관리자가 직접 새로운 정부 지원 정책 공고를 시스템에 등록합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Request Body (JSON):**
```json
{
  "title": "2026 스타트업 해외 진출 바우처",
  "category": "EXPORT",
  "content": "상세 모집 요강...",
  "target_region": "NATIONWIDE",
  "apply_start_date": "2026-05-01",
  "apply_end_date": "2026-05-31"
}
```
- **Response Body (JSON):**
```json
{
  "status": 201,
  "data": { "policy_id": "pol-999", "created_at": "2026-04-02T14:00:00Z" }
}
```
- **Error Codes:**
  - `403 Forbidden`: 관리자 권한 없음

---

## 2. 콘텐츠 발행 (Publish Content)
- **Method:** `POST`
- **Endpoint:** `/api/v1/admin/contents`
- **Description:** 비즈픽(Biz-Pick) 탭에 노출될 새로운 가이드나 성공 사례 콘텐츠를 작성하고 즉시 발행합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Request Body (JSON):**
```json
{
  "title": "성공하는 사장님의 3가지 습관",
  "body_html": "<p>본문 내용...</p>",
  "thumbnail_url": "[https://cdn.bizup.com/static/thumb.jpg](https://cdn.bizup.com/static/thumb.jpg)",
  "is_published": true
}
```
- **Response Body (JSON):**
```json
{
  "status": 201,
  "data": { "content_id": "cnt-777" }
}
```

---

## 3. AI 상담 모니터링 로그 조회 (Monitor Chat Logs)
- **Method:** `GET`
- **Endpoint:** `/api/v1/admin/chats/logs`
- **Description:** 비즈몽 AI와 사용자 간의 대화 내역을 모니터링하여 답변의 정확도와 품질을 체크합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Query Params:** `user_id="uuid"`, `page=1`, `size=20`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "items": [
      { "session_id": "sess-01", "user_msg": "지원금 문의", "ai_res": "답변 내용...", "timestamp": "..." }
    ]
  }
}
```

---

## 4. 정책 공고 수정 (Update Policy)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/admin/policies/{id}`
- **Description:** 기등록된 정책의 오타 수정, 지원 조건 변경, 또는 마감 기한을 연장합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Request Body (JSON):** `{ "title": "수정된 제목", "apply_end_date": "2026-06-30" }`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "message": "정책 정보가 성공적으로 수정되었습니다."
}
```

---

## 5. 콘텐츠 수정 및 비공개 (Update Biz-Pick)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/admin/contents/{id}`
- **Description:** 기존 비즈픽 콘텐츠 내용을 수정하거나, 발행 상태(`is_published`)를 변경하여 비공개 처리합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "message": "콘텐츠 상태가 업데이트되었습니다."
}
```

---

## 6. 운영 대시보드 (Get Stats Dashboard)
- **Method:** `GET`
- **Endpoint:** `/api/v1/admin/stats/dashboard`
- **Description:** 신규 가입자 수, 일일 상담 건수, 인기 정책 TOP 5 등 주요 운영 지표를 한눈에 조회합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "new_users_today": 125,
    "active_chats_today": 450,
    "popular_policies": [{ "id": "pol-01", "hits": 2300 }]
  }
}
```

---

## 7. 운영 감사 로그 (Status & Audit)
- **Method:** `GET`
- **Endpoint:** `/api/v1/admin/audit-logs`
- **Description:** 관리자들이 수행한 민감 작업(정책 삭제, 사용자 제재 등)의 이력을 조회하여 보안을 강화합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "admin_id": "admin-01", "action": "DELETE_POLICY", "target": "pol-101", "created_at": "..." }
  ]
}
```

---

## 8. 배치 작업 상태 조회 (Monitor Batch Jobs)
- **Method:** `GET`
- **Endpoint:** `/api/v1/admin/batch/status`
- **Description:** 정책 크롤링, 알림 발송 등 자동화된 배치 작업의 최근 실행 결과와 성공 여부를 확인합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "job_name": "DAILY_CRAWL", "last_run": "2026-04-02 04:00", "status": "SUCCESS" }
  ]
}
```

---

## 9. 특정 배치 로그 상세 조회 (Get Batch Detail)
- **Method:** `GET`
- **Endpoint:** `/api/v1/admin/batch/logs/{job_id}`
- **Description:** 특정 배치 작업 실패 시, 상세한 에러 로그(Stack Trace 등)를 확인하여 원인을 분석합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": { "job_id": "job-001", "raw_log": "Error: Connection Timeout..." }
}
```

---

## 10. 전체 사용자 목록 조회 (Get All Users)
- **Method:** `GET`
- **Endpoint:** `/api/v1/admin/users`
- **Description:** 가입된 전체 사용자 리스트를 조회하고 검색(이름, 이메일) 및 상태별 필터링을 수행합니다.
- **Headers:** `Authorization: Bearer {ADMIN_TOKEN}`
- **Query Params:** `page=1`, `size=20`, `search_keyword="이종혁"`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "user_id": "uuid-001",
        "name": "이종혁",
        "email": "ryan@example.com",
        "is_active": true,
        "created_at": "2026-01-11T09:00:00Z"
      }
    ],
    "total_count": 1250,
    "total_pages": 63
  }
}
```
- **Error Codes:**
  - `401 Unauthorized`: 관리자 토큰 만료
  - `400 Bad Request`: 잘못된 검색 조건