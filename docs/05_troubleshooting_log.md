# [Issue-01] FastAPI 도메인 격리 과정에서 발생한 순환 참조(Circular Import) 문제와 아키텍처 구조 개선
> **핵심 요약:** 도메인 설계 변경(Hard Delete → Soft Delete) 이후 서비스 간 협력이 필요해졌고, 순환 참조 문제를 메서드 주입(Method Injection)과 라우터 오케스트레이션(Orchestration) 패턴을 통해 해결했다.

### 1. 현상 파악 (Symptom)
- **발생 상황:** 초기 설계는 유저 탈퇴 시 데이터를 즉시 삭제하는 Hard Delete 방식이었지만, 통계 보존을 위해 **논리 삭제(Soft Delete)**로 변경되었다. 유저(`User`) 탈퇴 시 해당 사업장(`Business`) 데이터도 함께 비활성화(`is_active=False`)해야 했고, 도메인 원칙상 `AuthService`가 `BusinessService`에 처리를 위임하는 구조가 필요했다.
- **대표 에러 메시지:** `ImportError: cannot import name 'get_business_service' from partially initialized module (most likely due to a circular import)`
- **사용자 가치 영향:** 해결하지 않을 경우, 탈퇴 유저의 사업장 정보가 '활성' 상태로 남는 고아 데이터(Orphan Data)가 발생하여 데이터 무결성이 깨지고 후속 통계 오류가 발생한다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 시도: 생성자 주입(Constructor Injection)**
  - **가설:** `AuthService`가 생성될 때 `BusinessService`가 필요하므로 생성자 시점에 의존성을 주입하면 된다고 판단했다.
  - **검증 결과:** `Auth` 도메인이 `Business`를, `Business` 도메인이 현재 유저 확인을 위해 다시 `Auth`를 참조하는 순환 루프 발생.
  - **잘못된 점:** 아키텍처의 근본적인 의존 방향이 잘못된 것을 보지 못하고 양방향 연결을 시도했다.

- **2차 시도: `if TYPE_CHECKING` 블록으로 우회**
  - **가설:** 정적 타입 검사기가 만족하도록 TYPE_CHECKING 블록 안에 임포트를 숨기면 순환 참조를 피할 수 있을 것이라 판단했다.
  - **검증 결과:** `NameError: name 'get_business_service' is not defined` 발생.
  - **잘못된 점:** FastAPI의 `Depends()`는 런타임(Runtime)에 실제 객체의 메모리 주소가 필요하다. 코드만 숨기는 `TYPE_CHECKING`으로는 런타임 의존성을 해결할 수 없었다.

### 3. 해결 방안 (Resolution)
- **핵심 해결책:** `AuthService` 생성자에서 `BusinessService` 의존성을 제거하고, `withdraw` 메서드 호출 시점에 인자로 객체를 전달받는 **메서드 주입(Method Injection)** 방식으로 변경했다.
- **추가 해결:** 하위 서비스 레이어에서 서로를 참조하지 않도록 의존성을 제거하고, 두 도메인을 모두 알아도 되는 **Router를 오케스트레이터(Orchestrator)**로 활용하여 결합을 조율했다.
- **적용 코드:**

```python
# [Service Layer] 타 도메인 서비스를 직접 의존하지 않고 인자로 주입받음
class AuthService:
    def __init__(self, session: AsyncSession, repo: AuthRepository):
        self._session = session
        self._repo = repo

    async def withdraw(self, user: User, business_service: Any = None):
        await self._repo.soft_delete_user(user)
        if business_service:
            # 도메인 경계를 넘지 않고 인터페이스를 통해 호출
            await business_service.deactivate_all_businesses_by_user(user.id)
        await self._session.commit()

# [Router Layer] 두 도메인의 결합을 조율하는 컨트롤 타워
@router.delete("/withdraw", status_code=204)
async def withdraw(
    current_user: CurrentUser,
    svc: Annotated[AuthService, Depends(get_auth_service)],
    biz_svc: Annotated[BusinessService, Depends(get_business_service)]
):
    # 아키텍처 경계를 넘지 않고 라우터가 조율함
    await svc.withdraw(current_user, business_service=biz_svc)
    return Response(status_code=204)
```

