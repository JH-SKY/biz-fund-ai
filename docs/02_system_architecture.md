# 🏗️ System Architecture (02_system_architecture.md)

> **Core Concept**
> FastAPI와 PostgreSQL 기반의 고성능 백엔드와 RAG(검색 증강 생성) 엔진을 결합한 **지능형 정책자금 매칭 서비스** 아키텍처

---

## 1. 기술 스택 (Technology Stack)

### 🖥️ Frontend
* **Framework**: `React.js (v18+)`
* **Routing**: `React Router DOM` (Single Page Application 구조)
* **State Management**: `Axios` (HTTP Client), `React Query` (Server State Management 권장)
* **Styling**: `Tailwind CSS` (Utility-first CSS)

### ⚙️ Backend
* **Framework**: `Python FastAPI` (Asynchronous Server Gateway Interface)
* **Validation**: `Pydantic` (Data Parsing & Strict Typing)
* **ORM**: `SQLAlchemy 2.0` (Database Abstraction Layer)
* **Environment**: `uv` (Next-generation Python Package Installer & Resolver)

### 🧠 Database & AI Engine
* **RDB**: `PostgreSQL` (Relational Database Management System)
* **Vector DB**: `pgvector` (PostgreSQL Extension for Vector Similarity Search)
* **AI/LLM**: `OpenAI GPT-4o` (Reasoning), `Text-Embedding-3-Small` (Vectorizing)
* **Orchestration**: `LangChain` (RAG Pipeline Management)

---

## 2. 시스템 통합 구조 (System Architecture)

### 2.1 전체 구조도 (High-Level Architecture)
서비스는 **클라이언트-서버 모델**을 따르며, 외부 API 및 AI 모델과 유기적으로 통신합니다.

1. **Client Tier**: React 기반 웹 인터페이스가 사용자 경험을 담당.
2. **API Tier**: FastAPI 서버가 비즈니스 로직 처리, 인증(JWT), 외부 API 연동 수행.
3. **Data Tier**: PostgreSQL이 정형 데이터(User, Biz Info)와 비정형 데이터(Policy Embedding)를 통합 관리.

### 2.2 보안 아키텍처 (Security)
실제 서비스 운영이 가능한 수준의 보안성을 확보하면서, 유지보수가 용이한 구조를 지향합니다.

| 구분 | 전략 및 기술 | 상세 설명 |
| :--- | :--- | :--- |
| **인증(Auth)** | **Dual Token Strategy** | 단기 Access Token(30분) 및 장기 Refresh Token(7일) 분리 발급 |
| **토큰 저장** | **Token Storage** | Access는 메모리(State), Refresh는 보안 쿠키(HttpOnly)에 저장하여 XSS 방어 |
| **권한 관리** | **Dependency Injection** | FastAPI의 `Depends(get_current_user)`를 활용한 엔드포인트 보호 |
| **데이터 보호** | **Environment Variables** | `python-dotenv`를 통해 민감 정보(API Key, DB 접속문자열) 분리 관리 |
| **접근 제어** | **CORS Policy** | FastAPI 미들웨어를 통해 허용된 프론트엔드 도메인의 요청만 수락 |
| **비밀번호** | **BCrypt Hashing** | `passlib`의 BCrypt 알고리즘을 사용한 단방향 솔팅(Salting) 암호화 저장 |

---

## 3. 핵심 데이터 플로우 (Data Flow)

### 3.1 사용자 온보딩 및 데이터 동기화
1. **Request**: 클라이언트가 **사업자등록번호** 전송.
2. **External API**: 서버에서 **국세청 API** 호출하여 진위 확인 및 기업 기본정보(업종, 소재지 등) 수집.
3. **Persistence**: 수집된 데이터를 Pydantic으로 검증 후 **PostgreSQL**에 영속화.

### 3.2 RAG 기반 정책 자금 상담 (AI Workflow)
* **Step 1. Retrieval**: 유저 질문을 임베딩하여 `pgvector` 내 정책 공고 데이터와 유사도 검색 수행.
* **Step 2. Augmentation**: 검색된 공고 원문과 유저 프로필(매출, 업종)을 프롬프트에 결합.
* **Step 3. Generation**: LLM이 개인화된 답변을 생성하여 인터페이스로 반환.

---

## 4. 인프라 및 운영 환경 (Infrastructure)
* **Version Control**: `Git` / `GitHub` (Feature Branch 전략)
* **Package Manager**: `uv` (Python), `npm` (JavaScript)
* **Editor**: `Visual Studio Code` (Workspace 정규화)