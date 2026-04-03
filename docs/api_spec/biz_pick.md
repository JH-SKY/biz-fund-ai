# 📂 비즈업(Biz-Up) API 상세 명세서: [05. 비즈픽 콘텐츠]

본 문서는 사장님들을 위한 맞춤형 정책 가이드 및 성공 사례 콘텐츠 서비스 구축 가이드라인입니다. 효율적인 콘텐츠 서빙과 사용자 반응(좋아요) 수집을 원칙으로 합니다.

---

## 1. 비즈픽 콘텐츠 목록 조회 (Get Biz-Picks)
- **Method:** `GET`
- **Endpoint:** `/api/v1/contents`
- **Description:** 등록된 모든 비즈픽 콘텐츠 리스트를 조회합니다. 카테고리별 필터링과 페이징을 지원합니다.
- **Query Params:** `category="SUCCESS_STORY"`, `page=1`, `size=10`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "content_id": "cnt-001",
        "title": "도봉구 사장님이 5천만 원 지원받은 비결",
        "thumbnail_url": "[https://cdn.bizup.com/thumb/001.jpg](https://cdn.bizup.com/thumb/001.jpg)",
        "category": "성공사례",
        "view_count": 1250,
        "like_count": 88,
        "is_liked": false,
        "created_at": "2026-04-01T09:00:00Z"
      }
    ],
    "total_count": 450,
    "total_pages": 45
  }
}
```
- **Error Codes:**
  - `400 Bad Request`: 유효하지 않은 카테고리 코드

---

## 2. 콘텐츠 상세 조회 (Get Content Detail)
- **Method:** `GET`
- **Endpoint:** `/api/v1/contents/{id}`
- **Description:** 특정 콘텐츠의 상세 본문 내용과 이미지, 관련 링크 등을 조회합니다. 조회 시 `view_count`가 1 증가합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}` (선택: 좋아요 여부 확인용)
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "content_id": "cnt-001",
    "title": "도봉구 사장님이 5천만 원 지원받은 비결",
    "body_html": "<div>본문 내용...</div>",
    "author": "비즈업 에디터",
    "is_liked": true,
    "related_policies": [
      { "id": "pol-001", "title": "소상공인 특별자금" }
    ],
    "tags": ["도봉구", "성공사례", "지원금"]
  }
}
```
- **Error Codes:**
  - `404 Not Found`: 존재하지 않거나 비공개 처리된 콘텐츠

---

## 3. 오늘의 추천 콘텐츠 (Get Today's Pick)
- **Method:** `GET`
- **Endpoint:** `/api/v1/contents/today`
- **Description:** 메인 화면 최상단에 노출될 '오늘의 추천' 콘텐츠 3개를 랜덤 또는 관리자 지정 로직에 따라 반환합니다.
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "content_id": "cnt-005", "title": "이번 주 꼭 신청해야 할 정책 TOP 3" },
    { "content_id": "cnt-008", "title": "법인 전환 시 주의사항" }
  ]
}
```

---

## 4. 콘텐츠 찜하기 (Toggle Content Like)
- **Method:** `POST`
- **Endpoint:** `/api/v1/contents/{id}/like`
- **Description:** 특정 콘텐츠에 대해 '좋아요'를 누르거나 취소합니다. (Toggle 방식)
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "is_liked": true,
    "total_likes": 89
  }
}
```
- **Error Codes:**
  - `401 Unauthorized`: 로그인 후 이용 가능
  - `404 Not Found`: 대상 콘텐츠 없음

---

## 5. 콘텐츠 카테고리 목록 조회 (Get Content Categories)
- **Method:** `GET`
- **Endpoint:** `/api/v1/contents/categories`
- **Description:** 비즈픽 탭 상단에 표시될 카테고리 탭 리스트를 조회합니다.
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "code": "SUCCESS_STORY", "name": "성공사례" },
    { "code": "POLICY_GUIDE", "name": "정책가이드" },
    { "code": "BIZ_TIP", "name": "운영꿀팁" }
  ]
}
```

---

## 🚥 구현 가이드라인 (Implementation Note)
1. **View Counting:** 중복 조회수 증가 방지를 위해 클라이언트 세션 또는 쿠키 기반의 어뷰징 방지 로직을 권장합니다.
2. **HTML Sanitization:** `body_html` 제공 시 XSS 공격 방지를 위해 서버 단에서 Sanitize 처리를 거쳐야 합니다.
3. **Image Optimization:** 썸네일 URL은 가급적 CDN을 통해 최적화된 크기로 제공되어야 합니다.