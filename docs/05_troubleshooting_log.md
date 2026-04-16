# [Issue-01] 서비스 간 상호 참조 발생에 따른 런타임 에러 및 라우터 오케스트레이션을 통한 구조 개선
> **한 줄 요약:** 도메인 격리 원칙을 준수하며 논리 삭제(Soft Delete) 로직을 구현하던 중 발생한 순환 참조 문제를 메서드 주입(Method Injection)과 라우터 조율(Orchestration) 방식을 통해 해결함.

### 1. 현상 파악 (Symptom)
- **발생 상황:** 초기 설계는 유저 탈퇴 시 연관 데이터를 즉시 삭제하는 물리 삭제(Hard Delete) 방식이었으나, 통계 보존을 위한 **논리 삭제(Soft Delete)**로 기획이 변경되었습니다. 유저(`User`) 탈퇴 시 그가 소유한 사업장(`Business`) 데이터도 함께 비활성화(`is_active=False`)되어야 했으며, 도메인 격리 원칙에 따라 `AuthService`가 `BusinessService`에 처리를 위임하는 구조를 설계했습니다.
- **핵심 에러 메시지:** `ImportError: cannot import name 'get_business_service' from partially initialized module (most likely due to a circular import)`
- **사용자 가치:** 해결되지 않을 경우, 탈퇴 유저의 사업자 정보가 '활성' 상태로 방치되는 고아 데이터(Orphan Data)가 발생하여 데이터 정합성이 깨지고 재가입 시 로직 충돌이 발생합니다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 접근: 생성자 주입(Constructor Injection)**
  - **나의 생각:** `AuthService`가 기능을 수행할 때 `BusinessService`가 필요하므로 생성 시점에 의존성을 주입받아야 한다고 판단했습니다.
  - **실행 결과:** `Auth` 도메인이 `Business`를, `Business` 도메인이 현재 유저 식별을 위해 다시 `Auth`를 참조하며 무한 루프 발생.
  - **원인 파악:** 서비스 간의 물리적인 의존성 그래프가 원을 그리며 모듈 로딩 단계에서 교착 상태에 빠졌습니다.

- **2차 접근: `if TYPE_CHECKING` 및 지연 임포트**
  - **나의 생각:** 파이썬의 정적 타입 힌트 블록 내에서 임포트하면 순환 참조를 피할 수 있을 것으로 기대했습니다.
  - **실행 결과:** `NameError: name 'get_business_service' is not defined` 발생.
  - **원인 파악:** FastAPI의 `Depends()`는 앱 기동 시(Runtime) 실제 객체의 주소를 확인해야 합니다. 힌트만 제공하는 `TYPE_CHECKING`으로는 런타임 의존성을 해결할 수 없었습니다.

### 3. 해결 방안 (Resolution)
- **단기 조치:** `AuthService` 생성자에서 `BusinessService` 의존성을 제거하고, `withdraw` 메서드 호출 시점에 외부에서 객체를 전달받는 **메서드 주입(Method Injection)** 방식으로 변경했습니다.
- **근본 대책:** 하위 서비스 계층에서 서로를 참조하지 않도록 의존성을 끊고, 두 도메인을 모두 주입받을 수 있는 **Router를 오케스트레이터(Orchestrator)**로 활용하여 제어권을 상위로 끌어올렸습니다.
- **적용 코드:**

```python
# [Service Layer] 타 도메인 서비스를 직접 소유하지 않고 인자로 전달받음
class AuthService:
    def __init__(self, session: AsyncSession, repo: AuthRepository):
        self._session = session
        self._repo = repo

    async def withdraw(self, user: User, business_service: Any = None):
        await self._repo.soft_delete_user(user)
        if business_service:
            # 도메인 경계를 넘지 않고 인터페이스만 호출
            await business_service.deactivate_all_businesses_by_user(user.id)
        await self._session.commit()

# [Router Layer] 두 도메인의 결합을 조율하는 컨트롤 타워 역할
@router.delete("/withdraw", status_code=204)
async def withdraw(
    current_user: CurrentUser,
    svc: Annotated[AuthService, Depends(get_auth_service)],
    biz_svc: Annotated[BusinessService, Depends(get_business_service)]
):
    # 서비스 계층 간의 직접 의존성 없이 라우터가 흐름을 제어함
    await svc.withdraw(current_user, business_service=biz_svc)
    return Response(status_code=204)
```

