# 📂 비즈업(Biz-Up) API 상세 명세서: [06. 알림 서비스]

본 문서는 맞춤형 정책 업데이트, AI 상담 답변 완료, 서류 처리 상태 등 사용자에게 전달되는 모든 알림 시스템 구축 가이드라인입니다. 실시간성 확보와 읽음 상태 관리를 원칙으로 합니다.

---

## 1. 내 알림 내역 조회 (Get My Notifications)
- **Method:** `GET`
- **Endpoint:** `/api/v1/notifications`
- **Description:** 로그인한 사용자에게 발송된 전체 알림 리스트를 최신순으로 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Query Params:** `page=1`, `size=20`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "noti_id": "noti-uuid-101",
        "type": "POLICY_MATCH",
        "title": "새로운 맞춤 정책 도착!",
        "content": "사장님 조건에 딱 맞는 '청년 창업 지원금' 공고가 떴습니다.",
        "is_read": false,
        "deep_link": "/policies/pol-005",
        "created_at": "2026-04-02T10:30:00Z"
      }
    ],
    "total_count": 15
  }
}
```
- **Error Codes:**
  - `401 Unauthorized`: 인증 실패

---

## 2. 알림 전체 읽음 처리 (Mark All as Read)
- **Method:** `POST`
- **Endpoint:** `/api/v1/notifications/read-all`
- **Description:** 사용자가 확인하지 않은 모든 알림을 한꺼번에 '읽음' 상태로 변경합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "message": "모든 알림이 읽음 처리되었습니다."
}
```

---

## 3. 안 읽은 알림 개수 조회 (Get Unread Count)
- **Method:** `GET`
- **Endpoint:** `/api/v1/notifications/unread-count`
- **Description:** 홈 화면 종 모양 아이콘에 표시할 '읽지 않은 알림'의 총개수를 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "unread_count": 5
  }
}
```

---

## 4. 알림 개별 읽음 처리 (Read Notifications)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/notifications/{id}/read`
- **Description:** 특정 알림 하나를 클릭했을 때 '읽음' 상태로 업데이트합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "noti_id": "noti-uuid-101",
    "is_read": true
  }
}
```
- **Error Codes:**
  - `404 Not Found`: 존재하지 않는 알림 ID

---

## 5. 알림 설정 조회 (Get Noti Settings)
- **Method:** `GET`
- **Endpoint:** `/api/v1/notifications/settings`
- **Description:** 사용자의 푸시 알림 수신 동의 현황(마케팅, 정책 알림, 상담 알림 등)을 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "push_enabled": true,
    "marketing_enabled": false,
    "policy_update_enabled": true,
    "chat_answer_enabled": true
  }
}
```

---

## 6. 알림 설정 변경 (Update Noti Settings)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/notifications/settings`
- **Description:** 특정 카테고리의 알림 수신 여부를 On/Off 설정합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "marketing_enabled": true,
  "policy_update_enabled": false
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "message": "알림 설정이 변경되었습니다."
}
```

---

## 🚥 구현 가이드라인 (Implementation Note)
1. **Deep Linking:** `deep_link` 필드는 프론트엔드에서 알림 클릭 시 해당 상세 페이지로 즉시 이동할 수 있는 경로를 포함해야 합니다.
2. **Push Service:** 실제 푸시 발송(FCM 등)은 백그라운드 태스크로 처리하여 API 응답 속도에 영향을 주지 않도록 합니다.
3. **Data Retention:** 알림 데이터가 무한정 쌓이지 않도록 일정 기간(예: 90일)이 지난 알림은 자동 삭제하는 배치 로직을 고려하세요.