# 개발 명령어 가이드

## 왜 이 문서가 필요한가

이 저장소는 프론트엔드와 백엔드가 분리되어 있습니다.

- 프론트엔드는 `frontend/package.json` 기준으로 동작합니다.
- 백엔드는 `backend/pyproject.toml` 기준으로 동작합니다.

그래서 저장소 루트에서 바로 `uv run pytest`를 실행하면 아래 같은 문제가 생길 수 있습니다.

- `backend` 프로젝트를 찾지 못해 `pytest` 실행 파일을 못 찾는 경우
- `backend/src/app/dev/test_seed.py` 같은 개발용 파일까지 테스트로 수집되어 import 에러가 나는 경우

## 권장 실행 방법

루트(`biz-fund-ai`)에서 아래 명령어를 사용합니다.

```bash
npm run frontend:lint
npm run frontend:type-check
npm run frontend:build
npm run backend:test
npm run backend:quality-eval -- --limit 3
npm run backend:quality-eval:local -- --limit 3
npm run check
```

## 각 명령어가 하는 일

- `npm run frontend:lint`: 프론트엔드 ESLint 검사
- `npm run frontend:type-check`: 프론트엔드 TypeScript 타입 검사
- `npm run frontend:build`: 프론트엔드 프로덕션 빌드 검증
- `npm run backend:test`: `uv run --project backend pytest backend/tests`로 백엔드 테스트 디렉터리만 정확히 실행
- `npm run backend:quality-eval -- --limit 3`: 현재 `.env` 기준 DB로 BizMong 품질평가를 실행
- `npm run backend:quality-eval:local -- --limit 3`: 로컬 Postgres 주소를 직접 넘겨 BizMong 품질평가를 실행
- `npm run check`: 프론트 린트 + 타입체크 + 백엔드 테스트를 한 번에 실행

## 기존 방식과 차이

백엔드 폴더로 직접 들어가서 아래처럼 실행해도 됩니다.

```bash
cd backend
uv run pytest
```

다만 팀 작업이나 자동화에서는 루트 기준 명령어를 통일해두는 편이 실수를 줄이기 쉽습니다.

## 품질평가 실행 팁

품질평가 스크립트는 시작 전에 DB preflight 를 먼저 수행합니다.

- `preflight_error` 와 함께 `ENOTFOUND`, `connection refused` 같은 메시지가 나오면 DB 주소나 네트워크 설정부터 확인합니다.
- 원격 개발 DB 주소가 깨져 있거나 접속이 막혀 있으면 `npm run backend:quality-eval:local` 로 로컬 Postgres 주소를 넘겨 바로 확인할 수 있습니다.
- 로컬 DB를 쓸 때 기본 주소는 `postgresql+asyncpg://biz_user:biz_password@localhost:5432/biz_fund_ai` 입니다.