### 4. 기술적 회고 및 성장 (Retrospective)
- **성능/효율성 변화:** 도메인 간의 직접적인 참조가 사라지면서 코드의 가독성이 높아졌고, 특정 도메인의 변경이 다른 도메인에 영향을 주지 않는 **느슨한 결합(Loose Coupling)**을 달성했습니다. 또한, 테스트 코드 작성 시 Mock 객체를 주입하기가 용이해져 단위 테스트의 신뢰도가 향상되었습니다.
- **새롭게 배운 개념:** 1. **Runtime vs Static Check:** 파이썬의 `TYPE_CHECKING`은 정적 분석용일 뿐, FastAPI의 `Depends`처럼 실행 시점의 객체를 요구하는 프레임워크 특성 앞에서는 무력할 수 있음을 배웠습니다.
    2. **Inversion of Control (IoC):** 하위 계층에서 의존성을 해결하려 하지 않고, 상위 계층으로 제어권을 끌어올려 전체 흐름을 관리하는 설계의 중요성을 체득했습니다.
- **실무적 인사이트:** - **라우터 조율의 적정성:** 메시지 큐(MQ)를 이용한 이벤트 기반 아키텍처가 결합도를 낮추는 데는 최상이나, 현재 프로젝트 규모에서는 오버엔지니어링이 될 수 있습니다. `Depends`를 활용한 라우터 오케스트레이션은 복잡도와 관리 효율성 사이의 훌륭한 타협점임을 깨달았습니다.
    - **도메인 격리의 가치:** A 도메인의 로직을 위해 B 도메인의 DB 테이블을 직접 건드리는 것은 미래의 기술 부채가 됩니다. 서비스 인터페이스를 통해 협력하는 것이 비전공자 신입 개발자로서 지켜야 할 핵심적인 아키텍처 원칙임을 명심하게 되었습니다.

---


# [Issue-02] 배치 작업 중 롤백(Rollback) 오용으로 인한 데이터 증발 현상 해결
> **한 줄 요약:** 대량 데이터 적재 중 발생한 중복 에러를 처리하기 위해 `session.rollback()`을 호출했다가, 이전까지 성공했던 데이터들까지 모두 되돌려지는 트랜잭션 원자성 문제를 해결함.

### 1. 현상 파악 (Symptom)
- **발생 상황:** 외부 API로부터 정책 공고 데이터를 가져와 DB에 적재하는 배치(Batch) 작업을 수행하던 중, 이미 DB에 존재하는 데이터와 중복되는 'UniqueViolationError'가 발생했습니다. 세션이 잠기는 것을 방지하기 위해 예외 처리 구간에서 `session.rollback()`을 호출했습니다.
- **핵심 에러 메시지:** `sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint`
  - **이유:** 공고의 고유 번호가 이미 존재함에도 `INSERT`를 시도하여 DB 제약 조건에 의해 에러 발생.
- **사용자 가치:** 로직상으로는 성공 로그(`success_cnt`)가 1,282건으로 찍히지만, 실제 DB에는 약 300여 건만 남는 데이터 유실이 발생했습니다. 이는 관리자에게 잘못된 정보를 제공하며, 수집되지 않은 정책 공고는 실제 서비스 이용자에게 노출되지 않는 비즈니스 손실을 야기합니다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 접근: 예외 처리 루프 내 롤백 호출**
  - **나의 생각:** 중복 에러가 발생하면 DB 세션이 오염되어 다음 작업을 수행할 수 없으므로, 에러가 날 때마다 롤백을 호출해 세션을 초기화해야 한다고 판단했습니다.
  - **실행 결과:** 에러 없이 루프는 끝났으나, 데이터가 실시간으로 증발했습니다.
  - **원인 파악:** **트랜잭션의 원자성(Atomicity)**에 대한 오해였습니다. 롤백은 에러가 난 '한 줄'만 취소하는 것이 아니라, 마지막 커밋(Commit) 시점 이후에 성공했던 모든 앞선 작업들을 한꺼번에 '없던 일'로 되돌려버렸습니다.

- **2차 접근: 중복 상황을 '예외'가 아닌 '정상 로직'으로 전환**
  - **나의 생각:** 에러가 발생한 뒤에 수습(Except)하려니 롤백이 강제되었습니다. 아예 에러가 발생하지 않도록 DB 수준에서 처리하는 방법을 고민했습니다.