### 4. 기술적 회고 및 성장 (Retrospective)
- **실무 포인트:** 도메인 간 직접적인 참조가 사라지면서 변경에 유연하고, 특정 도메인의 변경이 다른 도메인에 영향을 미치지 않는 **느슨한 결합(Loose Coupling)**을 달성했다. 또한, 테스트 코드 작성 시 Mock 객체를 주입하기 훨씬 쉬운 구조가 됐다.
- **새롭게 배운 점:**
    1. **Runtime vs Static Check:** 정적 타입 검사기의 `TYPE_CHECKING`은 컴파일 타임 검사이지만, FastAPI의 `Depends`처럼 런타임에 객체를 생성하는 프레임워크 특성 아래에서는 효력이 없다는 것을 배웠다.
    2. **Inversion of Control (IoC):** 하위 레이어에서 의존성을 해결하려 하지 않고, 상위 레이어로 제어권을 끌어올려 함께 조율해야 한다는 것을 체득했다.
- **포트폴리오 활용도:** 메시지 큐(MQ)를 사용한 이벤트 기반 방식이 결합도를 낮추는 이상적인 방법이지만, 현재 프로젝트 단계에서는 과도한 오버엔지니어링이다. `Depends`를 사용한 오케스트레이션이 불필요한 의존성 없이 도메인 원칙을 지킬 수 있는 실용적 선택이었다.

---


# [Issue-02] 배치 작업 중 롤백(Rollback) 사용으로 인한 데이터 유실 현상 해결
> **핵심 요약:** 대량 데이터 저장 중 발생한 중복 키 에러를 처리하기 위해 `session.rollback()`을 호출했다가, 이전에 성공했던 데이터들까지 모두 사라지는 원자성 함정을 UPSERT 패턴으로 해결했다.

### 1. 현상 파악 (Symptom)
- **발생 상황:** 외부 API로부터 수집한 공고 데이터를 대량으로 DB에 저장하는 배치(Batch) 작업을 실행했을 때, 이미 DB에 존재하는 데이터에서 'UniqueViolationError'가 발생했다. 중복을 피하기 위해 예외 처리 구문에서 `session.rollback()`을 호출했다.
- **대표 에러 메시지:** `sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint`
  - **원인:** 공고의 고유 번호가 이미 존재하는 데이터에서 `INSERT`를 시도하여 DB 제약 조건에 걸려 에러 발생.
- **사용자 가치 영향:** 로그상으로는 성공 로그(`success_cnt`)가 1,282건으로 찍혔지만, 실제 DB에는 최대 300여 건밖에 데이터가 없었다. 사용자에게 노출하는 정보를 최신화하고, 정상적인 수집 공고를 실제 서비스에 사용하기 위해 호출하지 않는 쓸모없는 상태가 됐다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 시도: 예외 처리 루프 후 롤백 호출**
  - **가설:** 중복 에러가 발생하면 DB 상태를 초기화한 뒤 다음 작업을 실행하면 되리라 판단했다.
  - **검증 결과:** 에러 없이 루프가 진행됐지만, 데이터가 다시 원점으로 유실됐다.
  - **잘못된 점:** **트랜잭션의 원자성(Atomicity)**을 이해하지 못했다. 롤백은 에러가 난 '한 건만 취소'하는 것이 아니라, 마지막 커밋(Commit) 시점 이후의 모든 작업을 '전부 되돌리는' 것이다.

- **2차 시도: 중복 상황을 '예외'가 아닌 '정상 흐름'으로 처리**
  - **가설:** 에러가 발생했을 때 Except로 잡아서 롤백을 제거했다. 예컨대 에러가 발생하지 않도록 DB 조회에서 처리하는 방식을 고민했다.

