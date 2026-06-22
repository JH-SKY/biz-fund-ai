# 📂 비즈업(Biz-Up) API 상세 명세서: [02. 사업장 데이터 및 서류 관리]

본 문서는 사장님의 사업장 기본 정보, 재무 지표, 증빙 서류 관리를 위한 통합 API 가이드라인입니다. 모든 구현은 아래 정의된 데이터 규격 및 비즈니스 로직을 엄격히 준수해야 합니다.

---

### 🛡️ 데이터 보존 및 연계 정책 (비즈니스 로직)
1. **Soft Delete 원칙**: 유저 데이터를 물리적으로 즉시 삭제하지 않고 `is_active=False` 상태로 관리합니다.
2. **연관 데이터 유지**: 탈퇴 시 '사업장 정보(Business)', '채팅 이력(Chat)' 등은 삭제하지 않고 그대로 유지합니다.
   - *이유*: 재가입 시 데이터 복구 편의성 및 정책 매칭 통계 데이터 확보.
3. **조회 제한**: 향후 모든 도메인 API(사업장 조회 등)는 호출 시 유저의 `is_active` 상태를 확인하여, 탈퇴한 유저의 데이터는 응답에서 제외해야 합니다.

---

## 1. 사업장 정보 조회 (Get Business Info)
- **Method:** `GET`
- **Endpoint:** `/api/v1/businesses/me`
- **Description:** 로그인한 사용자의 사업장 기본 정보(상호명, 사업자번호, 대표자, 주소 등)를 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body:** 없음
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "biz_id": "uuid-9999",
    "company_name": "라이언테크",
    "biz_number": "123-45-67890",
    "representative_name": "이종혁",
    "address": "서울특별시 도봉구 마들로 13길 61",
    "established_at": "2024-01-01"
  }
}
```
- **Error Codes:**
  - `401 Unauthorized`: 인증 토큰 유효하지 않음
  - `404 Not Found`: 등록된 사업장 정보가 없음

---

## 2. 사업장 정보 수정 (Update Business Info)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/businesses/me`
- **Description:** 사업장 상호명, 주소, 대표자 성명 등 기본 인적 사항을 수정합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "company_name": "string",
  "address": "string",
  "representative_name": "string"
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "message": "사업장 정보가 성공적으로 업데이트되었습니다."
}
```

---

## 3. 사업자 번호 확인 (Verify Business)
- **Method:** `POST`
- **Endpoint:** `/api/v1/onboarding/verify-biz`
- **Description:** 공공 데이터 포털 API를 통해 입력된 사업자 번호의 진위 여부 및 휴폐업 상태를 실시간 확인합니다.
- **Request Body (JSON):**
```json
{
  "biz_number": "1234567890"
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "is_valid": true,
    "company_name": "라이언테크",
    "biz_status": "활동중",
    "open_date": "20240101"
  }
}
```

---

## 4. 신규 재무 정보 등록 (Create Finance Stats)
- **Method:** `POST`
- **Endpoint:** `/api/v1/businesses/finance`
- **Description:** 특정 연도의 매출액, 영업이익, 자본금 등 재무 데이터를 최초로 시스템에 등록합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "year": 2025,
  "revenue": 500000000,
  "operating_profit": 50000000,
  "capital": 100000000
}
```
- **Response Body (JSON):**
```json
{
  "status": 201,
  "data": {
    "finance_id": "uuid-finance-001",
    "year": 2025
  }
}
```

---

## 5. 재무 및 고용 정보 업데이트 (Update Finance & HR)
- **Method:** `PATCH`
- **Endpoint:** `/api/v1/businesses/finance/{year}`
- **Description:** 이미 등록된 특정 연도의 재무 수치나 현재 시점의 상시 근로자 수(HR)를 수정합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "revenue": 600000000,
  "employee_count": 8,
  "operating_profit": 55000000
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "message": "재무 및 고용 정보가 갱신되었습니다."
}
```

---

## 6. 과거 재무 이력 조회 (Get Finance History)
- **Method:** `GET`
- **Endpoint:** `/api/v1/businesses/finance/history`
- **Description:** 유저가 등록한 연도별 재무 및 고용 지표 전체 리스트를 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "year": 2024, "revenue": 300000000, "employee_count": 5 },
    { "year": 2025, "revenue": 500000000, "employee_count": 8 }
  ]
}
```

---

## 7. 재무 스냅샷 삭제 (Delete Finance Snapshot)
- **Method:** `DELETE`
- **Endpoint:** `/api/v1/businesses/finance/{year}`
- **Description:** 잘못 입력되었거나 불필요한 특정 연도의 재무 레코드를 영구 삭제합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 204,
  "message": "해당 연도의 데이터가 삭제되었습니다."
}
```

---

## 8. 매출/인원 입력값 실시간 검증 (Validate Stats)
- **Method:** `POST`
- **Endpoint:** `/api/v1/businesses/validate`
- **Description:** 매출액이나 고용 인원 입력 시, 업종 평균 대비 이상치 여부를 판단하여 사용자에게 경고 피드백을 제공하기 위한 검증 로직입니다.
- **Request Body (JSON):**
```json
{
  "type": "REVENUE",
  "value": 10000000000
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "is_valid": true,
  "message": "정상 범위의 입력값입니다."
}
```

---

## 9. 디지털 서류 업로드 (Upload Document)
- **Method:** `POST`
- **Endpoint:** `/api/v1/documents`
- **Description:** 증빙 서류 파일을 업로드하고 `documents` 레코드를 생성합니다. 현재 응답 상태는 `PENDING`으로 시작하며, OCR 워커 연동은 향후 확장 예정입니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (Multipart/form-data):**
  - `file`: (Binary File) PDF, JPG, PNG
  - `document_type`: `string` (`BIZ_REG`, `VAT_CERT`, `FINANCIAL_STAT`)
- **Response Body (JSON):**
```json
{
  "status": 202,
  "data": {
    "document_id": "doc-uuid-101",
    "status": "PENDING"
  }
}
```

---

## 10. 내 서류함 조회 (Get My Documents)
- **Method:** `GET`
- **Endpoint:** `/api/v1/documents`
- **Description:** 사장님이 보관 중인 모든 서류의 목록과 저장된 상태값(`PENDING` 등)을 확인합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    {
      "document_id": "doc-uuid-101",
      "document_type": "BIZ_REG",
      "status": "COMPLETED",
      "created_at": "2026-04-02T10:00:00Z"
    }
  ]
}
```

---

## 11. 서류 상세 조회 (Get Document Detail)
- **Method:** `GET`
- **Endpoint:** `/api/v1/documents/{id}`
- **Description:** 특정 서류의 파일 URL과 저장된 OCR 결과 필드(`ocr_data`, 존재 시)를 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "document_id": "doc-uuid-101",
    "file_url": "[https://s3.bizup.com/docs/file.pdf](https://s3.bizup.com/docs/file.pdf)",
    "ocr_data": {
      "biz_num": "123-45-67890",
      "owner": "이종혁",
      "company_name": "라이언테크"
    }
  }
}
```

---

## 12. 서류 삭제 (Delete Document)
- **Method:** `DELETE`
- **Endpoint:** `/api/v1/documents/{id}`
- **Description:** 특정 서류를 파기합니다. 본인 소유 확인 후 스토리지의 실제 파일과 DB 레코드를 모두 삭제합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 204,
  "message": "서류가 영구 삭제되었습니다."
}
```