### 3. 해결 방안 (Resolution)
- **단기 조치 (UPSERT 도입):** `ON CONFLICT (공고번호) DO UPDATE` 구문을 사용하는 **UPSERT** 방식을 도입했습니다. 중복이 발생하면 에러를 내는 대신 기존 데이터를 업데이트하도록 하여 트랜잭션이 깨지는 상황을 원천 봉쇄했습니다.
- **근본 대책 (트랜잭션 단위 재설계):** 롤백의 범위를 명확히 이해하고, 대량 적재 시에는 적절한 단위(Batch Size)로 커밋을 수행하거나, 중복 가능성이 있는 시나리오는 예외 처리가 아닌 비즈니스 로직(예: 존재 여부 체크 후 진입) 내에서 해결하도록 구조를 개선했습니다.
- **적용 코드:**

```python
# [수정 전: 데이터 유실의 원인]
for data in policy_list:
    try:
        session.add(Policy(**data))
        session.flush() # 여기서 중복 에러 발생 시
    except IntegrityError:
        session.rollback() # ⚠️ 주의: 이전 성공 데이터까지 전부 롤백됨

# [수정 후: ON CONFLICT를 활용한 안정적 적재]
from sqlalchemy.dialects.postgresql import insert

stmt = insert(Policy).values(policy_list)
upsert_stmt = stmt.on_conflict_do_update(
    index_elements=['policy_id'], # 중복을 체크할 기준 컬럼
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
- **성능/효율성 변화:** 매번 시도하고 실패 시 롤백하던 방식에서 DB 고유의 UPSERT 기능을 활용하는 방식으로 전환하여 연산 횟수가 줄어들었고, 데이터 유실 없이 1,282건 전량을 정확하게 적재할 수 있게 되었습니다.
- **새롭게 배운 개념:**
    1. **트랜잭션의 원자성(Atomicity):** 롤백은 특정 지점이 아닌 '마지막 커밋' 이후의 모든 성과를 되돌리는 타임머신과 같다는 점을 배웠습니다.
    2. **Idempotency(등방성):** 동일한 작업을 여러 번 수행해도 결과가 항상 같아야 하는 배치 작업에서 UPSERT가 얼마나 강력한 도구인지 체감했습니다.
- **실무적 인사이트:**
    - **로그와 실제 데이터의 간극:** "코드가 에러 없이 수행되었다"는 로그가 "데이터가 올바르게 들어갔다"는 것을 보장하지 않습니다. 반드시 실제 결과물(DB)과 코드의 실행 결과(Log)를 교차 검증하는 습관이 필요합니다.
    - **예외 처리보다 비즈니스 로직 우선:** 중복 처리를 `try-except`에 의존하기보다, DB 수준의 기능을 활용해 정상적인 비즈니스 흐름 안에서 관리하는 것이 아키텍처적으로 훨씬 견고합니다.

---

# [Issue-03] 공공 API 데이터 불일치 및 수집 엔진의 회복 탄력성(Resilience) 확보
> **한 줄 요약:** API 응답의 정보 누락과 지저분한 데이터를 바이너리 분석 기반의 '멀티 파서'와 '중첩 트랜잭션(SAVEPOINT)'으로 해결하며 RAG 시스템의 정밀도를 극대화함.

### 1. 현상 파악 (Symptom)
- **발생 상황:** 공공데이터포털(기업마당) API를 활용해 정책 공고를 수집하던 중, API가 제공하는 요약 정보(`bsnsSumryCn`)만으로는 RAG(검색 증강 생성) 시스템이 요구하는 정밀한 매칭이 불가능함을 발견했습니다. 진짜 핵심 정보(지원 자격, 상세 가점 등)는 첨부파일 속에 있었으나, 제공되는 URL은 확장자가 없거나 실제 파일 형식과 일치하지 않는 등 데이터 오염이 심각했습니다.
- **핵심 에러 메시지:** 1. `UnsupportedFileError: Unknown file signature for URL /getImageFile.do` (확장자 부재로 인한 판별 불가)
  2. `DataLossWarning: Total rollback occurred due to single item failure` (단일 실패가 전체 배치 취소로 이어짐)
- **사용자 가치:** 이 문제가 해결되지 않으면 사용자는 AI로부터 "공고문에 적힌 상세 자격 요건"을 안내받지 못하고 겉핥기식 정보만 제공받게 되며, 수집 시스템은 사소한 에러에도 전체 작업이 중단되어 운영 효율이 급격히 저하됩니다.

### 2. 해결을 위한 과정 (Trials & Errors)
- **1차 접근: API 명세서 기반의 단순 수집**
  - **나의 생각:** API 명세서에 명시된 요약 필드와 파일 경로(`fileNm`)만 믿고 표준적인 수집 로직을 설계했습니다.
  - **실행 결과:** GPT가 공고문의 맥락을 이해하지 못해 엉뚱한 답변을 내놓거나, 확장자가 없는 URL 앞에서 수집 엔진이 멈춰버렸습니다.
  - **원인 파악:** API 응답은 '참고용'일 뿐이었으며, 실제 파일 주소는 규칙성이 없고 데이터 안에 HTML 노이즈가 가득한 '야생의 상태'였습니다.

- **2차 접근: 확장자 기반 파싱 시도**
  - **나의 생각:** 파일명 끝자리(`.pdf`, `.hwp`)를 분석해 파서를 배분했습니다.
  - **실행 결과:** 이름은 `.pdf`인데 실제로는 `HWP` 파일인 경우 파싱 에러가 발생하며 전체 배치가 롤백되었습니다.
  - **원인 파악:** 공공 데이터 특성상 파일명과 실제 바이너리 형식이 일치하지 않는 경우가 태반이었습니다. 또한, 전체를 하나의 트랜잭션으로 묶어 단일 에러가 전체 실패로 번지는 '전염성 롤백' 구조였습니다.

### 3. 해결 방안 (Resolution)
- **단기 조치 (Magic Number 분석 & Savepoint):** 1. 파일의 첫 1KB 바이너리를 읽어 실제 형식을 판별하는 **Magic Number 판별 로직**을 도입했습니다.
  2. SQLAlchemy의 `begin_nested()`를 사용해 각 공고 수집 단위를 **중첩 트랜잭션**으로 격리했습니다.
- **근본 대책 (멀티 파서 아키텍처):** 파일 우선순위 큐를 통해 가장 정보량이 많은 파일을 자동 선택하고, HTML 전처리기를 통해 노이즈를 제거한 순수 텍스트만 추출하는 파이프라인을 구축했습니다.
- **적용 코드:**

```python
# [바이너리 헤더 기반 파일 판별 로직]
def detect_file_type(binary_content: bytes) -> str:
    # 파일의 지문(Magic Number)을 확인하여 실제 형식 판별
    if binary_content.startswith(b'%PDF'):
        return "PDF"
    elif binary_content.startswith(b'\xd0\xcf\x11\xe0'):
        return "HWP" # 한글 97~3.0 및 5.0 표준 서명
    return "UNKNOWN"