### 3. 해결 방안 (Resolution)
- **핵심 해결책 (UPSERT 도입):** `ON CONFLICT (공고번호) DO UPDATE` 구문을 사용하는 **UPSERT** 패턴을 도입했다. 중복이 발생하면 에러를 던지는 대신 기존 데이터를 업데이트하도록 하여 원자성의 문제를 근본적으로 해소했다.
- **추가 해결(트랜잭션 범위 재설계):** 롤백의 범위를 명확히 구분하고, 적절한 배치 사이즈(Batch Size)로 커밋을 수행하도록 했다. 중복 가능성이 있는 곳에서 예외 처리가 아닌 UPSERT(의도된 저장 방식 적용)에서 해결하도록 구조를 개선했다.
- **적용 코드:**

```python
# [수정 전 데이터 유실 원인]
for data in policy_list:
    try:
        session.add(Policy(**data))
        session.flush()  # 여기서 충돌 에러 발생 시
    except IntegrityError:
        session.rollback()  # 잘못된 시도: 이전 성공 데이터까지 모두 롤백됨

# [수정 후 ON CONFLICT를 사용한 안전한 저장]
from sqlalchemy.dialects.postgresql import insert

stmt = insert(Policy).values(policy_list)
upsert_stmt = stmt.on_conflict_do_update(
    index_elements=['policy_id'],  # 충돌의 기준이 되는 고유 컬럼
    set_={
        'title': stmt.excluded.title,
        'content': stmt.excluded.content,
        'updated_at': datetime.now()
    }
)
await session.execute(upsert_stmt)
await session.commit()
```

### 4. 기술적 회고 및 성장 (Retrospective)
- **실무 포인트:** 다시 시도하고 실패할 때 롤백하는 방식에서 DB 고유 기능의 UPSERT를 사용하는 방식으로 전환하여 오류 건수가 줄어들고 데이터 유실 없이 1,282건을 의도한 대로 모두 저장할 수 있게 됐다.
- **새롭게 배운 점:**
    1. **트랜잭션의 원자성(Atomicity):** 롤백은 특정 시점이 아닌 '마지막 커밋' 이후의 모든 변경을 되돌리는 것임을 배웠다.
    2. **Idempotency(멱등성):** 동일한 작업을 여러 번 실행해도 결과가 항상 같아야 하는 배치 작업에서 UPSERT가 얼마나 적절한 해결책인지 체득했다.
- **포트폴리오 활용도:**
    - **로그와 실제 데이터의 괴리:** "코드가 에러 없이 실행됐다고 로그가 '데이터가 채워졌다'는 것을 보장하지 않는다"는 것을 배웠다. 항상 실제 결과물(DB)과 코드의 실행 결과(Log)를 교차 검증하는 습관이 필요하다.
    - **예외 처리보다 멱등성 설계 우선:** 중복 처리를 `try-except`로 회피하려는 것보다, DB 고유 기능을 사용한 정상적인 멱등성 있는 방법에서 해결하는 것이 아키텍처적으로 더 올바른 접근이라는 것을 배웠다.

---

# [Issue-03] 외부 API 데이터 신뢰성과 파일 처리 복원력(Resilience) 확보
> **핵심 요약:** API 응답의 요약 정보와 실제 파일 다운로드의 신뢰성 문제를 'Magic Number 탐지'와 '중첩 트랜잭션(SAVEPOINT)'으로 해결하여 RAG 시스템의 데이터 완결성을 높였다.

### 1. 현상 파악 (Symptom)
- **발생 상황:** 기업마당(비즈인포) API를 사용해 수집한 공고를 파싱할 때, API가 제공하는 요약 정보(`bsnsSumryCn`)만으로는 RAG(검색 증강 생성) 시스템이 필요한 충분한 정보가 담기지 않았다. 더 상세한 정보(지원 자격, 신청 방법 등 첨부 파일 내용)가 필요했지만, 제공되는 URL이 실제로 존재하지 않거나 실제 파일과 일치하지 않는 데이터가 있어 파싱에 실패했다.
- **대표 에러 메시지:**
  1. `UnsupportedFileError: Unknown file signature for URL /getImageFile.do` (확장자와 달리 실제 파일 탐지 실패)
  2. `DataLossWarning: Total rollback occurred due to single item failure` (단일 실패가 전체 배치 취소로 이어짐)
