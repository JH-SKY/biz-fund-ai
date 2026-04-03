# 📂 비즈업(Biz-Up) API 상세 명세서: [03. 정책 탐색 및 매칭] (v2.3)

본 문서는 공공 정책 데이터베이스 조회, 맞춤형 추천 엔진 연동, 북마크 기능을 위한 가이드라인입니다. **도메인 규칙 v2.2**에 따라 모든 개인화 요청은 사업장 컨텍스트(X-Business-Id)를 포함해야 합니다.

---

## 1. 전체 정책 목록 조회 (Get All Policies)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies`
- **Description:** 시스템에 등록된 모든 지원 사업 리스트를 조회합니다. 최신순 정렬 및 페이징이 기본 적용됩니다.
- **Query Params:** `page=1`, `size=10`, `sort="latest"`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "policy_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "title": "2026년 비대면 서비스 바우처 사업",
        "category": "금융/바우처",
        "closed_at": "2026-12-31",
        "is_bookmarked": false
      }
    ],
    "total_count": 1500,
    "total_pages": 150
  },
  "message": "success"
}
```

---

## 2. 맞춤형 정책 추천 목록 (Get Matched Policies)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/recommend`
- **Description:** 로그인한 사장님의 특정 사업장 정보와 정밀진단 결과를 바탕으로 **신호등 로직(RED/YELLOW/GREEN)**이 적용된 추천 리스트를 반환합니다.
- **Headers:** - `Authorization: Bearer {ACCESS_TOKEN}`
  - `X-Business-Id: {BUSINESS_UUID}` (필수: 사업장별 맞칭 결과 격리)
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    {
      "policy_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "청년 창업 기업 인건비 지원사업",
      "match_level": "GREEN", 
      "match_score": 95.8,
      "reason": "서울 소재 3년 미만 창업 기업 조건 충족",
      "is_bookmarked": false
    }
  ],
  "message": "success"
}
```

---

## 3. 정책 상세 정보 조회 (Get Policy Detail)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/{id}`
- **Description:** 특정 정책의 상세 공고 내용, 지원 자격, 신청 방법 등을 확인합니다. 해당 사업장의 북마크 여부를 함께 반환합니다.
- **Headers:** - `X-Business-Id: {BUSINESS_UUID}` (선택: 북마크 상태 확인용)
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "policy_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "2026년 비대면 서비스 바우처 사업",
    "content": "상세 모집 요강 텍스트...",
    "support_amount": "최대 400만원",
    "apply_url": "[https://k-startup.go.kr/](https://k-startup.go.kr/)...",
    "required_documents": ["사업자등록증", "부가가치세과세표준증명"],
    "is_bookmarked": true
  },
  "message": "success"
}
```

---

## 4. 정책 키워드 검색 (Search Policies)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/search`
- **Description:** 정책 제목 또는 내용에서 특정 키워드가 포함된 결과를 검색합니다.
- **Query Params:** `keyword="인공지능"`, `region="서울"`, `category="R&D"`
- **Response Body (JSON):** (전체 목록 조회와 동일 규격)

---

## 5. 관심 정책 즐겨찾기 (Toggle Bookmark)

- **Method:** `POST`
- **Endpoint:** `/api/v1/policies/{id}/bookmark`
- **Description:** 특정 정책을 찜하거나 취소합니다. (이미 있으면 삭제, 없으면 추가)
- **Headers:** - `Authorization: Bearer {ACCESS_TOKEN}`
  - `X-Business-Id: {BUSINESS_UUID}` (필수: 어느 사업장의 북마크인지 명시)
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "is_bookmarked": true,
    "policy_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  },
  "message": "success"
}
```

---

## 6. 찜한 정책 목록 조회 (Get Bookmarks)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/bookmarks`
- **Description:** 특정 사업장(X-Business-Id) 기준으로 즐겨찾기한 정책 리스트를 조회합니다.
- **Headers:** - `Authorization: Bearer {ACCESS_TOKEN}`
  - `X-Business-Id: {BUSINESS_UUID}`
- **Response Body (JSON):** (전체 목록 조회와 동일 규격)

---

## 🚥 구현 가이드라인 (Implementation Note)

1. **Context Lock (X-Business-Id):** 추천 및 북마크 API는 반드시 헤더의 사업장 ID를 기준으로 데이터를 격리해야 합니다. (규칙 2.2 준수)
2. **Traffic Light Logic:** 추천 엔진은 도메인 규칙 4.1에 따라 `match_level`을 계산하여 반환합니다.
3. **Soft Delete Filter:** 모든 조회 API는 `is_active=True`인 정책과 북마크만 반환해야 합니다. (규칙 0 준수)
4. **UUID Standard:** 모든 `id` 값은 `pol-001`과 같은 가짜 형식이 아닌 실제 `UUID` 형식을 따릅니다.