# Biz-Up Frontend

사장님을 위한 AI 정책자금 비서 — 웹 프론트엔드.

## 기술 스택

| 분류 | 라이브러리 |
|:---|:---|
| 프레임워크 | Next.js 15 (App Router) + React 19 + TypeScript |
| 스타일링 | Tailwind CSS 3 |
| 서버 상태 | TanStack Query v5 |
| HTTP | Axios (envelope 자동 언래핑 + 토큰 로테이션) |
| 아이콘 | lucide-react |
| 차트 | Recharts |
| 전역 상태 | Zustand (UI 상태 전용) |
| 날짜 | date-fns |

## 폴더 구조

```
frontend/
├── src/
│   ├── app/                  # App Router — 페이지 & 레이아웃
│   │   ├── layout.tsx
│   │   ├── page.tsx          # [P01] 랜딩
│   │   └── globals.css
│   ├── types/
│   │   └── index.ts          # 백엔드 models/schemas 기반 공통 타입
│   ├── lib/
│   │   ├── api-client.ts     # Axios 인스턴스 (envelope 언래핑 + 401 재발급)
│   │   └── utils.ts          # cn() 등 헬퍼
│   └── providers/
│       ├── QueryProvider.tsx # TanStack QueryClientProvider
│       └── index.tsx         # 최상위 Providers 컴포지션
├── tailwind.config.ts
├── next.config.ts
├── tsconfig.json
└── package.json
```

## 시작하기

### 1. 의존성 설치

```bash
cd frontend
npm install
```

(또는 `pnpm install` / `yarn`)

### 2. 환경변수 설정

```bash
cp .env.local.example .env.local
# NEXT_PUBLIC_API_BASE_URL 값을 백엔드 URL로 수정
```

### 3. 개발 서버

```bash
npm run dev
# → http://localhost:3000
```

## API 연동 규약

- 백엔드 응답 envelope `{ status, data, message }` 는 Axios 응답 인터셉터에서 자동으로 `data` 필드만 반환하도록 언래핑합니다.
- 호출부에서는 `apiClient.get<PolicyListItem[]>(...)` 형태로 제네릭만 지정하면 됩니다.
- 401 Unauthorized 응답 시 Refresh Token 으로 자동 재발급 후 원요청을 재시도합니다.