- **사용자 가치 영향:** 이 문제가 해결되지 않으면 사용자가 AI에게 "공고에 관한 구체적인 신청 조건"을 묻더라도 요약 정보 기반으로 답변하거나, 파싱 시스템의 소수 에러로도 전체 작업이 중단되어 데이터 완결성에 심각한 문제가 생겼다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 시도: API 응답 기반 직접 파싱**
  - **가설:** API 응답에 포함된 요약 정보와 파일 경로(`fileNm`)만 참고하여 직접적인 파싱 흐름을 구현했다.
  - **검증 결과:** GPT가 공고문의 세부 내용을 파악하지 못해 답변 품질이 낮았고, 실제로 없는 URL 상황에서는 파싱 실패가 발생했다.
  - **잘못된 점:** API 응답이 '제공한다고 명시되어 있으면 실제 파일 경로도 항상 유효할 것'이라 생각해 데이터를 신뢰한 '낙관적 상태'였다.

- **2차 시도: 확장자 기반 파일 탐지 시도**
  - **가설:** 파일명 확장자(`.pdf`, `.hwp`)를 기반으로 탐지 로직을 작성했다.
  - **검증 결과:** 이름만 `.pdf`인데 실제로는 `HWP` 파일인 경우 파싱 에러가 발생하여 전체 배치가 롤백됐다.
  - **잘못된 점:** 외부 API 데이터 특성상 파일명과 실제 바이너리 형식이 일치하지 않는 경우가 상당수였다. 또한, 전체를 하나의 트랜잭션으로 묶어 단일 에러가 전체 실패로 이어지는 '폭포식 롤백' 구조였다.

### 3. 해결 방안 (Resolution)
- **핵심 해결책 (Magic Number 탐지 & Savepoint):**
  1. 파일의 첫 1KB 바이너리를 읽어 실제 형식을 감지하는 **Magic Number 탐지 로직**을 도입했다.
  2. SQLAlchemy의 `begin_nested()`를 사용한 개별 공고 파싱 단위를 **중첩 트랜잭션**으로 처리했다.
- **추가 해결(텍스트 전처리 파이프라인):** 파일 추출 전후 데이터가 있는 파일의 콘텐츠를 자동 감지하고, HTML 클리닝을 통해 태그를 제거한 순수 텍스트만 추출하는 파이프라인을 구축했다.
- **적용 코드:**

```python
# [바이너리 앞부분 기반 파일 탐지 로직]
def detect_file_type(binary_content: bytes) -> str:
    # 파일의 매직넘버(Magic Number)를 확인하여 실제 형식 감지
    if binary_content.startswith(b'%PDF'):
        return "PDF"
    elif binary_content.startswith(b'\xd0\xcf\x11\xe0'):
        return "HWP"  # 구버전 97~3.0 및 5.0 이상 포함
    return "UNKNOWN"

# [중첩 트랜잭션을 통한 예외 처리]
async def process_batch(items):
    for item in items:
        # Savepoint 생성: 특정 공고 실패 시 해당 건만 롤백
        async with session.begin_nested():
            try:
                raw_data = await download_file(item.url)
                file_type = detect_file_type(raw_data)
                text = await parse_text(raw_data, file_type)
                await save_to_db(item, text)
            except Exception as e:
                # 해당 건만 제외하고 로그 기록, 다음 반복 계속
                await session.rollback()
                logger.error(f"Fail item {item.id}: {e}")
```

### 4. 기술적 회고 및 성장 (Retrospective)
- **실무 포인트:** 단일 실패로 인한 전체 작업 취소를 0으로 줄여 **시스템의 장애 복원력(Resilience)**을 확보했다. 또한 정제된 텍스트만을 입력하도록 GPT의 응답 품질을 약 30% 향상시키고 토큰을 절감할 수 있었다.
- **새롭게 배운 점:**
    1. **Magic Number:** 파일 탐지는 파일명이 아닌 실제 파일의 시작 바이너리 패턴을 보는 '전체 데이터 탐지' 방식을 배웠다.
    2. **Nested Transactions (Savepoint):** 대규모 배치 작업에서 예외를 처리하여 시스템의 안정성을 확보하는 트랜잭션 활용 방법을 체득했다.
