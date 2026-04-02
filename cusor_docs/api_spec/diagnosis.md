# 📂 비즈업(Biz-Up) API 상세 명세서: [08. 정밀진단 및 시뮬레이션]

본 문서는 사용자의 사업 역량을 수치화하고, 정책 합격 가능성을 예측하는 '정밀진단 엔진' 구축 가이드라인입니다. 데이터 스냅샷 보존과 복잡한 가점 산출 로직 구현을 원칙으로 합니다.

---

## 1. 정밀진단 입력 폼 세팅 (Prepare Diagnosis)
- **Method:** `GET`
- **Endpoint:** `/api/v1/diagnoses/prepare`
- **Description:** 정밀진단을 시작하기 전, 현재 DB에 저장된 사용자의 최신 재무/고용 데이터를 불러와 입력 폼에 자동 세팅합니다. 부족한 정보가 무엇인지 미리 파악하는 용도입니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "current_snapshot": {
      "revenue": 500000000,
      "employee_count": 5,
      "biz_sector": "IT/SW"
    },
    "missing_fields": ["established_at", "military_service"],
    "message": "필수 정보가 일부 누락되었습니다. 보완 후 진단을 시작하세요."
  }
}
```

---

## 2. 정밀진단 실행 및 결과 저장 (Execute Diagnosis)
- **Method:** `POST`
- **Endpoint:** `/api/v1/diagnoses`
- **Description:** 최종 확인된 데이터를 바탕으로 진단 엔진을 가동합니다. 종합 점수를 산출하고 분석 결과를 DB에 영구 저장합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "year": 2025,
  "use_ai_analysis": true,
  "final_inputs": { "revenue": 550000000, "employee_count": 6 }
}
```
- **Response Body (JSON):**
```json
{
  "status": 201,
  "data": {
    "diagnosis_id": "diag-uuid-777",
    "total_score": 85.5,
    "grade": "EXCELLENT",
    "created_at": "2026-04-02T12:00:00Z"
  }
}
```
- **Error Codes:**
  - `400 Bad Request`: 유효하지 않은 입력 데이터 형식
  - `503 Service Unavailable`: 산출 엔진 서버 과부하

---

## 3. 정밀진단 결과 상세 조회 (Get Diagnosis Detail)
- **Method:** `GET`
- **Endpoint:** `/api/v1/diagnoses/{id}`
- **Description:** 특정 시점에 수행된 정밀진단의 상세 수치, 부문별 점수(안정성, 성장성 등), AI의 정밀 코멘트를 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "diagnosis_id": "diag-uuid-777",
    "scores": { "stability": 80, "growth": 90, "tech": 85 },
    "ai_comment": "매출 대비 고용 지표가 우수하여 인건비 지원사업에 최적화된 상태입니다.",
    "snapshot": { "revenue": 550000000, "employees": 6 }
  }
}
```
- **Error Codes:**
  - `404 Not Found`: 존재하지 않는 진단 ID

---

## 4. 진단 이력 조회 (Get Diagnosis History)
- **Method:** `GET`
- **Endpoint:** `/api/v1/diagnoses`
- **Description:** 사용자가 과거에 수행했던 모든 정밀진단 기록을 리스트로 조회하여 점수 변화를 추적합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "diagnosis_id": "diag-uuid-777", "score": 85.5, "date": "2026-04-02" },
    { "diagnosis_id": "diag-uuid-001", "score": 70.2, "date": "2026-01-10" }
  ]
}
```

---

## 5. 진단 기록 삭제 (Delete Diagnosis)
- **Method:** `DELETE`
- **Endpoint:** `/api/v1/diagnoses/{id}`
- **Description:** 불필요해진 과거 진단 데이터를 파기합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body:** (204 No Content)
- **Error Codes:**
  - `403 Forbidden`: 타인의 진단 기록 삭제 시도

---

## 6. 가산점 시뮬레이션 실행 (Execute Simulation)
- **Method:** `POST`
- **Endpoint:** `/api/v1/simulations`
- **Description:** 특정 정책을 선택하고 "인원을 2명 더 뽑는다면?" 같은 가상 조건을 입력하여 합격 확률 변동을 예측합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Request Body (JSON):**
```json
{
  "policy_id": "pol-101",
  "virtual_conditions": { "new_hire": 2, "patent_count": 1 }
}
```
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": {
    "base_rate": 65.0,
    "simulated_rate": 88.5,
    "gain_factors": ["신규 고용 가점 +15점", "특허 보유 가점 +8.5점"]
  }
}
```

---

## 7. 시뮬레이션 이력 조회 (Get Sim Logs)
- **Method:** `GET`
- **Endpoint:** `/api/v1/simulations/history`
- **Description:** 사용자가 시뮬레이션해 본 정책들과 예상 합격률 기록을 조회합니다.
- **Headers:** `Authorization: Bearer {ACCESS_TOKEN}`
- **Response Body (JSON):**
```json
{
  "status": 200,
  "data": [
    { "policy_title": "청년 디지털 일자리", "sim_rate": 88.5, "created_at": "2026-04-02" }
  ]
}
```

---

## 🚥 구현 가이드라인 (Implementation Note)
1. **Calculation Accuracy:** 소수점 둘째 자리까지 점수를 유지하며, 반올림 정책은 전사 공통 가이드라인을 따릅니다.
2. **Snapshot Logic:** 진단이 완료된 시점의 입력 데이터는 `diagnoses_snapshots` 테이블에 따로 저장하여 원본 데이터 수정에 영향을 받지 않도록 합니다.
3. **Async Simulation:** 시뮬레이션 로직이 복잡할 경우 Celery 등 비동기 큐 사용을 검토합니다.