# 📂 비즈업(Biz-Up) API 상세 명세서: [04. 비즈몽 AI 상담]

본 문서는 사장님들을 위한 AI 정책 상담 에이전트 '비즈몽'과의 대화 시스템 구축 가이드라인입니다. 세션 기반의 대화 관리와 RAG(검색 증강 생성) 기반의 정확한 답변 제공을 원칙으로 합니다.

---

## 1. 상담 세션 생성 (Create Chat Session)
- **Method:** `POST`
- **Endpoint:** `/api/v1/chats/sessions`
- **Description:** 비즈몽과 새로운 상담을 시작하기 위한 세션을 생성합니다. 각 세션은 고유한 ID를 가지며 대화의 맥락(Context)을 유지합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):** ```json
{
  "initial_message": "정부지원금에 대해 물어보고 싶어요"
}
```
- **Response Body (JSON):**
```json
{
  "status": 201,
  "data": {
    "session_id": "session-uuid-001",
    "title": "새로운 상담",
    "created_at": "2026-04-02T11:30:00Z"
  }
}
```
- **Error Codes:**
  - `401 Unauthorized`: 로그인 필요
  - `429 Too Many Requests`: 단시간 내 과도한 세션 생성 시 제한

---

## 2. 상담 세션 목록 조회 (Get Chat Sessions)
- **Method:** `GET`
- **Endpoint:** `/api/v1/chats/sessions`
- **Description:** 사용자가 과거에 진행했던 모든 상담 세션 리스트를 최신순으로 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    {
      "session_id": "session-uuid-001",
      "title": "고용지원금 상담 (2026-04-02)",
      "last_message": "감사합니다 사장님!",
      "updated_at": "2026-04-02T11:35:00Z"
    }
  ]
}
```
- **Error Codes:**
  - `401 Unauthorized`: 인증 실패

---

## 3. 메시지 전송 및 답변 수신 (Send Message)
- **Method:** `POST`
- **Endpoint:** `/api/v1/chats/sessions/{session_id}/messages`
- **Description:** 특정 세션에서 비즈몽에게 질문을 던지고 AI의 답변을 수신합니다. 내부적으로 RAG 로직이 작동하여 정책 데이터를 참조합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "message": "우리 회사가 받을 수 있는 인건비 지원금이 있을까?"
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "message_id": "msg-uuid-555",
    "role": "assistant",
    "content": "사장님, 현재 사업장 정보를 보니 '청년추가채용장려금' 대상이 될 가능성이 높습니다!",
    "referenced_policies": [
      { "id": "pol-005", "title": "청년추가채용장려금" }
    ],
    "created_at": "2026-04-02T11:31:00Z"
  }
}
```
- **Error Codes:**
  - `404 Not Found`: 존재하지 않는 상담 세션 ID
  - `503 Service Unavailable`: AI 모델 또는 RAG 엔진 응답 지연

---

## 4. 특정 상담 대화 이력 조회 (Get Chat Messages)
- **Method:** `GET`
- **Endpoint:** `/api/v1/chats/sessions/{session_id}/messages`
- **Description:** 특정 상담 세션에서 오고 간 유저와 AI의 모든 대화 내역을 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "role": "user", "content": "안녕?" },
    { "role": "assistant", "content": "안녕하세요 사장님! 무엇을 도와드릴까요?" }
  ]
}
```

---

## 5. 상담 제목 자동 요약 (Auto Summary)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/chats/sessions/{session_id}/summary`
- **Description:** 대화 내용을 바탕으로 상담 리스트에 표시될 적절한 제목을 AI가 자동으로 생성하여 업데이트합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "new_title": "IT 창업 인건비 지원 사업 문의"
  }
}
```

---

## 6. 상담 세션 삭제 (Delete Chat Session)
- **Method:** `DELETE`
- **Endpoint:** `/api/v1/chats/sessions/{session_id}`
- **Description:** 더 이상 필요 없는 상담 이력을 삭제합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body:** (204 No Content)
- **Error Codes:**
  - `403 Forbidden`: 타인의 상담 세션 삭제 시도

---

## 🚥 구현 가이드라인 (Implementation Note)
1. **Context Management:** AI 답변 생성 시 해당 `session_id`의 과거 대화 내역(최근 5-10개)을 모델에 전달하여 문맥을 유지하세요.
2. **Streaming Support:** (추후 고려) 답변이 길어질 경우를 대비해 `Server-Sent Events(SSE)`를 통한 스트리밍 응답 구조를 염두에 둡니다.
3. **Policy Linking:** 답변 내용에 정책 언급이 있을 경우, 반드시 `referenced_policies` 필드에 ID를 포함하여 상세 페이지 이동을 지원하세요.