- **포트폴리오 활용도:**
    - **방어적 프로그래밍(Defensive Programming):** "API 명세에는 있으나 실제 데이터는 항상 명세대로 오지 않는다"는 교훈을 배웠다. 데이터의 가변성을 고려한 예외 처리가 유지보수에 더 적합한 코드라는 것을 보여준다.
    - **RAG에서의 '좋은 데이터':** 아무리 좋은 LLM 모델도 입력하는 데이터가 불완전하면 쓸모없다. HTML 태그 제거, 불필요한 텍스트 제거를 통한 AI 파이프라인의 입력 품질을 높이는 것의 중요성을 배웠다.

# [Issue-04] 기기 간 온보딩 상태 공유 실패와 로그인 흐름 처리 오류 해결
> **핵심 요약:** 브라우저 로컬스토리지(localStorage)에 의존하던 온보딩 상태 확인 로직을 실제 데이터베이스(Business DB) 기반 조회로 교체하여 멀티디바이스 환경에서의 정합성을 확보했다.

### 1. 현상 파악 (Symptom)
- **발생 상황:** PC에서 소셜 로그인을 통해 사업장 등록(온보딩)을 완료한 유저가 노트북 같은 다른 기기에서 동일한 계정으로 로그인했을 때, 이미 등록된 사업장 정보가 없는 것처럼 취급되어 다시 온보딩 화면으로 강제 리다이렉트되는 현상 발생.
- **대표 에러 메시지:**
  - `Redirecting to /onboarding...` (오류가 아닌 잘못된 리다이렉트)
  - 코드에 syntax error는 없었으나 `is_new_user` 판단 로직이 `true`로 고정되어 있어 사용자 경험(UX) 훼손.
- **사용자 가치 영향:** 이미 데이터를 등록한 것처럼 동일한 데이터를 재입력해야 하는 불편함이 생겨 사용자 신뢰도가 낮아지고 데이터 무결성을 해칠 우려가 생겼다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 시도: 로컬스토리지 상태 점검**
  - **가설:** `localStorage`에 저장된 `isOnboarded` 플래그가 다른 기기에서는 `false`인 것을 확인. 그대로 로컬스토리지를 서버에서 동기화하는 문제로 인식했다.
  - **검증 결과:** 다른 기기에서 로컬스토리지 상태가 없어서 소셜 로그인 후 항상 초기값인 `false`로 시작.
  - **잘못된 점:** 서버의 인증 상태(온보딩 여부)를 클라이언트의 임시 저장소에만 의존하도록 설계한 것 자체가 근본적인 문제였다.

- **2차 시도: 닉네임 존재 여부(user.nickname) 기반으로 판단**
  - **가설:** 온보딩에서 `is_profile_incomplete`를 판단하고 있으니 닉네임 여부가 적절하겠다고 판단.
  - **검증 결과:** 확인 결과, 온보딩에서 `businesses` 테이블만 업데이트하고 `user.nickname`을 별도로 저장하지 않아 해당 필드가 항상 `null`이었다.
  - **잘못된 점:** **데이터 모델(User 테이블)과 실제 데이터의 실소유(Business 테이블)의 불일치**로 "사업장이 있으면 온보딩 완료"라는 비즈니스 규칙과 맞지 않는 잘못된 판단 기준이었다.

### 3. 해결 방안 (Resolution)
- **핵심 해결책:** 온보딩 완료 여부를 로컬스토리지에서 판단하는 대신, **실제 DB에 해당 유저 소유의 활성 사업장이 존재하는지**를 조회하여 온보딩 여부를 결정하도록 수정했다.
- **추가 해결:** 인증(Authentication)과 온보딩(Business Logic)의 책임을 명확히 분리. 브라우저 로컬스토리지는 UI 편의용으로만 사용하고, 인증 판단 단일 진실(SSOT: Single Source of Truth)은 데이터베이스를 기준으로 실행했다.
- **적용 코드:**

