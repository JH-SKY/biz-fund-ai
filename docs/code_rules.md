# 🏗️ 비즈업(Biz-Up) 백엔드 코드 구조 규칙서 (Cursor AI Guide)

## 0. 기본 전제

- 당신은 FastAPI 기반 **비동기(Async) 실무 백엔드 엔지니어**다.
- 이 프로젝트는 실제 서비스 운영을 목표로 한다.
- “예시 코드”, “간단 구현”, “mock”은 절대 금지하며, 즉시 배포 가능한 수준의 코드를 작성한다.

---

## 1. 아키텍처 원칙 (필수)

### 1.1 계층 구조 및 흐름

- 반드시 다음 구조를 엄격히 따른다: **router → service → repository → database**
- **Router:** 요청(Request)을 받고 응답(Response)을 반환하는 창구 역할만 수행.
- **Service:** 실제 비즈니스 로직, 데이터 가공, 트랜잭션 관리를 수행.
- **Repository:** 데이터베이스(ORM)에 직접 접근하는 유일한 계층.

프로젝트는 기능 단위로 응집된 **도메인 중심 구조**를 따른다.

```
app/
├── api/v1/             # 외부 노출 API 엔드포인트 (Router)
│   ├── user_router.py
│   └── admin_router.py
├── domains/            # 핵심 비즈니스 로직 (도메인별 격리)
│   ├── user/
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── schema.py
│   │   └── exception.py
│   └── admin/
│       ├── service.py
│       └── ...
├── models/             # DB 모델 (중앙 관리 - 기존 파일 유지)
│   ├── auth/
│   ├── chat/
│   └── ...
```

### 1.2 책임 분리 및 금지 사항

- **Router:** DB 객체(Session) 접근 금지, 복잡한 로직 작성 금지.
- **Service:** SQL 알케미 모델(ORM) 직접 조작 금지, 오직 Repository를 통해서만 데이터 소통.
- **Repository:** 비즈니스 판단 금지, 오직 CRUD 및 데이터 필터링만 수행.

### 1.3 비동기 및 의존성 주입 (Dependency Injection)

- **비동기 처리:** 모든 함수는 `async def`로 선언하며, DB 호출 및 서비스 간 호출 시 반드시 `await`를 사용한다.
- **DI 방식:** 모든 계층 간 호출은 FastAPI의 `Depends`를 활용한다.
- **객체 관리:** Service와 Repository는 클래스(Class) 형태로 정의하며, 필요한 의존성을 생성자(`__init__`)나 `Depends`를 통해 주입받는다.


### 1.4 엔진 확장성 (Future-Proof for RAG/Agent)
- **Decoupling AI Logic**: 채팅(Chat) 및 진단(Diagnosis) 도메인의 Service 레이어는 실제 AI 추론 로직(LLM, RAG)과 철저히 분리한다.
- **Interface Driven**: Service는 Engine 인터페이스(추상화)를 호출하며, 현재는 Mock 데이터를 반환하도록 구현한다. (나중에 엔진 내부만 교체해도 기존 서비스 코드가 깨지지 않아야 함)
- **Async Handling**: AI 연산은 고부하/장시간 작업이므로, 모든 관련 흐름은 async/await 기반의 비동기 파이프라인으로 설계한다.
- **Selective Extension**: AI 피드백, 외부 데이터 연동, 또는 업종별 가변 데이터가 발생하는 핵심 도메인(User, Business, Policy, Chat, Diagnosis, Match) 모델에 한하여 metadata (JSONB) 필드를 포함한다. 단순 로그성 테이블은 정규화된 컬럼만 사용한다.

---

## 2. 파일 생성 및 참조 규칙

API 도메인 생성 시 반드시 다음 파일 세트를 확인/생성한다:

1. **router.py:** API 엔드포인트 정의
2. **service.py:** 비즈니스 로직 구현
3. **repository.py:** DB 접근 로직 구현
4. **schema.py:** Pydantic 모델 (Request/Response DTO)
5. **exception.py:** 해당 도메인 전용 커스텀 에러 정의

**[Model 참조 규칙]**

- **기존 도메인:** `model.py`가 이미 존재한다면 절대 새로 생성하지 말고 기존 모델을 `import`하여 사용한다.
- **모델 수정:** 필드 추가 등 모델 변경이 필요할 경우, 반드시 사용자에게 먼저 제안하고 승인을 받은 후에만 수정한다.

---

## 3. 데이터베이스 및 응답 표준

### 3.1 비동기 DB 설정

- **ORM:** `SQLAlchemy 2.0` 이상 사용.
- **Session:** `AsyncSession`을 사용하며, `postgresql+asyncpg` 드라이버를 기준으로 코드를 작성한다.

### 3.2 공통 응답 포맷 (Base Response)

- 모든 API 응답은 일관된 JSON 구조를 유지해야 한다.
- 공통 스키마 예시:
  ```json
  {
    "status": 200,
    "data": { ... },
    "message": "success"
  }
  ```

---

## 4. 세부 구현 규칙

### 4.1 Schema (Pydantic)

- Request용 스키마와 Response용 스키마를 명확히 분리한다.
- 모든 필드에는 적절한 Type Hint와 설명을 추가한다.

### 4.2 인증 및 보안

- JWT (Access & Refresh Token) 방식을 사용한다.
- Refresh Token은 반드시 DB 또는 Redis에 저장하는 로직을 포함한다.
- 관리자 API의 경우 `is_admin` 권한 체크 로직을 필수 포함한다.

### 4.3 네이밍 규칙

- 함수/변수: `snake_case` (예: `get_business_by_id`)
- 클래스: `PascalCase` (예: `BusinessService`)
- 변수명은 실무에서 사용하는 의미 있는 영문명을 사용한다.

### 4.4 주석 및 문서화 규칙

- Docstring: 모든 함수 상단에는 기능 요약, 파라미터 설명, 리턴 값 타입을 명시하는 Python 표준 Docstring을 작성한다.
- **설계 의도 설명:** 해당 코드가 왜 존재하는지 이유(Why)를 주석으로 명시한다.

---

## 5. 출력 및 보고 규칙 (Output Protocol)

코드 생성 시 반드시 아래 순서를 지켜서 응답한다:

1. **파일 구조 트리:** 생성/수정될 파일 위치 표시
2. **전체 코드:** 각 파일의 전체 소스 코드 (생략 금지)
3. **ASSUMPTION:** 문서에 명시되지 않아 임의로 가정한 사항 (반드시 목록화)
4. **TODO:** 추가로 구현해야 하거나 보완이 필요한 사항
5. **리스크 포인트:** 성능 저하 우려나 보안상 주의가 필요한 지점

---

## 6. ASSUMPTION 가이드 (임의 판단 금지)

- 문서에 없는 내용은 반드시 질문하거나 `ASSUMPTION` 섹션에 명시한다.
- 예: "Refresh Token 저장 위치를 알 수 없어 DB Table에 저장하는 것으로 가정함."
