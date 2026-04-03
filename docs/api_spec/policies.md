# 📂 비즈업(Biz-Up) API 상세 명세서: [03. 정책 탐색 및 매칭]

본 문서는 공공 정책 데이터베이스 조회, 맞춤형 추천 엔진 연동, 북마크 기능을 위한 가이드라인입니다. 대량의 데이터를 다루므로 페이징 처리와 효율적인 검색 필터링 구현을 원칙으로 합니다.

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
        "policy_id": "pol-001",
        "title": "2026년 비대면 서비스 바우처 사업",
        "category": "금융/바우처",
        "end_date": "2026-12-31",
        "is_bookmarked": false
      }
    ],
    "total_count": 1500,
    "total_pages": 150
  }
}
```

- **Error Codes:**
  - `400 Bad Request`: 잘못된 페이지 번호 또는 정렬 파라미터

---

## 2. 맞춤형 정책 추천 목록 (Get Matched Policies)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/recommend`
- **Description:** 로그인한 사장님의 사업장 정보(업종, 매출, 고용 등)와 정밀진단 결과를 바탕으로 합격 가능성이 높은 정책을 상위에 노출합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**

```json
{
  "status": 200,
  "data": [
    {
      "policy_id": "pol-005",
      "title": "청년 창업 기업 인건비 지원사업",
      "match_score": 95.8,
      "reason": "서울 소재 3년 미만 창업 기업 조건 충족"
    }
  ]
}
```

- **Error Codes:**
  - `401 Unauthorized`: 인증 토큰 유효하지 않음
  - `404 Not Found`: 추천에 필요한 사용자 프로필/진단 데이터 부족

---

## 3. 정책 상세 정보 조회 (Get Policy Detail)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/{id}`
- **Description:** 특정 정책의 상세 공고 내용, 지원 자격, 신청 방법, 첨부 서류 리스트 등을 확인합니다.
- **Response Body (JSON):**

```json
{
  "status": 200,
  "data": {
    "policy_id": "pol-001",
    "content": "상세 모집 요강 텍스트...",
    "support_amount": "최대 400만원",
    "apply_url": "[https://k-startup.go.kr/](https://k-startup.go.kr/)...",
    "required_documents": ["사업자등록증", "부가가치세과세표준증명"]
  }
}
```

- **Error Codes:**
  - `404 Not Found`: 존재하지 않거나 삭제된 정책 ID

---

## 4. 정책 키워드 검색 (Search Policies)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/search`
- **Description:** 정책 제목 또는 내용에서 특정 키워드가 포함된 결과를 검색합니다.
- **Query Params:** `keyword="인공지능"`, `region="서울"`, `category="R&D"`
- **Response Body (JSON):** (전체 목록 조회와 동일 규격)
- **Error Codes:**
  - `400 Bad Request`: 검색 키워드 미입력 또는 유효하지 않은 지역 코드

---

## 5. 관심 정책 즐겨찾기 (Toggle Bookmark)

- **Method:** `POST`
- **Endpoint:** `/api/v1/policies/{id}/bookmark`
- **Description:** 특정 정책을 찜하거나 취소합니다. (Toggle 방식: 이미 있으면 삭제, 없으면 추가)
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**

```json
{
  "status": 200,
  "data": {
    "is_bookmarked": true,
    "policy_id": "pol-001"
  }
}
```

- **Error Codes:**
  - `401 Unauthorized`: 로그인 필요
  - `404 Not Found`: 존재하지 않는 정책 ID에 대한 북마크 시도

---

## 6. 찜한 정책 목록 조회 (Get Bookmarks)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/bookmarks`
- **Description:** 사장님이 즐겨찾기(찜)한 정책들만 모아서 리스트로 확인합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):** (전체 목록 조회와 동일 규격)

---

## 7. 카테고리 목록 조회 (Get Categories)

- **Method:** `GET`
- **Endpoint:** `/api/v1/policies/categories`
- **Description:** 정책 분류 필터링을 위한 카테고리(금융, 기술, 인력, 수출 등) 코드 리스트를 조회합니다.
- **Response Body (JSON):**

```json
{
  "status": 200,
  "data": [
    { "code": "FIN", "name": "금융/자금" },
    { "code": "RND", "name": "R&D/기술" }
  ]
}
```

---

## 🚥 구현 가이드라인 (Implementation Note)

1. **Search Indexing:** 검색 성능을 위해 `title`과 `content` 필드에 대한 Full-text Search 또는 인덱싱 설정을 고려하세요.
2. **Dynamic Matching:** 맞춤형 추천 API 호출 시, 사장님의 최신 재무 스냅샷(02번 섹션) 데이터를 실시간으로 반영해야 합니다.
3. **Response Structure:** 모든 에러 응답은 공통 규격인 `{ "status": 4xx, "error_code": "STRING", "message": "STRING" }`을 따릅니다.