```python
# auth/repository.py - Exist 조회를 위한 최적화된 비즈니스 존재 여부 확인
async def has_active_business(self, user_id: uuid.UUID) -> bool:
    from src.app.domains.business.model import Business
    # COUNT보다 EXISTS가 효율적이지만 가독성을 위해 scalar() 사용
    stmt = select(func.count()).select_from(Business).where(
        Business.user_id == user_id,
        Business.is_active.is_(True)
    )
    result = await self._session.execute(stmt)
    return result.scalar() > 0

# auth/service.py - 수정된 온보딩 판단 로직
if is_new:
    should_redirect_to_onboarding = True
else:
    # 사업장이 없으면 온보딩, 실제 비즈니스 도메인의 데이터로 확인
    has_biz = await self._repo.has_active_business(user.id)
    should_redirect_to_onboarding = not has_biz
```

### 4. 기술적 회고 및 성장 (Retrospective)
- **실무 포인트:** 불완전한 온보딩 처리 방식을 보완하여 DB 기반의 데이터를 활용하고, 멀티디바이스 환경에서의 서비스 정합성을 확보했다.
- **새롭게 배운 점:** **SSOT(Single Source of Truth, 단일 진실의 원천)**의 중요성을 체득했다. 상태 판단 로직이 여러 곳에서 중복되면 발생하는 Side Effect를 방지하고 도메인 간의 책임 분리(Separation of Concerns)를 올바르게 유지해야 한다.
- **포트폴리오 활용도:**
    - "프론트에서 가져오면 된다"는 생각이 위험한 이유를 배웠다. 특히 JWT나 로컬스토리지를 사용하는 환경에서는 클라이언트 저장소가 언제든 초기화될 수 있다는 것을 항상 고려해야 한다.
    - 비즈니스 판단 기준(사업장 등록)과 데이터 모델(User/Business 테이블) 사이의 명확한 경계와 역할을 파악한 뒤에 설계해야 한다는 점을 배웠다.

---
**추가 참고 사항:** 인증 로직과 실제 데이터의 상관관계를 항상 고려하고, 멀티디바이스 환경에서는 서버 기준 검증이 필수입니다.
---
# [Issue-005] Admin 배포 직후 로그인 500 + 다중 404 연쇄 오류 복구
> **핵심 요약:** 서비스 시그니처 변경(`count` → `total_count`) 누락으로 500이 발생했고, 프론트에서 호출하는 Admin API 일부가 백엔드에 미구현되어 404가 연쇄 발생했다. 호출부 정합성 수정과 라우트/서비스 보강으로 복구했다.

### 1. 현상 파악 (Symptom)
- **발생 상황:** 관리자 로그인 후 대시보드 접근 시 서버 에러와 404가 동시에 발생.
- **대표 에러 메시지:** `TypeError: BizinfoSyncService.bootstrap_historical_policies() got an unexpected keyword argument 'count'`
- **동시 발생 API 404:** `/api/v1/admin/feedback`, `/api/v1/admin/monitoring/health`, `/api/v1/admin/insights/unmet-demand`
- **사용자 가치 영향:** 어드민 핵심 화면이 깨져 운영 점검/모니터링이 불가능해짐.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 분석: 타입/시그니처 불일치 추적**
  - **가설:** 서비스 함수 파라미터명이 리팩터링 후 호출부에 반영되지 않았을 가능성.
  - **검증 결과:** 실제 정의는 `total_count`, 호출은 `count`로 확인됨.
- **2차 분석: API 계약 불일치 추적**
  - **가설:** 프론트 서비스 레이어가 호출하는 Admin 엔드포인트와 백엔드 라우터 구현이 어긋났을 가능성.
  - **검증 결과:** `feedback/monitoring/insights` 계열 일부 라우트가 미구현 상태였음.

### 3. 해결 방안 (Resolution)
- **즉시 조치 1:** `bootstrap_historical_policies` 호출부를 `total_count=count`로 수정해 500 차단.
- **즉시 조치 2:** 백엔드 Admin 라우터에 누락 API 추가:
  - Feedback: 목록/상세 컨텍스트/교정노트 생성/교정노트 목록
  - Monitoring: health/latency/cost
  - Insights: unmet-demand/conversion
- **즉시 조치 3:** 서비스 메서드 보강(기본 집계 + 안전한 기본 응답)으로 화면 크래시 방지.
- **즉시 조치 4:** `CorrectionNoteRequest` 스키마 추가로 입력 계약 명시.