# [중첩 트랜잭션을 통한 오류 격리]
async def process_batch(items):
    for item in items:
        # Savepoint 생성: 특정 공고 실패 시 여기까지만 롤백
        async with session.begin_nested():
            try:
                raw_data = await download_file(item.url)
                file_type = detect_file_type(raw_data)
                text = await parse_text(raw_data, file_type)
                await save_to_db(item, text)
            except Exception as e:
                # 해당 건만 취소하고 로그 기록, 다음 루프 진행
                await session.rollback()
                logger.error(f"Fail item {item.id}: {e}")
```

### 4. 기술적 회고 및 성장 (Retrospective)
- **성능/효율성 변화:** 단일 실패로 인한 전체 재작업 비용이 0으로 줄어들어 **시스템의 회복 탄력성(Resilience)**을 확보했습니다. 또한 정제된 텍스트만 전달함으로써 GPT의 토큰 소모량을 약 30% 절감하고 답변의 정확도를 높였습니다.
- **새롭게 배운 개념:**
    1. **Magic Number:** 파일 확장자는 언제든 바뀔 수 있지만, 파일 시작부의 고유 바이너리 서명은 거짓말을 하지 않는다는 '실전 데이터 판별법'을 배웠습니다.
    
    2. **Nested Transactions (Savepoint):** 대규모 배치 작업에서 오류를 격리하여 시스템의 안정성을 유지하는 트랜잭션 설계 기법을 체득했습니다.
- **실무적 인사이트:**
    - **방어적 프로그래밍(Defensive Programming):** "API 명세서는 참고서일 뿐, 실제 데이터는 항상 의심해야 한다"는 진리를 깨달았습니다. 데이터의 가변성을 고려한 예외 처리가 실무 코드의 완성도를 결정한다는 것을 알게 되었습니다.
    - **RAG의 핵심은 '깨끗한 데이터':** 아무리 좋은 LLM 모델을 써도 입력되는 데이터가 지저분하면 소용없습니다. HTML 노이즈 제거와 고품질 텍스트 추출이 AI 서비스 개발자의 핵심 역량임을 실감했습니다.