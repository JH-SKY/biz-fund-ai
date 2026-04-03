# 📂 비즈업(Biz-Up) API 상세 명세서: [01. 인증 및 온보딩]

본 문서는 커서(Cursor AI)가 '인증 및 사용자 관리' 시스템을 구축하기 위한 표준 가이드라인입니다. 모든 구현은 아래 정의된 Request/Response 규격 및 에러 코드를 엄격히 준수해야 합니다.

---

## 1. 카카오 로그인 (Kakao Auth)
- **Method:** `POST`
- **Endpoint:** `/api/v1/auth/kakao`
- **Description:** 카카오 OAuth2를 통해 전달받은 액세스 토큰으로 인증을 수행하며, 신규 유저일 경우 자동 회원가입을 처리하고 기존 유저일 경우 로그인을 수행합니다.
- **Request Body (JSON):**
```json
{
  "access_token": "string",
  "device_type": "string"
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "access_token": "jwt_access_token_string",
    "refresh_token": "jwt_refresh_token_string",
    "user_id": "uuid-1234-5678",
    "is_new_user": true
  }
}
```
- **Error Codes:**
  - `401 Unauthorized`: 유효하지 않거나 만료된 카카오 토큰
  - `500 Internal Server Error`: 카카오 API 서버 통신 실패

---

## 2. 네이버 로그인 (Naver Auth)
- **Method:** `POST`
- **Endpoint:** `/api/v1/auth/naver`
- **Description:** 네이버 OAuth2 액세스 토큰을 이용한 인증 및 회원가입/로그인 처리입니다.
- **Request Body (JSON):**
```json
{
  "access_token": "string",`
  "device_type": "string"
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "access_token": "jwt_access_token_string",
    "refresh_token": "jwt_refresh_token_string",
    "user_id": "uuid-5678-1234",
    "is_new_user": false
  }
}
```
- **Error Codes:**
  - `401 Unauthorized`: 유효하지 않은 네이버 인증 정보

---

## 3. 로그아웃 (Logout)
- **Method:** `POST`
- **Endpoint:** `/api/v1/auth/logout`
- **Description:** 현재 사용자의 세션을 종료합니다. 보안을 위해 Redis 등에 저장된 리프레시 토큰을 무효화 처리합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body:** 없음
- **Response Body (JSON):**
```json
{
  "status": 200,
  "message": "성공적으로 로그아웃되었습니다."
}
```
- **Error Codes:**
  - `401 Unauthorized`: 인증되지 않은 사용자 또는 토큰 만료

---

## 4. 회원 탈퇴 (Withdraw Membership)
- **Method:** `DELETE`
- **Endpoint:** `/api/v1/users/withdraw`
- **Description:** 사용자의 계정 정보를 영구 삭제합니다. 연관된 모든 데이터(사업장 정보, 진단 이력 등)를 관계 법령에 의거하여 정리합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body:** 없음 (204 No Content)
- **Error Codes:**
  - `401 Unauthorized`: 권한 없음
  - `500 Internal Server Error`: 데이터 삭제 처리 중 서버 오류

---

## 5. 내 프로필 정보 조회 (Get My Profile)
- **Method:** `GET`
- **Endpoint:** `/api/v1/users/me`
- **Description:** 로그인한 사용자의 마이페이지 구성을 위한 기본 프로필 및 설정 정보를 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "user_id": "uuid-1234",
    "name": "이종혁",
    "email": "ryan@example.com",
    "profile_image": "[https://cdn.bizup.com/profiles/ryan.jpg](https://cdn.bizup.com/profiles/ryan.jpg)",
    "interest_sectors": ["IT", "AI Agent"],
    "is_profile_completed": true
  }
}
```

---

## 6. 추가 프로필 설정 (Complete Profile)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/users/profile`
- **Description:** 정교한 정책 매칭을 위해 군필 여부, 관심 분야, 비전공 여부 등 추가적인 페르소나 정보를 저장합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "military_service": "COMPLETED",
  "interest_sectors": ["IT", "Manufacturing"],
  "is_non_major": true,
  "tech_stack": ["Python", "FastAPI"]
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "updated_at": "2026-04-02T11:12:00Z"
  }
}
```
- **Error Codes:**
  - `400 Bad Request`: 필수 필드 누락 또는 잘못된 데이터 형식