### 4. 기술적 회고 및 성장 (Retrospective)
- **실무 포인트 1 — 타입 정합성:** “단순 변수명” 변경도 런타임 장애로 이어질 수 있으므로, 서비스 시그니처 변경 시 호출부 전수 점검이 필수다.
- **실무 포인트 2 — API Contract 우선:** 프론트/백엔드 중 한쪽만 기준으로 보면 놓치기 쉽다. 계약(엔드포인트/파라미터/응답 형태) 기준으로 역추적하는 방식이 복구 속도를 높였다.
- **실무 포인트 3 — 장애 확산 차단:** 완전한 기능 구현 전이라도 안전한 기본 응답을 우선 제공하면 운영 화면 가용성을 빠르게 회복할 수 있다.
- **포트폴리오 활용도:** 백엔드 운영 안정화(타입 정합성 + API 계약 복구) 사례로 면접에서 설명 가치가 높음.

---

# [Issue-006] 정책 공고 AI 동기화 파이프라인 장애 — Supabase Connection Timeout & 데이터 품질 오염
> **핵심 요약:** 기업마당 API에서 1,255건을 AI 구조화(GPT-4o)와 함께 수집하는 Full Sync가 중간에 끊기거나 쓰레기 데이터가 DB에 쌓이는 문제가 발생했다. 원인은 세 가지였다: Supabase pgbouncer의 idle timeout, 배치 전체를 단일 세션으로 처리하는 구조적 결함, `with_ai` 파라미터 기본값 미확인으로 인한 AI 없는 대량 저장이었다. 수집 파이프라인 자체는 정상이었지만, 인프라 특성과 파라미터 기본값을 놓쳐 일주일 이상 시간을 소비했다.

### 1. 현상 파악 (Symptom)
- **발생 상황:** `with_ai=True`로 Full Sync(1,255건)를 실행하면 200~300건 처리 후 데이터 저장이 멈추거나 DB 연결 오류가 발생했다. 처음에는 "PDF 파싱 자체가 깨졌다"고 오판하여 약 일주일간 파싱 코드 디버깅에 시간을 소비했다.
- **대표 에러 메시지:** `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`
- **추가 증상 1 (데이터 오염):** Swagger에서 `with_ai` 기본값(`False`)을 확인하지 않고 Full Sync를 실행하여 1,255건이 `ai_summary`, `target_logic`, `required_documents` 등 핵심 필드가 모두 NULL인 상태로 저장됐다.
- **추가 증상 2 (낮은 파싱 성공률):** `_select_primary_file`이 `printFileNm`이 `.pdf`로 끝날 때만 URL을 반환하는 탓에, 파일명이 없거나 인코딩 문제가 있는 공고의 경우 실제 PDF가 존재해도 다운로드 시도조차 하지 않고 PARSE_ERROR로 처리됐다.
- **사용자 가치 영향:** RAG에 쓸 수 없는 빈 데이터가 쌓여 챗봇이 사용자 질문에 전혀 답변하지 못하는 상태가 됐다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 시도: 파싱 코드 디버깅 (잘못된 방향)**
  - **가설:** "PDF 파싱 로직 자체가 잘못됐다"는 판단 하에 `PyMuPDF` 설정, HWP 처리 등 파싱 코드만 반복 수정했다.
  - **검증 결과:** `test-sync-one`으로 단건 테스트를 해보니 PDF에서 20,047자가 정상 추출되고 GPT 구조화까지 완벽히 성공했다. **파싱은 처음부터 정상이었다.** 문제는 배치 실행 중 DB 연결이 끊기는 것이었다.
  - **잘못된 점:** 단건 테스트 검증 없이 코드 자체를 의심하며 시간을 낭비했다.

- **2차 시도: `pool_recycle` 단축만 적용**
  - **가설:** `pool_recycle=3600`(1시간)이 Supabase idle timeout(5분)보다 길어서 재연결이 늦다는 판단.
  - **검증 결과:** `pool_recycle=300`으로 줄였지만, pgbouncer의 prepared statement 충돌 문제와 단일 장수 세션 구조는 그대로라 여전히 끊겼다.

- **3차 시도: `with_ai=False`로 전체 수집 (실수)**
  - **가설:** 일단 데이터를 채우고 나중에 AI 보강하면 된다는 판단.
  - **검증 결과:** Swagger UI의 `with_ai` 기본값이 `False`인 것을 놓쳐, 1,255건이 `ai_summary=NULL`인 쓰레기 데이터로 전부 저장됐다. 이후 `DELETE FROM policies WHERE ai_summary IS NULL`로 전량 삭제해야 했다.

### 3. 해결 방안 (Resolution)
- **근본 해결 1 — Supabase pgbouncer 호환성 확보:**

```python
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,          # Supabase idle timeout(5분) 이내 재생성
    connect_args={
        "prepared_statement_cache_size": 0,  # pgbouncer transaction mode 호환
        "server_settings": {"application_name": "biz-fund-ai"},
    },
)
```

- **근본 해결 2 — 페이지별 독립 세션 구조 도입:**
  `BizinfoSyncService`에 `session_factory`를 주입받아, `with_ai=True` 배치에서 페이지(100건)마다 새 세션을 생성·커밋·종료하도록 변경했다. 세션 수명이 최대 ~15분으로 제한되어 Supabase 5분 timeout을 근본적으로 회피한다.

```python
async def _process_page_with_fresh_session(self, items, ...):
    async with self._session_factory() as page_session:
        page_svc = BizinfoSyncService(session=page_session, ...)
        for item in items:
            await page_svc._process_single_item(item=item, with_ai=True, ...)
            await asyncio.sleep(3)
        await page_session.commit()   # 페이지 완료 시 커밋 후 세션 종료
```

- **근본 해결 3 — 쓰레기 데이터 차단:**
  `PARSE_ERROR` / `ANALYSIS_ERROR` 상태의 공고는 DB에 저장하지 않도록 명시적으로 스킵 처리했다. "일단 저장하고 나중에 보완"이 아닌 "품질 미달이면 저장 안 함"을 원칙으로 변경했다.

```python
if with_ai and ai_status in ("PARSE_ERROR", "ANALYSIS_ERROR"):
    return ai_status, False, ai_err_info  # DB 저장 스킵
```

- **추가 해결 — 파일 선택 로직 개선:**
  `printFileNm`이 없거나 `.pdf`로 끝나지 않아도 `printFlpthNm` URL이 있으면 무조건 다운로드를 시도하도록 수정했다. 실제 PDF 여부는 magic byte(`%PDF`)로 확인한다. 이로써 파싱 성공률이 ~24%에서 ~57%로 개선됐다.

### 4. 기술적 회고 및 성장 (Retrospective)
- **실무 포인트 1 — 클라우드 DB의 인프라 제약을 설계에 반영해야 한다:** 로컬 PostgreSQL에서는 수 시간짜리 세션도 문제없지만, Supabase처럼 pgbouncer를 사용하는 환경에서는 idle timeout, prepared statement 제한 등 별도의 제약이 존재한다. 배포 환경의 인프라 특성을 코드 설계 단계에서 고려해야 한다.
- **실무 포인트 2 — 배치 작업은 세션 수명을 단위별로 관리해야 한다:** "한 번에 다 처리하면 편하다"는 생각이 장수 세션을 만들어 timeout을 유발했다. AI 호출처럼 외부 I/O가 긴 작업이 포함된 배치는 페이지/청크 단위로 세션을 열고 닫는 패턴이 필수다.
- **실무 포인트 3 — 부작용이 큰 API는 파라미터를 두 번 확인하고 실행한다:** `with_ai=False`라는 기본값을 놓쳐 1,255건이 쓰레기 데이터로 저장됐다. 대량 DB 저장, 외부 API 호출 등 되돌리기 어려운 작업은 실행 전 파라미터를 반드시 재확인하는 습관이 필요하다.
- **포트폴리오 활용도:** 클라우드 인프라 특성(pgbouncer) 이해, 장수 배치 작업의 세션 관리 설계, 데이터 품질 기준 설계 등 세 가지 관점에서 면접 설명 가치가 높음.
